"""B052/B060: queen-generator label ranges and complete coordinate matrices."""
from collections import Counter
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QueenGeneratorBounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        for name in ['queens', 'queens-dlx']:
            generated = work/(name+'.c')
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/(name+'.w')), '-', str(generated)],
                           check=True, capture_output=True)
            program = work/name
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, name, n):
        return subprocess.run([str(self.programs[name]), str(n)], capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_reject_before_dimension_arithmetic_or_label_overflow(self):
        for name, maximum in [('queens', 21), ('queens-dlx', 32)]:
            for n in [0, -1, -2147483648, maximum+1, 2147483647]:
                with self.subTest(name=name, n=n):
                    result = self.solve(name, n)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b'n must', result.stderr)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertEqual(result.stdout, b'')

    def test_all_options_match_direct_row_column_and_diagonal_coordinates(self):
        alphabet = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for name, maximum in [('queens', 21), ('queens-dlx', 32)]:
            alphabet = ('0123456789'+''.join(chr(c) for c in range(ord('a'), ord('~')+1))
                        if name == 'queens' else '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
            for n in [1, 2, 3, 4, 5, 6, maximum]:
                with self.subTest(name=name, n=n):
                    result = self.solve(name, n)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    lines = [line.split() for line in result.stdout.decode().splitlines()
                             if not line.startswith('|')]
                    expected = Counter()
                    for i in range(n):
                        for j in range(n):
                            row = ['r'+alphabet[i], 'c'+alphabet[j]]
                            if 0 < i+j < 2*n-2:
                                row.append('a'+alphabet[i+j])
                            if 0 < n-1-i+j < 2*n-2:
                                row.append('b'+alphabet[n-1-i+j])
                            expected[tuple(sorted(row))] += 1
                    primary = {'r'+alphabet[i] for i in range(n)} | {'c'+alphabet[i] for i in range(n)}
                    secondary = {prefix+alphabet[i] for prefix in 'ab' for i in range(1, 2*n-2)}
                    self.assertEqual(set(lines[0][:lines[0].index('|')]), primary)
                    self.assertEqual(set(lines[0][lines[0].index('|')+1:]), secondary)
                    self.assertEqual(Counter(tuple(sorted(row)) for row in lines[1:]), expected)


if __name__ == '__main__':
    unittest.main()
