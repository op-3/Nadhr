#!/usr/bin/env python3
# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generates the chained Windows build workflows.

GitHub Actions has no loops, and a Chromium build needs several 6-hour jobs,
so the stage jobs are generated here instead of being edited by hand:

    python devutils/generate_workflows.py   # rewrites .github/workflows/build-*.yml
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / '.github' / 'workflows'

SMOKE = '''      - name: Launch smoke test
        if: steps.stage.outputs.built_here == 'true'
        shell: pwsh
        run: |
          # The runner is disposable, so the default-profile check may write to LOCALAPPDATA.
          $extra = @('--check-default-profile')
          if (Select-String -Quiet -Pattern '^nadhr/ublock/' -Path patches/series) {
            $extra += '--expect-content-blocking'
          }
          python devutils/smoke_test.py C:\\nadhr\\build\\src\\out\\Default\\chrome.exe @extra | Tee-Object smoke-test.txt
          exit $LASTEXITCODE
      - uses: actions/upload-artifact@v7
        if: always() && steps.stage.outputs.built_here == 'true'
        with:
          name: smoke-test-evidence
          path: smoke-test.txt
'''

RESTORE_DEV_TREE = '''      - name: Restore the latest dev tree from main
        if: ${{ !inputs.seed }}
        shell: pwsh
        env:
          GH_TOKEN: ${{ github.token }}
          GITHUB_ACTIONS: ''
        run: |
          $id = gh run list -R $env:GITHUB_REPOSITORY --workflow build-dev.yml --branch main `
                --status success -L 1 --json databaseId --jq '.[0].databaseId'
          if (-not $id) { throw 'No successful dev build on main yet: run build-dev with seed=true on main first.' }
          Write-Host "Restoring dev tree from run $id"
          $t = Get-Date
          gh run download $id -R $env:GITHUB_REPOSITORY -n dev-tree -D C:\\nadhr\\build
          Write-Host ("[timing] download dev tree: {0:N1} min" -f ((Get-Date) - $t).TotalMinutes)
          $archive = Get-ChildItem C:\\nadhr\\build -Filter 'dev-tree.*' | Select-Object -First 1
          node -e "import('./.github/actions/stage/index.js').then(m => m.extractTree(process.argv[1]))" $archive.FullName
'''


def stage_job(index, mode, extra_steps_first='', extra_steps_last=''):
    prev = f'stage-{index - 1}'
    lines = [f'  stage-{index}:']
    if index > 1:
        lines.append(f'    needs: {prev}')
    lines += ['    runs-on: windows-2022', '    timeout-minutes: 360', '    steps:',
              '      - uses: actions/checkout@v7', '        with:', '          submodules: recursive']
    finished = 'false' if index == 1 else f'${{{{ needs.{prev}.outputs.finished }}}}'
    if index > 1:
        # Nothing to do once an earlier stage finished: skip the slow setup.
        lines += ['      - uses: ./.github/actions/prepare',
                  f"        if: needs.{prev}.outputs.finished != 'true'"]
    else:
        lines += ['      - uses: ./.github/actions/prepare']
    body = '\n'.join(lines) + '\n'
    if index == 1:
        body += extra_steps_first
    skip = f"        if: needs.{prev}.outputs.finished != 'true'\n" if index > 1 else ''
    body += f'''      - id: stage
        uses: ./.github/actions/stage
{skip}        with:
          finished: {finished}
          from_artifact: {'false' if index == 1 else 'true'}
          mode: {mode}
          jobs: '4'
'''
    if mode == 'dev':
        body += "          publish_tree: ${{ github.ref == 'refs/heads/main' }}\n"
    body += extra_steps_last
    # A skipped stage passes the earlier result through.
    passthrough = f' || needs.{prev}.outputs.finished' if index > 1 else ''
    body += f'    outputs:\n      finished: ${{{{ steps.stage.outputs.finished{passthrough} }}}}\n'
    return body


