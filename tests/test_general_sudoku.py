"""B052: generalized Sudoku matrices and direct filling families."""
import os
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_dlx6_memo import subsets

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

    def test_holes_do_not_increase_region_coverage_demands(self):
        groups_cases = [[], [['00', '..']], [['00', '..'], ['1.', '1.']]]
        positions = [(i, j) for i in range(2) for j in range(2)]
        for mask in range(16):
            holes = {p for bit, p in enumerate(positions) if mask >> bit & 1}
            grid = [''.join('#' if (i, j) in holes else '.' for j in range(2)) for i in range(2)]
            cells = [p for p in positions if p not in holes]
            for groups in groups_cases:
                with self.subTest(mask=mask, groups=groups):
                    regions = [{(i, j) for i, j in cells if group[i][j] == label}
                               for group in groups for label in '01']
                    units = [{(i, j) for j in range(2)} for i in range(2)]
                    units += [{(i, j) for i in range(2)} for j in range(2)]
                    units += regions
                    expected = set()
                    for values in itertools.product([1, 2], repeat=len(cells)):
                        filling = dict(zip(cells, values))
                        if all(len(vals := [value for p, value in filling.items() if p in unit])
                               == len(set(vals)) for unit in units):
                            expected.add(tuple(sorted(filling.items())))
                    data = ('\n'.join(grid+sum(groups, []))+'\n').encode()
                    result = self.solve(data)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    lines = [line.split() for line in result.stdout.decode().splitlines()
                             if not line.startswith('|sudoku')]
                    primary = lines[0][:lines[0].index('|')]
                    rows = lines[1:]
                    actual = set()
                    for chosen in subsets(rows, primary):
                        filling = {}
                        for index in chosen:
                            row = rows[index-1]
                            pos = next(t for t in row if t.startswith('p'))
                            digit = int(next(t for t in row if t.startswith('r'))[2])
                            filling[int(pos[1]), int(pos[2])] = digit
                        actual.add(tuple(sorted(filling.items())))
                    self.assertEqual(actual, expected)

    def test_clue_values_must_fit_the_board(self):
        for data in [b'2\n', b'9\n', b'w\n', b'3.\n..\n', b'..\n.w\n']:
            with self.subTest(data=data):
                result = self.solve(data)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'Clue', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertEqual(result.stdout, b'')
        for data in [b'1\n', b'2.\n.1\n']:
            result = self.solve(data)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

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
