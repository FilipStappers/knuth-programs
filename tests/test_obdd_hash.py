"""OBDD matching construction: defined hashing and direct quotient matching counts."""
from functools import lru_cache
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/obdd.w'
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


def matching_count(m, n):
    cells = m*n
    choices = []
    for cell in range(cells//2):
        x, y = divmod(cell, n)
        if (x+y) % 2:
            continue
        neighbors = []
        for dx, dy in [(1, 2), (1, -2), (-1, 2), (-1, -2),
                       (2, 1), (2, -1), (-2, 1), (-2, -1)]:
            xx, yy = x+dx, y+dy
            if 0 <= xx < m and 0 <= yy < n:
                other = xx*n+yy
                neighbors.append(min(other, cells-1-other))
        choices.append(neighbors)
    @lru_cache(None)
    def visit(k, used):
        if k == len(choices):
            return 1
        return sum(visit(k+1, used | (1 << other)) for other in choices[k]
                   if not used & (1 << other))
    return visit(0, 0)


@unittest.skipUnless((GRAPHBASE/'gb_types.w').exists(), 'GraphBase sources required')
class ObddHash(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.objects = []
        for name in ['gb_graph', 'gb_basic', 'gb_flip']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-w',
                            '-I'+str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')), '-o', str(obj)],
                           check=True, capture_output=True)
            cls.objects.append(str(obj))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_counting_capacity_diagnostic(self):
        text = SOURCE.read_text().replace('@d mm 8 ', '@d mm 4 ')
        text = text.replace('@d nn 8 ', '@d nn 4 ')
        text = text.replace('@d max_final_nodes (max_nodes/2)', '@d max_final_nodes 2')
        source, generated, program = [self.work/('limited'+suffix) for suffix in ['.w', '.c', '']]
        source.write_text(text)
        subprocess.run(['ctangle', str(source), '-', str(generated)], cwd=GRAPHBASE,
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), *self.objects, '-lm', '-o', str(program)],
                       check=True, capture_output=True)
        result = subprocess.run([str(program)], capture_output=True, timeout=10, env=ENV)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'out of memory for counting', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_printed_tours_are_complete_independent_cycles(self):
        for m, n, cycles, pseudo in [(6, 6, 78, 84), (6, 8, 5634, 5674)]:
            text = SOURCE.read_text().replace('@d mm 8 ', f'@d mm {m} ')
            text = text.replace('@d nn 8 ', f'@d nn {n} ')
            text = text.replace('@d interval 100000 ', '@d interval 1 ')
            source, generated, program = [self.work/('tours'+s) for s in ['.w', '.c', '']]
            source.write_text(text)
            subprocess.run(['ctangle', str(source), '-', str(generated)], cwd=GRAPHBASE,
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                            str(generated), *self.objects, '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            result = subprocess.run([str(program)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            summary = f'Total {cycles} solutions and {pseudo} pseudo-solutions.'
            self.assertIn(summary.encode(), result.stdout)
            answers = re.findall(rb'(?m)^\d+:([^\n]+)', result.stdout)
            self.assertEqual(len(answers), cycles)
            seen = set()
            opposite = lambda point: (m-1-point[0], n-1-point[1])
            for answer in answers:
                edges = re.findall(rb'(\d+)\.(\d+)-(\d+)\.(\d+)(\*?)', answer)
                self.assertEqual(len(edges), m*n//2)
                adjacency = {(x, y): set() for x in range(m) for y in range(n)}
                undirected = set()
                for x, y, xx, yy, star in edges:
                    first, second = (int(x), int(y)), (int(xx), int(yy))
                    if star:
                        second = opposite(second)
                    self.assertEqual(sorted([abs(first[0]-second[0]), abs(first[1]-second[1])]), [1, 2])
                    for a, b in [(first, second), (opposite(first), opposite(second))]:
                        edge = frozenset((a, b))
                        self.assertNotIn(edge, undirected)
                        undirected.add(edge)
                        adjacency[a].add(b); adjacency[b].add(a)
                self.assertTrue(all(len(neighbors) == 2 for neighbors in adjacency.values()))
                reached, todo = {(0, 0)}, [(0, 0)]
                while todo:
                    for point in adjacency[todo.pop()]:
                        if point not in reached:
                            reached.add(point); todo.append(point)
                self.assertEqual(len(reached), m*n)
                certificate = frozenset(undirected)
                self.assertNotIn(certificate, seen)
                seen.add(certificate)

    def test_matching_construction_and_counts(self):
        for m, n in [(4, 4), (4, 6), (6, 4), (6, 6), (6, 8), (8, 8)]:
            with self.subTest(m=m, n=n):
                text = SOURCE.read_text().replace('@d mm 8 ', f'@d mm {m} ')
                text = text.replace('@d nn 8 ', f'@d nn {n} ')
                # Stop only after original matching construction/counting; full
                # default tour enumeration is a separate, lengthy computation.
                marker = '@<Traverse and count Hamiltonian cycles@>;'
                self.assertEqual(text.count(marker), 1)
                text = text.replace(marker, 'return 0;')
                source, generated, program = [self.work/('obdd'+suffix) for suffix in ['.w', '.c', '']]
                source.write_text(text)
                subprocess.run(['ctangle', str(source), '-', str(generated)], cwd=GRAPHBASE,
                               check=True, capture_output=True)
                subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                                '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                                str(generated), *self.objects, '-lm', '-o', str(program)],
                               check=True, capture_output=True)
                result = subprocess.run([str(program)], capture_output=True, timeout=20, env=ENV)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                count = re.search(rb'Total solutions (\d+) in OBDD of size (\d+)', result.stdout)
                self.assertIsNotNone(count)
                self.assertEqual(int(count[1]), matching_count(m, n))
                if (m, n) == (8, 8):
                    self.assertEqual(tuple(map(int, count.groups())), (106256, 112740))


if __name__ == '__main__':
    unittest.main()
