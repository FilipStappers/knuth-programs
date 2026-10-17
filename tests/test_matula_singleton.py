"""Rectree subtree embeddings checked by direct injective vertex maps."""
from itertools import permutations, product
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/programs'


def trees(n):
    return [(-1, *parents) for parents in product(*(range(i) for i in range(1, n)))]


def write_rectree(parents, path):
    children = {i: [] for i in range(len(parents))}
    for i, p in enumerate(parents[1:], 1):
        children[p].append(i)
    preorder, mapped_children, sizes = [], {}, {}
    def visit(node):
        index = len(preorder)
        preorder.append(node)
        mapped_children[index] = [visit(child) for child in children[node]]
        sizes[index] = len(preorder)-index
        return index
    visit(0)
    lines = [f'T{len(parents)}_0.']
    def emit(node):
        if sizes[node] > 2:
            lines.append(f'T{sizes[node]}_{node}='+''.join(f'+1T{sizes[c]}_{c}'
                                                         for c in mapped_children[node])+'.')
        for child in reversed(mapped_children[node]):
            emit(child)
    emit(0)
    path.write_text('\n'.join(lines)+'\n')
    inverse = {node: i for i, node in enumerate(preorder)}
    return {tuple(sorted((inverse[i], inverse[p]))) for i, p in enumerate(parents) if p >= 0}


def embeds(m, source_edges, n, target_edges):
    return any(all(tuple(sorted((mapping[u], mapping[v]))) in target_edges
                   for u, v in source_edges) for mapping in permutations(range(n), m))


class MatulaSingleton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'matula.c'
        subprocess.run(['ctangle', str(SOURCES/'matula.w'), str(SOURCES/'matula-big.ch'),
                        str(generated)], check=True, capture_output=True)
        cls.program = cls.work/'matula'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_pair(self, source, target):
        s, t = self.work/'source.rectree', self.work/'target.rectree'
        se, te = write_rectree(source, s), write_rectree(target, t)
        result = subprocess.run([str(self.program), str(s), str(t)],
                                text=True, capture_output=True, timeout=5)
        self.assertNotIn("I'm confused", result.stderr)
        self.assertIn('Altogether ', result.stderr)
        mapping = tuple(map(int, result.stdout.split()))
        self.assertEqual(bool(mapping), embeds(len(source), se, len(target), te), result.stderr)
        if mapping:
            self.assertEqual(len(mapping), len(source))
            self.assertEqual(len(set(mapping)), len(mapping))
            self.assertTrue(all(0 <= v < len(target) for v in mapping))
            self.assertTrue(all(tuple(sorted((mapping[u], mapping[v]))) in te for u, v in se))
        if len(source) == 1:
            n = len(target)
            self.assertIn(f'There {"is" if n == 1 else "are"} {n} place', result.stderr)

    def test_singleton_rectree(self):
        self.check_pair((-1,), (-1,))

    def test_all_small_parent_trees(self):
        family = [tree for n in range(1, 6) for tree in trees(n)]
        self.assertEqual(len(family), 34)
        for source in family:
            for target in family:
                with self.subTest(source=source, target=target):
                    self.check_pair(source, target)

    def test_nested_and_bicentroidal_clones(self):
        cases = [
            ('T7_0.\nT7_0=+2T3_1.\nT3_1=+2T1_2.\n',
             {(0, 1), (1, 2), (1, 3), (0, 4), (4, 5), (4, 6)}),
            ('2T3_0.\nT3_0=+2T1_1.\n',
             {(0, 1), (0, 2), (0, 3), (3, 4), (3, 5)}),
            ('T3_0,T3_3.\nT3_3=+1T2_4.\nT3_0=+2T1_1.\n',
             {(0, 1), (0, 2), (0, 3), (3, 4), (4, 5)})]
        source, target = self.work/'cloned-source.rectree', self.work/'cloned-target.rectree'
        for text, edges in cases:
            for singleton in [False, True]:
                with self.subTest(text=text, singleton=singleton):
                    source.write_text('T1_0.\n' if singleton else text)
                    target.write_text(text)
                    result = subprocess.run([str(self.program), str(source), str(target)],
                                            text=True, capture_output=True, timeout=5)
                    self.assertIn('Altogether ', result.stderr)
                    mapping = tuple(map(int, result.stdout.split()))
                    n = len(edges)+1
                    self.assertEqual(len(mapping), 1 if singleton else n)
                    self.assertEqual(len(set(mapping)), len(mapping))
                    self.assertTrue(all(0 <= v < n for v in mapping))
                    if not singleton:
                        self.assertTrue(all(tuple(sorted((mapping[u], mapping[v]))) in edges for u, v in edges))


if __name__ == '__main__':
    unittest.main()
