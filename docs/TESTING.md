# Testing

## Existing checks

| Check | Where | What it proves |
|---|---|---|
| Patch series consistency | `devutils/validate_patches.py` | every listed patch exists, every patch is listed, no duplicates |
| Patches apply to the pinned release | `devutils/validate_patches.py --remote`, CI `validate` | Nadhr's patches, plus any upstream patch touching the same files, apply in build order to Chromium at the pinned tag |
| Python sources compile | CI `validate` | build scripts have no syntax errors |
| Name substitution unit tests | `utils/tests`, CI `validate` | product mentions are renamed, upstream-project mentions ("The Chromium Authors", "Chromium OS", the credits link) are kept, and only changed messages' translations are re-keyed |
| Name substitution on real strings | `devutils/verify_name_substitution.py`, CI `validate` | on Chromium's real `chromium_strings.grd` and all 81 locales (68,607 translations): the fingerprint computation matches every shipped translation ID, no translation is lost after renaming, and no English product mention remains. Negative control: with re-keying disabled, it reports 563 lost translations per locale. |
| Full Windows build | CI `build-windows` | the patched tree compiles and packages (**not yet run successfully**) |
| Launch smoke test | `devutils/smoke_test.py`, CI `build-windows` → `smoke-test` | the packaged browser starts headless with a fresh profile, loads a page over HTTP and runs JavaScript; the executable is branded Nadhr; the default profile goes to `%LOCALAPPDATA%\Nadhr\User Data` and no Chromium directory is created; when uBlock patches are in the series, a request matching EasyList's `/banner_ads/*` rule is blocked while a control request is not. The transcript is uploaded as `smoke-test-evidence`. Controls run against Microsoft Edge (no blocker): JavaScript and control-request checks pass, branding and blocking checks correctly fail. The positive blocking case can only be shown by a Nadhr build that includes uBlock. |
| Arabic product name | `utils/tests`, `devutils/verify_name_substitution.py` | نظر is stored in logical order (U+0646 U+0638 U+0631). In Chromium's real Arabic translations: 738 occurrences, 0 of the reversed sequence, no Latin name. |

## Test matrix (target)

| Area | Windows | Linux | macOS |
|---|---|---|---|
| Build and package | planned | planned | planned |
| Launch smoke test (chromedriver: start, load page, quit) | planned | planned | planned |
| Install, update, uninstall | planned | planned | planned |
| Policy enforcement | planned | planned | planned |
| Layout switching keeps tabs | planned | planned | planned |
| uBlock Origin blocking (local fixture pages) | planned | planned | planned |
| Arabic RTL screenshots | planned | planned | planned |
| Performance regression suite | planned | planned | planned |

A platform is called tested only after native execution on that platform.
Cross-compilation does not count.

## Evidence

Test evidence (logs, screenshots taken from real runs, benchmark data) is
stored with each CI run as artifacts and, for releases, linked from the release
notes. Mock screenshots and invented numbers are never used.
