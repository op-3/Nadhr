# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end tests of signed list updates, including attacks on the mirror.

Every failure case checks two things: the update is rejected, and the last
verified lists are still installed and still match (offline protection).
"""

import datetime
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from threat_intel import client, listformat  # pylint: disable=wrong-import-position
from threat_intel.repository import Repository, generate_signers  # pylint: disable=wrong-import-position

NOW = datetime.datetime.now(datetime.timezone.utc)


class UpdateTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = Repository(self.tmp / 'mirror', generate_signers())
        self.trusted_root = self.repo.init(now=NOW)
        self.mirror_url = (self.tmp / 'mirror').as_uri()
        self.install = self.tmp / 'profile' / 'ThreatProtection'

    def _publish(self, hosts, now=NOW):
        data, _ = listformat.encode(hosts)
        return self.repo.publish({'phishing': data}, now=now,
                                 attributions={'phishing': 'Test feed (CC0)'})

    def _update(self, url=None):
        return client.update(self.install, url or self.mirror_url, self.trusted_root)

    def _assert_still_protected(self, host='phish.example'):
        lists = client.load_installed(self.install)
        self.assertEqual(lists['phishing.ntpl'].match(host), host)

    def test_install_and_match(self):
        self._publish(['phish.example'])
        result = self._update()
        self.assertTrue(result.updated, result.error)
        self.assertEqual(result.lists, ('phishing.ntpl',))
        lists = client.load_installed(self.install)
        self.assertEqual(lists['phishing.ntpl'].match('login.phish.example'), 'phish.example')
        self.assertIsNone(lists['phishing.ntpl'].match('example.org'))
        state = client.installed_state(self.install)
        self.assertEqual(state['attributions'], {'phishing.ntpl': 'Test feed (CC0)'})

    def test_upgrade_replaces_lists(self):
        self._publish(['phish.example'])
        self._update()
        self._publish(['phish.example', 'new-phish.example'])
        result = self._update()
        self.assertTrue(result.updated, result.error)
        self._assert_still_protected('new-phish.example')
        self.assertEqual(len(list(self.install.glob('lists.*'))), 1)  # old set removed

    def test_tampered_list_is_rejected(self):
        self._publish(['phish.example'])
        self._update()
        version = self._publish(['phish.example', 'other.example'])
        target = next((self.tmp / 'mirror' / 'targets').glob('*.phishing.ntpl'))
        for path in (self.tmp / 'mirror' / 'targets').glob('*.phishing.ntpl'):
            forged, _ = listformat.encode(['phish.example'])  # attacker drops an entry
            path.write_bytes(forged)
        self.assertTrue(target.exists())
        result = self._update()
        self.assertFalse(result.updated)
        self.assertIn('Mismatch', result.error)
        self.assertLess(result.targets_version, version)
        self._assert_still_protected()

    def test_rollback_to_older_metadata_is_rejected(self):
        self._publish(['phish.example'])
        old = self.tmp / 'old-mirror'
        shutil.copytree(self.tmp / 'mirror', old)
        self._publish(['phish.example', 'second.example'])
        self.assertTrue(self._update().updated)
        result = self._update(old.as_uri())  # an attacker replays the older snapshot
        self.assertFalse(result.updated)
        self.assertIn('Version', result.error)
        self._assert_still_protected('second.example')

    def test_freeze_with_expired_metadata_is_rejected(self):
        self._publish(['phish.example'])
        self.assertTrue(self._update().updated)
        # The mirror keeps serving metadata signed long ago (now expired).
        self._publish(['phish.example', 'newer.example'],
                      now=NOW - datetime.timedelta(days=40))
        result = self._update()
        self.assertFalse(result.updated)
        self.assertIn('Expired', result.error)
        self._assert_still_protected()

    def test_repository_signed_with_other_keys_is_rejected(self):
        self._publish(['phish.example'])
        self.assertTrue(self._update().updated)
        evil = Repository(self.tmp / 'evil', generate_signers())
        evil.init(now=NOW)
        data, _ = listformat.encode(['harmless.example'])
        evil.publish({'phishing': data}, now=NOW)
        result = self._update((self.tmp / 'evil').as_uri())
        self.assertFalse(result.updated)
        self._assert_still_protected()

    def test_unreachable_mirror_keeps_last_good_lists(self):
        self._publish(['phish.example'])
        self.assertTrue(self._update().updated)
        result = self._update((self.tmp / 'nowhere').as_uri())
        self.assertFalse(result.updated)
        self._assert_still_protected()

    def test_no_lists_before_first_successful_update(self):
        result = self._update((self.tmp / 'nowhere').as_uri())
        self.assertFalse(result.updated)
        self.assertEqual(client.load_installed(self.install), {})


if __name__ == '__main__':
    unittest.main()
