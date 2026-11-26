# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests and shared vectors for the NTPL format. The C++ matcher must pass these."""

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from threat_intel import listformat as lf  # pylint: disable=wrong-import-position

# (input, canonical form or None). Shared with the browser's C++ implementation.
CANONICAL_VECTORS = [
    ('Example.COM', 'example.com'),
    ('example.com.', 'example.com'),
    ('  login.example.com ', 'login.example.com'),
    ('xn--mgbh0fb.xn--kgbechtv', 'xn--mgbh0fb.xn--kgbechtv'),
    ('مثال.إختبار', 'xn--mgbh0fb.xn--kgbechtv'),
    ('192.0.2.1', '192.0.2.1'),
    ('[2001:db8::1]', '2001:db8::1'),
    ('2001:0db8:0000::0001', '2001:db8::1'),
    ('com', None),
    ('', None),
    ('a..b', None),
    ('bad host.com', None),
    ('x' * 64 + '.com', None),
]
# SHA-256("example.com")[:8], computed independently of this module.
EXAMPLE_COM_HASH = 0xa379a6f6eeafb9a5


class CanonicalTest(unittest.TestCase):

    def test_vectors(self):
        for raw, want in CANONICAL_VECTORS:
            self.assertEqual(lf.canonical_host(raw), want, raw)

    def test_hash_vector(self):
        self.assertEqual(lf.host_hash('example.com'), EXAMPLE_COM_HASH)


class FormatTest(unittest.TestCase):

    def test_round_trip_and_matching(self):
        data, rejected = lf.encode(['phish.example', 'Bad.Example.org', '198.51.100.7', 'com',
                                    'phish.example'])
        self.assertEqual(rejected, ['com'])
        tl = lf.ThreatList(data)
        self.assertEqual(len(tl), 3)  # duplicates collapse
        self.assertEqual(tl.match('phish.example'), 'phish.example')
        self.assertEqual(tl.match('login.secure.phish.example'), 'phish.example')
        self.assertEqual(tl.match('bad.example.org'), 'bad.example.org')
        self.assertIsNone(tl.match('example.org'))  # parent of a listed host is not listed
        self.assertIsNone(tl.match('notphish.example'))  # no partial-label matches
        self.assertEqual(tl.match('198.51.100.7'), '198.51.100.7')
        self.assertIsNone(tl.match('7.198.51.100.7'))
        self.assertIsNone(tl.match('example'))

    def test_header_layout(self):
        data, _ = lf.encode(['example.com'])
        self.assertEqual(data, b'NTPL' + struct.pack('>HHI', 1, 0, 1) +
                         struct.pack('>Q', EXAMPLE_COM_HASH))

    def test_rejects_malformed_lists(self):
        good, _ = lf.encode(['a.example', 'b.example'])
        cases = {
            'truncated': good[:10],
            'magic': b'XXXX' + good[4:],
            'version': good[:4] + struct.pack('>H', 2) + good[6:],
            'count': good[:8] + struct.pack('>I', 3) + good[12:],
            'unsorted': good[:12] + good[20:28] + good[12:20],
            'duplicate': good[:12] + good[12:20] * 2,
        }
        for name, data in cases.items():
            with self.assertRaises(lf.ListFormatError, msg=name):
                lf.ThreatList(data)


if __name__ == '__main__':
    unittest.main()
