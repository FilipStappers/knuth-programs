"""B052: relation-coordinate storage and independent indicator matrices."""
from collections import Counter
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IndicatorBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'indicator.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/indicator-dlx.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = work/'indicator'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, d, k, tuples):
        return subprocess.run([str(self.program), str(d), str(k), *tuples], capture_output=True,
                              timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_excess_relation_arity_rejects_before_tuple_writes(self):
        for tuples in [['0'*11], ['0'*100], ['0'*11, '/', '0'], ['0', '/', '0'*11]]:
            with self.subTest(tuples=tuples):
                result = self.solve(2, 1, tuples)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'Relation arity', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_all_supported_relation_arities_match_independent_matrices(self):
        for arity in range(1, 11):
            tuples = [''.join(str((i+j) % 2) for j in range(arity)) for i in range(2)]
            for k in [1, 2]:
                with self.subTest(arity=arity, k=k):
                    expected = Counter()
                    primary = set()
                    for indices in itertools.product(range(2), repeat=k):
                        item = 'a'+''.join(map(str, indices))
                        primary.add(item)
                        for output in tuples:
                            mapping = {}
                            for j in range(arity):
                                args = ''.join(tuples[index][j] for index in indices)
                                mapping.setdefault(args, set()).add(output[j])
                            if all(len(values) == 1 for values in mapping.values()):
                                expected[tuple(sorted([item]+[args+':'+next(iter(values))
                                                               for args, values in mapping.items()]))] += 1
                    result = self.solve(2, k, tuples)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    lines = [line.split() for line in result.stdout.decode().splitlines()
                             if not line.startswith('|')]
                    separator = lines[0].index('|')
                    self.assertEqual(set(lines[0][:separator]), primary)
                    self.assertEqual(set(lines[0][separator+1:]),
                                     {''.join(args) for args in itertools.product('01', repeat=k)})
                    self.assertEqual(Counter(tuple(sorted(row)) for row in lines[1:]), expected)


if __name__ == '__main__':
    unittest.main()
