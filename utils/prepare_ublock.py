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


LIST_POLICY_FILE = ROOT / 'resources' / 'ublock' / 'default_lists.json'


def apply_default_lists(ublock_dir, policy=None):
    """Enables by default only filter lists whose licence was reviewed and approved.

    uBlock Origin selects its defaults once, on first run, from assets.json: lists
    without "off", plus lists whose "lang"/"ua" match the environment. It then
    persists that selection, so later remote metadata cannot re-enable a list.
    Returns (enabled, disabled) asset keys.
    """
    policy = policy or json.loads(LIST_POLICY_FILE.read_text(encoding='utf-8'))
    approved, pending = policy['approved'], policy['excluded']
    assets_path = ublock_dir / 'assets' / 'assets.json'
    assets = json.loads(assets_path.read_text(encoding='utf-8'))

    missing = sorted(k for k in approved if k not in assets)
    if missing:
        raise RuntimeError(f'Approved lists missing from uBlock Origin (renamed?): {missing}')
    enabled, disabled = [], []
    for key, entry in assets.items():
        if entry.get('content') != 'filters' or key in approved:
            if key in approved and (entry.get('off') is not True or 'lang' in entry):
                enabled.append(key)
            continue
        default_on = entry.get('off') is not True
        if default_on and key not in pending:
            raise RuntimeError(
                f'uBlock Origin enables "{key}" ({entry.get("title")}) by default, but its licence '
                f'has not been reviewed. Add it to {LIST_POLICY_FILE.name}.')
        if default_on or 'lang' in entry or 'ua' in entry:
            disabled.append(key)
        entry['off'] = True
        entry.pop('lang', None)  # no automatic selection by browser language...
        entry.pop('ua', None)    # ...or user agent
    assets_path.write_text(json.dumps(assets, indent=1, ensure_ascii=False) + '\n',
                           encoding='utf-8', newline='\n')
    return sorted(enabled), sorted(disabled)


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
    enabled, disabled = apply_default_lists(args.ublock_dir)
    print(f'Default-eligible lists (licence approved): {", ".join(enabled)}')
    print(f'Off by default (licence not approved or not reviewed): {len(disabled)} lists')
    return 0


if __name__ == '__main__':
    sys.exit(main())
