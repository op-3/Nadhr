# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fetches pristine Chromium files from chromium.googlesource.com (gitiles)."""

import base64
import time
import urllib.error
import urllib.request
from pathlib import Path

_UC = (Path(__file__).resolve().parent.parent / 'upstream' / 'ungoogled-chromium-windows' /
       'ungoogled-chromium')
_BASE = 'https://chromium.googlesource.com/chromium/src'


def chromium_version():
    return (_UC / 'chromium_version.txt').read_text(encoding='utf-8').strip()


def _get(url):
    """GET with backoff: gitiles rate-limits bursts with HTTP 429/503."""
    for attempt in range(8):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == 7:
                raise
            retry_after = exc.headers.get('Retry-After', '')
            time.sleep(int(retry_after) if retry_after.isdigit() else min(2**attempt, 60))
    raise AssertionError('unreachable')


def fetch_file(rel, version=None):
    """Returns a file's bytes at the pinned tag, or None if it does not exist."""
    try:
        data = _get(f'{_BASE}/+/refs/tags/{version or chromium_version()}/{rel}?format=TEXT')
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    return base64.b64decode(data)


def fetch_archive(rel, version=None):
    """Returns a directory as .tar.gz bytes at the pinned tag."""
    return _get(f'{_BASE}/+archive/refs/tags/{version or chromium_version()}/{rel}.tar.gz')
