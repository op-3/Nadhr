# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference client: securely updates the locally installed threat lists.

The browser's C++ updater must behave like this (and pass the TUF conformance
suite). Behaviour:
- Metadata and lists are verified with python-tuf's ngclient, starting from a
  trusted root that ships with the browser (or is set by enterprise policy).
- Only verified lists that parse as NTPL are installed; installation is atomic.
- If an update fails for any reason (offline, tampered, rolled back, expired),
  the last verified lists stay installed and keep protecting the user. The
  status says why, so the UI can show "protection list out of date".
- Only the mirror sees the request (list metadata and files); no browsing data
  is ever sent.
"""

import dataclasses
import json
import os
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from tuf.api import exceptions as tuf_exceptions
from tuf.ngclient import FetcherInterface, Updater

from threat_intel import listformat


class LocalFileFetcher(FetcherInterface):
    """Fetches from file:// mirrors (offline media, network shares)."""

    def _fetch(self, url):
        path = Path(urllib.request.url2pathname(urllib.parse.urlparse(url).path))
        if not path.is_file():
            raise tuf_exceptions.DownloadHTTPError(f'{url} not found', 404)
        with open(path, 'rb') as f:
            while chunk := f.read(64 * 1024):
                yield chunk


@dataclasses.dataclass
class UpdateResult:
    updated: bool
    error: str = ''
    targets_version: int = 0
    lists: tuple = ()


def _targets_version(meta_dir):
    """Version of the targets metadata ngclient just verified and stored."""
    from tuf.api.metadata import Metadata  # pylint: disable=import-outside-toplevel
    return Metadata.from_file(str(meta_dir / 'targets.json')).signed.version


def _state_path(install_dir):
    return install_dir / 'state.json'


def installed_state(install_dir):
    try:
        return json.loads(_state_path(install_dir).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def update(install_dir, mirror_url, trusted_root):
    """Updates install_dir/lists/ from a mirror. Never removes the last good lists."""
    install_dir = Path(install_dir)
    meta_dir = install_dir / 'tuf'
    meta_dir.mkdir(parents=True, exist_ok=True)
    fetcher = LocalFileFetcher() if mirror_url.startswith('file:') else None
    base = mirror_url.rstrip('/')
    try:
        updater = Updater(metadata_dir=str(meta_dir), metadata_base_url=f'{base}/metadata/',
                          target_base_url=f'{base}/targets/', fetcher=fetcher,
                          bootstrap=trusted_root)
        updater.refresh()
        with tempfile.TemporaryDirectory(dir=install_dir) as staging:
            index_info = updater.get_targetinfo('index.json')
            if index_info is None:
                raise ValueError('mirror has no index.json')
            index_path = Path(staging) / 'index.json'
            updater.download_target(index_info, filepath=str(index_path))
            index = json.loads(index_path.read_text(encoding='utf-8'))
            names = []
            for target_path in index['lists']:
                info = updater.get_targetinfo(target_path)
                if info is None or not target_path.endswith('.ntpl') or '/' in target_path:
                    raise ValueError(f'index names an invalid list: {target_path!r}')
                local = Path(staging) / target_path
                updater.download_target(info, filepath=str(local))
                listformat.ThreatList(local.read_bytes())  # must be a valid list
                names.append(target_path)
            version = _targets_version(meta_dir)
            new_dir = install_dir / f'lists.{version}'
            if new_dir.exists():
                shutil.rmtree(new_dir)
            shutil.copytree(staging, new_dir)
        state = {'targets_version': version, 'lists_dir': new_dir.name, 'lists': names,
                 'attributions': index.get('attributions', {})}
        tmp = _state_path(install_dir).with_suffix('.tmp')
        tmp.write_text(json.dumps(state), encoding='utf-8')
        os.replace(tmp, _state_path(install_dir))  # atomic switch to the new set
        for old in install_dir.glob('lists.*'):
            if old.name != new_dir.name:
                shutil.rmtree(old, ignore_errors=True)
        return UpdateResult(True, targets_version=version, lists=tuple(names))
    except (tuf_exceptions.RepositoryError, tuf_exceptions.DownloadError,
            listformat.ListFormatError, OSError, ValueError) as exc:
        state = installed_state(install_dir)
        return UpdateResult(False, error=f'{type(exc).__name__}: {exc}',
                            targets_version=state.get('targets_version', 0),
                            lists=tuple(state.get('lists', ())))


def load_installed(install_dir):
    """Returns {name: ThreatList} for the last verified set (empty if none)."""
    install_dir = Path(install_dir)
    state = installed_state(install_dir)
    lists = {}
    for name in state.get('lists', ()):
        lists[name] = listformat.ThreatList(
            (install_dir / state['lists_dir'] / name).read_bytes())
    return lists
