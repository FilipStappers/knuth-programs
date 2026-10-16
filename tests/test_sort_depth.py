"""B059: enforce documented sorting depth and check tiny network semantics."""
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable
from test_dimacs_empty_clause import native_clauses

ROOT = Path(__file__).resolve().parents[1]


class SortDepth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        source = ROOT/'programs/archives/SATexamples/sources/sat-mintime-sort.w'
        generated = work/'sort.c'
        cls.program = work/'sort'
        subprocess.run(['ctangle', str(source), '-', str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, depth):
        return subprocess.run([str(self.program), '3', str(depth)],
                              capture_output=True, timeout=5)

    def test_invalid_depths_reject_before_output(self):
        for depth in [0, -1, -2147483648, 10, 2147483647]:
            with self.subTest(depth=depth):
                result = self.encode(depth)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertNotIn(b'runtime error', result.stderr)

    def test_all_three_wire_networks_through_depth_three(self):
        pairs = [(1, 2), (1, 3), (2, 3)]
        for depth in range(1, 4):
            result = self.encode(depth)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            clauses = native_clauses(result.stdout.decode())
            for layers in itertools.product([None, *pairs], repeat=depth):
                units = [[('' if pair == chosen else '~')+f'{pair[0]}{pair[1]}C{t}']
                         for t, chosen in enumerate(layers, 1) for pair in pairs]
                sorts = True
                for bits in itertools.product([0, 1], repeat=3):
                    output = list(bits)
                    for pair in layers:
                        if pair:
                            i, j = pair[0]-1, pair[1]-1
                            output[i], output[j] = min(output[i], output[j]), max(output[i], output[j])
                    sorts &= output == sorted(bits)
                with self.subTest(depth=depth, layers=layers):
                    self.assertEqual(satisfiable(clauses+units), sorts)


if __name__ == '__main__':
    unittest.main()
