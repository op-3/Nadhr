// Adapted from ungoogled-chromium-windows (BSD-3-Clause).
// Runs one time-limited build stage. A stage either finishes the build and
// uploads packages, or hits its time budget and uploads the partial tree so
// the next stage can resume.
import * as core from '@actions/core';
import * as io from '@actions/io';
import * as exec from '@actions/exec';
import { DefaultArtifactClient } from '@actions/artifact';
import * as glob from '@actions/glob';

const BUILD_TIMEOUT_EXIT_CODE = 124;
const WORK = 'C:\\nadhr';
const STATE_ARTIFACT = 'build-state-windows-x64';
const PACKAGE_ARTIFACT = 'nadhr-windows-x64';

async function uploadWithRetry(artifact, name, files, rootDir, retentionDays) {
    for (let i = 0; i < 5; ++i) {
        try { await artifact.deleteArtifact(name); } catch (e) { /* not there yet */ }
        try {
            await artifact.uploadArtifact(name, files, rootDir, {retentionDays, compressionLevel: 0});
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
    console.log(`finished: ${finished}, from_artifact: ${fromArtifact}`);
    if (finished) {
        core.setOutput('finished', true);
        return;
    }

    const artifact = new DefaultArtifactClient();
    if (fromArtifact) {
        await exec.exec(process.execPath, [`${import.meta.dirname}\\download.js`, STATE_ARTIFACT,
            `${WORK}\\build`]);
        await exec.exec('7z', ['x', `${WORK}\\build\\artifacts.zip`, `-o${WORK}\\build`, '-y']);
        await io.rmRF(`${WORK}\\build\\artifacts.zip`);
    }

    await exec.exec('python', ['-m', 'pip', 'install', 'httplib2==0.22.0', 'clang==21.1.7'],
        {cwd: WORK});
    const retCode = await exec.exec('python', ['platforms\\windows\\build.py', '--ci', '-j', '2'],
        {cwd: WORK, ignoreReturnCode: true});

    if (retCode === 0) {
        core.setOutput('finished', true);
        const globber = await glob.create(`${WORK}\\build\\dist\\nadhr_*`, {matchDirectories: false});
        await uploadWithRetry(artifact, PACKAGE_ARTIFACT, await globber.glob(),
            `${WORK}\\build\\dist`, 14);
    } else if (retCode === BUILD_TIMEOUT_EXIT_CODE) {
        await new Promise(r => setTimeout(r, 5000));
        await exec.exec('7z', ['a', '-tzip', `${WORK}\\artifacts.zip`, `${WORK}\\build\\src`,
            '-mx=3', '-mtc=on'], {ignoreReturnCode: true});
        await uploadWithRetry(artifact, STATE_ARTIFACT, [`${WORK}\\artifacts.zip`], WORK, 2);
        core.setOutput('finished', false);
    } else {
        throw new Error(`Build failed with exit code ${retCode}`);
    }
}

run().catch(err => core.setFailed(err.message));
