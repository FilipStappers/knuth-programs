"""B059: duplicate declarations and tiny tomography projections."""
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable
from test_dimacs_empty_clause import native_clauses

ROOT = Path(__file__).resolve().parents[1]


class TomographyInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'tomography.c'
        cls.program = work/'tomography'
        subprocess.run(['ctangle', str(ROOT/'programs/archives/SATexamples/sources/sat-tomography.w'),
                        '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, data):
        return subprocess.run([str(self.program)], input=data.encode(),
                              capture_output=True, timeout=5)

    def test_duplicate_values_including_zero_reject(self):
        for family in 'rcab':
            for first, second in itertools.product([0, 1], repeat=2):
                result = self.encode(f'{family}1={first}\n{family}1={second}\n')
                with self.subTest(family=family, first=first, second=second):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b'already been given', result.stderr)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertEqual(result.stdout, b'')

    def test_all_two_by_two_projections_with_explicit_zeros(self):
        matrices = list(itertools.product([0, 1], repeat=4))
        def sums(bits):
            a, b, c, d = bits
            return [a+b, c+d, a+c, b+d, a, b+c, d, b, a+d, c]
        keys = ['r1', 'r2', 'c1', 'c2', 'a1', 'a2', 'a3', 'b1', 'b2', 'b3']
        for original in matrices:
            expected = sums(original)
            data = ''.join(f'{key}={value}\n' for key, value in zip(keys, expected))
            result = self.encode(data)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            clauses = native_clauses(result.stdout.decode())
            for candidate in matrices:
                units = [[('' if bit else '~')+f'{i//2+1}x{i%2+1}']
                         for i, bit in enumerate(candidate)]
                with self.subTest(original=original, candidate=candidate):
                    self.assertEqual(satisfiable(clauses+units), sums(candidate) == expected)


if __name__ == '__main__':
    unittest.main()
