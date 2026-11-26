# Enterprise and government deployment

Nadhr uses Chromium's policy system unchanged, under its own namespace, so the
full set of Chromium policies is available. There is one product, with no
separate "government edition".

## Policy locations

| Platform | Mandatory | Recommended | Status |
|---|---|---|---|
| Windows | `HKLM\Software\Policies\Nadhr` (also `HKCU`) | `...\Nadhr\Recommended` | patched (`nadhr/policy/policy-namespace.patch`), **not yet tested in a build** |
| Linux | `/etc/nadhr/policies/managed/*.json` | `/etc/nadhr/policies/recommended/*.json` | templates only. The runtime path is still `/etc/chromium/policies` (see KNOWN_LIMITATIONS) |
| macOS | managed preferences for `org.nadhr.Nadhr` | | not yet built |

Precedence follows Chromium: platform mandatory > cloud (not used) > platform
recommended > user setting. A managed value cannot be changed from settings or
by switching layouts.

## Templates

ADMX/ADML templates for Group Policy will be generated from Chromium's
`policy_templates` during the build, using the Nadhr names and categories, and
published with each release.

## Built-in uBlock Origin

The bundled uBlock Origin has the extension ID `mhmkochafbhohfaebfieaalahinnplkb`.
It uses standard Chromium policy mechanisms; no new policy is needed:

- **Configure it** through uBlock Origin's managed storage
  (`3rdparty` → `extensions` → `mhmkochafbhohfaebfieaalahinnplkb` →
  `adminSettings`, `toOverwrite`, …), as described in uBlock Origin's
  "Deploying uBlock Origin" documentation. Internal filter-list mirrors for
  restricted networks are set the same way.
- **Turn it off** by blocking that ID explicitly, in `ExtensionInstallBlocklist`
  or in `ExtensionSettings` with `"installation_mode": "blocked"`. A `*` entry
  does **not** turn it off, so organisations that block user-installed
  extensions keep the built-in protection.

Status: implemented on the `feature/ublock-origin` branch, not yet
runtime-tested.

## Planned Nadhr-specific policies

Layout lock, performance mode, update channel, update server URL and update
deferral. Each will be added as a regular Chromium policy definition so that
the existing validation and precedence rules apply.

## What a browser can and cannot enforce

Browser policies control browser behaviour: downloads, printing, extensions,
URL access, developer tools, clipboard access for web pages, and data
retention. They do not stop a user from photographing a screen, copying files
outside the browser, or using another program. Data-loss prevention needs
endpoint and network controls as well. Nadhr does not monitor browsing history
by default and does not include employee surveillance features.
