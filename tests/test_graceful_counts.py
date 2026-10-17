"""Graceful graph counts from independent complete edge-endpoint tuples."""
from collections import Counter
from functools import lru_cache
from itertools import product
from math import factorial
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/programs'


@lru_cache(None)
def direct_counts(m):
    counts = Counter()
    # Include both complement orientations directly, with no symmetry shortcut.
    for starts in product(*(range(m-difference+1) for difference in range(1, m+1))):
        edges = [(u, u+difference) for difference, u in enumerate(starts, 1)]
        vertices = set(v for edge in edges for v in edge)
        reached = {next(iter(vertices))}
        while True:
            expanded = reached | {v for u, v in edges if u in reached} | {u for u, v in edges if v in reached}
            if expanded == reached:
                break
            reached = expanded
        counts[len(vertices), reached == vertices] += 1
    assert sum(counts.values()) == factorial(m)
    return counts


class GracefulCounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for mode in ['base', 'small']:
            generated = cls.work/(mode+'.c')
            change = str(SOURCES/'graceful-count-small.ch') if mode == 'small' else '-'
            subprocess.run(['ctangle', str(SOURCES/'graceful-count.w'), change, str(generated)],
                           check=True, capture_output=True)
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_counts(self, m, limit=None):
        mode = 'base' if limit is None else 'small'
        result = subprocess.run([str(self.programs[mode]), str(m)]+([] if limit is None else [str(limit)]),
                                text=True, capture_output=True, timeout=10)
        self.assertNotIn('runtime error', result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = Counter()
        for n, connected, disconnected in re.findall(r'on\s+(\d+) vertices, (\d+) are connected, (\d+) not', result.stdout):
            if int(connected):
                actual[int(n), True] = int(connected)
            if int(disconnected):
                actual[int(n), False] = int(disconnected)
        expected = Counter({key: count for key, count in direct_counts(m).items()
                            if limit is None or key[0] <= limit})
        self.assertEqual(actual, expected)
        self.assertIn(f'Altogether {sum(count for (n, c), count in expected.items() if c)} connected and '
                      f'{sum(count for (n, c), count in expected.items() if not c)} not.', result.stdout)

    def test_initial_union_root(self):
        for limit in [None, 3]:
            with self.subTest(limit=limit):
                self.check_counts(2, limit)

    def test_full_small_edge_tuple_counts(self):
        for m in range(2, 9):
            with self.subTest(m=m, limit=None):
                self.check_counts(m)
            for limit in range(3, m+2):
                with self.subTest(m=m, limit=limit):
                    self.check_counts(m, limit)


if __name__ == '__main__':
    unittest.main()
