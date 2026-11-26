# Upstream maintenance

Nadhr follows ungoogled-chromium, which follows Chromium stable. Security
releases come every one to two weeks, so this process must stay fast.

## Bumping to a new Chromium version

1. Wait for ungoogled-chromium-windows to tag the new version. It pins the
   matching ungoogled-chromium commit.
2. Update the submodule:
   ```sh
   cd upstream/ungoogled-chromium-windows
   git fetch --tags && git checkout <new tag>
   git submodule update --init
   cd ../..
   ```
3. Reset `revision.txt` to `1` and update the baseline table in
   `docs/ARCHITECTURE.md`.
4. `python devutils/validate_patches.py --remote`.
5. For each failing Nadhr patch: fetch the new upstream file, reapply the
   change by hand, regenerate the patch with `diff -u`, then re-validate.
6. Open a pull request. The `validate` workflow must pass before the CI build runs.

## Keeping patches easy to rebase

- Small patches, one concern each.
- Put new code in new files (`chrome/browser/nadhr/...`) and keep the edits to
  upstream files to small hook points.
- Avoid reformatting or reordering upstream code.
- When upstream adds an equivalent feature, delete the Nadhr patch instead of rebasing it.

## Linux and macOS

When added, `upstream/` will also pin ungoogled-chromium-portablelinux and
ungoogled-chromium-macos at tags for the same Chromium version, and
`validate_patches.py` will gain those platforms.
