"""Graph cycle bounds with real GraphBase files and deterministic SAT ordering."""
from itertools import combinations, permutations
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(), 'GraphBase sources required')
class GraphCycleStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        objects = []
        for name in ['gb_graph', 'gb_io', 'gb_save', 'gb_flip']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-fcommon',
                            '-I'+str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')), '-o', str(obj)],
                           check=True, capture_output=True)
            objects.append(str(obj))
        flags = ['-std=gnu99', '-Wno-implicit-int', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                 '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all']
        fixture = cls.work/'fixture.c'
        fixture.write_text('''#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  int n=atoi(argv[1]),i,j; char name[16]; Graph *g=gb_new_graph(n);
  if(!g) return 1;
  for(i=0;i<n;i++) {sprintf(name,"v%d",i);g->vertices[i].name=gb_save_string(name);}
  while(scanf("%d %d",&i,&j)==2) gb_new_edge(g->vertices+i,g->vertices+j,1);
  return save_graph(g,argv[2]);
}
''')
        cls.writer = cls.work/'fixture'
        subprocess.run(['gcc', *flags, str(fixture), *objects, '-o', str(cls.writer)],
                       check=True, capture_output=True)
        change = (SOURCES/'sat-graph-cyc.ch').read_text()
        call = '  @<Set up the random total order@>;'
        assert change.count(call) == 1
        change = change.replace(call, '  for (v=g->vertices;v<g->vertices+g->n;v++) v->rrank=v-g->vertices;')
        cls.change = cls.work/'deterministic.ch'
        cls.change.write_text(change)
        cls.programs = {}
        for mode in ['base', 'sat']:
            generated, program = [cls.work/(mode+s) for s in ['.c', '']]
            subprocess.run(['ctangle', str(SOURCES/'graph-cyc.w'),
                            '-' if mode == 'base' else str(cls.change), str(generated)],
                           cwd=GRAPHBASE, check=True, capture_output=True)
            subprocess.run(['gcc', *flags, str(generated), *objects, '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def graph(self, n, edges):
        path = self.work/'graph.gb'
        result = subprocess.run([str(self.writer), str(n), str(path)],
                                input=''.join(f'{i} {j}\n' for i, j in edges).encode(),
                                capture_output=True, timeout=5, env=ENV)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return path

    def enumerate(self, mode, path, length):
        arguments = [str(self.programs[mode]), str(path), str(length)]
        if mode == 'sat':
            arguments.append('0')  # parsed, but no RNG runs in the test derivative
        return subprocess.run(arguments, capture_output=True, timeout=5, env=ENV)

    def test_empty_and_impossible_cycle_lengths(self):
        for n, edges, length in [(0, [], 3), (1, [], 3), (3, [(0, 1), (1, 2), (0, 2)], 4)]:
            path = self.graph(n, edges)
            for mode in self.programs:
                result = self.enumerate(mode, path, length)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertIn(b'Altogether 0 cycles found', result.stderr)

    def test_default_capacity_cycle_and_closing_slots(self):
        path = self.graph(100, [(i, (i+1) % 100) for i in range(100)])
        for mode in self.programs:
            result = self.enumerate(mode, path, 100)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn(b'Altogether 1 cycles found', result.stderr)
            rows = [row.split() for row in result.stdout.splitlines() if row and not row.startswith(b'~ ')]
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(rows[0]), 100)

    def test_small_graph_cycle_counts(self):
        for n in range(1, 5):
            pairs = list(combinations(range(n), 2))
            for mask in range(1 << len(pairs)):
                edges = [e for k, e in enumerate(pairs) if mask >> k & 1]
                edge_set = {frozenset(e) for e in edges}
                path = self.graph(n, edges)
                for length in range(3, n+1):
                    expected = sum(all(frozenset((cycle[i], cycle[(i+1) % length])) in edge_set
                                       for i in range(length)) for cycle in permutations(range(n), length)
                                   if cycle[0] == min(cycle) and cycle[1] < cycle[-1])
                    for mode in self.programs:
                        result = self.enumerate(mode, path, length)
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        count = int(re.search(rb'Altogether (\d+) cycles', result.stderr)[1])
                        self.assertEqual(count, expected, (n, mask, length, mode))


if __name__ == '__main__':
    unittest.main()
