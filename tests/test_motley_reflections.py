"""B052: independent rectangle dissections and coverage of reflection orbits."""
from collections import Counter
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def dissections(m, n):
    rectangles = []
    for a, b in itertools.combinations(range(m+1), 2):
        for c, d in itertools.combinations(range(n+1), 2):
            if (a, b) == (0, m) or (c, d) == (0, n):
                continue
            cells = sum(1 << (i*n+j) for i in range(a, b) for j in range(c, d))
            rectangles.append(((a, b, c, d), cells))
    by_cell = [[pair for pair in rectangles if pair[1] >> i & 1] for i in range(m*n)]
    full = (1 << (m*n))-1
    result = set()
    def visit(occupied, xs, ys, chosen):
        if occupied == full:
            if {r[0] for r in chosen} == set(range(m)) and {r[2] for r in chosen} == set(range(n)):
                result.add(tuple(sorted(chosen)))
            return
        empty = full ^ occupied
        cell = (empty & -empty).bit_length()-1
        for rectangle, mask in by_cell[cell]:
            a, b, c, d = rectangle
            if occupied & mask or (a, b) in xs or (c, d) in ys:
                continue
            visit(occupied | mask, xs | {(a, b)}, ys | {(c, d)}, chosen+[rectangle])
    visit(0, set(), set(), [])
    return result


class MotleyReflections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'motley.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/motley-dlx.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = work/'motley'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_native_matrix_preserves_every_independent_reflection_orbit(self):
        for m, n in [(4, 4), (4, 5), (5, 4), (5, 5), (6, 6)]:
            with self.subTest(m=m, n=n):
                result = subprocess.run([str(self.program), str(m), str(n)], capture_output=True,
                                        timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                lines = [line.split() for line in result.stdout.decode().splitlines() if not line.startswith('|')]
                split = lines[0].index('|')
                bounds = {}
                for token in lines[0][:split]:
                    if '|' in token:
                        limits, name = token.split('|')
                        bounds[name] = tuple(map(int, limits.split(':')))
                    else:
                        bounds[token] = (1, 1)
                secondary = set(lines[0][split+1:])
                native = {}
                for row in lines[1:]:
                    x = next(t for t in row if t.startswith('x') and len(t) == 3)
                    y = next(t for t in row if t.startswith('y') and len(t) == 3)
                    native[tuple(map(int, x[1:]+y[1:]))] = row
                def accepts(dissection):
                    if any(rectangle not in native for rectangle in dissection):
                        return False
                    counts = Counter(t for rectangle in dissection for t in native[rectangle])
                    return (all(lo <= counts[name] <= hi for name, (lo, hi) in bounds.items())
                            and all(counts[name] <= 1 for name in secondary))
                family = dissections(m, n)
                if (m, n) == (6, 6):
                    self.assertEqual(len(family), 11700)
                orbits = set()
                lost = []
                retained_total = 0
                for dissection in family:
                    reflected = tuple(sorted((a, b, n-d, n-c) for a, b, c, d in dissection))
                    self.assertIn(reflected, family)
                    orbit = frozenset([dissection, reflected])
                    if orbit in orbits:
                        continue
                    orbits.add(orbit)
                    retained = sum(accepts(s) for s in orbit)
                    retained_total += retained
                    if not retained:
                        lost.append(dissection)
                    else:
                        top = next(r for r in dissection if r[1] == 1)
                        bottom = next(r for r in dissection if r[0] == m-1)
                        both_centered = top[2]+top[3] == n and bottom[2]+bottom[3] == n
                        self.assertEqual(retained, len(orbit) if both_centered else 1)
                self.assertEqual(lost, [], f'{len(lost)} entire reflection orbits lost')
                if (m, n) == (6, 6):
                    self.assertEqual(len(orbits), 5850)
                    self.assertEqual(retained_total, 5898)


if __name__ == '__main__':
    unittest.main()
