"""B046: reconstruct alphabetic tree witnesses and compare interval DP."""
import functools
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def optimum(weights):
    @functools.lru_cache(None)
    def cost(i, j):
        if i == j:
            return 0
        return sum(weights[i:j+1])+min(cost(i, k)+cost(k+1, j) for k in range(i, j))
    return cost(0, len(weights)-1)


class AlphabeticTrees(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'tree.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/garsia-wachs.w'),
                        '-', str(generated)], check=True, capture_output=True)
        cls.program = cls.work/'tree'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-include', 'stdlib.h',
                        '-O1', '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_tree(self, weights):
        result = subprocess.run([str(self.program), *map(str, weights)],
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        text = result.stdout.decode().split('Phase III:\n')[-1]
        nodes = {int(j): (int(l), int(r)) for j, l, r in
                 re.findall(r'node (\d+) = (\d+) \+ (\d+)', text)}
        order = []
        def walk(j, depth):
            if j < len(weights):
                order.append(j)
                return weights[j]*depth
            self.assertIn(j, nodes)
            left, right = nodes[j]
            self.assertLess(left, j)
            self.assertLess(right, j)
            return walk(left, depth+1)+walk(right, depth+1)
        self.assertEqual(walk(2*(len(weights)-1), 0), optimum(weights))
        self.assertEqual(order, list(range(len(weights))))

    def test_singleton_is_one_leaf_at_depth_zero(self):
        for weight in (0, 1, 999999999):
            with self.subTest(weight=weight):
                self.check_tree((weight,))

    def test_small_optima_and_full_leaf_capacity(self):
        for n in range(2, 7):
            for weights in itertools.product((0, 1, 3), repeat=n):
                self.check_tree(weights)
        self.check_tree(tuple(range(1, 33)))
        self.check_tree(tuple(range(32, 0, -1)))


if __name__ == '__main__':
    unittest.main()
