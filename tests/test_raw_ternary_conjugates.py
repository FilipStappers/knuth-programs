"""Skew conjugates checked by independent rerooting at every plane-tree bud."""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/programs'


@lru_cache(None)
def ternaries(n):
    if not n:
        return (None,)
    return tuple((a, b, c) for i in range(n) for j in range(n-i)
                 for a in ternaries(i) for b in ternaries(j) for c in ternaries(n-1-i-j))


def labelled(tree):
    nodes = {}
    def visit(tree):
        if tree is None:
            return '-'
        name = chr(ord('A')+len(nodes))
        nodes[name] = ''
        nodes[name] = ''.join(visit(child) for child in tree)
        return name
    return visit(tree), nodes


def minimum_rank(root, nodes, rank=0):
    return min([rank]+[minimum_rank(child, nodes, rank+delta)
                       for child, delta in zip(nodes[root], (-1, 0, 1)) if child != '-'])


def signature(root, nodes):
    return root, tuple(sorted(nodes.items()))


def conjugates(root, nodes):
    # Parent/left/middle/right are cyclic ports; reroot at each actual bud.
    ports = {node: [None, *children] for node, children in nodes.items()}
    ports[root][0] = '!root'
    buds = [('!root', root)]
    for node in ports:
        for port in range(1, 4):
            child = ports[node][port]
            if child == '-':
                child = f'!{node}{port}'
                ports[node][port] = child
                buds.append((child, node))
            else:
                ports[child][0] = node
    result = Counter()
    for bud, new_root in buds:
        rerooted = {}
        def visit(node, parent):
            start = ports[node].index(parent)
            children = [ports[node][(start+i)%4] for i in range(1, 4)]
            rerooted[node] = ''.join('-' if child.startswith('!') else child for child in children)
            for child in children:
                if not child.startswith('!'):
                    visit(child, node)
        visit(new_root, bud)
        if minimum_rank(new_root, rerooted) >= 0:
            result[signature(new_root, rerooted)] += 1
    assert sum(result.values()) == 4
    return result


class RawTernaryConjugates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for mode in ['base', 'raw']:
            generated = cls.work/(mode+'.c')
            change = str(SOURCES/'skew-ternary-calc-raw.ch') if mode == 'raw' else '-'
            subprocess.run(['ctangle', str(SOURCES/'skew-ternary-calc.w'), change, str(generated)],
                           check=True, capture_output=True)
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int',
                            '-Wno-implicit-function-declaration', str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_tree(self, tree, mode='raw'):
        root, nodes = labelled(tree)
        result = subprocess.run([str(self.programs[mode]), *[node+children for node, children in nodes.items()]],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        actual = Counter()
        if mode == 'base':
            actual[signature(root, nodes)] += 1
        for line in result.stdout.splitlines():
            if re.match(r'^\+*:', line):
                family = {word[0]: word[1:] for word in line.split(':', 1)[1].split()}
                self.assertEqual(set(family), set(nodes))
                roots = set(family)-set(''.join(family.values()))
                self.assertEqual(len(roots), 1)
                actual[signature(roots.pop(), family)] += 1
        self.assertEqual(actual, conjugates(root, nodes))

    def test_singleton_returns_all_four(self):
        self.check_tree((None, None, None))

    def test_complete_small_families(self):
        for n in range(1, 6):
            for tree in ternaries(n):
                with self.subTest(n=n, tree=tree):
                    self.check_tree(tree)
                    root, nodes = labelled(tree)
                    if minimum_rank(root, nodes) >= 0:
                        self.check_tree(tree, 'base')

    def test_deep_left_middle_and_right_chains(self):
        for branch in range(3):
            tree = None
            for _ in range(25):
                children = [None]*3
                children[branch] = tree
                tree = tuple(children)
            with self.subTest(branch=branch):
                self.check_tree(tree)


if __name__ == '__main__':
    unittest.main()
