# Building Nadhr

## Windows (x64)

### Requirements

- Windows 10 or 11, x64.
- Visual Studio 2022 (Community or Build Tools) with the
  **Desktop development with C++** workload.
- Windows SDK **10.0.28000.0** with the *Debugging Tools for Windows* feature.
  The CI installs it with the same command used in
  [`.github/actions/prepare/action.yml`](../.github/actions/prepare/action.yml).
- Python 3.12 or newer, plus `pip install httplib2==0.22.0 clang==21.1.7`.
- Git, and 7-Zip (found through the registry; or pass `--7z-path`).
- **Disk:** about 120 GB free. The source tree is roughly 35 GB and the
  output directory 50 to 70 GB.
- **Memory:** 16 GB minimum, 32 GB recommended.
- **Time:** many hours. A 10-core, 15 W laptop CPU can take well over 12 hours
  for a full official build. An incremental rebuild after a small patch is much faster.

The build uses its own LLVM, Rust and Ninja downloads (checksummed in
ungoogled-chromium-windows' `downloads.ini`), not Google's toolchain.

### Steps

```powershell
git clone --recursive https://github.com/op-3/Nadhr.git
cd Nadhr
python -m pip install httplib2==0.22.0 clang==21.1.7
python platforms\windows\build.py            # full build
python platforms\windows\build.py -j 8       # limit parallel jobs
```

Packages are written to `build\dist\`:

- `nadhr_<version>_windows_x64_installer.exe`
- `nadhr_<version>_windows_x64_portable.zip`

`--tarball` builds from Chromium's source tarball instead of a git clone. The
tarball lacks PGO profiles, so the result is slower; use it only when cloning
is not possible.

### Rebuilding after changing a Nadhr patch

Patches are applied once, when `build/src` is created. After changing a patch,
either delete `build/src` (slow, safe), or revert the old patch and apply the
new one inside `build/src` by hand, then rerun ninja:

```powershell
cd build\src
third_party\ninja\ninja.exe -C out\Default chrome
```

### CI builds

[`build-windows.yml`](../.github/workflows/build-windows.yml) runs the same
script on GitHub-hosted runners. Because one job is limited to 6 hours, the
build runs as up to 16 chained stages. Each stage builds for 3.5 hours, then
uploads the partial tree for the next stage. Start it from the Actions tab
(*Run workflow*) or by pushing a `v*` tag.

## Linux and macOS

Not yet wired up. The plan is to reuse ungoogled-chromium-portablelinux and
ungoogled-chromium-macos the same way the Windows build reuses
ungoogled-chromium-windows. Tracked in [ROADMAP.md](ROADMAP.md).

## Checking patches without building

```sh
python devutils/validate_patches.py            # series consistency only
python devutils/validate_patches.py --remote   # apply against Chromium at the pinned tag
python devutils/validate_patches.py --local path\to\unmodified\src
```

Remote mode downloads only the files Nadhr's patches touch, applies any upstream
patch that touches the same files, then applies Nadhr's patches with `git apply`.
