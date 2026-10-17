"""Compare native series-parallel graphs and tree families with direct models."""
from functools import lru_cache
from itertools import combinations
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))


@lru_cache(None)
def formulas(n):
    if n == 1:
        return ('-',)
    return tuple(a+b+op for k in range(1, n) for a in formulas(k)
                 for b in formulas(n-k) for op in 'sp')


def graph(formula):
    stack = []
    for char in formula:
        if char == '-':
            stack.append(None)
        else:
            right, left = stack.pop(), stack.pop()
            stack.append((char, left, right))
    edges = []
    vertices = 2
    def build(tree, left, right):
        nonlocal vertices
        if tree is None:
            edges.append((left, right))
        elif tree[0] == 's':
            middle = vertices
            vertices += 1
            build(tree[1], left, middle)
            build(tree[2], middle, right)
        else:
            build(tree[1], left, right)
            build(tree[2], left, right)
    build(stack.pop(), 0, 1)
    return vertices, edges


def tree_family(n, edges):
    result = set()
    for chosen in combinations(range(len(edges)), n-1):
        reached = {0}
        while True:
            old = len(reached)
            for edge in chosen:
                u, v = edges[edge]
                if u in reached or v in reached:
                    reached.update((u, v))
            if len(reached) == old:
                break
        if len(reached) == n:
            result.add(frozenset(chosen))
    return result


