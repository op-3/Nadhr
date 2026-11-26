# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the mirror build pipeline: licence gates and false-positive guards."""

import dataclasses
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from threat_intel import build, listformat, providers  # pylint: disable=wrong-import-position

PSL = '// test PSL\ncom\ngithub.io\n*.ck\n!www.ck\n'
FEED = {
    'ok': 'phish.example\n# comment\nlogin.bank-secure.example\ngithub.io\nevil.github.io\n'
          'google.com\nx.ck\nnot a host\n',
    'hosts': '0.0.0.0 scam.example\n127.0.0.1 other.example # note\nfoo\n',
}


def _provider(name, **overrides):
    base = dict(name=name, title=name, url='https://feed.example/' + name, format='domains',
                licence='CC0', commercial_use=True, redistribution=True,
                evidence='https://feed.example/terms')
    base.update(overrides)
    return providers.Provider(**base)


class BuildTest(unittest.TestCase):

    def setUp(self):
        self.guard = providers.SuffixGuard(PSL, ['google.com'])

    def _build(self, provider_list):
        return build.build_lists(provider_list, self.guard, fetch=lambda p: FEED[p.name])

    def test_guards_drop_platforms_and_never_block_domains(self):
        lists, _, report = self._build([_provider('ok')])
        tl = listformat.ThreatList(lists['ok'])
        self.assertEqual(tl.match('phish.example'), 'phish.example')
        self.assertEqual(tl.match('evil.github.io'), 'evil.github.io')
        self.assertIsNone(tl.match('innocent.github.io'))  # "github.io" itself was dropped
        self.assertIsNone(tl.match('google.com'))
        self.assertIsNone(tl.match('x.ck'))  # wildcard public suffix
        self.assertEqual(len(tl), 3)
        self.assertIn('4 dropped', report[0])

    def test_hosts_format(self):
        lists, _, _ = self._build([_provider('hosts', format='hosts')])
        tl = listformat.ThreatList(lists['hosts'])
        self.assertEqual(tl.match('scam.example'), 'scam.example')
        self.assertEqual(tl.match('other.example'), 'other.example')
        self.assertEqual(len(tl), 2)

    def test_unpermitted_provider_stops_the_build(self):
        for field in ('commercial_use', 'redistribution'):
            with self.assertRaises(providers.ProviderNotPermitted, msg=field):
                self._build([_provider('ok', **{field: False})])
        with self.assertRaises(providers.ProviderNotPermitted):
            self._build([_provider('ok', evidence='')])

    def test_disabled_provider_is_skipped(self):
        lists, _, report = self._build([_provider('ok', enabled=False)])
        self.assertEqual(lists, {})
        self.assertEqual(report, ['ok: disabled'])

    def test_feeds_must_use_https(self):
        with self.assertRaises(ValueError):
            _provider('ok', url='http://feed.example/list').fetch()

    def test_shipped_provider_config_is_permitted(self):
        for provider in providers.load_providers():
            if provider.enabled:
                provider.check_permitted()
                self.assertTrue(provider.url.startswith('https://'), provider.name)
            self.assertTrue(provider.false_positive_url, provider.name)

    def test_never_block_file_parses(self):
        domains = providers.read_never_block(build.NEVER_BLOCK)
        self.assertIn('google.com', domains)
        self.assertTrue(all(listformat.canonical_host(d) == d for d in domains))
        self.assertTrue(dataclasses.is_dataclass(providers.Provider))


if __name__ == '__main__':
    unittest.main()
