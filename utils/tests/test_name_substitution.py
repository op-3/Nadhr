# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline tests for utils/name_substitution.py.

Fingerprint fidelity against real GRIT and Chromium translations is verified
separately (see docs/TESTING.md); these tests pin down the text rules and the
translation re-keying.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import name_substitution as ns  # pylint: disable=wrong-import-position


class ReplaceNameTest(unittest.TestCase):

    def test_product_mentions_are_replaced(self):
        cases = {
            'Chromium is up to date': 'Nadhr is up to date',
            'Relaunch Chromium.': 'Relaunch Nadhr.',
            'Chromium-Daten löschen': 'Nadhr-Daten löschen',
            'Chromium and Chromium': 'Nadhr and Nadhr',
        }
        for src, want in cases.items():
            self.assertEqual(ns.replace_name(src), want)

    def test_upstream_project_mentions_are_kept(self):
        for text in ('Copyright 2026 The Chromium Authors.', 'Chromium OS needs an update',
                     'ChromiumOS', 'the Chromium open source project',
                     'https://www.chromium.org/', 'chrome/app/chromium_strings.grd',
                     'org.chromium.Chromium', 'ChromiumHTM'):
            self.assertEqual(ns.replace_name(text), text, text)

    def test_credit_link_is_kept_in_grd_and_xtb_forms(self):
        grd = ('made possible by the <ph name="BEGIN_LINK_CHROMIUM">&lt;a href="$1"&gt;</ph>'
               'Chromium<ph name="END_LINK_CHROMIUM">&lt;/a&gt;</ph> open source project')
        xtb = 'يعتمد على <ph name="BEGIN_LINK_CHROMIUM"/>Chromium<ph name="END_LINK_CHROMIUM"/>'
        self.assertEqual(ns.replace_name(grd), grd)
        self.assertEqual(ns.replace_name(xtb, 'نظر'), xtb)

    def test_localized_product_name(self):
        self.assertEqual(ns.replace_name('تحديث Chromium', 'نظر'), 'تحديث نظر')


class SubstituteXtbTest(unittest.TestCase):

    def test_only_changed_messages_are_rekeyed(self):
        xtb = ('<?xml version="1.0" ?>\n<translationbundle lang="ar">\n'
               '<translation id="111">تحديث Chromium</translation>\n'
               '<translation id="222">نظام التشغيل Chromium</translation>\n'
               '</translationbundle>\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'x_ar.xtb'
            path.write_text(xtb, encoding='utf-8')
            self.assertTrue(ns.substitute_xtb(path, 'ar', {'111': '999'}))
            out = path.read_text(encoding='utf-8')
        self.assertIn('<translation id="999">تحديث نظر</translation>', out)
        # Not in the map: its source message did not change, so it stays as is.
        self.assertIn('<translation id="222">نظام التشغيل Chromium</translation>', out)
        self.assertNotIn('id="111"', out)


if __name__ == '__main__':
    unittest.main()
