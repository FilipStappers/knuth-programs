"""B052: generalized Sudoku matrices and direct filling families."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GeneralSudoku(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'sudoku.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/sudoku-general-dlx.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = work/'sudoku'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, data):
        return subprocess.run([str(self.program)], input=data, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_unsigned_box_bits_for_all_supported_sizes(self):
        for n in [1, 2, 9, 32]:
            with self.subTest(n=n):
                result = self.solve((('.'*n+'\n')*n).encode())
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                lines = [line.split() for line in result.stdout.decode().splitlines()
                         if not line.startswith('|sudoku')]
                self.assertEqual(len(lines)-1, n**3)
                self.assertEqual(lines[0].count('|'), 1)


if __name__ == '__main__':
    unittest.main()
