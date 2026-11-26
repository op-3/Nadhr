# Security architecture

For reporting vulnerabilities, see the top-level [SECURITY.md](../SECURITY.md).

## Principles

- Chromium's sandbox, Site Isolation, process separation, certificate
  verification and extension isolation are kept as upstream ships them.
  No Nadhr feature or performance mode may disable them.
- Security claims need evidence. Nadhr makes no certification or compliance
  claim without independent evidence.

## Current state

Nadhr currently inherits ungoogled-chromium's security posture unchanged. The
only Nadhr changes are identity and policy-namespace patches. These change names,
paths and IDs, not security logic.

## Phishing and malware protection

ungoogled-chromium compiles out Safe Browsing (`safe_browsing_mode=0`) because
it contacts Google. Nadhr therefore has **no URL reputation protection today**.
This is a release-blocking gap.

Options to evaluate, documenting the privacy trade-off of each:

1. Bundled, regularly updated blocklists of malicious domains enforced locally
   (for example through the built-in content blocker). Nothing is sent per URL.
2. Safe Browsing's Update API (v4/v5 local hash-prefix databases), opt-in, so
   only hash prefixes of matching URLs are ever sent.
3. Both: local lists by default, hash-prefix lookups offered as an option.

## Manifest V2

Full uBlock Origin requires Manifest V2. ungoogled-chromium carries
`extensions-manifestv2.patch` to keep MV2 working as Chromium removes it.
Risks and mitigations:

- **Maintenance:** each Chromium release may remove more MV2 code. Nadhr tracks
  ungoogled-chromium's patch and tests uBlock Origin on every upstream bump.
- **Scope:** MV2 support for arbitrary extensions widens the attack surface
  that upstream no longer tests. Nadhr will evaluate restricting MV2 to the
  bundled uBlock Origin by default, with an enterprise policy to allow others.

## Credential storage

- Windows: DPAPI (on by default). ungoogled-chromium-windows adds an opt-in
  `--disable-encryption` switch for portable profiles. Nadhr does not enable it,
  and it will be blockable by policy.
- Linux: the system keyring (libsecret/KWallet) where available.
- macOS: Keychain.

## Release integrity

Planned: signed installers (Authenticode, Apple notarization), signed update
metadata, SHA-256 checksums and an SBOM published with every release. See
[UPDATES.md](UPDATES.md) and [RELEASE.md](RELEASE.md).

## Supply chain

- Upstream sources are pinned by commit. Build downloads are checksummed (SHA-512)
  in ungoogled-chromium's `downloads.ini` files.
- CI dependencies are locked (`package-lock.json`) and updated through Dependabot.
