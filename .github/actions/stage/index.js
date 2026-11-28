// Adapted from ungoogled-chromium-windows (BSD-3-Clause).
// Runs one time-limited build stage. A stage either finishes the build, or hits
// its time budget and uploads the partial tree so the next stage can resume.
import * as core from '@actions/core';
import * as io from '@actions/io';
import * as exec from '@actions/exec';
import { DefaultArtifactClient } from '@actions/artifact';
import * as glob from '@actions/glob';
import * as fs from 'node:fs';
import { spawn } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const BUILD_TIMEOUT_EXIT_CODE = 124;
const SEED_REQUIRED_EXIT_CODE = 3;
const WORK = 'C:\\nadhr';
const BUILD = `${WORK}\\build`;
const TAR = 'C:\\Windows\\System32\\tar.exe';

async function timed(label, fn) {
    const start = Date.now();
    try {
        return await fn();
    } finally {
        console.log(`[timing] ${label}: ${((Date.now() - start) / 60000).toFixed(1)} min`);
    }
}

async function haveZstd() {
    const code = await exec.exec('zstd', ['--version'], {ignoreReturnCode: true, silent: true})
        .catch(() => 1);
    return code === 0 && fs.existsSync(TAR);
}

// Runs `producer | consumer` with Node streams (no shell, so no quoting issues).
// Resolves true only if both processes exit with 0.
function pipe(producer, consumer) {
    return new Promise(resolve => {
        const a = spawn(producer[0], producer.slice(1), {stdio: ['ignore', 'pipe', 'inherit']});
        const b = spawn(consumer[0], consumer.slice(1), {stdio: ['pipe', 'inherit', 'inherit']});
        a.stdout.pipe(b.stdin);
        let pending = 2, ok = true;
        const done = code => { ok = ok && code === 0; if (--pending === 0) resolve(ok); };
        a.on('error', () => done(1)).on('close', done);
        b.on('error', () => done(1)).on('close', done);
    });
}

// Archives BUILD\src. tar piped into multi-threaded zstd is much faster than
// 7-Zip zip (the runner's bsdtar has no built-in zstd, so the zstd tool is
// used). 7-Zip is the fallback if zstd/tar is missing or fails.
export async function archiveTree(outBase) {
    if (await haveZstd()) {
        const out = `${outBase}.tar.zst`;
        const ok = await timed('archive (tar|zstd)', () => pipe(
            [TAR, '-cf', '-', '-C', BUILD, 'src'], ['zstd', '-T0', '-3', '-q', '-f', '-o', out]));
        if (ok) return out;
        console.log('tar|zstd failed, falling back to 7-Zip');
        await io.rmRF(out);
    }
    const out = `${outBase}.zip`;
    await timed('archive (7-Zip)', () => exec.exec('7z', ['a', '-tzip', out, `${BUILD}\\src`,
        '-mx=3', '-mtc=on'], {ignoreReturnCode: true}));
    return out;
}

export async function extractTree(archive) {
    if (archive.endsWith('.tar.zst')) {
        fs.mkdirSync(BUILD, {recursive: true});
        const ok = await timed('extract (zstd|tar)', () => pipe(
            ['zstd', '-d', '-c', '-q', archive], [TAR, '-xf', '-', '-C', BUILD]));
        if (!ok) throw new Error(`Could not extract ${archive}`);
    } else {
        await timed('extract (7-Zip)', () => exec.exec('7z', ['x', archive, `-o${BUILD}`, '-y']));
    }
    await io.rmRF(archive);
}

async function uploadWithRetry(artifact, name, files, rootDir, retentionDays) {
    for (let i = 0; i < 5; ++i) {
        try { await artifact.deleteArtifact(name); } catch (e) { /* not there yet */ }
        try {
            await timed(`upload ${name}`, () => artifact.uploadArtifact(name, files, rootDir,
                {retentionDays, compressionLevel: 0}));
            return;
        } catch (e) {
            console.error(`Upload of ${name} failed: ${e}`);
            await new Promise(r => setTimeout(r, 10000));
        }
    }
    throw new Error(`Could not upload ${name}`);
}

async function run() {
    process.on('SIGINT', () => {});  // ninja is interrupted, not this process
    const finished = core.getBooleanInput('finished', {required: true});
    const fromArtifact = core.getBooleanInput('from_artifact', {required: true});
    const mode = core.getInput('mode') || 'release';
    const jobs = core.getInput('jobs') || '4';
    const stateArtifact = `build-state-windows-x64-${mode}`;
    console.log(`finished: ${finished}, from_artifact: ${fromArtifact}, mode: ${mode}, jobs: ${jobs}`);
    core.setOutput('built_here', false);
    if (finished) {
        core.setOutput('finished', true);
        return;
    }

    const artifact = new DefaultArtifactClient();
    if (fromArtifact) {
        await timed('download state', () => exec.exec(process.execPath,
            [`${import.meta.dirname}\\download.js`, stateArtifact, BUILD]));
        const archive = ['artifacts.tar.zst', 'artifacts.zip'].map(n => `${BUILD}\\${n}`)
            .find(p => fs.existsSync(p));
        if (!archive) throw new Error('Downloaded build state contains no archive');
        await extractTree(archive);
    }

    await exec.exec('python', ['-m', 'pip', 'install', 'httplib2==0.22.0', 'clang==21.1.7'],
        {cwd: WORK});
    const args = ['platforms\\windows\\build.py', '--ci', '-j', jobs];
    if (mode === 'dev') {
        args.push('--dev');
        if (fs.existsSync(`${BUILD}\\src\\.nadhr-tree-state.json`)) args.push('--resync');
    }
    const retCode = await timed('build.py', () => exec.exec('python', args,
        {cwd: WORK, ignoreReturnCode: true}));

    if (retCode === 0) {
        core.setOutput('finished', true);
        core.setOutput('built_here', true);
        if (mode === 'dev' && core.getBooleanInput('publish_tree')) {
            // Base for later incremental dev builds (main only; one copy, short-lived).
            const archive = await archiveTree(`${WORK}\\dev-tree`);
            await uploadWithRetry(artifact, 'dev-tree', [archive], WORK, 7);
        }
        if (mode === 'release') {
            const globber = await glob.create(`${BUILD}\\dist\\nadhr_*`, {matchDirectories: false});
            await uploadWithRetry(artifact, 'nadhr-windows-x64', await globber.glob(),
                `${BUILD}\\dist`, 14);
        }
    } else if (retCode === BUILD_TIMEOUT_EXIT_CODE) {
        await new Promise(r => setTimeout(r, 5000));
        const archive = await archiveTree(`${WORK}\\artifacts`);
        await uploadWithRetry(artifact, stateArtifact, [archive], WORK, 2);
        core.setOutput('finished', false);
    } else if (retCode === SEED_REQUIRED_EXIT_CODE) {
        throw new Error('The restored dev tree cannot be updated incrementally (see log). ' +
                        'Run build-dev with seed=true.');
    } else {
        throw new Error(`Build failed with exit code ${retCode}`);
    }
}

// Run only as the action's entry point, not when imported (selftest, restore step).
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    run().catch(err => core.setFailed(err.message));
}
