"""B048: direct degree/connectivity oracle for the specialized loop change."""
import itertools
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def grid(h, w):
    vertices = [(2*x, 2*y) for x in range(h) for y in range(w)]
    edges = [(u, (u[0]+dx, u[1]+dy)) for u in vertices for dx, dy in [(2, 0), (0, 2)]
             if (u[0]+dx, u[1]+dy) in vertices]
    name = lambda v: ''.join(map(str, v))
    midpoint = lambda e: ((e[0][0]+e[1][0])//2, (e[0][1]+e[1][1])//2)
    lines = [' '.join(map(name, vertices))+' | '+' '.join(name(midpoint(e)) for e in edges)]
    for vertex in vertices:
        incident = [e for e in edges if vertex in e]
        for bits in itertools.product([0, 1], repeat=len(incident)):
            if sum(bits) in [0, 2]:
                lines.append(name(vertex)+' '+ ' '.join(name(midpoint(e))+':'+str(bit)
                                                       for e, bit in zip(incident, bits)))
    expected = set()
    for mask in range(1, 1 << len(edges)):
        chosen = [e for i, e in enumerate(edges) if mask >> i & 1]
        degree = {v: sum(v in e for e in chosen) for v in vertices}
        if any(d not in [0, 2] for d in degree.values()):
            continue
        seen, todo = {chosen[0][0]}, [chosen[0][0]]
        while todo:
            u = todo.pop()
            for a, b in chosen:
                if u in (a, b):
                    v = b if u == a else a
                    if v not in seen:
                        seen.add(v)
                        todo.append(v)
        if len(seen) == sum(d > 0 for d in degree.values()):
            expected.add(mask)
    return ('\n'.join(lines)+'\n').encode(), edges, expected


class DlxLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for DLX2 loop integration checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        text = (ROOT/'programs/programs/dlx2.w').read_text()
        for key, value in [('max_level', 128), ('max_cols', 256), ('max_nodes', 8192)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        source = cls.work/'dlx2.w'
        source.write_text(text)
        generated = cls.work/'loop.c'
        subprocess.run(['ctangle', str(source), str(ROOT/'programs/programs/dlx2-loop.ch'),
                        str(generated)], check=True, capture_output=True)
        cls.program = cls.work/'loop'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-I'+sgb, '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), str(Path(sgb)/'gb_flip.c'), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_matrix(self, matrix):
        return subprocess.run([str(self.program), 'm1', 'v1'], input=matrix,
                              capture_output=True, timeout=10,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_all_zero_edges_are_not_a_cycle(self):
        result = self.run_matrix(b'00 02 | 01\n00 01:0\n02 01:0\n')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertRegex(result.stderr, rb'Altogether 0 solutions?')
        self.assertEqual(result.stdout, b'')

    def test_high_boundary_edges_reject_before_neighbor_lookup(self):
        for matrix in [b'Y0 | Z0\nY0 Z0:0\n', b'0Y | 0Z\n0Y 0Z:0\n']:
            with self.subTest(matrix=matrix):
                result = self.run_matrix(matrix)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'nonexistent vertex', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)

    def test_last_valid_high_coordinate_square_is_accepted(self):
        matrix, _, _ = grid(2, 2)
        # Shift the 0/1/2 coordinate square to W/X/Y = 58/59/60.
        translation = bytes.maketrans(b'012', b'WXY')
        shifted = b'\n'.join(b' '.join(token[:2].translate(translation)+token[2:]
                                     for token in line.split())
                             for line in matrix.splitlines())+b'\n'
        result = self.run_matrix(shifted)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertRegex(result.stderr, rb'Altogether 1 solution')
        self.assertEqual(len(result.stdout.splitlines()), 1)

    def test_complete_small_grid_cycle_families(self):
        for h, w, count in [(2, 2, 1), (2, 3, 3), (3, 3, 13)]:
            with self.subTest(h=h, w=w):
                matrix, edges, expected = grid(h, w)
                self.assertEqual(len(expected), count)
                result = self.run_matrix(matrix)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(int(re.search(rb'Altogether (\d+) solutions?', result.stderr)[1]), count)
                edge_ids = {frozenset(e): i for i, e in enumerate(edges)}
                actual = []
                for line in result.stdout.splitlines():
                    points = [tuple(map(int, token.decode())) for token in line.split(b':')[1].split()]
                    self.assertGreaterEqual(len(points), 5)
                    self.assertEqual(points[0], points[-1])
                    self.assertEqual(len(set(points[:-1])), len(points)-1)
                    mask = 0
                    for u, v in zip(points, points[1:]):
                        self.assertIn(frozenset((u, v)), edge_ids)
                        mask |= 1 << edge_ids[frozenset((u, v))]
                    actual.append(mask)
                self.assertEqual(set(actual), expected)
                self.assertEqual(len(actual), len(expected))


if __name__ == '__main__':
    unittest.main()
