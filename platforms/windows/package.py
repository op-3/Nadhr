#!/usr/bin/env python3
# Copyright 2018 The ungoogled-chromium Authors (original package.py, BSD-3-Clause)
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Packages a finished Windows build into an installer and a portable zip."""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UC = ROOT / 'upstream' / 'ungoogled-chromium-windows' / 'ungoogled-chromium'

sys.path.insert(0, str(UC / 'utils'))
import filescfg  # pylint: disable=wrong-import-position
from _common import ENCODING, get_chromium_version  # pylint: disable=wrong-import-position
sys.path.pop(0)

BUILD_OUTPUTS = ROOT / 'build' / 'src' / 'out' / 'Default'


def nadhr_version():
    """<chromium version>-<nadhr revision>, e.g. 158.0.8127.88-1."""
    revision = (ROOT / 'revision.txt').read_text(encoding=ENCODING).strip()
    return f'{get_chromium_version()}-{revision}'


def main():
    args_gn = (BUILD_OUTPUTS / 'args.gn').read_text(encoding=ENCODING)
    if 'target_cpu="x64"' not in args_gn:
        raise RuntimeError('Only x64 Windows builds are packaged at the moment')
    stem = f'nadhr_{nadhr_version()}_windows_x64'
    dist = ROOT / 'build' / 'dist'
    dist.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(BUILD_OUTPUTS / 'mini_installer.exe', dist / f'{stem}_installer.exe')

    timestamp = None
    lastchange = ROOT / 'build' / 'src' / 'build' / 'util' / 'LASTCHANGE.committime'
    if lastchange.exists():
        timestamp = int(lastchange.read_text(encoding=ENCODING))
    excluded = {Path('mini_installer.exe'), Path('mini_installer_exe_version.rc'),
                Path('setup.exe'), Path('chrome.packed.7z')}
    files = filescfg.filescfg_generator(
        ROOT / 'build' / 'src' / 'chrome' / 'tools' / 'build' / 'win' / 'FILES.cfg',
        BUILD_OUTPUTS, '64bit', excluded)
    filescfg.create_archive(files, tuple(), BUILD_OUTPUTS, dist / f'{stem}_portable.zip',
                            timestamp)
    print(f'Packages written to {dist}')


if __name__ == '__main__':
    main()
