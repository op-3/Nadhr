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
- `utils/name_substitution.py`: build-time rename of "Chromium" in GRIT strings,
  re-keying translations. Verified by `devutils/verify_name_substitution.py`.
- `devutils/smoke_test.py`: launches a built browser; runs in CI after the build.
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
`op-3`. Commits use the GitHub no-reply email (repo-local git config). Never
publish the owner's personal email.

**Owner decision:** never install Visual Studio or the Windows SDK, and never
download a Chromium tree on this laptop. Full builds run only on GitHub Actions
(free tier; no paid runners without approval). Verify locally with
`devutils/validate_patches.py --remote`, `devutils/verify_name_substitution.py`
and `python -m unittest discover -s utils/tests`.

## Current work and how to resume (updated 2026-11-27)

1. **First Windows CI build: done.** Run 45891287269 (bb201e9) passed all 16
   stages and the smoke test (JS runs, executable branded Nadhr). Earlier runs
   failed on the clone path bug, fixed in bb201e9. When a run finishes, delete
   its `build-state-windows-x64` artifact (about 18 GB) to save storage. Check it with `gh run list -R op-3/Nadhr --workflow build-windows.yml`.
   A full build takes up to 16 chained stages (about 1 to 2 days). Read
   failures with `gh run view <id> --log-failed`.
2. **uBlock Origin**: draft PR #2, branch `feature/ublock-origin`. Branch
   build 46136614194 is running.
2b. **Fast builds** (docs/BUILDING.md, "Four kinds of build"): `build-dev.yml`
   restores the `dev-tree` from the latest successful dev build on main and
   resyncs patches with `utils/tree_state.py`. Seed run 46168333592 is
   running (the first, 46138914484, failed in a component-build link; dev
   builds are now static). Once it succeeds, use
   `gh workflow run build-dev.yml --ref <branch>` for native work. Record
   `[timing]` lines from the logs in docs/BUILDING.md. Workflows are
   generated: edit `devutils/generate_workflows.py`, then run it. Merge only
   after it compiles and a smoke test shows blocking. Open items are listed in
   KNOWN_LIMITATIONS.md.
3. **Next priorities** (owner, 2026-11-26): remaining branding (icons, exe
   name, "Chrome" strings), the three layouts, phishing/malware protection,
   enterprise policies, performance engine, Arabic RTL.

Pitfalls learned:
- Git Bash heredocs mangle backslashes and `\n`. Write Python scripts with the
  Write tool instead.
- Global `core.autocrlf=true` checks submodule patches out with CRLF.
  Normalise them before `git apply`; the validator already does.
- gitiles rate-limits bursts (HTTP 429). Use `devutils/gitiles.py`, which retries.
- When reproducing a bug offline, reproduce the exact code path. A first "fix"
  for the clone bug passed a simplified repro and still failed in CI.

## Owner decisions, 2026-11-27 (binding)

- Threat protection on by default, but only with sources whose terms
  **explicitly** allow personal, enterprise, government and commercial use
  (a mirror also needs redistribution rights). Pointing at a URL does not
  exempt a restricted feed. The same rule is applied to uBlock's default filter
  lists (`resources/ublock/default_lists.json`, enforced by `prepare_ublock.py`).
- No paid services, hosting, subscriptions or contracts without the owner's
  approval. No production server yet. Mirror tooling only (`threat_intel/`).
- **No licensing outreach (final owner decision, 2026-11-27).** Never contact
  feed providers, request permissions, negotiate licences, or buy threat
  intelligence. Use only sources whose published terms already allow
  personal, enterprise, government and commercial use (plus redistribution for
  the mirror). Exclude anything ambiguous. If coverage is lacking, document
  the gap and keep looking for openly licensed alternatives.
  `docs/THREAT_PROTECTION_OUTREACH.md` is cancelled, historical only.
- CC BY 4.0 attribution (NetAPI) is approved for About/Credits and for warning
  pages on matches from that list.
- PR #2 merges only after a branch build shows uBlock blocking ads, letting
  normal requests through, and respecting policy.
- Never claim parity with Safe Browsing or SmartScreen, or enterprise- or
  government-readiness. Global phishing coverage with permitted sources is
  inadequate today.

Threat-intel tooling tests: `pip install -r threat_intel/requirements.txt`,
then `python -m unittest discover -s threat_intel/tests -t .`
