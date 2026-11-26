# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Nadhr threat list format ("NTPL") and host matching.

This is the reference implementation; the browser's C++ matcher must produce
identical results (tests/test_listformat.py holds the shared test vectors).

A list holds hostnames only, never full URLs. Each canonical hostname is
stored as the first 8 bytes of its SHA-256, big-endian, in a sorted array:

    offset  size  field
    0       4     magic b"NTPL"
    4       2     format version (1), big-endian
    6       2     reserved, zero
    8       4     entry count N, big-endian
    12      8*N   sorted unique uint64 hashes, big-endian

200,000 domains take 1.6 MB, and a lookup is a binary search per candidate
host. With N entries the chance that an unlisted host collides is about
N / 2**64 (around 1e-14 for 200,000), which is negligible.

Matching: a host matches if it, or any parent domain with at least two labels,
is listed ("example.com" also covers "login.example.com"). Single labels
("com") are never looked up.
"""

import bisect
import hashlib
import ipaddress
import struct

MAGIC = b'NTPL'
VERSION = 1
_HEADER = struct.Struct('>4sHHI')
_MAX_HOST_LEN = 253


class ListFormatError(ValueError):
    """The data is not a valid NTPL list."""


def canonical_host(host):
    """Returns the canonical form of a hostname or IP literal, or None if invalid.

    Lowercase, trailing dot removed, IDN converted to punycode (IDNA 2003 as used
    by Python's codec; inputs from list providers are normally ASCII already).
    """
    host = host.strip().rstrip('.').lower()
    if host.startswith('[') and host.endswith(']'):
        host = host[1:-1]
    if not host or len(host) > _MAX_HOST_LEN:
        return None
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        pass
    try:
        host = host.encode('idna').decode('ascii')
    except UnicodeError:
        return None
    labels = host.split('.')
    if len(labels) < 2 or any(not l or len(l) > 63 for l in labels):
        return None
    if any(not all(c.isalnum() or c in '-_' for c in l) for l in labels):
        return None
    return host


def _is_ip(text):
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False


def host_hash(canonical):
    return int.from_bytes(hashlib.sha256(canonical.encode('ascii')).digest()[:8], 'big')


def encode(hosts):
    """Encodes hostnames into an NTPL list. Returns (bytes, rejected_inputs)."""
    hashes, rejected = set(), []
    for host in hosts:
        canonical = canonical_host(host)
        if canonical is None:
            rejected.append(host)
        else:
            hashes.add(host_hash(canonical))
    ordered = sorted(hashes)
    body = b''.join(struct.pack('>Q', h) for h in ordered)
    return _HEADER.pack(MAGIC, VERSION, 0, len(ordered)) + body, rejected


class ThreatList:
    """A decoded, validated NTPL list."""

    def __init__(self, data):
        if len(data) < _HEADER.size:
            raise ListFormatError('truncated header')
        magic, version, reserved, count = _HEADER.unpack_from(data)
        if magic != MAGIC or version != VERSION or reserved != 0:
            raise ListFormatError('bad magic, version or reserved field')
        if len(data) != _HEADER.size + 8 * count:
            raise ListFormatError('length does not match entry count')
        self._hashes = [h for (h,) in struct.iter_unpack('>Q', data[_HEADER.size:])]
        if any(a >= b for a, b in zip(self._hashes, self._hashes[1:])):
            raise ListFormatError('entries are not sorted and unique')

    def __len__(self):
        return len(self._hashes)

    def _contains(self, value):
        i = bisect.bisect_left(self._hashes, value)
        return i < len(self._hashes) and self._hashes[i] == value

    def match(self, host):
        """Returns the listed host or parent domain that matches, or None."""
        canonical = canonical_host(host)
        if canonical is None:
            return None
        try:
            ipaddress.ip_address(canonical)
            candidates = [canonical]
        except ValueError:
            labels = canonical.split('.')
            # A listed IP matches only that exact IP, never a hostname ending in it.
            candidates = [c for c in ('.'.join(labels[i:]) for i in range(len(labels) - 1))
                          if not _is_ip(c)]
        for candidate in candidates:
            if self._contains(host_hash(candidate)):
                return candidate
        return None
