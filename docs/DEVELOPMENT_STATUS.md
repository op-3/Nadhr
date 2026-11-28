# Development status

Last updated: 2026-11-28. This file lists only what has actually been done and
verified. It gives no completion percentages.

## Current stage

**Stage 1: environment and upstream foundation**: first Windows build done
(run 45891287269, 2026-11-27/28). Next: the uBlock branch build, then Stage 2.

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
| Product name and company (`BRANDING`) | 4. runtime-tested (Windows): the executable's version resource reads ProductName "Nadhr", CompanyName "The Nadhr Authors" (run 45891287269) | main |
| Windows install identity (user data dir, ProgIDs, registry, GUIDs) | 3. compiled. The default-profile check runs in the next build; the installer is not yet tested. | main |
| Policy namespace (`Software\Policies\Nadhr`, template names) | 3. compiled; policy enforcement not yet tested | main |
| UI string branding (Nadhr, Arabic نظر), translations preserved | 3. compiled (name substitution ran in the build). The UI text has not yet been seen in a running browser. | main |
| Launch smoke test (JS, branding, default profile, blocking) | JS and branding checks passed on the real build (run 45891287269). Default-profile and blocking checks first run in branch build 46136614194. | main |
| Built-in uBlock Origin: bundle, component load, restricted privileges, l10n | 2. patch-validated | PR #2 |
| uBlock Origin: enterprise managed configuration | 2. patch-validated | PR #2 |
| uBlock Origin: enterprise off switch (explicit ID block) | 2. patch-validated | PR #2 |
| uBlock Origin `redirect=empty` | no patch needed. Upstream code path read, not runtime-tested. | n/a |
| Threat protection mirror tooling: NTPL list format, licence-gated providers, PSL and never-block guards, TUF-signed static repository, reference client | 1. implemented and tested (20 tests, including tamper, rollback, freeze and foreign-key attacks). Real-data dry run: 130,935 distinct hosts from CERT Polska, DurableNapkin and NetAPI related-phishing (deduplicated), about 1.0 MB. | main (`threat_intel/`) |
| Threat protection in the browser (list store, navigation check, warning page, C++ TUF updater, policies) | not started. Design in docs/THREAT_PROTECTION.md. | n/a |
| Default filter lists limited to licence-approved ones | 1. implemented and tested | PR #2 |
| Global phishing coverage with permitted sources | **inadequate**: the permitted set is mainly Poland-targeted (see THREAT_PROTECTION.md, Limits) | n/a |
| Windows build pipeline (x64) | 4. working: run 45891287269 passed all 16 stages, packaging (installer + portable zip, 337 MB artifact) and the smoke test. Builds 1 and 2 had failed in stage 1 (clone path bug, fixed in bb201e9). | main |
| Layouts, performance engine, onboarding, updater, Linux, macOS | not started | n/a |

## Done and verified

| Item | Evidence |
|---|---|
| Upstream baseline pinned (Chromium 158.0.8127.88, ungoogled-chromium 158.0.8127.88-1, ungoogled-chromium-windows 158.0.8127.88-1.1) | submodule commits in [ARCHITECTURE.md](ARCHITECTURE.md#baseline) |
| Nadhr patch layer and series | `patches/series` |
| Identity patches: product name, Windows install identity, policy namespace | `devutils/validate_patches.py --remote` applies all three cleanly to 158.0.8127.88. A negative test (corrupted context line) fails as expected. |
| No upstream patch touches the same files as Nadhr's patches | validator's "stack under test" output |
| Windows build driver adapted to the layered patch stack | `platforms/windows/build.py`; full CI build succeeded (run 45891287269) |
| CI: patch validation workflow, 16-stage Windows build workflow, Dependabot | `.github/`. `validate` passed on GitHub (run 45886591706). |
| Repository published at https://github.com/op-3/Nadhr. History audited before publishing (no credentials, keys or binaries; commit email set to the GitHub no-reply address). | 2026-11-26 |
| Launch smoke test script | `devutils/smoke_test.py`. Checked against Microsoft Edge as a control: page and JavaScript check passes, branding check correctly fails. |
| UI string branding with translation-safe fingerprint re-keying (English "Nadhr", Arabic "نظر") | `devutils/verify_name_substitution.py`: 81 locales, 68,607 translations, none lost. Negative control fails as expected. |
| **First Nadhr build, launched** | Run 45891287269 (commit bb201e9): Chromium 158.0.8127.88 with ungoogled-chromium and Nadhr patches compiled in 16 CI stages and packaged. On a fresh Windows runner the packaged browser loaded a page over HTTP and ran JavaScript (PASS), and its executable reports ProductName "Nadhr" (PASS). Evidence: artifact `smoke-test-evidence`. |

## In progress

- uBlock Origin branch build (PR #2): run 46136614194 from 230a89a. It
  includes the smoke test's blocking and default-profile checks. PR #2 merges
  only if those pass.

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
