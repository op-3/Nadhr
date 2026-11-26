# Contributing to Nadhr

Thank you for helping. Please read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
first: Nadhr is a set of patches on top of ungoogled-chromium, not a copy of
the Chromium tree.

## Ground rules

- Never weaken Chromium's sandbox, Site Isolation, certificate verification or
  extension isolation, even for performance.
- No telemetry and no new network requests without documenting them in
  [docs/PRIVACY.md](docs/PRIVACY.md).
- Claims in docs and pull requests must be backed by something you actually
  ran: a build, a test, a measurement.

## Patches

- One concern per patch, with a header comment explaining why it exists.
- Generate patches against pristine files at the pinned Chromium tag
  (`diff -u` with `a/` and `b/` prefixes), and use LF line endings.
- Add the patch to `patches/series` and run:
  ```sh
  python devutils/validate_patches.py --remote
  ```
- Prefer new files plus small hooks over large edits to upstream files.

## Pull requests

- Keep each pull request focused. Describe what you changed, why, and how you
  verified it.
- CI (`validate`) must pass.
- Contributions are licensed under GPL-3.0-or-later.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
