"""B058: progression lengths, termination and independent binary-word predicates."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'


def no_progression(values, length, bit):
    return not any(all(values[start+j*step] == bit for j in range(length))
                   for step in range(1, len(values)+1)
                   for start in range(len(values)-(length-1)*step))


class ProgressionLengths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for name in ['waerden', 'arithprog']:
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(SOURCES/('sat-'+name+'.w')), '-', str(generated)],
                           check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[name] = program
        # Exact F3 values derived by direct word enumeration, not imported labels.
        cls.minima = []
        for count in range(1, 6):
            cls.minima.append(next(n for n in range(count, 10)
                                   if any(sum(bits) == count and no_progression(bits, 3, 1)
                                          for bits in itertools.product([0, 1], repeat=n))))
        (cls.work/'free3.dat').write_text(' '.join(map(str, cls.minima))+'\n')
        for t in [0, 1, 2, 2147483647]:
            (cls.work/f'free{t}.dat').write_text('1\n')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, name, parameters, discard=False):
        return subprocess.run([str(self.programs[name]), *map(str, parameters)], cwd=self.work,
                              stdout=subprocess.DEVNULL if discard else subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=0.3 if discard else 5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_singleton_and_invalid_progression_lengths_reject_without_looping(self):
        for name, parameters in [('waerden', [1, 2, 1]), ('waerden', [2, 1, 1]),
                                  ('waerden', [0, 2, 1]), ('waerden', [-1, 2, 1]),
                                  ('arithprog', [1, 3, 2]), ('arithprog', [0, 3, 2])]:
            with self.subTest(name=name, parameters=parameters):
                try:
                    result = self.encode(name, parameters, discard=True)
                except subprocess.TimeoutExpired:
                    self.fail('Invalid progression length did not reject within the bounded run')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'progression', result.stderr.lower())
                self.assertNotIn(b'runtime error', result.stderr)

    def test_arithprog_parameter_bounds_and_large_progression_filename(self):
        for n, r in [(-1, 0), (-2147483648, 0), (0, 1), (3, -1), (3, 4), (100, 101)]:
            with self.subTest(n=n, r=r):
                result = self.encode('arithprog', [3, n, r])
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertEqual(result.stdout, b'')
        result = self.encode('arithprog', [2147483647, 1, 1])
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        formula = [line.split() for line in result.stdout.decode().splitlines()
                   if line.strip() and not line.startswith('~ ')]
        self.assertTrue(satisfiable(formula+[['x1']]))
        self.assertFalse(satisfiable(formula+[['~x1']]))

    def test_every_small_two_color_progression_projection(self):
        for n in range(9):
            for k, l in itertools.product(range(2, 5), repeat=2):
                result = self.encode('waerden', [k, l, n])
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                formula = [line.split() for line in result.stdout.decode().splitlines()
                           if line.strip() and not line.startswith('~ ')]
                for bits in itertools.product([0, 1], repeat=n):
                    expected = no_progression(bits, k, 0) and no_progression(bits, l, 1)
                    fixed = [[('' if bit else '~')+str(i)] for i, bit in enumerate(bits, 1)]
                    with self.subTest(n=n, k=k, l=l, bits=bits):
                        self.assertEqual(satisfiable(formula+fixed), expected)

    def test_extremal_candidate_domain_uses_independent_prior_minima(self):
        for r, minimum in enumerate(self.minima, 1):
            for n in sorted({r, max(r, minimum-1), minimum}):
                result = self.encode('arithprog', [3, n, r])
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                formula = [line.split() for line in result.stdout.decode().splitlines()
                           if line.strip() and not line.startswith('~ ')]
                for bits in itertools.product([0, 1], repeat=n):
                    expected = sum(bits) == r and no_progression(bits, 3, 1)
                    if r % 2:
                        j, k = (n-r+1)//2, (r+1)//2
                        expected &= sum(bits[:j+k-1]) < k
                    elif n % 2 == 0:
                        expected &= sum(bits[:n//2]) >= r//2
                    fixed = [[('' if bit else '~')+f'x{i}'] for i, bit in enumerate(bits, 1)]
                    with self.subTest(n=n, r=r, bits=bits):
                        self.assertEqual(satisfiable(formula+fixed), expected)

    def test_nonextremal_valid_progression_free_word(self):
        result = self.encode('arithprog', [3, 5, 3])
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        formula = [line.split() for line in result.stdout.decode().splitlines()
                   if line.strip() and not line.startswith('~ ')]
        bits = [0, 1, 0, 1, 1]
        self.assertTrue(no_progression(bits, 3, 1))
        fixed = [[('' if bit else '~')+f'x{i}'] for i, bit in enumerate(bits, 1)]
        self.assertTrue(satisfiable(formula+fixed))

    def test_all_small_arithprog_cardinalities(self):
        for n in range(9):
            for r in range(min(n, 5)+1):
                result = self.encode('arithprog', [3, n, r])
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                formula = [line.split() for line in result.stdout.decode().splitlines()
                           if line.strip() and not line.startswith('~ ')]
                for bits in itertools.product([0, 1], repeat=n):
                    expected = sum(bits) == r and no_progression(bits, 3, 1)
                    if r % 2:
                        j, k = (n-r+1)//2, (r+1)//2
                        expected &= sum(bits[:j+k-1]) < k
                    elif n % 2 == 0:
                        expected &= sum(bits[:n//2]) >= r//2
                    fixed = [[('' if bit else '~')+f'x{i}'] for i, bit in enumerate(bits, 1)]
                    self.assertEqual(satisfiable(formula+fixed), expected, (n, r, bits))


if __name__ == '__main__':
    unittest.main()
