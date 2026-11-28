// Round-trip test of the build-state archive on a real Windows runner:
// archiveTree() then extractTree() must reproduce the tree exactly, including
// paths longer than 260 characters (common in Chromium) and binary files.
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as crypto from 'node:crypto';
import { archiveTree, extractTree } from './index.js';

const SRC = 'C:\\nadhr\\build\\src';
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');

function listing(root) {
    const out = {};
    for (const entry of fs.readdirSync(root, {recursive: true, withFileTypes: true})) {
        if (entry.isFile()) {
            const full = path.join(entry.parentPath, entry.name);
            out[path.relative(root, full)] = hash(full);
        }
    }
    return out;
}

fs.rmSync('C:\\nadhr', {recursive: true, force: true});
const deep = path.join(SRC, ...Array(12).fill('third_party_component_directory'));
fs.mkdirSync(deep, {recursive: true});
fs.writeFileSync(path.join(deep, 'long_path_file.cc'), 'int x = 1;\n');
fs.writeFileSync(path.join(SRC, 'binary.bin'), crypto.randomBytes(8 * 1024 * 1024));
fs.writeFileSync(path.join(SRC, 'BUILD.gn'), 'group("x") {}\n');
console.log(`deepest path: ${path.join(deep, 'long_path_file.cc').length} characters`);

const before = listing(SRC);
const archive = await archiveTree('C:\\nadhr\\artifacts');
console.log(`archive: ${archive} (${fs.statSync(archive).size} bytes)`);
fs.renameSync(SRC, `${SRC}.orig`);
const restored = path.join('C:\\nadhr\\build', path.basename(archive));
fs.renameSync(archive, restored);
await extractTree(restored);
const after = listing(SRC);

const same = JSON.stringify(before) === JSON.stringify(after);
console.log(`${Object.keys(before).length} files; round trip identical: ${same}`);
if (!same) {
    console.log('before', before, 'after', after);
    process.exit(1);
}
