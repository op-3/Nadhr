# Security policy

## Reporting a vulnerability

Please report vulnerabilities **privately** through GitHub: open this
repository's **Security** tab and choose **Report a vulnerability**. Do not
open a public issue.

Include the Nadhr version (`nadhr://version`), platform, steps to reproduce,
and the impact you expect.

We aim to acknowledge reports within 3 working days and to agree on a fix and
disclosure timeline with you.

## Scope

- **In scope:** Nadhr's own patches, build and packaging scripts, the updater
  (once it exists), and settings or defaults that Nadhr changes.
- **Chromium or ungoogled-chromium issues:** report them upstream
  ([Chromium](https://issues.chromium.org/),
  [ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium/security)).
  You are welcome to tell us as well, so we can ship the fix quickly.

## Supported versions

Nadhr is pre-alpha and has no supported release yet. Once releases exist, only
the latest release receives security fixes.

The security architecture is described in [docs/SECURITY.md](docs/SECURITY.md).
