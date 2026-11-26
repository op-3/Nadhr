# Privacy

## Commitments

- No telemetry, usage analytics, crash upload, advertising identifiers or
  tracking SDKs.
- No account is required for anything. Sync, when it exists, is opt-in.
- Browsing data stays on the device.

## Inherited from ungoogled-chromium

ungoogled-chromium removes Google integrations and background requests,
including Google sign-in, GCM, Safe Browsing, field trials, domain reliability
reporting, network time and the privacy sandbox APIs, and it blocks requests to
Google service hosts through domain substitution. Its documentation lists the
full set of changes. Nadhr keeps all of them.

## Network requests Nadhr itself will make

Nadhr currently makes **none** of its own. Every future request must be listed
here, with its purpose, destination, the data sent, and how to turn it off.
Expected entries:

| Request | Purpose | Default | Control |
|---|---|---|---|
| Update check | security updates | on, to be decided with the updater design | setting and policy |
| Filter list updates | content blocking | on | uBlock Origin settings |

## Planned controls

Third-party cookie blocking, partitioned storage, DNS-over-HTTPS provider
choice, HTTPS-First (HTTPS-Only optional), WebRTC IP handling, per-site data
controls, and anti-fingerprinting measures that are compatibility-tested.

Private windows do not save history or cookies after closing. They do not make
you anonymous to websites, your network or your ISP, and Nadhr will never claim
they do.
