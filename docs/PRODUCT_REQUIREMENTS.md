# Product requirements

The condensed specification for Nadhr. A requirement is met only when it is
implemented **and** verified with recorded evidence in
[DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).

## Identity

- Name: Nadhr (Arabic: نظر), "Nadhr Browser". Tagline: *Fast by nature. Private by design.*
- English primary. Arabic first-class with full RTL mirroring, keeping URLs,
  code and identifiers left-to-right.
- Independent visual identity: no Chromium or Helium artwork.
- Windows, Linux and macOS.

## Foundation

- Built from ungoogled-chromium source. Chromium's sandbox, Site Isolation,
  process model, certificate verification and extension isolation are never
  weakened, including for performance.
- Nadhr changes are isolated patches on a pinned upstream, with a documented
  rebase process.

## Interface

- Three layouts, switchable live without restart or tab loss, from one shared
  UI implementation:
  - **Classic:** horizontal tabs, full toolbar, bookmarks bar.
  - **Modern** (default): collapsible vertical tab sidebar, workspaces,
    pinned tabs, tab groups, split view, side panels, left or right placement.
  - **Focus:** minimal chrome, auto-hiding toolbar, keyboard-driven.
- Light, dark and system themes; accent colours; reduced motion; keyboard
  navigation; high-DPI and multi-monitor support.
- Redesigned New Tab, Settings (including `nadhr://settings/appearance`),
  Privacy and Security, Downloads, History, Bookmarks, Profiles, Extensions,
  Permissions, Performance Center, About, onboarding, update and policy pages.

## Content blocking

- Full uBlock Origin built in and enabled by default (not uBlock Origin Lite).
  Custom lists, user rules, per-site controls, enterprise-managed rules.

## Performance

- Adaptive (default), Ultra Lightweight, Balanced and Performance modes. None
  of them disables security protections.
- Lazy and progressive session restore, memory-pressure-aware tab discarding
  that never discards tabs with audio, calls, downloads or unsaved forms,
  background throttling, low idle CPU.
- The UI stays responsive under heavy page load.
- Performance Center showing tab memory, process CPU, extensions, sleeping tabs
  and pressure.
- Benchmarks against Chrome, Edge, Helium and an ungoogled-chromium baseline on
  4, 8 and 16 GB machines, with published methodology. No targets are claimed
  without measurements.

## Privacy

- No telemetry, accounts, advertising IDs or tracking SDKs. Minimal external requests.
- Third-party cookie controls, partitioned storage, tracker blocking, tested
  anti-fingerprinting, DNS-over-HTTPS choice, HTTPS-First (HTTPS-Only optional),
  WebRTC IP controls, configurable search engines, private browsing (not marketed
  as anonymity).

## Security

- Phishing and malware URL protection with a privacy-conscious design.
- Secure downloads, extension installation, credential storage, WebAuthn and passkeys.
- Signed releases, verified update metadata with downgrade and replay protection.
- A vulnerability response process and a fast path for upstream security fixes.

## Enterprise and government

- Chromium policy infrastructure under the Nadhr namespace, mandatory and
  recommended, with clear precedence. Appearance or personal settings cannot
  bypass managed policy.
- ADMX templates, Linux policy files, macOS managed preferences, silent and
  offline installation, self-hosted updates, internal CAs, client certificates,
  smart cards, restricted networks.
- No employee monitoring by default. Documentation is clear about what a
  browser cannot enforce.

## Browsing features

Windows, tabs, groups, pinned and vertical tabs, workspaces (visual, not a
security boundary), split view, profiles, guest and private modes, history,
bookmarks with import/export, downloads with resume, PDF, permissions,
passwords, passkeys, autofill, extensions, WebRTC, Wasm, WebGL, WebGPU, media,
printing, spell check, privacy-respecting translation, PWAs, DevTools, Task
Manager, session and crash recovery, reader mode, find, zoom, notifications,
screen sharing, security keys, and a local command bar (Ctrl+K).

## Sync (optional)

- Off unless the user opts in. Self-hostable. Standard cryptography only.
- No end-to-end encryption claim before independent review.

## Release

- Installers per platform, signed where credentials exist, a secure updater,
  GitHub Releases, SBOM, licence compliance, and a CI test matrix run natively
  on every platform.
