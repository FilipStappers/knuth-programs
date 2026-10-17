"""Full-word graph clique families and hypercube metric embeddings."""
from collections import deque
from itertools import combinations
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))


def maximal_cliques(n, edges):
    edges = {tuple(sorted(edge)) for edge in edges}
    cliques = []
    for mask in range(1 << n):
        vertices = frozenset(v for v in range(n) if mask & (1 << v))
        if all(pair in edges for pair in combinations(sorted(vertices), 2)):
            cliques.append(vertices)
    return {clique for clique in cliques if not any(clique < other for other in cliques)}


@unittest.skipUnless((GRAPHBASE/'gb_types.w').exists(), 'GraphBase sources required')
class GraphWordBoundaries(unittest.TestCase):
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
        cls.programs = {}
        for name in ['maxcliques', 'embed']:
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/(name+'.w')),
                            '-', str(generated)], cwd=GRAPHBASE, check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon',
                            '-Wno-implicit-int', '-Wno-implicit-function-declaration',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            '-I'+str(GRAPHBASE), str(generated), *objects, '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program
        fixture = cls.work/'fixture.c'
        fixture.write_text('''#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  int n=atoi(argv[1]),i,u,v;char name[16];Graph *g=gb_new_graph(n);
  if(!g)return 1;
  for(i=0;i<n;i++){sprintf(name,"v%d",i);g->vertices[i].name=gb_save_string(name);}
  while(scanf("%d %d",&u,&v)==2)gb_new_edge(g->vertices+u,g->vertices+v,1);
  return save_graph(g,argv[2]);
}
''')
        cls.writer = cls.work/'fixture'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        str(fixture), *objects, '-o', str(cls.writer)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_graph(self, mode, n, edges):
        saved = self.work/'input.gb'
        subprocess.run([str(self.writer), str(n), str(saved)],
                       input=''.join(f'{u} {v}\n' for u, v in edges), text=True,
                       check=True, capture_output=True)
        result = subprocess.run([str(self.programs[mode]), str(saved)],
                                text=True, capture_output=True, timeout=10)
        self.assertNotIn('runtime error', result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def check_cliques(self, n, edges, expected):
        output = self.run_graph('maxcliques', n, edges)
        lines = output.splitlines()
        match = re.search(r'has (\d+) maximal cliques:', lines[0])
        self.assertIsNotNone(match)
        count = int(match[1])
        actual = [frozenset(int(v) for v in re.findall(r'v(\d+)', line)) for line in lines[1:count+1]]
        self.assertEqual(len(actual), len(set(actual)))
        self.assertEqual(set(actual), expected)

    def test_full_width_clique_families(self):
        n = 64
        cases = [([], {frozenset({v}) for v in range(n)}),
                 (list(combinations(range(n), 2)), {frozenset(range(n))})]
        for edges in [[(v, v+1) for v in range(n-1)],
                      [(v, (v+1) % n) for v in range(n)],
                      [(v, v+1) for v in range(0, n, 2)],
                      [(0, v) for v in range(1, n)]]:
            cases.append((edges, {frozenset(edge) for edge in edges}))
        for edges, expected in cases:
            with self.subTest(edge_count=len(edges)):
                self.check_cliques(n, edges, expected)

    def test_all_small_maximal_clique_families(self):
        for n in range(6):
            pairs = list(combinations(range(n), 2))
            for mask in range(1 << len(pairs)):
                edges = [edge for k, edge in enumerate(pairs) if mask & (1 << k)]
                with self.subTest(n=n, edges=edges):
                    self.check_cliques(n, edges, maximal_cliques(n, edges))


if __name__ == '__main__':
    unittest.main()
