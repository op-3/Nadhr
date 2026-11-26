#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepares the downloaded uBlock Origin release for bundling.

Writes Nadhr's public key into third_party/ublock/manifest.json so the
component extension has the stable ID in components/nadhr/ublock_ids.h, and
checks that the ID derived from the key matches that header's value.

Only the public key exists: component extensions are never signed, so no
private key was kept.
"""

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / 'resources' / 'ublock' / 'manifest_key.txt'
EXPECTED_ID = 'mhmkochafbhohfaebfieaalahinnplkb'  # components/nadhr/ublock_ids.h


def extension_id(public_key_b64):
    """Chromium's extension ID: first 128 bits of SHA-256(key), as letters a-p."""
    digest = hashlib.sha256(base64.b64decode(public_key_b64)).hexdigest()[:32]
    return ''.join(chr(ord('a') + int(c, 16)) for c in digest)


def prepare(ublock_dir):
    key = KEY_FILE.read_text(encoding='utf-8').strip()
    if extension_id(key) != EXPECTED_ID:
        raise RuntimeError(f'{KEY_FILE} does not produce ID {EXPECTED_ID}')
    manifest_path = ublock_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('manifest_version') != 2:
        raise RuntimeError('Expected the Manifest V2 (full) build of uBlock Origin')
    manifest['key'] = key
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n',
                             encoding='utf-8', newline='\n')
    return manifest['version']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ublock_dir', type=Path, help='Path to third_party/ublock')
    args = parser.parse_args()
    print(f'uBlock Origin {prepare(args.ublock_dir)} prepared with ID {EXPECTED_ID}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
