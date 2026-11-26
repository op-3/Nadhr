# Changelog

All notable changes are recorded here. Versions follow
`<chromium version>-<nadhr revision>` (see [docs/RELEASE.md](docs/RELEASE.md)).

## Unreleased

### Added

- Project foundation on Chromium 158.0.8127.88 / ungoogled-chromium
  158.0.8127.88-1 / ungoogled-chromium-windows 158.0.8127.88-1.1.
- Nadhr patch layer with identity patches: product name, Windows install
  identity, enterprise policy namespace (`Software\Policies\Nadhr`).
- Windows build and packaging scripts and a resumable 16-stage CI build.
- Patch validation against the pinned Chromium release, run in CI.
- Project documentation.
