# Development status

Last updated: 2026-11-26. This file lists only what has actually been done and
verified. It gives no completion percentages.

## Current stage

**Stage 1: environment and upstream foundation** (in progress).

## Done and verified

| Item | Evidence |
|---|---|
| Upstream baseline pinned (Chromium 158.0.8127.88, ungoogled-chromium 158.0.8127.88-1, ungoogled-chromium-windows 158.0.8127.88-1.1) | submodule commits in [ARCHITECTURE.md](ARCHITECTURE.md#baseline) |
| Nadhr patch layer and series | `patches/series` |
| Identity patches: product name, Windows install identity, policy namespace | `devutils/validate_patches.py --remote` applies all three cleanly to 158.0.8127.88. A negative test (corrupted context line) fails as expected. |
| No upstream patch touches the same files as Nadhr's patches | validator's "stack under test" output |
| Windows build driver adapted to the layered patch stack | `platforms/windows/build.py` (imports and argument parsing checked; a full build is **not yet run**) |
| CI: patch validation workflow, 16-stage Windows build workflow, Dependabot | `.github/`. `validate` passed on GitHub (run 45886591706). |
| Repository published at https://github.com/op-3/Nadhr. History audited before publishing (no credentials, keys or binaries; commit email set to the GitHub no-reply address). | 2026-11-26 |
| Launch smoke test script | `devutils/smoke_test.py`. Checked against Microsoft Edge as a control: page and JavaScript check passes, branding check correctly fails. |
| UI string branding with translation-safe fingerprint re-keying (English "Nadhr", Arabic "نظر") | `devutils/verify_name_substitution.py`: 81 locales, 68,607 translations, none lost. Negative control fails as expected. |

## In progress

- First full Windows CI build: run 45886835192, started 2026-11-26 from commit
  1a00986 (identity patches only, before name substitution).
  **No Nadhr binary exists yet.**

## Owner decisions

- 2026-11-26: full Chromium builds run on GitHub Actions only (free tier,
  no paid runners). No Visual Studio, Windows SDK or Chromium tree on the
  development laptop. Local work is limited to source changes, patch validation
  and lightweight tests.

## Not started

Everything else in [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md), including
layouts, uBlock Origin, the Adaptive Resource Engine, localization, updates,
Linux and macOS builds, sync, and all benchmarks.

## Development machine (2026-11-26)

- Windows 11 Pro, Intel Core i7-1265U (10 cores / 12 threads, 15 W), 31.6 GB RAM,
  about 142 GB free on C:.
- Present: Git, GitHub CLI, Python 3.15, Node 26.
- Missing for a native build: Visual Studio 2022 C++ workload, Windows SDK 10.0.28000.0.
- A full local official build is expected to take well over 12 hours on this CPU.
  The free GitHub-hosted staged build is the primary path for full builds. Local
  builds are for incremental development.
