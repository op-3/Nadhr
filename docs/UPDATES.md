# Updates

**Not implemented yet.** ungoogled-chromium disables Chromium's auto-update,
so a Nadhr build today does not update itself.

## Requirements

- Signed update metadata and packages, verified before installation.
- Protection against downgrade, replay and freeze attacks (stale metadata).
- Release channels (stable, beta), staged rollout, failure recovery.
- Enterprise control: disable, defer, pin a version, point at an internal
  server, offline update packages.
- No identifier in update requests beyond what is needed (version, platform,
  architecture, channel).

## Candidate mechanisms (to evaluate, not decided)

| Platform | Candidate | Notes |
|---|---|---|
| Windows | WinSparkle (EdDSA-signed appcasts) | Mature. Helium uses it on Windows (`helium-windows/patches/helium/windows/updater`). |
| macOS | Sparkle 2 | The standard for non-App-Store apps. EdDSA signatures, sandboxed installer. |
| Linux | distribution repositories (apt/dnf) with signed metadata; AppImage with zsync | Packages update through the system package manager. |
| all | TUF-style metadata on top | Adds expiry and versioning to defeat replay, freeze and downgrade attacks, which appcast signatures alone do not fully cover. |

The decision will be recorded here with its reasoning before implementation.

## Emergency security releases

1. Upstream security fix lands in a Chromium stable release.
2. Bump ungoogled-chromium and its platform repository (they usually follow
   within days), run `devutils/validate_patches.py --remote`, fix any rejected
   Nadhr patches.
3. CI build, smoke test, sign, publish. Process details are in
   [UPSTREAM_MAINTENANCE.md](UPSTREAM_MAINTENANCE.md) and [RELEASE.md](RELEASE.md).
