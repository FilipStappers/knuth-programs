"""B060: incomplete legacy Sudoku input and independent candidate matrices."""
from collections import Counter
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LegacySudokuEof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'sudoku.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/sudoku.w'), '-', str(generated)],
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

    def test_missing_rows_reject_before_matrix_output(self):
        for rows in range(9):
            with self.subTest(rows=rows):
                result = self.solve(b'.........\n'*rows)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'nine', result.stderr)
                self.assertEqual(result.stdout, b'')
                self.assertNotIn(b'runtime error', result.stderr)

    def test_complete_candidate_matrices(self):
        rng = random.Random(60001)
        for case in range(12):
            grid = [[(i*3+i//3+j) % 9+1 if (case == 0 or (case != 1 and rng.randrange(3))) else 0
                     for j in range(9)] for i in range(9)]
            given_rows = [{v for v in grid[i] if v} for i in range(9)]
            given_cols = [{grid[i][j] for i in range(9)}-{0} for j in range(9)]
            given_boxes = [{grid[i][j] for i in range(9) for j in range(9)
                            if i//3*3+j//3 == b}-{0} for b in range(9)]
            header, options = set(), Counter()
            for i in range(9):
                for j in range(9):
                    if grid[i][j]:
                        continue
                    header.add(f'p{i}{j}')
                    for d in range(1, 10):
                        b = i//3*3+j//3
                        if d not in given_rows[i] | given_cols[j] | given_boxes[b]:
                            options[tuple(sorted([f'p{i}{j}', f'r{i}{d}', f'c{j}{d}', f'b{b}{d}']))] += 1
            for unit in range(9):
                for d in range(1, 10):
                    for prefix, given in [('r', given_rows), ('c', given_cols), ('b', given_boxes)]:
                        if d not in given[unit]:
                            header.add(f'{prefix}{unit}{d}')
            data = ''.join(''.join(str(v) if v else '.' for v in row)+'\n' for row in grid).encode()
            with self.subTest(case=case):
                result = self.solve(data)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                lines = result.stdout.decode().splitlines()
                self.assertEqual(set(lines[0].split()), header)
                self.assertEqual(Counter(tuple(sorted(line.split())) for line in lines[1:]), options)


if __name__ == '__main__':
    unittest.main()
