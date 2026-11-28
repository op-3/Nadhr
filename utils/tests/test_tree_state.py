# Copyright 2026 The Nadhr Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for incremental tree resync: the result must equal a fresh application."""

import difflib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tree_state  # pylint: disable=wrong-import-position

UPSTREAM = {
    'chrome/a.cc': 'int a = 1;\nint keep = 0;\n',
    'chrome/b.cc': 'int b = 1;\n',
    'third_party/dep/c.cc': 'int c = 1;\n',  # lives in its own git repo, like gclient deps
}


def _git(cwd, *args):
    subprocess.run(['git', '-c', 'core.autocrlf=false', *args], cwd=cwd, check=True,
                   capture_output=True)


def _patch(rel, before, after):
    """A unified diff from `before` to `after` (None = file absent)."""
    a = before.splitlines(True) if before is not None else []
    b = after.splitlines(True)
    return ''.join(difflib.unified_diff(a, b, '/dev/null' if before is None else f'a/{rel}',
                                        f'b/{rel}'))


class ResyncTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.layers = [self.tmp / 'upstream', self.tmp / 'nadhr']
        for layer in self.layers:
            layer.mkdir()
        self.base = self.tmp / 'base.ini'
        self.base.write_text('pinned', encoding='utf-8')
        self._set_series(0, {'up.patch': _patch('chrome/b.cc', UPSTREAM['chrome/b.cc'],
                                                'int b = 2;\n')})

    def _set_series(self, index, patches):
        layer = self.layers[index]
        for old in layer.glob('*.patch'):
            old.unlink()
        for name, text in patches.items():
            (layer / name).write_text(text, encoding='utf-8', newline='\n')
        (layer / 'series').write_text(''.join(f'{n}\n' for n in patches), encoding='utf-8')

    def _fresh_tree(self, name):
        tree = self.tmp / name
        for rel, text in UPSTREAM.items():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            (tree / rel).write_text(text, encoding='utf-8', newline='\n')
        _git(tree / 'third_party' / 'dep', 'init', '-q')
        _git(tree / 'third_party' / 'dep', 'add', '.')
        _git(tree / 'third_party' / 'dep', '-c', 'user.email=t@t', '-c', 'user.name=t',
             'commit', '-qm', 'dep')
        _git(tree, 'init', '-q')
        (tree / '.gitignore').write_text('third_party/dep/\n', encoding='utf-8')
        _git(tree, 'add', '.')
        _git(tree, '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-qm', 'src')
        for layer in self.layers:
            for rel in tree_state._series(layer):  # pylint: disable=protected-access
                _git(tree, 'apply', str(layer / rel))
        return tree

    def _state(self):
        return tree_state.describe(self.layers, {'base.ini': self.base})

    def _contents(self, tree):
        return {p.relative_to(tree).as_posix(): p.read_text(encoding='utf-8')
                for p in tree.rglob('*') if p.is_file() and '.git' not in p.parts
                and p.name not in (tree_state.STATE_NAME, '.gitignore')}

    def _assert_resync_equals_fresh(self, nadhr_v1, nadhr_v2):
        self._set_series(1, nadhr_v1)
        built = self._fresh_tree('built')
        tree_state.write_state(built, self._state())
        self._set_series(1, nadhr_v2)
        changed = tree_state.resync(built, self.layers, self._state())
        self.assertEqual(self._contents(built), self._contents(self._fresh_tree('fresh')))
        return changed

    def test_changed_patch_resets_and_reapplies_only_its_files(self):
        v1 = {'n.patch': _patch('chrome/a.cc', UPSTREAM['chrome/a.cc'], 'int a = 5;\nint keep = 0;\n')}
        v2 = {'n.patch': _patch('chrome/a.cc', UPSTREAM['chrome/a.cc'], 'int a = 6;\nint keep = 0;\n')}
        self.assertEqual(self._assert_resync_equals_fresh(v1, v2), ['chrome/a.cc'])

    def test_upstream_hunks_on_the_same_file_are_kept(self):
        # Nadhr and upstream both patch chrome/b.cc; resetting it must re-apply upstream too.
        up_result = 'int b = 2;\n'
        v1 = {'n.patch': _patch('chrome/b.cc', up_result, 'int b = 2;\nint n = 1;\n')}
        v2 = {'n.patch': _patch('chrome/b.cc', up_result, 'int b = 2;\nint n = 2;\n')}
        self._assert_resync_equals_fresh(v1, v2)

    def test_removed_patch_creating_a_file_deletes_it(self):
        v1 = {'new.patch': _patch('chrome/new.cc', None, 'int fresh = 1;\n')}
        self.assertEqual(self._assert_resync_equals_fresh(v1, {}), ['chrome/new.cc'])

    def test_file_in_a_nested_dependency_repo(self):
        v1 = {'d.patch': _patch('third_party/dep/c.cc', UPSTREAM['third_party/dep/c.cc'], 'int c = 7;\n')}
        v2 = {'d.patch': _patch('third_party/dep/c.cc', UPSTREAM['third_party/dep/c.cc'], 'int c = 8;\n')}
        self._assert_resync_equals_fresh(v1, v2)

    def test_unchanged_series_touches_nothing(self):
        v1 = {'n.patch': _patch('chrome/a.cc', UPSTREAM['chrome/a.cc'], 'int a = 5;\nint keep = 0;\n')}
        self.assertEqual(self._assert_resync_equals_fresh(v1, v1), [])

    def test_base_change_requires_seed(self):
        self._set_series(1, {})
        built = self._fresh_tree('built')
        tree_state.write_state(built, self._state())
        self.base.write_text('bumped', encoding='utf-8')
        with self.assertRaisesRegex(tree_state.SeedRequired, 'base.ini'):
            tree_state.resync(built, self.layers, self._state())

    def test_upstream_series_change_requires_seed(self):
        self._set_series(1, {})
        built = self._fresh_tree('built')
        tree_state.write_state(built, self._state())
        self._set_series(0, {})
        with self.assertRaisesRegex(tree_state.SeedRequired, 'upstream'):
            tree_state.resync(built, self.layers, self._state())

    def test_missing_state_requires_seed(self):
        with self.assertRaises(tree_state.SeedRequired):
            tree_state.read_state(self.tmp)


if __name__ == '__main__':
    unittest.main()
