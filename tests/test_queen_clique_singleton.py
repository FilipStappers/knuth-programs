"""Permuted queen-clique boundaries, using the deterministic organpipe change."""
from itertools import permutations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


@unittest.skipUnless((GRAPHBASE/'gb_flip.c').exists(), 'GraphBase sources required')
class QueenCliqueSingleton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.program = cls.work/'organpipe'
        for variant in ['base', 'organpipe']:
            generated = cls.work/(variant+'.c')
            change = '-' if variant == 'base' else str(SOURCES/'sat-queens-color-order-organpipe.ch')
            subprocess.run(['ctangle', str(SOURCES/'sat-queens-color-order-cliques2.w'), change,
                            str(generated)], check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-I'+str(GRAPHBASE),
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), str(GRAPHBASE/'gb_flip.c'), '-o',
                            str(cls.work/variant)], check=True, capture_output=True)
        # The random base is compiled for composition only, never executed.

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, n, d):
        result = subprocess.run([str(self.program), str(n), str(d)], capture_output=True,
                                timeout=5, env=ENV)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return [line.split() for line in result.stdout.decode().splitlines()
                if line.strip() and not line.startswith('~ ')]

    def test_singleton_at_maximum_color_count(self):
        self.assertTrue(satisfiable(self.encode(1, 100)))

    def test_nonpositive_dimensions_reject(self):
        for n, d in [(0, 1), (-1, 2), (1, 0), (0, 0)]:
            result = subprocess.run([str(self.program), str(n), str(d)], capture_output=True,
                                    timeout=5, env=ENV)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(result.stdout)
            self.assertNotIn(b'runtime error', result.stderr)

    def test_proper_colorings_extend_to_consistent_permuted_order(self):
        for n, d in [(1, k) for k in [1, 2, 3, 4, 5, 6, 100]]+[(2, 4), (2, 5)]:
            formula = self.encode(n, d)
            # A 2-by-2 queen graph is K4; all injective assignments are proper.
            for colors in permutations(range(d), n*n):
                fixed = [[('' if color < k else '~')+f'{i//n}.{i % n}<{k}']
                         for i, color in enumerate(colors) for k in range(1, d)]
                self.assertTrue(satisfiable(formula+fixed), (n, d, colors))


if __name__ == '__main__':
    unittest.main()
