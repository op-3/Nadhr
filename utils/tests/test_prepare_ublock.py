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


if __name__ == '__main__':
    unittest.main()
