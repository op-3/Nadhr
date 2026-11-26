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
it contacts Google. Today's Nadhr builds have **no URL reputation protection**.
This is a release-blocking gap.

### Research summary (2026-11-27)

Checked against source code and providers' published terms:

- **Re-enabling Chromium Safe Browsing is not a light option.** In
  `components/safe_browsing/buildflags.gni`, mode 0 is off, mode 1 is the full
  stack, and mode 2 is Android-only. Mode 1 brings back Google's hard-coded
  endpoints (`sb_protocol_manager_util.cc`), requires a Google API key, and the
  Safe Browsing API terms are non-commercial only. v4 is deprecated. Brave makes
  it private by running its own proxy, which still serves Google's data under
  Google's terms.
- **Microsoft SmartScreen** has no third-party API. **PhishTank** has closed new
  registrations. **OpenPhish**'s free feed forbids commercial use and
  redistribution. **Phishing.Database** has had no commit for about 8 weeks.
- **Usable sources** through the bundled uBlock Origin:
  - *uBlock filters – Badware risks*: GPLv3, curated, on by default.
  - *Online Malicious URL Blocklist*: malware, URLhaus-derived, updated twice a
    day, on by default.
  - *Phishing URL Blocklist*: phishing, off by default.
  - *CERT Polska Warning List*: commercial use explicitly allowed; focused on
    attacks targeting Poland.

  The defaults were confirmed in uBlock Origin 1.77.2's `assets/assets.json`.
  uBlock's strict blocking stops navigation to a listed domain with a warning
  page the user can click through.
- **DNS filtering** (for example Quad9 over DoH, which states that it does not
  log client IPs) works through Chromium's existing DoH settings and policies.

### Decision

1. **Default:** the bundled uBlock Origin with its malware and badware lists,
   evaluated locally. Nothing is sent per URL. Protection works offline until
   the lists expire.
2. **Optional:** a malware-filtering DoH resolver, offered in onboarding and
   settings. It is off by default because it routes DNS to a third party.
3. **Enterprise and government:** internal mirrors of the lists configured by
   policy (uBlock `adminSettings`, possible since
   `managed-storage-schema.patch`), internal RPZ/DoH filtering, and commercial
   feeds licensed by the organisation.

### What this does not provide

Say this plainly in product text and to customers:

- No real-time lookup. New phishing sites are covered only once a list includes
  them (lists update every few hours to 5 days).
- No download reputation, so malicious files on clean domains are not flagged.
- Blocking works per domain, so a phishing page on a shared hosting domain may
  not be blocked.
- No published false-positive rates exist for these lists.

Until this gap is reduced, for example by a signed Nadhr list service or a
licensed real-time source, Nadhr must not claim protection equivalent to Safe
Browsing or SmartScreen, and must not be described as enterprise- or
government-ready.

### Open decisions for the owner

- Whether to enable the *Phishing URL Blocklist* by default. It improves
  phishing coverage, but its upstream sources include OpenPhish, whose terms
  restrict redistribution. Nadhr would point uBlock at the list, not copy the
  data.
- URLhaus-derived data: abuse.ch's terms (21 Oct 2026) say commercial use may
  need a Spamhaus subscription. Free open-source use appears to be covered, but
  this needs written confirmation before any commercial distribution.
- A Nadhr-run, signed list mirror needs hosting, which costs money and needs approval.

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
