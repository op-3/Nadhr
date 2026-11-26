#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Replaces the user-visible product name "Chromium" with Nadhr's name.

Runs on a patched source tree before GN. Only GRIT string files are touched
(.grd/.grdp messages and their .xtb translations), never code or file names.

Changing a message's text changes its GRIT fingerprint, which is the ID its
translations are stored under. For every message whose text changes, the old
and new fingerprints are computed with GRIT's own code from the tree, and the
matching translations are re-keyed, so no translation is lost.

Inspired by the name-substitution approach in Helium (GPL-3.0); this is an
independent implementation.
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PRODUCT = 'Nadhr'
# Locales whose translations use the native product name.
# Arabic: نظر in logical (reading) order, NOON + ZAH + REH. Written as escapes so
# that no editor or terminal without bidi support can reorder it; the UI's bidi
# algorithm renders it right-to-left. Never store it visually reversed.
ARABIC_PRODUCT = 'نظر'
LOCALIZED_PRODUCT = {'ar': ARABIC_PRODUCT}

# Mentions that refer to the upstream project, not the product. They keep
# the name "Chromium".
_KEEP = re.compile(
    r'Chromium (?:Authors|OS|open source project|project|Web Store)'
    r'|ChromiumOS'
    # "...made possible by the <link>Chromium</link> open source project"
    r'|BEGIN_LINK_CHROMIUM"\s*(?:/>|>[^<]*</ph>)\s*Chromium')
# Not part of a path, URL or identifier; a following hyphen is allowed for
# compounds such as German "Chromium-Daten".
_NAME = re.compile(r'(?<![\w./-])Chromium(?!\w)')

SKIP_DIRS = {'out', 'testdata', 'test', 'tests', 'chromeos', 'ash', 'remoting', '.git'}
SEARCH_ROOTS = ('chrome', 'components', 'ui', 'extensions', 'content')


def replace_name(text, product=PRODUCT):
    """Replaces product mentions of Chromium, keeping upstream-project mentions."""
    out, pos = [], 0
    for keep in _KEEP.finditer(text):
        out.append(_NAME.sub(product, text[pos:keep.start()]))
        out.append(keep.group(0))
        pos = keep.end()
    out.append(_NAME.sub(product, text[pos:]))
    return ''.join(out)


def message_fingerprints(grd_text, tclib):
    """GRIT fingerprints of every <message> in a .grd/.grdp, in document order."""
    root = ET.fromstring(grd_text.encode('utf-8'))
    fps = []
    for msg in root.iter('message'):
        text = msg.text or ''
        for child in msg:
            if child.tag == 'ph':
                text += child.get('name').upper()
            text += child.tail or ''
        text = text.strip()
        # ''' marks preserved leading/trailing whitespace in GRIT.
        if text.startswith("'''"):
            text = text[3:]
        if text.endswith("'''"):
            text = text[:-3]
        fps.append(str(tclib.GenerateMessageId(text.strip(), msg.get('meaning', ''))))
    return fps


def xtb_files(grd_path, grd_text):
    """The .xtb translation files a .grd declares, with their language."""
    return [(grd_path.parent / m.group(1), m.group(2))
            for m in re.finditer(r'<file\s+path="([^"]+\.xtb)"\s+lang="([^"]+)"', grd_text)]


def substitute_xtb(xtb_path, lang, fp_map):
    """Re-keys translations of changed messages and renames the product in them."""
    text = xtb_path.read_text(encoding='utf-8')
    product = LOCALIZED_PRODUCT.get(lang.split('-')[0], PRODUCT)

    def rekey(match):
        new_id = fp_map.get(match.group(1))
        if new_id is None:
            return match.group(0)
        return f'<translation id="{new_id}"{replace_name(match.group(2), product)}</translation>'

    new_text = re.sub(r'<translation id="(\d+)"(.*?)</translation>', rekey, text, flags=re.S)
    if new_text == text:
        return False
    xtb_path.write_text(new_text, encoding='utf-8', newline='\n')
    return True


def substitute_file(path, tclib):
    """Renames the product in one .grd/.grdp. Returns {old fingerprint: new}, or None."""
    text = path.read_text(encoding='utf-8')
    new_text = replace_name(text)
    if new_text == text:
        return None
    old_fps = message_fingerprints(text, tclib)
    new_fps = message_fingerprints(new_text, tclib)
    assert len(old_fps) == len(new_fps), path
    path.write_text(new_text, encoding='utf-8', newline='\n')
    return {o: n for o, n in zip(old_fps, new_fps) if o != n}


def with_parts(grd_path):
    """A .grd plus every .grdp it includes, recursively (paths relative to the includer)."""
    files, queue = [], [grd_path]
    while queue:
        path = queue.pop()
        if path in files or not path.exists():
            continue
        files.append(path)
        text = path.read_text(encoding='utf-8')
        queue += [path.parent / p for p in re.findall(r'<part\s+file="([^"]+\.grdp)"', text)]
    return files


def substitute_grd(grd, tclib):
    """Processes one .grd with its parts and translations; returns files changed."""
    xtbs = xtb_files(grd, grd.read_text(encoding='utf-8'))
    changed, fp_map = 0, {}
    for path in with_parts(grd):
        file_map = substitute_file(path, tclib)
        if file_map is not None:
            changed += 1
            fp_map.update(file_map)
    if fp_map:
        changed += sum(substitute_xtb(x, lang, fp_map) for x, lang in xtbs if x.exists())
    return changed


def substitute_tree(tree):
    """Runs the substitution over a source tree; returns the number of files changed."""
    sys.path.insert(0, str(tree / 'tools' / 'grit'))
    from grit.extern import tclib  # pylint: disable=import-error,import-outside-toplevel
    changed = 0
    for root in SEARCH_ROOTS:
        for grd in sorted((tree / root).rglob('*.grd')):
            if not SKIP_DIRS.intersection(grd.relative_to(tree).parts):
                changed += substitute_grd(grd, tclib)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tree', type=Path, help='Patched Chromium source tree')
    args = parser.parse_args()
    print(f'Name substitution changed {substitute_tree(args.tree)} files')


if __name__ == '__main__':
    main()
