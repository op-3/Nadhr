# Architecture

## Baseline

| Component | Version | Pin |
|---|---|---|
| Chromium | 158.0.8127.88 | fetched at build time by ungoogled-chromium's `clone.py` |
| ungoogled-chromium | 158.0.8127.88-1 | commit `9746a5fe28e389b35ab1e2e2b258c802a8b4c117` (nested submodule) |
| ungoogled-chromium-windows | 158.0.8127.88-1.1 | commit `6661c751b20f9f8a75732e2818a430d6e7a30286` (`upstream/ungoogled-chromium-windows`) |
| Nadhr revision | 1 | [`revision.txt`](../revision.txt) |

Version strings are `<chromium version>-<nadhr revision>`, for example
`158.0.8127.88-1`.

The baseline was chosen on 2026-11-26: it is the current stable Chromium
release, and both ungoogled-chromium and Helium track it.

## Repository layout

```
patches/series            Nadhr patch order (applied after all upstream patches)
patches/nadhr/<area>/     Nadhr patches, grouped by area
platforms/windows/        Windows build and packaging scripts
upstream/                 pinned upstream submodules (never edited in place)
devutils/                 developer tools: patch validation
.github/                  CI: fast validation and the staged Windows build
docs/                     project documentation
```

The Chromium tree is never committed. `build/` is created by the build scripts
and ignored by git.

## Patch layers

Patches are applied in this order. A later layer may depend on an earlier one,
never the reverse.

1. **ungoogled-chromium** (`upstream/.../ungoogled-chromium/patches`):
   removes Google services, background requests and binaries, and keeps
   Manifest V2 extension support.
2. **Platform** (`upstream/ungoogled-chromium-windows/patches`): build fixes
   and Windows-specific privacy changes.
3. **Nadhr** (`patches/`): everything specific to this product.

Nadhr patch areas:

| Area | Purpose |
|---|---|
| `nadhr/branding` | product and company names (`BRANDING`) |
| `nadhr/policy` | enterprise policy namespace: registry key, template names, Linux policy path |
| `nadhr/windows` | Windows install identity: user data dir, ProgIDs, registry roots, COM/Active Setup IDs |

Rules for Nadhr patches:

- One concern per patch, with a header comment explaining why it exists.
- Prefer adding new files (for example under `chrome/browser/nadhr/`) over
  large edits to upstream files, so rebases touch as little as possible.
- Every patch must pass `devutils/validate_patches.py` against the pinned
  release before merge (enforced in CI).

## Planned components

These are design directions, not implemented features. Each will be recorded in
[DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) only when it is built and verified.

- **Layouts (Classic, Modern, Focus):** a single browser view tree whose
  tab strip, toolbar and side panel are configured by a layout preference,
  rather than three separate UI trees. Chromium already ships vertical tabs and
  side panels in Views; the layout layer selects and arranges them.
  Helium's `helium/ui/layout-*` patches are an engineering reference.
- **Content blocking:** full uBlock Origin (MV2) bundled as a component
  extension so it is present and updated with the browser. Helium does the same
  (`helium/core/ublock-*`). This depends on ungoogled-chromium keeping MV2
  support. See [SECURITY.md](SECURITY.md#manifest-v2) for the maintenance risk.
- **Adaptive Resource Engine:** built on Chromium's existing memory-pressure
  monitor, tab discarding/freezing and Memory Saver, with Nadhr policy on top.
  It is not a separate service. See [PERFORMANCE.md](PERFORMANCE.md).
- **Policy:** Chromium's policy stack, read from Nadhr's own namespace. Nadhr
  settings that need management are added as regular Chromium policies.
- **Updates:** see [UPDATES.md](UPDATES.md).

## Licensing

Nadhr's own code is **GPL-3.0-or-later**:

- uBlock Origin, which Nadhr will bundle, is GPL-3.0.
- Helium's patches, a useful reference, are GPL-3.0. Adapting any of them
  requires a GPL-3.0-compatible license.
- GPL-3.0 is compatible with ungoogled-chromium's BSD-3-Clause and with the
  permissive licenses of most of Chromium. Chromium's own third-party license
  inventory still applies to the combined binary and is shipped in it.

Files adapted from ungoogled-chromium keep their original copyright line and
note their BSD origin.

Helium is used only as an engineering reference. No Helium branding, artwork or
visual identity is used. Any code adapted from Helium must be credited in the
patch header.
