#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds and signs a Nadhr threat-intelligence mirror (static files).

    python -m threat_intel.build init    --repo DIR --keys KEYDIR
    python -m threat_intel.build publish --repo DIR --keys KEYDIR --psl public_suffix_list.dat
    python -m threat_intel.build verify  --repo DIR --root DIR/metadata/1.root.json

Nothing here runs a server. The output directory can be copied to any web
server, an enterprise intranet, or removable media for offline networks.
Private keys never belong in the repository; keep root and targets keys offline.
"""

import argparse
import sys
import tempfile
from pathlib import Path

from threat_intel import client, listformat, providers
from threat_intel.repository import Repository, generate_signers, load_signers, save_signers

NEVER_BLOCK = Path(__file__).resolve().parent / 'never_block.txt'


def build_lists(provider_list, guard, fetch=None):
    """Returns ({name: ntpl_bytes}, {name: attribution}, report lines).

    Hosts are deduplicated across providers: a host already published by an
    earlier provider (in providers.json order) is not repeated, so memory and
    lookup cost grow only with distinct hosts. A provider that adds nothing new
    is not published at all.
    """
    lists, attributions, report = {}, {}, []
    seen = set()
    for provider in provider_list:
        if not provider.enabled:
            report.append(f'{provider.name}: disabled')
            continue
        provider.check_permitted()  # raises: never publish unpermitted data
        text = fetch(provider) if fetch else provider.fetch()
        hosts, dropped, duplicates = set(), 0, 0
        for raw in provider.parse(text):
            canonical = listformat.canonical_host(raw)
            if canonical is None or guard.rejects(canonical):
                dropped += 1
            elif canonical in seen:
                duplicates += 1
            else:
                hosts.add(canonical)
        seen |= hosts
        line = (f'{provider.name}: {len(hosts)} new hosts, {duplicates} already listed by '
                f'an earlier provider, {dropped} dropped (invalid, public suffix or never-block)')
        if hosts:
            data, _ = listformat.encode(hosts)
            lists[provider.name] = data
            attributions[provider.name] = provider.attribution
        else:
            line += '; nothing new, not published'
        report.append(line)
    return lists, attributions, report


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('init', 'publish', 'verify'))
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--keys', type=Path)
    parser.add_argument('--psl', type=Path, help='Public Suffix List file')
    parser.add_argument('--providers', type=Path, default=providers.CONFIG)
    parser.add_argument('--root', type=Path, help='Trusted root.json (verify)')
    args = parser.parse_args()

    if args.command == 'init':
        if (args.repo / 'metadata').exists():
            parser.error(f'{args.repo} already contains a repository')
        signers = generate_signers()
        save_signers(signers, args.keys)
        Repository(args.repo, signers).init()
        print(f'Repository created. Ship {args.repo}/metadata/1.root.json as the trusted '
              f'root; move {args.keys}/root.pem and targets.pem offline.')
    elif args.command == 'publish':
        guard = providers.SuffixGuard(args.psl.read_text(encoding='utf-8'),
                                      providers.read_never_block(NEVER_BLOCK))
        lists, attributions, report = build_lists(providers.load_providers(args.providers),
                                                  guard)
        version = Repository(args.repo, load_signers(args.keys)).publish(
            lists, attributions=attributions)
        print('\n'.join(report) + f'\nPublished targets version {version}')
    else:
        with tempfile.TemporaryDirectory() as tmp:
            result = client.update(Path(tmp), args.repo.resolve().as_uri(),
                                   args.root.read_bytes())
        print('OK' if result.updated else f'FAILED: {result.error}', result.lists)
        return 0 if result.updated else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
