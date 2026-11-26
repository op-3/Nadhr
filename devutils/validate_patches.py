#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validates the full Nadhr patch stack against pristine Chromium source.

Patches are applied in the same order as the real build:
ungoogled-chromium -> ungoogled-chromium-<platform> -> Nadhr.
The stack is merged into a temporary directory and checked with
ungoogled-chromium's own validator, which fetches only the files the patches
touch (remote mode) or reads them from an unmodified local tree.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UC_WIN = ROOT / 'upstream' / 'ungoogled-chromium-windows'
UC = UC_WIN / 'ungoogled-chromium'

LAYERS = {
    'windows': [UC / 'patches', UC_WIN / 'patches', ROOT / 'patches'],
}


def read_series(patch_dir):
    lines = (patch_dir / 'series').read_text(encoding='utf-8').splitlines()
    return [l.strip() for l in lines if l.strip() and not l.lstrip().startswith('#')]


def check_series_consistency(patch_dir):
    """Every listed patch exists and every Nadhr patch file is listed."""
    listed = read_series(patch_dir)
    errors = [f'listed but missing: {p}' for p in listed if not (patch_dir / p).is_file()]
    on_disk = {p.relative_to(patch_dir).as_posix() for p in patch_dir.rglob('*.patch')}
    errors += [f'not in series: {p}' for p in sorted(on_disk - set(listed))]
    if len(listed) != len(set(listed)):
        errors.append('series lists a patch more than once')
    return errors


def touched_files(patch_path):
    """Paths a unified diff modifies (from its '+++ b/...' headers)."""
    out = set()
    for line in patch_path.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('+++ '):
            out.add(line[4:].split('\t')[0].strip().removeprefix('b/'))
    return out


def merge(layers, dest):
    """Merges the stack, keeping only upstream patches that share a file with Nadhr's.

    Nadhr's patches can only conflict with upstream patches touching the same
    files; upstream validates the rest of its own stack.
    """
    nadhr = layers[-1]
    ours = set().union(*(touched_files(nadhr / p) for p in read_series(nadhr)))
    series = []
    for idx, layer in enumerate(layers):
        for rel in read_series(layer):
            if layer is not nadhr and not touched_files(layer / rel) & ours:
                continue
            target = dest / f'{idx}' / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(layer / rel, target)
            series.append(f'{idx}/{rel}')
    (dest / 'series').write_text('\n'.join(series) + '\n', encoding='utf-8')
    print('Stack under test:\n  ' + '\n  '.join(series))
    return len(series)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=sorted(LAYERS), default='windows')
    src = parser.add_mutually_exclusive_group()
    src.add_argument('-r', '--remote', action='store_true',
                     help='Fetch required files from chromium.googlesource.com')
    src.add_argument('-l', '--local', type=Path, help='Unmodified local Chromium tree')
    args = parser.parse_args()

    errors = check_series_consistency(ROOT / 'patches')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Nadhr series is consistent.')
    if not (args.remote or args.local):
        return 0

    with tempfile.TemporaryDirectory(prefix='nadhr-patches-') as tmp:
        stack, tree = Path(tmp) / 'stack', Path(tmp) / 'tree'
        count = merge(LAYERS[args.platform], stack)
        series = read_series(stack)
        files = set().union(*(touched_files(stack / p) for p in series))
        print(f'Validating {count} patches touching {len(files)} files...')
        for rel in sorted(files):
            if args.local:
                src = args.local / rel
                data = src.read_bytes() if src.is_file() else None
            else:
                data = fetch_upstream(rel)
            if data is not None:  # absent files are ones a patch creates
                (tree / rel).parent.mkdir(parents=True, exist_ok=True)
                (tree / rel).write_bytes(data)
        failed = False
        for rel in series:
            res = subprocess.run(['git', 'apply', '--verbose', str(stack / rel)],
                                 cwd=tree, capture_output=True, text=True, check=False)
            print(('OK    ' if res.returncode == 0 else 'FAIL  ') + rel)
            if res.returncode != 0:
                print(res.stderr, file=sys.stderr)
                failed = True
        return 1 if failed else 0


def fetch_upstream(rel):
    """Returns a file from chromium/src at the pinned version, or None if absent."""
    import base64
    import urllib.error
    import urllib.request
    version = (UC / 'chromium_version.txt').read_text(encoding='utf-8').strip()
    url = (f'https://chromium.googlesource.com/chromium/src/+/refs/tags/{version}/'
           f'{rel}?format=TEXT')
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return base64.b64decode(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


if __name__ == '__main__':
    sys.exit(main())
