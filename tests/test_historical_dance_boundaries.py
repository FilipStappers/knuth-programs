"""B048: historical exact-cover input, reporting and profile boundaries."""
import itertools
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HistoricalDanceBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for name in ['dance', 'gdance', 'xgdance']:
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/(name+'.w')),
                            '-', str(generated)], check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-include', 'stdlib.h',
                            '-O1', '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_matrix(self, name, matrix, args=()):
        return subprocess.run([str(self.programs[name]), *args], input=matrix,
                              capture_output=True, timeout=10,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_missing_or_empty_c_string_header_and_rows_reject_cleanly(self):
        for name in self.programs:
            for data in [b'', b'\0\n', b'A\n\0\n']:
                with self.subTest(program=name, data=data):
                    result = self.run_matrix(name, data)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'AddressSanitizer', result.stderr)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertTrue(b'column' in result.stderr or b'line' in result.stderr)

    def test_all_64_primary_bearing_uncolored_families(self):
        options = [('A',), ('B',), ('A', 'B'), ('A', 'X'), ('B', 'X'), ('A', 'B', 'X')]
        for mask in range(64):
            rows = [r for i, r in enumerate(options) if mask >> i & 1]
            expected = 0
            for choice in itertools.product([False, True], repeat=len(rows)):
                counts = {x: sum(x in row for row, used in zip(rows, choice) if used)
                          for x in ['A', 'B', 'X']}
                expected += counts['A'] == counts['B'] == 1 and counts['X'] <= 1
            matrix = ('A B | X\n'+''.join(' '.join(row)+'\n' for row in rows)).encode()
            for name in self.programs:
                with self.subTest(program=name, mask=mask):
                    result = self.run_matrix(name, matrix)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(int(re.search(rb'Altogether (\d+) solutions', result.stdout)[1]),
                                     expected)


if __name__ == '__main__':
    unittest.main()
