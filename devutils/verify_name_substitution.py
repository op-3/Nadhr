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

import base64
import io
import re
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UC = ROOT / 'upstream' / 'ungoogled-chromium-windows' / 'ungoogled-chromium'
sys.path.insert(0, str(ROOT / 'utils'))
import name_substitution as ns  # pylint: disable=wrong-import-position

GRD = 'chrome/app/chromium_strings.grd'


def _url(version, rel, archive=False):
    kind = '+archive' if archive else '+'
    suffix = '.tar.gz' if archive else '?format=TEXT'
    return f'https://chromium.googlesource.com/chromium/src/{kind}/refs/tags/{version}/{rel}{suffix}'


def _fetch(version, rel, dest):
    for attempt in range(6):  # gitiles rate-limits bursts with HTTP 429/503
        try:
            with urllib.request.urlopen(_url(version, rel), timeout=120) as resp:
                data = base64.b64decode(resp.read())
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == 5:
                raise
            time.sleep(2 ** attempt)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def _translation_ids(xtb):
    return set(re.findall(r'<translation id="(\d+)"', xtb.read_text(encoding='utf-8')))


def main():
    version = (UC / 'chromium_version.txt').read_text(encoding='utf-8').strip()
    with tempfile.TemporaryDirectory(prefix='nadhr-names-') as tmp:
        tree = Path(tmp)
        with urllib.request.urlopen(_url(version, 'tools/grit', archive=True), timeout=300) as r:
            tarfile.open(fileobj=io.BytesIO(r.read())).extractall(tree / 'tools' / 'grit',
                                                                  filter='data')
        grd = tree / GRD
        _fetch(version, GRD, grd)
        grd_text = grd.read_text(encoding='utf-8')
        for part in re.findall(r'<part\s+file="([^"]+\.grdp)"', grd_text):
            _fetch(version, f'chrome/app/{part}', tree / 'chrome' / 'app' / part)
        xtbs = ns.xtb_files(grd, grd_text)
        for xtb, _ in xtbs:
            _fetch(version, xtb.relative_to(tree).as_posix(), xtb)

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

        print(f'{len(xtbs)} locales, {sum(counts.values())} translations checked')
        if failures:
            print('\n'.join(failures))
            return 1
        print('PASS: all translations preserved; English strings fully renamed')
        return 0


if __name__ == '__main__':
    sys.exit(main())
