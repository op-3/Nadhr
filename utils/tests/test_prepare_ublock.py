# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for utils/prepare_ublock.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import prepare_ublock  # pylint: disable=wrong-import-position

# Chromium's PDF viewer: public key from chrome/browser/resources/pdf/manifest.json
# and its well-known extension ID. An independent check of the ID derivation.
PDF_KEY = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDN6hM0rsDYGbzQPQfOygqlRtQgKUXMfnSjhIBL7LnReAVBEd7ZmKtyN2qmSasMl4HZpMhVe2rPWVVwBDl6iyNE/Kok6E6v6V3vCLGsOpQAuuNVye/3QxzIldzG/jQAdWZiyXReRVapOhZtLjGfywCvlWq7Sl/e3sbc0vWybSDI2QIDAQAB'
PDF_ID = 'mhjfbmdgcfjbbpaeojofohoefgiehjai'


class ExtensionIdTest(unittest.TestCase):

    def test_matches_chromium_for_a_known_extension(self):
        self.assertEqual(prepare_ublock.extension_id(PDF_KEY), PDF_ID)

    def test_nadhr_key_gives_the_id_compiled_into_the_browser(self):
        key = prepare_ublock.KEY_FILE.read_text(encoding='utf-8').strip()
        self.assertEqual(prepare_ublock.extension_id(key), prepare_ublock.EXPECTED_ID)
        header = (prepare_ublock.ROOT / 'patches/nadhr/ublock/load-as-component.patch'
                  ).read_text(encoding='utf-8')
        self.assertIn(f'+    "{prepare_ublock.EXPECTED_ID}";', header)


class PrepareTest(unittest.TestCase):

    def _manifest(self, version):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name)
        (path / 'manifest.json').write_text(
            json.dumps({'manifest_version': version, 'name': 'uBlock Origin', 'version': '1.0'}),
            encoding='utf-8')
        return path

    def test_key_is_written(self):
        path = self._manifest(2)
        prepare_ublock.prepare(path)
        manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(prepare_ublock.extension_id(manifest['key']), prepare_ublock.EXPECTED_ID)

    def test_rejects_the_mv3_lite_build(self):
        with self.assertRaises(RuntimeError):
            prepare_ublock.prepare(self._manifest(3))


class DefaultListsTest(unittest.TestCase):

    POLICY = {'approved': {'good': {}, 'good-regional': {}},
              'off_pending_review': {'ambiguous': 'reason'}}

    def _run(self, assets):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name)
        (path / 'assets').mkdir()
        (path / 'assets' / 'assets.json').write_text(json.dumps(assets), encoding='utf-8')
        result = prepare_ublock.apply_default_lists(path, self.POLICY)
        return result, json.loads((path / 'assets' / 'assets.json').read_text(encoding='utf-8'))

    def test_only_approved_lists_stay_on(self):
        (enabled, disabled), out = self._run({
            'good': {'content': 'filters'},
            'good-regional': {'content': 'filters', 'off': True, 'lang': 'ar'},
            'ambiguous': {'content': 'filters'},
            'unreviewed-regional': {'content': 'filters', 'off': True, 'lang': 'de', 'ua': 'x'},
            'public-suffix': {'content': 'internal'},
        })
        self.assertNotIn('off', out['good'])
        self.assertEqual(out['good-regional']['lang'], 'ar')  # still auto-selected for Arabic
        self.assertTrue(out['ambiguous']['off'])
        self.assertTrue(out['unreviewed-regional']['off'])
        self.assertNotIn('lang', out['unreviewed-regional'])
        self.assertNotIn('ua', out['unreviewed-regional'])
        self.assertEqual(out['public-suffix'], {'content': 'internal'})
        self.assertEqual(enabled, ['good', 'good-regional'])
        self.assertEqual(disabled, ['ambiguous', 'unreviewed-regional'])

    def test_new_unreviewed_default_list_fails_the_build(self):
        with self.assertRaisesRegex(RuntimeError, 'has not been reviewed'):
            self._run({'good': {'content': 'filters'}, 'good-regional': {'content': 'filters'},
                       'brand-new': {'content': 'filters', 'title': 'New list'}})

    def test_renamed_approved_list_fails_the_build(self):
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            self._run({'good': {'content': 'filters'}})

    def test_repository_policy_is_consistent(self):
        policy = json.loads(prepare_ublock.LIST_POLICY_FILE.read_text(encoding='utf-8'))
        self.assertFalse(set(policy['approved']) & set(policy['off_pending_review']))
        for key, entry in policy['approved'].items():
            self.assertTrue(entry.get('licence') and entry.get('evidence'), key)


if __name__ == '__main__':
    unittest.main()
