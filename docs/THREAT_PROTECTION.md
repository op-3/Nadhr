# Threat protection (phishing and malicious domains)

Nadhr replaces the Safe Browsing service that ungoogled-chromium removes with
local, list-based protection. This is **not equivalent** to Google Safe
Browsing or Microsoft SmartScreen, and Nadhr must never describe it that way
(see [Limits](#limits)).

## Principles (owner decisions, 2026-11-27)

- On by default, using only sources whose terms explicitly allow personal,
  enterprise, government and commercial use. A mirror also needs redistribution
  rights.
- Matching is local. No visited URL or browsing history is ever sent to Nadhr
  or anyone else.
- Updates are authenticated and integrity-verified. If an update fails, the
  last verified lists keep protecting the user, offline too.
- Providers are replaceable without browser changes.
- No paid services, hosting or contracts without the owner's approval.
- No new background services.

## Architecture

```
 feeds (HTTPS) ──► mirror build (threat_intel/build.py)
                     • licence gate: commercial + redistribution explicitly allowed
                     • canonicalise hosts; drop public suffixes (PSL) and never-block domains
                     • encode NTPL lists; sign with TUF (python-tuf)
                   ──► static files: metadata/*.json + targets/<sha256>.<list>.ntpl
                         (any web server, enterprise intranet, or removable media)
 browser ◄── HTTPS or file:// ── updater (TUF client) ──► installed lists (profile dir)
   navigation ──► local lookup ──► warning page: Back to safety / Proceed / Report error
```

### Components

| Component | Where | Level |
|---|---|---|
| NTPL list format and host matching (reference) | `threat_intel/listformat.py` | 1. implemented, tested |
| Providers with recorded terms, licence gate | `threat_intel/providers.py`, `providers.json` | 1. implemented, tested |
| False-positive guards (PSL, never-block) | `threat_intel/providers.py`, `never_block.txt` | 1. implemented, tested |
| Signed static repository (TUF) | `threat_intel/repository.py` | 1. implemented, tested |
| Reference update client | `threat_intel/client.py` | 1. implemented, tested |
| Mirror CLI (init / publish / verify) | `threat_intel/build.py` | 1. implemented; real-data dry run |
| Browser list store, navigation check, warning page | Chromium patch (planned) | not started |
| Browser TUF updater | Chromium patch (planned) | not started |
| Enterprise policies | Chromium patch (planned) | not started |
| Public Nadhr mirror | not run (owner decision: no server yet) | n/a |

### List format and matching

[`listformat.py`](../threat_intel/listformat.py) is the reference.

- A list holds hostnames only, stored as 64-bit hashes in a sorted array.
- A host matches if it, or a parent domain with at least two labels, is listed.
- A listed IP matches only that exact IP.

The same test vectors in [`tests/test_listformat.py`](../threat_intel/tests/test_listformat.py)
apply to the C++ implementation.

### Signed updates

Updates use [The Update Framework](https://theupdateframework.io/) (python-tuf
7.0.1, Apache-2.0), with consistent snapshots, one Ed25519 key per role, and
expiry of root 365 days, targets 30, snapshot 7 and timestamp 2. The signed
target `index.json` names the lists and carries attribution text.

The reference client installs only verified lists that parse correctly, and
switches to them atomically. Tests cover each attack. In every case the
update is rejected and the last verified lists keep matching:

| Attack or failure | Rejected by |
|---|---|
| Tampered list file | target hash/length mismatch |
| Replay of older metadata (rollback) | version checks |
| Mirror serving expired metadata (freeze) | expiry check |
| Repository signed with other keys | root signature check |
| Mirror unreachable | lists kept |

The browser needs a C++ TUF client, which is new security-critical code.
Before it is enabled it must pass the official TUF conformance suite
(`theupdateframework/tuf-conformance`) as well as the tests above. Root and
targets keys must be kept offline; only timestamp and snapshot keys may live
on the machine that publishes.

## Sources (licence audit, 2026-11-27)

The full audit covered about 20 feeds. Each claim was checked against the
provider's published terms; the key ones were re-checked by hand.

**Default (permitted):**

| Feed | Terms | Coverage | Size |
|---|---|---|---|
| CERT Polska Warning List | "any purpose, including commercial purposes"; no endorsement may be implied | phishing, mainly targeting Poland | 127,469 hosts |
| Scam Blocklist by DurableNapkin | MIT; maintainer's own research | fake shops, global | 2,152 hosts |
| uBlock filters – Badware risks (via the bundled uBlock Origin, not the mirror) | GPL-3.0 | curated badware | n/a |

**Permitted but not enabled:** NetAPI compromised domains (CC BY 4.0). The
attribution link must be shown in the UI before it is enabled; most entries
come from CERT Polska anyway.

**Not usable without written permission:**

- URLhaus/ThreatFox (abuse.ch): commercial use "may require" a Spamhaus subscription.
- PhishStats: redistribution prohibited without permission. It is the strongest
  global candidate and is built from its own data.
- OpenPhish, PhishTank (registration closed), maltrail trails.
- Aggregators that inherit restricted upstreams: HaGeZi TIF, Phishing Army,
  IPFire DBL, jarelllama, Ultimate Hosts Blacklist.

## Limits

State these plainly in the product and to customers:

- **Global phishing coverage is inadequate today.** The permitted default set is
  strong only for phishing targeting Poland. It covers almost nothing aimed at
  Arabic-speaking or Gulf users. The audit found no openly licensed global
  phishing feed with clean provenance.
- There is no real-time lookup, so new phishing sites are caught only after a
  list includes them.
- There is no download reputation.
- Blocking is per domain, so phishing pages on shared hosting may not be blocked.

Until coverage improves, Nadhr must not claim parity with Safe Browsing or
SmartScreen, and must not call itself enterprise- or government-ready.

Paths to better coverage, none of which costs anything without approval:

1. Written permission from PhishStats or abuse.ch (drafts in
   [THREAT_PROTECTION_OUTREACH.md](THREAT_PROTECTION_OUTREACH.md), awaiting
   owner approval to send).
2. National CERTs in the Gulf and Arab region, if any publish openly licensed lists.
3. Feeds licensed by enterprise customers for their own mirrors.

## Measurements (real data, 2026-11-27)

These come from the dry run of `threat_intel.build` with the CERT Polska and
DurableNapkin feeds:

- 129,621 entries. Total list data is about 1.0 MB; as a packed array in memory
  it is 1.0 MB (the Python reference uses 5.8 MB).
- Build, sign and publish: about 4.6 s.
- Lookup per navigation (all lists, 4-label host): **40 µs in the Python
  reference**. This is the upper bound; the C++ binary search is expected to be
  far below it, to be measured once built.

## False positives

1. The mirror drops entries that are public suffixes (for example `github.io`)
   or on the never-block list. Subdomains on those platforms can still be blocked.
2. The warning page offers "Proceed" (an administrator can disable it by policy)
   and "Report an incorrect warning", which opens the matched list's own
   false-positive page (`false_positive_url`). Nadhr sends nothing automatically.
3. Users can add per-site exceptions; enterprises can add allowlists by policy.

## Browser integration plan

- The list store loads the installed lists from the profile directory as
  memory-mapped sorted arrays.
- A `NavigationThrottle` checks main-frame and subframe navigations and shows a
  security interstitial built on `components/security_interstitials`.
- The updater runs inside the browser process while the browser is open:
  first check after a startup delay, then every few hours. There is no
  OS-level service. It is off when the user or policy disables it.
- Planned policies: `NadhrThreatProtectionEnabled`,
  `NadhrThreatProtectionMirrorUrl` (enterprise mirror or `file://`),
  `NadhrThreatProtectionTrustedRoot` (enterprise-signed repositories),
  `NadhrThreatProtectionAllowlist`, `NadhrThreatProtectionAllowProceed`.
- The trusted root ships with the browser. The default mirror URL stays empty
  until a mirror exists.
