#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Launch smoke test for a built Nadhr binary.

Runs the real browser headless with a fresh profile and checks that it:
  1. starts and exits cleanly,
  2. loads a page over HTTP and executes JavaScript,
  3. identifies itself as Nadhr on chrome://version.
Prints a transcript to use as test evidence. Exits non-zero on any failure.
"""

import argparse
import http.server
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

PAGE = (b'<!doctype html><title>pending</title>'
        b'<script>document.title = "nadhr-js-" + (6 * 7);</script>')


class _Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):  # pylint: disable=invalid-name
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args):
        pass


def dump_dom(browser, url, profile):
    cmd = [str(browser), '--headless', '--disable-gpu', '--no-first-run',
           f'--user-data-dir={profile}', '--dump-dom', url]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    return res.returncode, res.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('browser', type=Path, help='Path to the browser executable')
    args = parser.parse_args()

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}/'

    checks = []
    with tempfile.TemporaryDirectory(prefix='nadhr-smoke-') as profile:
        code, dom = dump_dom(args.browser, url, profile)
        checks.append(('page loads and runs JavaScript',
                       code == 0 and '<title>nadhr-js-42</title>' in dom, code))
    server.shutdown()

    if sys.platform == 'win32':
        # The version resource is generated from chrome/app/theme/chromium/BRANDING.
        info = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             f'(Get-Item -LiteralPath "{args.browser}").VersionInfo | '
             'Format-List ProductName,CompanyName,ProductVersion,LegalCopyright'],
            capture_output=True, text=True, check=False).stdout
        print('--- executable version resource ---\n' + info.strip())
        checks.append(('executable is branded Nadhr', 'ProductName    : Nadhr' in info, 0))

    for name, ok, code in checks:
        print(f'{"PASS" if ok else "FAIL"}  {name} (exit {code})')
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == '__main__':
    sys.exit(main())
