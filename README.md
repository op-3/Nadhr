# Nadhr Browser (نظر)

**Fast by nature. Private by design.**

Nadhr is an open-source desktop web browser built from source on
[ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium).
It keeps Chromium's engine, sandbox, Site Isolation and extension system, and
adds its own interface, built-in content blocking, adaptive resource management,
enterprise policy support, and first-class Arabic and English.

> **Status: pre-alpha. There is no released build yet.**
> The first Windows build pipeline is being brought up. See
> [docs/DEVELOPMENT_STATUS.md](docs/DEVELOPMENT_STATUS.md) for exactly what works
> today and [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for what does not.
> Nothing in this README describes a feature as available unless it is listed as
> done there.

## How it is built

Nadhr does not fork or vendor the Chromium tree. A build is:

1. Chromium **158.0.8127.88**, fetched at build time.
2. ungoogled-chromium's privacy patches (pinned submodule).
3. The platform layer from ungoogled-chromium-windows (pinned submodule).
4. Nadhr's own patches from [`patches/series`](patches/series), applied last.

This keeps every Nadhr change small, reviewable and rebasable onto new Chromium
security releases. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Building

See [docs/BUILDING.md](docs/BUILDING.md). In short, on Windows with Visual
Studio 2022 (C++ workload) and about 120 GB free disk space:

```powershell
git clone --recursive https://github.com/op-3/Nadhr.git
cd Nadhr
python -m pip install httplib2==0.22.0 clang==21.1.7
python platforms\windows\build.py
```

To check that Nadhr's patches still apply to the pinned Chromium release
without downloading it:

```sh
python devutils/validate_patches.py --remote
```

## Documentation

| Topic | Document |
|---|---|
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Requirements | [docs/PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md) |
| Status and roadmap | [docs/DEVELOPMENT_STATUS.md](docs/DEVELOPMENT_STATUS.md), [docs/ROADMAP.md](docs/ROADMAP.md) |
| Security model | [docs/SECURITY.md](docs/SECURITY.md) |
| Privacy | [docs/PRIVACY.md](docs/PRIVACY.md) |
| Performance | [docs/PERFORMANCE.md](docs/PERFORMANCE.md) |
| Enterprise | [docs/ENTERPRISE.md](docs/ENTERPRISE.md) |
| Updates | [docs/UPDATES.md](docs/UPDATES.md) |
| Testing | [docs/TESTING.md](docs/TESTING.md) |
| Releases | [docs/RELEASE.md](docs/RELEASE.md) |
| Upstream maintenance | [docs/UPSTREAM_MAINTENANCE.md](docs/UPSTREAM_MAINTENANCE.md) |

## License

Nadhr's own code and patches are licensed under the
[GNU General Public License v3.0 or later](LICENSE).
ungoogled-chromium is used under its [BSD-3-Clause license](LICENSE.ungoogled_chromium),
and Chromium under its own licenses (shown in the browser at `chrome://credits`).
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#licensing) for why GPL-3.0 was chosen.

Nadhr is an independent project. It is not affiliated with Google, the Chromium
project, the ungoogled-chromium project, or Helium.

## Reporting security issues

Please do not open public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).
