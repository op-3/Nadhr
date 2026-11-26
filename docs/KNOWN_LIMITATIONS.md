# Known limitations

Every known gap, honestly stated. Remove an entry only when it is fixed and verified.

## Product

- **No build has been produced yet.** Nadhr is pre-alpha.
- Windows only for now. Linux and macOS builds are not wired up.
- UI strings: "Chromium" is replaced in GRIT strings by `utils/name_substitution.py`
  (verified on `chromium_strings.grd` in all locales; **not yet seen in a built
  browser**). Still unbranded: the icons and logos, the executable name
  (`chrome.exe`), the internal `chrome://` scheme, and strings that say "Chrome"
  (not "Chromium"), which have not been reviewed yet.

## Built-in uBlock Origin (branch `feature/ublock-origin`)

- The patches apply cleanly to the pinned release but **have not been compiled
  or run**. Nothing below has been observed in a running browser.
- `redirect=empty` (zero-byte resource): Chromium 158 already serves a known,
  empty component resource as an empty 200 response
  (`chrome_url_request_util.cc` `GetResource`; a zero-length mojo write returns
  OK). Helium's global ResourceBundle change is therefore not needed. This is
  verified by reading source only, not yet at runtime.
- Enterprise configuration: Chromium reads `storage.managed_schema` from disk,
  which would drop every policy for a pak-bundled extension.
  `managed-storage-schema.patch` reads it from the pak. Not yet runtime-tested.
- Enterprise off switch: block the ID `mhmkochafbhohfaebfieaalahinnplkb`
  explicitly in `ExtensionInstallBlocklist` or `ExtensionSettings`
  (`policy-disable.patch`). A `*` wildcard deliberately does not turn it off.
  When it is blocked at startup it is not loaded; when the policy is removed
  at runtime it returns after a browser restart. Not yet runtime-tested.
- uBlock Origin's code updates only with Nadhr releases. Its filter lists
  update themselves over the network (see PRIVACY.md).

## Windows identity

- The elevation service and system tracing service COM IDs (`elevator_clsid`,
  `elevator_iid`, `tracing_service_*`) are still Chromium's. Changing them
  requires matching changes to the service IDL files. Until then, a
  **system-level** Nadhr install and a system-level Chromium install on the same
  machine could conflict over these registrations. Per-user installs are not
  affected.
- The app container SID prefix for the sandbox is unchanged from Chromium.

## Policy

- The Windows policy key is `Software\Policies\Nadhr` and the template
  generator uses the Nadhr names. The **Linux runtime** policy directory is
  still compiled in as `/etc/chromium/policies` until the Linux platform layer
  is added. The `/etc/nadhr/policies/` path appears only in generated templates.

## Upstream behaviour inherited from ungoogled-chromium

- Safe Browsing is compiled out (`safe_browsing_mode=0`). Nadhr has **no
  phishing or malware URL protection yet**. A privacy-preserving replacement is
  a release requirement (see [SECURITY.md](SECURITY.md#phishing-and-malware-protection)).
- Automatic updates are disabled. Nadhr's own updater is not built yet
  (see [UPDATES.md](UPDATES.md)).
- Widevine: `enable_widevine=true` allows the component to load, but there is
  no component updater to deliver it. DRM-protected streaming is therefore
  expected **not** to work. This is to be confirmed by testing and documented
  in a compatibility policy.
