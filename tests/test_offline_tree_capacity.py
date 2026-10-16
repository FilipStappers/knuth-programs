"""B008: reject excess permutation entries before writing bounded storage."""
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def insertion_tree(permutation):
    root = permutation[0]
    left, right = {}, {}
    for value in permutation[1:]:
        at = root
        while True:
            links = left if value < at else right
            if at not in links:
                links[at] = value
                break
            at = links[at]
    return root, [(left.get(k, 0), right.get(k, 0))
                  for k in range(1, len(permutation)+1)]


class OfflineTreeCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'offline-tree-insertion.c'
        cls.program = work/'offline-tree-insertion'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/offline-tree-insertion.w'),
                        '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_input(self, permutation):
        return subprocess.run([str(self.program)], capture_output=True, timeout=5,
                              input=(' '.join(map(str, permutation))+'\n').encode())

    def test_capacity_rejected_before_storage(self):
        for length in [1025, 1026]:
            result = self.run_input([1]*length)
            with self.subTest(length=length):
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'too many elements', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)

    def assert_tree(self, permutation):
        result = self.run_input(permutation)
        self.assertEqual(result.stderr, b'')
        lines = result.stdout.decode().splitlines()
        self.assertTrue(lines, result.stdout)
        root = int(re.fullmatch(r'The root is (\d+)\.', lines[0])[1])
        actual = []
        for k, line in enumerate(lines[1:], 1):
            label, children = line.split(':')
            self.assertEqual(int(label), k)
            a, b = children.rstrip('.').split(',')
            actual.append(tuple(int(x) if x.strip().isdigit() else 0 for x in [a, b]))
        self.assertEqual((root, actual), insertion_tree(permutation))

    def test_complete_small_permutation_families(self):
        for n in range(1, 7):
            for permutation in itertools.permutations(range(1, n+1)):
                self.assert_tree(permutation)

    def test_full_capacity(self):
        self.assert_tree(list(range(1, 1025)))
        self.assert_tree(list(range(1024, 0, -1)))


if __name__ == '__main__':
    unittest.main()
