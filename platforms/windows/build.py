#!/usr/bin/env python3
# Copyright 2019 The ungoogled-chromium Authors (original build.py, BSD-3-Clause)
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds Nadhr for Microsoft Windows.

Adapted from ungoogled-chromium-windows/build.py. Every upstream input
(patches, downloads, pruning and substitution lists, GN flags) is read from the
pinned submodule in upstream/, so rebasing is a submodule bump. Nadhr's own
patches are applied last, from patches/series.

Phases are idempotent in --ci mode so that a build can resume across the
time-limited CI stages.
"""

import argparse
import ctypes
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UC_WIN = ROOT / 'upstream' / 'ungoogled-chromium-windows'
UC = UC_WIN / 'ungoogled-chromium'

sys.path.insert(0, str(UC / 'utils'))
import domain_substitution  # pylint: disable=wrong-import-position
import downloads  # pylint: disable=wrong-import-position
import patches  # pylint: disable=wrong-import-position
import prune_binaries  # pylint: disable=wrong-import-position
from _common import ENCODING, USE_REGISTRY, ExtractorEnum, get_logger  # pylint: disable=wrong-import-position
sys.path.pop(0)

BUILD_DIR = ROOT / 'build'
SOURCE_TREE = BUILD_DIR / 'src'
DOWNLOAD_CACHE = BUILD_DIR / 'download_cache'
OUT_DIR = 'out\\Default'
PATCH_BIN_RELPATH = Path('third_party/git/usr/bin/patch.exe')
BUILD_TIMEOUT_EXIT_CODE = 124
# Leave CI stages enough of their 6 h limit to compress and upload the tree.
CI_NINJA_TIMEOUT_SECONDS = 3.5 * 60 * 60


class BuildTimeout(Exception):
    """Raised when the CI stage time budget is used up."""


def _vcvars_path():
    vswhere = os.path.expandvars(
        r'%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe')
    result = subprocess.run([vswhere, '-products', '*', '-prerelease', '-latest', '-property',
                             'installationPath'],
                            check=True, stdout=subprocess.PIPE, universal_newlines=True)
    path = Path(result.stdout.strip(), 'VC/Auxiliary/Build/vcvars64.bat')
    if not path.exists():
        raise RuntimeError(f'Could not find vcvars64.bat at {path}. '
                           'Install Visual Studio 2022 with the C++ desktop workload.')
    return path


def _msvc_script(*args):
    return '\n'.join([
        f'call "{_vcvars_path()}" >nul',
        'set DEPOT_TOOLS_WIN_TOOLCHAIN=0',
        ' '.join(f'"{a}"' for a in args),
        'exit\n',
    ])


def run_msvc(*args, **kwargs):
    """Runs a command inside the MSVC developer environment."""
    subprocess.run(('cmd.exe', '/k'), input=_msvc_script(*args), check=True, encoding=ENCODING,
                   **kwargs)


def run_msvc_with_timeout(*args, timeout):
    """Like run_msvc, but interrupts ninja cleanly so the next CI stage can resume."""
    with subprocess.Popen(('cmd.exe', '/k'), encoding=ENCODING, stdin=subprocess.PIPE,
                          creationflags=subprocess.CREATE_NEW_PROCESS_GROUP) as proc:
        proc.stdin.write(_msvc_script(*args))
        proc.stdin.close()
        try:
            proc.wait(timeout)
            if proc.returncode != 0:
                raise RuntimeError('Build failed!')
        except subprocess.TimeoutExpired as exc:
            print('Stage time budget reached; interrupting ninja')
            for _ in range(3):
                ctypes.windll.kernel32.GenerateConsoleCtrlEvent(1, proc.pid)
                time.sleep(1)
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise BuildTimeout from exc


def prepare_source(args):
    """Fetches Chromium and applies the ungoogled-chromium, Windows and Nadhr layers."""
    SOURCE_TREE.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_CACHE.mkdir(parents=True, exist_ok=True)
    for var in ('TMP', 'TEMP'):  # ninja fails if these do not exist
        Path(os.environ[var]).mkdir(parents=True, exist_ok=True)

    extractors = {ExtractorEnum.SEVENZIP: args.sevenz_path, ExtractorEnum.WINRAR: args.winrar_path}

    if args.tarball:
        get_logger().info('Downloading Chromium source tarball...')
        info = downloads.DownloadInfo([UC / 'downloads.ini'])
        downloads.retrieve_downloads(info, DOWNLOAD_CACHE, None, True,
                                     args.disable_ssl_verification)
        downloads.check_downloads(info, DOWNLOAD_CACHE, None)
        downloads.unpack_downloads(info, DOWNLOAD_CACHE, None, SOURCE_TREE, extractors)
    else:
        subprocess.run([sys.executable, str(UC / 'utils' / 'clone.py'), '-o', str(SOURCE_TREE),
                        '-p', 'win64'], check=True)
        # clone.py does not run the 'minibranch' DEPS hook.
        subprocess.run([sys.executable, str(SOURCE_TREE / 'build' / 'util' / 'lastchange.py'),
                        '--minibranch-out',
                        str(SOURCE_TREE / 'build' / 'util' / 'MINIBRANCH')], check=True)

    get_logger().info('Downloading Windows build dependencies...')
    win_info = downloads.DownloadInfo([UC_WIN / 'downloads.ini'])
    downloads.retrieve_downloads(win_info, DOWNLOAD_CACHE, None, True,
                                 args.disable_ssl_verification)
    downloads.check_downloads(win_info, DOWNLOAD_CACHE, None)  # raises on hash mismatch

    pruning_list = (UC if args.tarball else UC_WIN) / 'pruning.list'
    unremovable = prune_binaries.prune_files(
        SOURCE_TREE, pruning_list.read_text(encoding=ENCODING).splitlines())
    if unremovable:
        raise RuntimeError(f'Files could not be pruned: {unremovable}')

    # These directories are replaced wholesale by downloads.ini entries.
    for rel in ('third_party/microsoft_dxheaders/src',
                'third_party/devtools-frontend/src/third_party/esbuild'):
        path = SOURCE_TREE / rel
        if path.exists():
            shutil.rmtree(path)
            path.mkdir()
    downloads.unpack_downloads(win_info, DOWNLOAD_CACHE, None, SOURCE_TREE, extractors)

    for layer in (UC / 'patches', UC_WIN / 'patches', ROOT / 'patches'):
        get_logger().info('Applying patches from %s', layer.relative_to(ROOT))
        patches.apply_patches(patches.generate_patches_from_series(layer, resolve=True),
                              SOURCE_TREE, patch_bin_path=SOURCE_TREE / PATCH_BIN_RELPATH)

    substitution_list = (UC if args.tarball else UC_WIN) / 'domain_substitution.list'
    domain_substitution.apply_substitution(UC / 'domain_regex.list', substitution_list,
                                           SOURCE_TREE, None)


def prepare_rust_toolchain():
    """Assembles third_party/rust-toolchain from the per-architecture downloads."""
    dst = SOURCE_TREE / 'third_party' / 'rust-toolchain'
    src64 = SOURCE_TREE / 'third_party' / 'rust-toolchain-x64'
    for src in (src64, SOURCE_TREE / 'third_party' / 'rust-toolchain-x86',
                SOURCE_TREE / 'third_party' / 'rust-toolchain-arm'):
        for sub in ('bin', 'lib'):
            if sub == 'bin' and src != src64:  # host binaries are x64 only
                continue
            (dst / sub).mkdir(parents=True, exist_ok=True)
            for item in src.glob(f'*/{sub}/*'):
                if item.is_dir():
                    shutil.copytree(item, dst / sub / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dst / sub / item.name)
    # rustc_private crates for the x64 host, needed by Crubit.
    for item in (SOURCE_TREE / 'third_party' / 'rust-toolchain-x64-dev').glob('*/lib/*'):
        shutil.copytree(item, dst / 'lib' / item.name, dirs_exist_ok=True)
    with open(dst / 'INSTALLED_VERSION', 'w', encoding=ENCODING) as out:
        subprocess.run([src64 / 'rustc' / 'bin' / 'rustc.exe', '--version'], stdout=out,
                       check=True)


def write_gn_args(args):
    out = SOURCE_TREE / 'out' / 'Default'
    out.mkdir(parents=True, exist_ok=True)
    flags = (UC / 'flags.gn').read_text(encoding=ENCODING) + '\n'
    flags += (UC_WIN / 'flags.windows.gn').read_text(encoding=ENCODING) + '\n'
    if args.tarball:
        flags += 'chrome_pgo_phase=0\n'  # the tarball ships without PGO profiles
    clang_spec = importlib.util.find_spec('clang')
    if clang_spec is None or not clang_spec.submodule_search_locations:
        raise RuntimeError('Python clang bindings not found: pip install clang')
    libclang = SOURCE_TREE / 'third_party' / 'llvm-build' / 'Release+Asserts' / 'bin' / 'libclang.dll'
    bindings = Path(list(clang_spec.submodule_search_locations)[0]).parent
    flags += f'v8_metagen_libclang_so="{libclang.resolve().as_posix()}"\n'
    flags += f'v8_metagen_libclang_bindings_dir="{bindings.resolve().as_posix()}"\n'
    (out / 'args.gn').write_text(flags, encoding=ENCODING)


def build_crubit():
    crubit_root = Path('third_party', 'rust-toolchain', 'crubit')
    exe = crubit_root / 'bin' / 'cc_bindings_from_rs.exe'
    rust_bin = Path('third_party', 'rust-toolchain', 'bin').resolve()
    target = Path('out', 'crubit').resolve()
    env = dict(os.environ, RUSTC=str(rust_bin / 'rustc.exe'), CARGO_HOME=str(target / 'cargo_home'),
               # Static CRT like rustc.exe, so no VCRUNTIME140.dll is needed.
               RUSTFLAGS='-Ctarget-feature=+crt-static')
    run_msvc(str(rust_bin / 'cargo.exe'), 'build', '--release', '--locked', '-p',
             'cc_bindings_from_rs', '--bin', 'cc_bindings_from_rs', '--manifest-path',
             str((crubit_root / 'lib' / 'third_party' / 'crubit' / 'Cargo.toml').resolve()),
             '--target-dir', str(target), env=env)
    exe.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target / 'release' / 'cc_bindings_from_rs.exe', exe)
    for dll in rust_bin.glob('*.dll'):  # Windows has no rpath
        shutil.copy2(dll, exe.parent / dll.name)
    subprocess.run([str(exe), '--help'], stdout=subprocess.DEVNULL, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disable-ssl-verification', action='store_true')
    parser.add_argument('--7z-path', dest='sevenz_path', default=USE_REGISTRY)
    parser.add_argument('--winrar-path', dest='winrar_path', default=USE_REGISTRY)
    parser.add_argument('-j', type=int, dest='thread_count', help='Parallel compile jobs')
    parser.add_argument('--ci', action='store_true',
                        help='Resume-friendly mode with a per-stage time budget')
    parser.add_argument('--tarball', action='store_true',
                        help='Use the source tarball instead of a git clone (no PGO)')
    args = parser.parse_args()

    # In --ci mode each phase is skipped when an earlier stage already completed it.
    resume = args.ci
    if not (resume and (SOURCE_TREE / 'BUILD.gn').exists()):
        prepare_source(args)
    if not (resume and (SOURCE_TREE / 'third_party/rust-toolchain/INSTALLED_VERSION').exists()):
        prepare_rust_toolchain()
    if not (resume and (SOURCE_TREE / 'out/Default/args.gn').exists()):
        write_gn_args(args)

    os.chdir(SOURCE_TREE)
    if not (resume and Path(OUT_DIR, 'gn.exe').exists()):
        run_msvc(sys.executable, 'tools\\gn\\bootstrap\\bootstrap.py', '-o', f'{OUT_DIR}\\gn.exe',
                 '--skip-generate-buildfiles')
        run_msvc(f'{OUT_DIR}\\gn.exe', 'gen', OUT_DIR, '--fail-on-unused-args')
    if not (resume and Path('third_party/rust-toolchain/bin/bindgen.exe').exists()):
        run_msvc(sys.executable, 'tools\\rust\\build_bindgen.py', '--skip-test')
    if not (resume and Path('third_party/rust-toolchain/crubit/bin/cc_bindings_from_rs.exe').exists()):
        build_crubit()

    ninja = ['third_party\\ninja\\ninja.exe', '-C', OUT_DIR, 'chrome', 'chromedriver',
             'mini_installer']
    if args.thread_count:
        ninja[1:1] = ['-j', str(args.thread_count)]
    if args.ci:
        run_msvc_with_timeout(*ninja, timeout=CI_NINJA_TIMEOUT_SECONDS)
    else:
        run_msvc(*ninja)

    os.chdir(ROOT)
    subprocess.run([sys.executable, str(ROOT / 'platforms' / 'windows' / 'package.py')],
                   check=True)


if __name__ == '__main__':
    try:
        main()
    except BuildTimeout:
        sys.exit(BUILD_TIMEOUT_EXIT_CODE)