@unittest.skipUnless((GRAPHBASE/'gb_types.w').exists(), 'GraphBase sources required')
class SeriesParallelIndices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        objects = []
        for name in ['gb_graph', 'gb_io', 'gb_save']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-w',
                            '-I'+str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')),
                            '-o', str(obj)], check=True, capture_output=True)
            objects.append(str(obj))
        for name in ['spgraph', 'spspan', 'grayspspan']:
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/(name+'.w')),
                            '-', str(generated)], cwd=GRAPHBASE,
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon',
                            '-Wno-implicit-int', '-Wno-implicit-function-declaration',
                            '-I'+str(GRAPHBASE), str(generated),
                            *(objects if name != 'spspan' else []), '-lm',
                            '-o', str(cls.work/name)], check=True, capture_output=True)
        reader = cls.work/'read_graph.c'
        reader.write_text('''#include <stdio.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  Graph *g=restore_graph(argv[1]); Vertex *v; Arc *a;
  if(!g) return 1;
  printf("%ld %ld\\n",g->n,g->m/2);
  for(v=g->vertices;v<g->vertices+g->n;v++)
    for(a=v->arcs;a;a=a->next)
      printf("%ld %ld\\n",v-g->vertices,a->tip-g->vertices);
  return 0;
}
''')
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        str(reader), *objects, '-lm', '-o', str(cls.work/'read_graph')],
                       check=True, capture_output=True)
        writer = cls.work/'write_graph.c'
        writer.write_text('''#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  int n=atoi(argv[1]),i,u,v; char name[16]; Graph *g=gb_new_graph(n);
  if(!g) return 1;
  for(i=0;i<n;i++){sprintf(name,"v%d",i);g->vertices[i].name=gb_save_string(name);}
  while(scanf("%d %d",&u,&v)==2) gb_new_edge(g->vertices+u,g->vertices+v,1);
  return save_graph(g,argv[2]);
}
''')
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        str(writer), *objects, '-lm', '-o', str(cls.work/'write_graph')],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def native_graph(self, formula):
        saved = self.work/'sample.gb'
        result = subprocess.run([str(self.work/'spgraph'), formula, str(saved)],
                                capture_output=True, timeout=10)
        self.assertIn(b'saved successfully', result.stdout, result.stderr)
        result = subprocess.run([str(self.work/'read_graph'), str(saved)],
                                capture_output=True, check=True)
        rows = [tuple(map(int, line.split())) for line in result.stdout.splitlines()]
        (n, m), arcs = rows[0], rows[1:]
        self.assertEqual(len(arcs), 2*m)
        self.assertFalse(any(u == v for u, v in arcs), 'unexpected loop')
        return n, sorted((u, v) for u, v in arcs if u < v)

    def native_trees(self, formula, verbose=False):
        result = subprocess.run([str(self.work/'spspan'), formula]+(['show'] if verbose else []),
                                capture_output=True, timeout=10, text=True)
        match = re.search(r'Altogether (\d+) spanning trees', result.stdout)
        self.assertIsNotNone(match, result.stderr)
        return int(match[1]), result.stdout

    def test_large_parallel_and_series_formulas(self):
        for leaves in [255, 256, 257, 300, 1000]:
            for op in 'ps':
                with self.subTest(leaves=leaves, op=op):
                    formula = '-' + ('-'+op)*(leaves-1)
                    # Avoid Python's recursion limit for the deepest legal formulas.
                    n, edges = self.native_graph(formula)
                    self.assertEqual(n, 2 if op == 'p' else leaves+1)
                    self.assertEqual(len(edges), leaves)
                    if op == 'p':
                        self.assertEqual(set(edges), {(0, 1)})
                    else:
                        degrees = [0]*n
                        for u, v in edges:
                            degrees[u] += 1
                            degrees[v] += 1
                        self.assertEqual(sorted(degrees), [1, 1]+[2]*(n-2))
                    self.assertEqual(self.native_trees(formula)[0], leaves if op == 'p' else 1)

    def test_257_parallel_tree_count(self):
        self.assertEqual(self.native_trees('-'+'-p'*256)[0], 257)

    def test_mixed_large_operator_indices(self):
        parallel = lambda n: '-' + '-p'*(n-1)
        series = lambda n: '-' + '-s'*(n-1)
        for formula, count in [(parallel(256)+parallel(2)+'s', 512),
                               (series(256)+'-p', 257),
                               (parallel(300)+'-s', 300),
                               (series(300)+'-p', 301)]:
            with self.subTest(formula=formula):
                n, edges = graph(formula)
                actual_n, actual_edges = self.native_graph(formula)
                self.assertEqual(actual_n, n)
                # Internal vertex numbers are assigned in reverse preorder by SPGRAPH.
                expected = sorted(tuple(sorted((u if u < 2 else n+1-u,
                                               v if v < 2 else n+1-v))) for u, v in edges)
                self.assertEqual(actual_edges, expected)
                self.assertEqual(self.native_trees(formula)[0], count)

    def test_all_small_tree_families(self):
        for leaves in range(1, 6):
            for formula in formulas(leaves):
                with self.subTest(formula=formula):
                    n, edges = graph(formula)
                    actual_n, actual_edges = self.native_graph(formula)
                    expected = sorted(tuple(sorted((u if u < 2 else n+1-u,
                                                   v if v < 2 else n+1-v))) for u, v in edges)
                    self.assertEqual((actual_n, actual_edges), (n, expected))
                    family = tree_family(n, edges)
                    count, output = self.native_trees(formula, verbose=True)
                    self.assertEqual(count, len(family))
                    first = re.search(r'The first spanning tree is ([a-z]*)\.', output)
                    self.assertIsNotNone(first)
                    state = {ord(c)-ord('a') for c in first[1]}
                    seen = {frozenset(state)}
                    for signs in re.findall(r'^ ([+-])([a-z])([+-])([a-z])$', output, re.M):
                        for sign, label in zip(signs[::2], signs[1::2]):
                            edge = ord(label)-ord('a')
                            if sign == '+':
                                self.assertNotIn(edge, state)
                                state.add(edge)
                            else:
                                state.remove(edge)
                        self.assertNotIn(frozenset(state), seen)
                        seen.add(frozenset(state))
                    self.assertEqual(seen, family)

    def gray_count(self, n, edges, verbose=False):
        saved = self.work/'gray.gb'
        subprocess.run([str(self.work/'write_graph'), str(n), str(saved)],
                       input=''.join(f'{u} {v}\n' for u, v in edges), text=True,
                       check=True, capture_output=True)
        return subprocess.run([str(self.work/'grayspspan'), str(saved)]+
                              (['show'] if verbose else []),
                              text=True, capture_output=True, timeout=10)

    def test_gray_singleton_has_one_empty_tree(self):
        for loops in range(4):
            for verbose in [False, True]:
                with self.subTest(loops=loops, verbose=verbose):
                    result = self.gray_count(1, [(0, 0)]*loops, verbose)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('Altogether 1 spanning trees', result.stdout)
                    if verbose:
                        self.assertRegex(result.stdout, r'(?m)^1:$')

    def test_gray_small_graph_counts(self):
        cases = []
        for n in range(2, 5):
            pairs = list(combinations(range(n), 2))
            for mask in range(1 << len(pairs)):
                cases.append((n, [e for k, e in enumerate(pairs) if mask & (1 << k)]))
        cases += [(2, [(0, 1)]*k) for k in range(1, 8)]
        cases += [(3, [(0, 1)]*k+[(1, 2)]*j) for k in range(1, 4) for j in range(1, 4)]
        for n, edges in cases:
            with self.subTest(n=n, edges=edges):
                expected = len(tree_family(n, edges))
                result = self.gray_count(n, edges)
                if expected:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(f'Altogether {expected} spanning trees', result.stdout)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("graph isn't connected", result.stderr)


if __name__ == '__main__':
    unittest.main()
