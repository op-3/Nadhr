#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Proves that name substitution keeps every translation, on real Chromium data.

Fetches GRIT and chrome/app/chromium_strings.grd (with its .grdp parts and all
of its .xtb translations) at the pinned Chromium tag, then checks:
  1. our fingerprint computation matches every translation ID Chromium ships,
  2. after substitution, every translation still matches a message, and
  3. no product mention of Chromium is left in the English strings.
Downloads about 10 MB into a temporary directory.
"""

import io
import re
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'utils'))
import name_substitution as ns  # pylint: disable=wrong-import-position
import gitiles  # pylint: disable=wrong-import-position

GRD = 'chrome/app/chromium_strings.grd'


def _fetch(rel, dest):
    data = gitiles.fetch_file(rel)
    if data is None:
        raise FileNotFoundError(rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def _translation_ids(xtb):
    return set(re.findall(r'<translation id="(\d+)"', xtb.read_text(encoding='utf-8')))


def main():
    with tempfile.TemporaryDirectory(prefix='nadhr-names-') as tmp:
        tree = Path(tmp)
        tarfile.open(fileobj=io.BytesIO(gitiles.fetch_archive('tools/grit'))).extractall(
            tree / 'tools' / 'grit', filter='data')
        grd = tree / GRD
        _fetch(GRD, grd)
        grd_text = grd.read_text(encoding='utf-8')
        for part in re.findall(r'<part\s+file="([^"]+\.grdp)"', grd_text):
            _fetch(f'chrome/app/{part}', tree / 'chrome' / 'app' / part)
        xtbs = ns.xtb_files(grd, grd_text)
        for xtb, _ in xtbs:
            _fetch(xtb.relative_to(tree).as_posix(), xtb)

        sys.path.insert(0, str(tree / 'tools' / 'grit'))
        from grit.extern import tclib  # pylint: disable=import-error,import-outside-toplevel

        def fingerprints():
            return set().union(*(ns.message_fingerprints(p.read_text(encoding='utf-8'), tclib)
                                 for p in ns.with_parts(grd)))

        failures = []
        before = fingerprints()
        counts = {}
        for xtb, lang in xtbs:
            ids = _translation_ids(xtb)
            counts[lang] = len(ids)
            if not ids <= before:
                failures.append(f'{lang}: {len(ids - before)} translation IDs do not match '
                                'computed fingerprints before substitution')

        ns.substitute_grd(grd, tclib)
        after = fingerprints()
        for xtb, lang in xtbs:
            ids = _translation_ids(xtb)
            if len(ids) != counts[lang] or not ids <= after:
                failures.append(f'{lang}: {len(ids - after)} translations lost after substitution')

        leftovers = [m for p in ns.with_parts(grd)
                     for m in re.findall(r'.{0,30}\bChromium\b.{0,30}', p.read_text(encoding='utf-8'))
                     if ns.replace_name(m) != m]
        failures += [f'product mention left: {m.strip()}' for m in leftovers]

        # Arabic: the native name, in logical order, and never the Latin name.
        ar_xtb = next(x for x, lang in xtbs if lang == 'ar')
        ar_text = ar_xtb.read_text(encoding='utf-8')
        ar_hits = ar_text.count(ns.ARABIC_PRODUCT)
        reversed_name = ns.ARABIC_PRODUCT[::-1]
        if ar_hits == 0:
            failures.append('ar: Arabic product name not found in translations')
        if reversed_name in ar_text:
            failures.append('ar: visually reversed product name found')
        if ns.PRODUCT in ar_text:
            failures.append('ar: Latin product name used instead of the Arabic one')
        print(f'ar: {ar_hits} occurrences of U+0646 U+0638 U+0631 (logical order); '
              f'reversed sequence: {ar_text.count(reversed_name)}')

        print(f'{len(xtbs)} locales, {sum(counts.values())} translations checked')
        if failures:
            print('\n'.join(failures))
            return 1
        print('PASS: all translations preserved; English strings fully renamed')
        return 0


if __name__ == '__main__':
    sys.exit(main())