def complete_job(last):
    return f'''  complete:
    needs: stage-{last}
    runs-on: ubuntu-latest
    steps:
      - name: Ensure the build finished
        run: |
          if [ "${{{{ needs.stage-{last}.outputs.finished }}}}" != "true" ]; then
            echo "Build did not finish within {last} stages."
            exit 1
          fi
'''


RELEASE_SMOKE_JOB = '''  smoke-test:
    needs: complete
    runs-on: windows-2022
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.12'
      - uses: actions/download-artifact@v8
        with:
          name: nadhr-windows-x64
          path: dist
      - name: Unpack portable build
        shell: pwsh
        run: |
          $zip = Get-ChildItem dist -Filter 'nadhr_*_portable.zip' | Select-Object -First 1
          if (-not $zip) { throw 'Portable zip not found in build artifact' }
          Expand-Archive $zip.FullName -DestinationPath portable
          $exe = Get-ChildItem portable -Recurse -Filter chrome.exe | Select-Object -First 1
          if (-not $exe) { throw 'chrome.exe not found in portable zip' }
          "NADHR_EXE=$($exe.FullName)" >> $env:GITHUB_ENV
      - name: Launch smoke test
        shell: pwsh
        run: |
          # The runner is disposable, so the default-profile check may write to LOCALAPPDATA.
          $extra = @('--check-default-profile')
          if (Select-String -Quiet -Pattern '^nadhr/ublock/' -Path patches/series) {
            $extra += '--expect-content-blocking'
          }
          python devutils/smoke_test.py "$env:NADHR_EXE" @extra | Tee-Object smoke-test.txt
          exit $LASTEXITCODE
      - uses: actions/upload-artifact@v7
        if: always()
        with:
          name: smoke-test-evidence
          path: smoke-test.txt
'''


def release_workflow(stages=16):
    head = '''# GENERATED by devutils/generate_workflows.py - edit that file, not this one.
# Release build of Nadhr for Windows x64: official build with PGO and ThinLTO,
# packaged and smoke-tested. A full Chromium build needs far longer than one
# job's 6 h limit, so it runs as chained stages; each resumes the previous one.
name: build-windows
on:
  workflow_dispatch:
  push:
    tags: ['v*']

permissions:
  contents: read

concurrency:
  group: build-windows-${{ github.ref }}
  cancel-in-progress: false

jobs:
'''
    jobs = ''.join(stage_job(i, 'release') for i in range(1, stages + 1))
    return head + jobs + complete_job(stages) + RELEASE_SMOKE_JOB


def dev_workflow(stages=8):
    head = '''# GENERATED by devutils/generate_workflows.py - edit that file, not this one.
# Development build of Nadhr for Windows x64 (component build, no PGO/LTO).
# Normally incremental: it restores the latest dev tree built on main,
# re-patches only the files whose patches changed (utils/tree_state.py), and
# recompiles only what depends on them. seed=true builds a dev tree from
# scratch (needed once, and after upstream or download changes).
# Never use these binaries for distribution.
name: build-dev
on:
  workflow_dispatch:
    inputs:
      seed:
        description: Build the dev tree from scratch instead of restoring it
        type: boolean
        default: false

permissions:
  contents: read
  actions: read

concurrency:
  group: build-dev-${{ github.ref }}
  cancel-in-progress: false

jobs:
'''
    jobs = ''.join(stage_job(i, 'dev',
                             extra_steps_first=RESTORE_DEV_TREE if i == 1 else '',
                             extra_steps_last=SMOKE)
                   for i in range(1, stages + 1))
    return head + jobs + complete_job(stages)


def main():
    (WORKFLOWS / 'build-windows.yml').write_text(release_workflow(), encoding='utf-8',
                                                 newline='\n')
    (WORKFLOWS / 'build-dev.yml').write_text(dev_workflow(), encoding='utf-8', newline='\n')
    print('wrote build-windows.yml and build-dev.yml')


if __name__ == '__main__':
    main()
