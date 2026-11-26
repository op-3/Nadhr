# Testing

## Existing checks

| Check | Where | What it proves |
|---|---|---|
| Patch series consistency | `devutils/validate_patches.py` | every listed patch exists, every patch is listed, no duplicates |
| Patches apply to the pinned release | `devutils/validate_patches.py --remote`, CI `validate` | Nadhr's patches, plus any upstream patch touching the same files, apply in build order to Chromium at the pinned tag |
| Python sources compile | CI `validate` | build scripts have no syntax errors |
| Full Windows build | CI `build-windows` | the patched tree compiles and packages (**not yet run successfully**) |

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
