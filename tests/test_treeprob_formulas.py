"""Evaluate generated weighted-tree formulas against every binary assignment."""
from functools import lru_cache
from itertools import product
from math import prod
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(None)
def trees(n):
    if n == 1:
        return ((),)
    return (tuple((tree,) for tree in trees(n-1))+
            tuple((a, b) for i in range(1, n-1) for a in trees(i) for b in trees(n-1-i)))


def edges(tree):
    result, serial = [], 0
    def visit(tree):
        nonlocal serial
        serial += 1
        node = serial
        for child in tree:
            result.append((node, serial+1))
            visit(child)
    visit(tree)
    return sorted(result), serial


def evaluate(text, weights):
    values = {}
    answer = None
    for line in text.splitlines():
        lhs, rhs = line.split('=')
        def replace(match):
            source = weights if match[1] == 'w' else values
            return '('+str(source[tuple(map(int, match[2].split(',')))])+')'
        expression = re.sub(r'([Tw])\[([0-9,]+)\]', replace, rhs).replace(')(', ')*(')
        assert re.fullmatch(r'[0-9()+*]+', expression)
        value = eval(expression, {'__builtins__': {}})
        if lhs == 'ans':
            answer = value
        else:
            values[tuple(map(int, lhs[2:-1].split(',')))] = value
    assert answer is not None
    return answer


class TreeprobFormulas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'treeprobs.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/treeprobs.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = cls.work/'treeprobs'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int', str(generated),
                        '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_tree(self, tree):
        graph, n = edges(tree)
        data = ''.join(f'{u} {v}\n' for u, v in graph)
        all_weights = [{(v, a, b): (1 if mode == 0 else
                                  1+(v+2*a+3*b)%7 if mode == 1 else (v+3*a+b)%4)
                        for _, v in graph for a, b in product((0, 1), repeat=2)}
                       for mode in range(3)]
        expected = [[0]*(n+1) for _ in all_weights]
        for bits in product((0, 1), repeat=n):
            for k, weights in enumerate(all_weights):
                expected[k][sum(bits)] += prod(weights[v, bits[u-1], bits[v-1]] for u, v in graph)
        for m in range(n+1):
            result = subprocess.run([str(self.program), str(m)], input=data, text=True,
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            for k, weights in enumerate(all_weights):
                self.assertEqual(evaluate(result.stdout, weights), expected[k][m])

    def test_singleton_and_left_heavy_example(self):
        for tree in [(), (((),), ())]:
            with self.subTest(tree=tree):
                self.check_tree(tree)

    def test_complete_small_binary_tree_families(self):
        for n in range(1, 8):
            for tree in trees(n):
                with self.subTest(n=n, tree=tree):
                    self.check_tree(tree)


if __name__ == '__main__':
    unittest.main()
