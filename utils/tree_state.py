# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Records how a patched source tree was made, and brings it up to date incrementally.

A full Chromium checkout takes many hours to prepare and compile. Development
builds instead restore the previous build tree and apply only what changed:

1. The state file (.nadhr-tree-state.json in the tree) lists every applied
   patch, in order, with its SHA-256 and the files it touches, plus hashes of
   the inputs that cannot be updated incrementally (upstream pins, downloads).
2. resync() finds the patches that were added, removed or changed, resets just
   their files to pristine upstream (git checkout in the file's own gclient
   repository, or deletion for files a patch created), then re-applies every
   patch hunk for those files in order. Unchanged files keep their timestamps,
   so ninja recompiles only what depends on the changed files.

If a base input changed, resync() refuses and asks for a full (seed) build.
"""

import hashlib
import json
import subprocess
from pathlib import Path

STATE_NAME = '.nadhr-tree-state.json'


class SeedRequired(Exception):
    """The tree cannot be updated incrementally; run a full build."""


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _normalized(path):
    # Windows checkouts may hold CRLF copies of LF patches; hash and apply LF.
    return Path(path).read_bytes().replace(b'\r\n', b'\n')


def touched_files(patch_bytes):
    """Paths a unified diff modifies or creates (from '+++ b/...' headers)."""
    out = []
    for line in patch_bytes.decode('utf-8', errors='replace').splitlines():
        if line.startswith('+++ '):
            path = line[4:].split('\t')[0].strip()
            if path != '/dev/null':
                out.append(path.removeprefix('b/'))
    return out


def _series(layer):
    lines = (Path(layer) / 'series').read_text(encoding='utf-8').splitlines()
    return [l.strip() for l in lines if l.strip() and not l.lstrip().startswith('#')]


def describe(layers, base_inputs):
    """State of a tree built from `layers` (ordered dirs with a series file).

    base_inputs: {name: path} of files whose change requires a full build.
    """
    patches = []
    for index, layer in enumerate(layers):
        for rel in _series(layer):
            data = _normalized(Path(layer) / rel)
            patches.append({'id': f'{index}/{rel}', 'sha256': _sha256(data),
                            'files': touched_files(data)})
    base = {name: _sha256(_normalized(path)) for name, path in sorted(base_inputs.items())}
    return {'format': 1, 'layers': len(layers), 'base': base, 'patches': patches}


def write_state(tree, state):
    (Path(tree) / STATE_NAME).write_text(json.dumps(state, indent=1), encoding='utf-8')


def read_state(tree):
    path = Path(tree) / STATE_NAME
    if not path.exists():
        raise SeedRequired(f'{path} not found: the tree was not made by a Nadhr build')
    return json.loads(path.read_text(encoding='utf-8'))


def plan(old, new):
    """Returns the set of files to reset and re-patch, or raises SeedRequired."""
    if old.get('format') != new['format']:
        raise SeedRequired('tree state format changed')
    changed_base = sorted(k for k in set(old['base']) | set(new['base'])
                          if old['base'].get(k) != new['base'].get(k))
    if changed_base:
        raise SeedRequired(f'base inputs changed: {", ".join(changed_base)}')
    old_by_id = {p['id']: p for p in old['patches']}
    new_by_id = {p['id']: p for p in new['patches']}
    files = set()
    for pid in set(old_by_id) | set(new_by_id):
        before, after = old_by_id.get(pid), new_by_id.get(pid)
        if before and after and before['sha256'] == after['sha256']:
            continue
        for patch in (before, after):
            if patch:
                files.update(patch['files'])
    # Only the last layer (Nadhr's) may change incrementally; upstream layers
    # change only with a base bump, which needs a seed build.
    if old.get('layers') != new['layers'] or _upstream(old) != _upstream(new):
        raise SeedRequired('upstream patch series changed')
    return files


def _upstream(state):
    """(id, sha256) of every patch outside the last (Nadhr) layer."""
    last = f'{state["layers"] - 1}/'
    return [(p['id'], p['sha256']) for p in state['patches'] if not p['id'].startswith(last)]


def _git_root(path, tree):
    """The nearest directory at or above `path` (inside `tree`) holding a .git."""
    current = path.parent
    tree = Path(tree).resolve()
    while True:
        if (current / '.git').exists():
            return current
        if current.resolve() == tree:
            return None
        current = current.parent


def _reset_file(tree, rel):
    path = Path(tree) / rel
    root = _git_root(path, tree)
    if root is not None:
        inner = path.resolve().relative_to(root.resolve()).as_posix()
        known = subprocess.run(['git', '-C', str(root), 'cat-file', '-e', f'HEAD:{inner}'],
                               capture_output=True, check=False).returncode == 0
        if known:
            subprocess.run(['git', '-C', str(root), '-c', 'core.autocrlf=false', 'checkout',
                            'HEAD', '--', inner], check=True, capture_output=True)
            return 'reset'
    if path.exists():
        path.unlink()  # created by a patch
        return 'deleted'
    return 'absent'


def resync(tree, layers, new_state):
    """Updates a previously built tree to `new_state`. Returns the re-patched files."""
    old_state = read_state(tree)
    files = plan(old_state, new_state)
    if not files:
        write_state(tree, new_state)
        return []
    for rel in sorted(files):
        _reset_file(tree, rel)
    for patch in new_state['patches']:
        targets = [f for f in patch['files'] if f in files]
        if not targets:
            continue
        index, rel = patch['id'].split('/', 1)
        data = _normalized(Path(layers[int(index)]) / rel)
        result = subprocess.run(
            ['git', '-c', 'core.autocrlf=false', 'apply', '-p1',
             *[f'--include={f}' for f in targets], '-'],
            cwd=tree, input=data, capture_output=True, check=False)
        if result.returncode != 0:
            raise SeedRequired(f'{patch["id"]} does not apply incrementally: '
                               f'{result.stderr.decode(errors="replace").strip()}')
    write_state(tree, new_state)
    return sorted(files)
