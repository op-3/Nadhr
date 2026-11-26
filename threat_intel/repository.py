# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds a signed, static TUF repository of Nadhr threat lists.

Uses The Update Framework (python-tuf) rather than a custom format, so update
metadata is protected against tampering, rollback, freeze and mix-and-match
attacks by an established, reviewed standard. The output is plain static files
(consistent snapshots), so any web server, an enterprise mirror or a local
directory can host it.

Layout of a repository directory:
    metadata/<N>.root.json, metadata/<N>.targets.json, metadata/<N>.snapshot.json,
    metadata/timestamp.json, targets/<sha256>.<list name>.ntpl
"""

import datetime
import json
from pathlib import Path

from securesystemslib.signer import CryptoSigner
from tuf.api.metadata import (Metadata, MetaFile, Root, Snapshot, TargetFile, Targets,
                              Timestamp)
from tuf.api.serialization.json import JSONSerializer

ROLES = ('root', 'targets', 'snapshot', 'timestamp')
# Short timestamp expiry bounds how long a mirror can serve stale data
# unnoticed (freeze attack); longer-lived roles are re-signed on every publish.
EXPIRY = {'root': 365, 'targets': 30, 'snapshot': 7, 'timestamp': 2}
_SERIALIZER = JSONSerializer(compact=False)


def _expires(role, now):
    return now + datetime.timedelta(days=EXPIRY[role])


def generate_signers():
    """One Ed25519 signer per role. For tests and first-time setup only."""
    return {role: CryptoSigner.generate_ed25519() for role in ROLES}


def save_signers(signers, key_dir):
    """Writes private keys as PEM files. Keep root and targets keys offline."""
    key_dir.mkdir(parents=True, exist_ok=True)
    for role, signer in signers.items():
        path = key_dir / f'{role}.pem'
        path.write_bytes(signer.private_bytes)
        path.chmod(0o600)


def load_signers(key_dir):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    signers = {}
    for role in ROLES:
        key = load_pem_private_key((key_dir / f'{role}.pem').read_bytes(), password=None)
        signers[role] = CryptoSigner(key)
    return signers


class Repository:
    """A TUF repository on disk with one key (threshold 1) per role."""

    def __init__(self, path, signers):
        self.path = Path(path)
        self.meta_dir = self.path / 'metadata'
        self.targets_dir = self.path / 'targets'
        self.signers = signers

    def _write(self, md, versioned=True):
        name = f'{md.signed.version}.{md.signed.type}.json' if versioned else 'timestamp.json'
        (self.meta_dir / name).write_bytes(md.to_bytes(_SERIALIZER))

    def _sign(self, signed, role):
        md = Metadata(signed)
        md.sign(self.signers[role])
        return md

    def init(self, now=None):
        """Creates version 1 of every role. Returns the trusted root bytes to ship."""
        now = now or datetime.datetime.now(datetime.timezone.utc)
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self.targets_dir.mkdir(parents=True, exist_ok=True)
        root = Root(expires=_expires('root', now), consistent_snapshot=True)
        for role in ROLES:
            root.add_key(self.signers[role].public_key, role)
        self._write(self._sign(root, 'root'))
        self.publish({}, now=now, _first=True)
        return (self.meta_dir / '1.root.json').read_bytes()

    def _latest(self, role):
        versions = [int(p.name.split('.')[0]) for p in self.meta_dir.glob(f'*.{role}.json')]
        return Metadata.from_file(str(self.meta_dir / f'{max(versions)}.{role}.json'))

    def publish(self, lists, now=None, _first=False, attributions=None):
        """Publishes {name: ntpl_bytes} as the complete new set of lists.

        Also publishes the signed target index.json, which names the lists and
        carries each provider's attribution text for display in the browser.
        """
        now = now or datetime.datetime.now(datetime.timezone.utc)
        if _first:
            targets, snap_version, ts_version = Targets(expires=_expires('targets', now)), 1, 1
        else:
            prev_targets = self._latest('targets').signed
            targets = Targets(version=prev_targets.version + 1, expires=_expires('targets', now))
            snap_version = self._latest('snapshot').signed.version + 1
            ts_version = Metadata.from_file(
                str(self.meta_dir / 'timestamp.json')).signed.version + 1
        files = {f'{name}.ntpl': data for name, data in lists.items()}
        index = {'lists': sorted(files),
                 'attributions': {f'{n}.ntpl': t for n, t in (attributions or {}).items() if t}}
        files['index.json'] = json.dumps(index, indent=1, sort_keys=True).encode('utf-8')
        for target_path, data in sorted(files.items()):
            info = TargetFile.from_data(target_path, data, ['sha256'])
            targets.targets[target_path] = info
            (self.targets_dir / f'{info.hashes["sha256"]}.{target_path}').write_bytes(data)
        self._write(self._sign(targets, 'targets'))

        snapshot = Snapshot(version=snap_version, expires=_expires('snapshot', now),
                            meta={'targets.json': MetaFile(version=targets.version)})
        self._write(self._sign(snapshot, 'snapshot'))
        timestamp = Timestamp(version=ts_version, expires=_expires('timestamp', now),
                              snapshot_meta=MetaFile(version=snapshot.version))
        self._write(self._sign(timestamp, 'timestamp'), versioned=False)
        return targets.version

    def refresh_timestamp(self, now=None):
        """Re-signs timestamp only: proves the mirror is live without new lists."""
        now = now or datetime.datetime.now(datetime.timezone.utc)
        current = Metadata.from_file(str(self.meta_dir / 'timestamp.json')).signed
        timestamp = Timestamp(version=current.version + 1, expires=_expires('timestamp', now),
                              snapshot_meta=current.snapshot_meta)
        self._write(self._sign(timestamp, 'timestamp'), versioned=False)
