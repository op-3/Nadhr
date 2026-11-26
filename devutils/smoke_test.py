#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Launch smoke test for a built Nadhr binary.

Runs the real browser headless and checks that it:
  1. starts, loads a page over HTTP and executes JavaScript (fresh profile),
  2. is branded Nadhr (Windows version resource),
  3. optionally, blocks ads with the built-in uBlock Origin (--expect-content-blocking),
  4. optionally, keeps its default profile in its own directory, separate from
     Chromium's (--check-default-profile; writes to %LOCALAPPDATA%, so only for
     disposable CI machines).
Prints a transcript to use as test evidence. Exits non-zero on any failure.
"""

import argparse
import http.server
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

JS_PAGE = (b'<!doctype html><title>pending</title>'
           b'<script>document.title = "nadhr-js-" + (6 * 7);</script>')

# The slow image keeps the load event (and so --dump-dom) open in real time.
# The late requests are made after uBlock Origin has had time to start; the
# banner path matches EasyList's generic "/banner_ads/*$~xmlhttprequest" rule,
# which ships inside the uBlock Origin package (works offline).
BLOCK_PAGE = (b'<!doctype html><title>blocking</title>'
              b'<script>setTimeout(function () {'
              b'  new Image().src = "/banner_ads/late.gif";'
              b'  new Image().src = "/ok/late.gif";'
              b'}, 8000);</script>'
              b'<img src="/slow.gif">')
SLOW_SECONDS = 12
GIF = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00'
       b'\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')


class _Handler(http.server.BaseHTTPRequestHandler):
    requested = []

    def do_GET(self):  # pylint: disable=invalid-name
        _Handler.requested.append(self.path)
        if self.path == '/block':
            body, ctype = BLOCK_PAGE, 'text/html'
        elif self.path.endswith('.gif'):
            if self.path == '/slow.gif':
                time.sleep(SLOW_SECONDS)
            body, ctype = GIF, 'image/gif'
        else:
            body, ctype = JS_PAGE, 'text/html'
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def dump_dom(browser, url, profile=None):
    cmd = [str(browser), '--headless', '--disable-gpu', '--no-first-run']
    if profile:
        cmd.append(f'--user-data-dir={profile}')
    cmd += ['--dump-dom', url]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    return res.returncode, res.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('browser', type=Path, help='Path to the browser executable')
    parser.add_argument('--expect-content-blocking', action='store_true',
                        help='Require the built-in uBlock Origin to block a known ad URL')
    parser.add_argument('--check-default-profile', action='store_true',
                        help='Launch with the default profile (CI only: writes to %%LOCALAPPDATA%%)')
    args = parser.parse_args()

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'

    checks = []
    with tempfile.TemporaryDirectory(prefix='nadhr-smoke-') as profile:
        code, dom = dump_dom(args.browser, base + '/', profile)
        checks.append(('page loads and runs JavaScript',
                       code == 0 and '<title>nadhr-js-42</title>' in dom, code))

        if args.expect_content_blocking:
            _Handler.requested.clear()
            code, _ = dump_dom(args.browser, base + '/block', profile)
            seen = list(_Handler.requested)
            print('--- requests seen by the test server ---\n' + '\n'.join(seen))
            control = '/ok/late.gif' in seen
            blocked = '/banner_ads/late.gif' not in seen
            checks.append(('late control request reached the server (test is conclusive)',
                           control, code))
            checks.append(('built-in uBlock Origin blocked /banner_ads/late.gif',
                           control and blocked, code))
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

        if args.check_default_profile:
            local = Path(os.environ['LOCALAPPDATA'])
            chromium_existed = (local / 'Chromium').exists()
            code, _ = dump_dom(args.browser, 'about:blank')
            nadhr_dir = local / 'Nadhr' / 'User Data'
            print(f'--- default profile ---\n{nadhr_dir} exists: {nadhr_dir.exists()}')
            checks.append(('default profile is in %LOCALAPPDATA%\\Nadhr\\User Data',
                           nadhr_dir.exists(), code))
            checks.append(('no Chromium profile directory was created',
                           chromium_existed or not (local / 'Chromium').exists(), code))

    for name, ok, code in checks:
        print(f'{"PASS" if ok else "FAIL"}  {name} (exit {code})')
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == '__main__':
    sys.exit(main())
