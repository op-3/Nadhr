# Development status

Last updated: 2026-11-27. This file lists only what has actually been done and
verified. It gives no completion percentages.

## Current stage

**Stage 1: environment and upstream foundation** (in progress). There is no
verified build yet.

## Verification levels

Each feature is at exactly one level. It moves up only with recorded evidence.

1. **Implemented:** code or patch written.
2. **Patch-validated:** applies to the pinned Chromium release with the
   upstream patches (`validate_patches.py --remote`, CI).
3. **Compiled:** built successfully in CI.
4. **Runtime-tested:** observed working in a running Nadhr build (smoke test or
   recorded manual test).
5. **Production-verified:** runtime-tested on every supported platform and
   covered by release checks.

| Feature | Level | Where |
|---|---|---|
| Product name and company (`BRANDING`) | 2. patch-validated | main |
| Windows install identity (user data dir, ProgIDs, registry, GUIDs) | 2. patch-validated | main |
| Policy namespace (`Software\Policies\Nadhr`, template names) | 2. patch-validated | main |
| UI string branding (Nadhr, Arabic نظر), translations preserved | 2. patch-validated. Verified on real strings, not seen in a build. | main |
| Launch smoke test (JS, branding, default profile, blocking) | 1. implemented; controls run against Edge | main |
| Built-in uBlock Origin: bundle, component load, restricted privileges, l10n | 2. patch-validated | PR #2 |
| uBlock Origin: enterprise managed configuration | 2. patch-validated | PR #2 |
| uBlock Origin: enterprise off switch (explicit ID block) | 2. patch-validated | PR #2 |
| uBlock Origin `redirect=empty` | no patch needed. Upstream code path read, not runtime-tested. | n/a |
| Phishing/malware protection | design decided (docs/SECURITY.md). Malware lists come with uBlock; real-time and download protection: none. | PR #2 |
| Windows build pipeline | 1. implemented. Builds 1 and 2 failed in stage 1 (clone path bug, fixed); build 3 in progress. | main |
| Layouts, performance engine, onboarding, updater, Linux, macOS | not started | n/a |

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
