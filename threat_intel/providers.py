# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Threat-intelligence providers for the Nadhr mirror.

A provider turns one upstream feed into hostnames. Providers are replaceable:
adding, removing or licensing a new feed means editing providers.json, never the
browser. A mirror publishes (redistributes) the data, so a provider is used only
if its terms explicitly allow both commercial use and redistribution, recorded
with evidence; build.py refuses anything else.
"""

import dataclasses
import json
import re
import urllib.request
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / 'providers.json'
_USER_AGENT = 'Nadhr-threat-intel-mirror'


class ProviderNotPermitted(Exception):
    """A provider's recorded terms do not allow use by a Nadhr mirror."""


@dataclasses.dataclass(frozen=True)
class Provider:
    name: str
    title: str
    url: str
    format: str  # "domains" (one per line) or "hosts" ("0.0.0.0 domain")
    licence: str
    commercial_use: bool
    redistribution: bool
    evidence: str
    attribution: str = ''
    false_positive_url: str = ''
    enabled: bool = True

    def check_permitted(self):
        if not (self.commercial_use and self.redistribution and self.evidence):
            raise ProviderNotPermitted(
                f'{self.name}: terms must explicitly allow commercial use and redistribution '
                '(with recorded evidence) before a mirror may publish it')

    def parse(self, text):
        """Yields raw hostnames from the feed text (not yet canonicalised)."""
        for line in text.splitlines():
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            if self.format == 'domains':
                yield line
            elif self.format == 'hosts':
                parts = line.split()
                if len(parts) >= 2 and parts[0] in ('0.0.0.0', '127.0.0.1', '::'):
                    yield parts[1]
            else:
                raise ValueError(f'{self.name}: unknown format {self.format}')

    def fetch(self, timeout=120):
        request = urllib.request.Request(self.url, headers={'User-Agent': _USER_AGENT})
        if not self.url.startswith(('https://', 'file:')):
            raise ValueError(f'{self.name}: feeds must be fetched over HTTPS (or a local file)')
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')


def load_providers(path=CONFIG):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return [Provider(**entry) for entry in data['providers']]


class SuffixGuard:
    """Rejects entries that would block a whole platform or a never-block domain.

    An entry that is itself a public suffix (for example "github.io") would block
    every site under it, so it is dropped. Rules come from the Public Suffix
    List (MPL-2.0).
    """

    def __init__(self, psl_text, never_block=()):
        self.rules, self.wildcards = set(), set()
        for line in psl_text.splitlines():
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('!'):
                continue
            if line.startswith('*.'):
                self.wildcards.add(line[2:])
            else:
                self.rules.add(line.encode('idna').decode('ascii') if not line.isascii() else line)
        self.never_block = {d.lower() for d in never_block}

    def rejects(self, canonical):
        if canonical in self.rules or canonical in self.never_block:
            return True
        parent = canonical.split('.', 1)[1] if '.' in canonical else ''
        return parent in self.wildcards


def read_never_block(path):
    """One domain per line; '#' comments allowed."""
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    return [l.split('#', 1)[0].strip() for l in lines if re.sub(r'#.*', '', l).strip()]
