"""B058: closest-string storage limits and independent Hamming predicates."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/archives/SATexamples/sources/sat-closest-string.w'


class ClosestStringBounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'closest.c'
        cls.program = work/'closest'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, records):
        return subprocess.run([str(self.program)], input=records.encode(), capture_output=True,
                              timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_oversized_strings_reject_before_tree_storage(self):
        for n in [10001, 10016]:
            with self.subTest(n=n):
                result = self.encode('0'*n+' 1\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'10000', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertFalse(any(line and not line.startswith(b'~ ')
                                     for line in result.stdout.splitlines()))

    def test_full_supported_length(self):
        result = self.encode('0'*10000+' 1\n')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'~x10000', result.stdout)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_small_projections_match_direct_hamming_distance(self):
        for n in range(2, 5):
            words = list(itertools.product([0, 1], repeat=n))
            for center in words:
                for radius in range(1, n):
                    # A second, complementary center also checks auxiliary namespaces.
                    centers = [center, tuple(1-bit for bit in center)]
                    for rows in [centers[:1], centers]:
                        result = self.encode(''.join(''.join(map(str, row))+f' {radius}\n'
                                                     for row in rows))
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        formula = [line.split() for line in result.stdout.decode().splitlines()
                                   if line.strip() and not line.startswith('~ ')]
                        for word in words:
                            expected = all(sum(a != b for a, b in zip(word, row)) <= radius
                                           for row in rows)
                            fixed = [[('' if bit else '~')+f'x{i}']
                                     for i, bit in enumerate(word, 1)]
                            self.assertEqual(satisfiable(formula+fixed), expected,
                                             (n, rows, radius, word))


if __name__ == '__main__':
    unittest.main()
