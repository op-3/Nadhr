# Nadhr: notes for Claude Code sessions

Nadhr is a desktop browser built as patches on ungoogled-chromium. Read
`docs/DEVELOPMENT_STATUS.md` first: it is the source of truth for what is done.
Update it, together with `docs/KNOWN_LIMITATIONS.md`, whenever something is
finished or found broken.

## Ground rules

- Never claim a feature, build, test or benchmark result that was not actually
  run and verified. Record evidence in DEVELOPMENT_STATUS.md.
- Never weaken the sandbox, Site Isolation, certificate checks or extension
  isolation.
- Never commit the Chromium tree, build outputs, secrets or signing keys.
  `prompt.md` (the owner's private brief) is git-ignored. Keep it that way.
- Upstream submodules under `upstream/` are never edited in place. All changes
  go in `patches/`.
- Helium (imputnet) is GPL-3.0 and may be used as a reference. Its maintainers
  do not accept AI-generated contributions, so never open issues or PRs on
  imputnet repositories.

## Layout

- `patches/series`: Nadhr patch order. Patches live in `patches/nadhr/<area>/`.
- `platforms/windows/build.py`, `package.py`: Windows build (adapted from
  ungoogled-chromium-windows).
- `devutils/validate_patches.py`: run `--remote` after any patch change.
- `.github/workflows/validate.yml`: fast checks. `build-windows.yml`: 16-stage
  CI build (manual dispatch or `v*` tag).

## Making a patch

1. Fetch the pristine file at the pinned tag:
   `https://chromium.googlesource.com/chromium/src/+/refs/tags/<ver>/<path>?format=TEXT`
   (base64), into `a/<path>`, and copy it to `b/<path>`.
2. Edit `b/` with a Python script, not shell heredocs: Git Bash mangles backslashes.
3. `diff -u --label a/<path> --label b/<path> a/<path> b/<path>` into the
   patch file, with a `# why` header.
4. Add it to `patches/series`, then run `python devutils/validate_patches.py --remote`.

Repository files use LF line endings (`.gitattributes`, `core.autocrlf=false`).
Patches with CRLF will not apply.

## Environment (2026-11-26)

Windows 11, i7-1265U, 31.6 GB RAM, about 142 GB free. `gh` is authenticated as
`op-3`. Visual Studio C++ workload and SDK 10.0.28000.0 are not installed yet.
Full builds run on GitHub Actions (free for public repositories).
