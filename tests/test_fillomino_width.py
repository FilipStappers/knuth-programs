"""B052: bounded Fillomino boards and independent connected-region candidates."""
from collections import Counter
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FillominoWidth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'fillomino.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/fillomino-dlx.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = work/'fillomino'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, data):
        return subprocess.run([str(self.program)], input=data, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_oversized_columns_reject_before_board_or_frame_writes(self):
        for height, width, char in [(1, 17, '.'), (16, 17, '.'), (16, 32, '1'), (17, 16, '1')]:
            with self.subTest(height=height, width=width, char=char):
                result = self.solve(((char*width+'\n')*height).encode())
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'too many', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_maximum_board_and_ragged_row_padding(self):
        result = self.solve((('.'*16+'\n')*16).encode())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        lines = [line.split() for line in result.stdout.decode().splitlines() if not line.startswith('|')]
        self.assertEqual(set(lines[0]), {f'{i:x}{j:x}' for i in range(16) for j in range(16)} | {'|'})
        ragged = self.solve(b'2.\n.\n')
        padded = self.solve(b'2.\n..\n')
        self.assertEqual(ragged.returncode, 0, ragged.stderr.decode())
        self.assertEqual(padded.returncode, 0, padded.stderr.decode())
        self.assertEqual([line for line in ragged.stdout.splitlines() if not line.startswith(b'|')],
                         [line for line in padded.stdout.splitlines() if not line.startswith(b'|')])

    def test_all_two_by_two_clue_candidate_families(self):
        cells = [(i, j) for i in range(2) for j in range(2)]
        def neighbors(p):
            i, j = p
            return {(i+di, j+dj) for di, dj in [(1, 0), (-1, 0), (0, 1), (0, -1)]} & set(cells)
        for values in itertools.product([0, 1, 2], repeat=4):
            clues = dict(zip(cells, values))
            expected = Counter()
            for d in range(1, max(values)+1):
                for candidate in itertools.combinations(cells, d):
                    region = set(candidate)
                    reached = {candidate[0]}
                    while (expanded := reached | set().union(*(neighbors(p) & region for p in reached))) != reached:
                        reached = expanded
                    if reached != region or any(clues[p] not in [0, d] for p in region):
                        continue
                    if any(clues[q] == d for p in region for q in neighbors(p)-region):
                        continue
                    row = [f'{i}{j}' for i, j in region]
                    for i, j in region:
                        if clues[i, j]:
                            continue
                        for ii, jj in neighbors((i, j))-region:
                            if clues[ii, jj]:
                                continue
                            row.append(f'h{max(i, ii)}{j}{d}' if ii != i else f'v{i}{max(j, jj)}{d}')
                    expected[tuple(sorted(row))] += 1
            data = ''.join(''.join(str(clues[i, j]) if clues[i, j] else '.' for j in range(2))+'\n'
                           for i in range(2)).encode()
            with self.subTest(values=values):
                result = self.solve(data)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                lines = [line.split() for line in result.stdout.decode().splitlines() if not line.startswith('|')]
                self.assertEqual(Counter(tuple(sorted(line)) for line in lines[1:]), expected)


if __name__ == '__main__':
    unittest.main()
