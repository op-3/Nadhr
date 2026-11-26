#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validates the full Nadhr patch stack against pristine Chromium source.

Patches are applied in the same order as the real build:
ungoogled-chromium -> ungoogled-chromium-<platform> -> Nadhr.
Only the files Nadhr's patches touch are fetched (remote mode) or read from an
unmodified local tree; upstream patches touching the same files are applied
first, then Nadhr's, with `git apply`.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import gitiles

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
    files; upstream validates the rest of its own stack. Returns the set of
    files Nadhr's patches touch.
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
            # Submodule checkouts on Windows may have CRLF (core.autocrlf); the
            # patches are LF in git, and `git apply` is strict about it.
            target.write_bytes((layer / rel).read_bytes().replace(b'\r\n', b'\n'))
            series.append(f'{idx}/{rel}')
    (dest / 'series').write_text('\n'.join(series) + '\n', encoding='utf-8')
    print('Stack under test:\n  ' + '\n  '.join(series))
    return ours


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
        files = merge(LAYERS[args.platform], stack)
        series = read_series(stack)
        nadhr_prefix = f'{len(LAYERS[args.platform]) - 1}/'
        print(f'Validating {len(series)} patches on the {len(files)} files Nadhr touches...')
        for rel in sorted(files):
            if args.local:
                src = args.local / rel
                data = src.read_bytes() if src.is_file() else None
            else:
                data = gitiles.fetch_file(rel)
            if data is not None:  # absent files are ones a patch creates
                (tree / rel).parent.mkdir(parents=True, exist_ok=True)
                (tree / rel).write_bytes(data)
        failed = False
        for rel in series:
            # Upstream patches are applied only to the files Nadhr touches: that is
            # the state Nadhr's patches meet in the real build.
            include = [] if rel.startswith(nadhr_prefix) else [f'--include={f}' for f in files]
            res = subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--verbose',
                                  *include, str(stack / rel)],
                                 cwd=tree, capture_output=True, text=True, check=False)
            print(('OK    ' if res.returncode == 0 else 'FAIL  ') + rel)
            if res.returncode != 0:
                print(res.stderr, file=sys.stderr)
                failed = True
        return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
