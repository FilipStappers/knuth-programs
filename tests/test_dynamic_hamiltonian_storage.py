"""Dynamic Hamiltonian storage with bounded resources and factorial block oracles."""
from itertools import combinations, permutations
from math import factorial
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')
MODES = ['dynaham', 'dynahamp', 'dynadiham', 'dynabidiham']


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(), 'GraphBase sources required')
class DynamicHamiltonianStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        objects = []
        for name in ['gb_graph', 'gb_io', 'gb_save']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-fcommon',
                            '-I'+str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')), '-o', str(obj)],
                           check=True, capture_output=True)
            objects.append(str(obj))
        cls.flags = ['-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                     '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all']
        fixture = cls.work/'fixture.c'
        fixture.write_text('''#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  int n=atoi(argv[1]),directed=atoi(argv[2]),i,j; char name[16]; Graph *g=gb_new_graph(n);
  if(!g) return 1;
  for(i=0;i<n;i++){sprintf(name,"v%d",i);g->vertices[i].name=gb_save_string(name);}
  while(scanf("%d %d",&i,&j)==2) {
    if(directed) gb_new_arc(g->vertices+i,g->vertices+j,1);
    else gb_new_edge(g->vertices+i,g->vertices+j,1);
  }
  return save_graph(g,argv[3]);
}
''')
        cls.writer = cls.work/'fixture'
        subprocess.run(['gcc', *cls.flags, str(fixture), *objects, '-o', str(cls.writer)],
                       check=True, capture_output=True)
        cls.programs = {}
        for mode in MODES:
            source, generated, program = [cls.work/(mode+s) for s in ['.w', '.c', '']]
            text = (ROOT/('programs/programs/'+mode+'.w')).read_text()
            for macro, value in [('memsize', '200000'), ('wtsize', '30000'), ('oldmemsize', '100000')]:
                text, count = re.subn(r'(?m)^@d '+macro+r'\s+\S+', '@d '+macro+' '+value, text)
                assert count == 1
            allocation = 'oldweight=(bignum*)malloc(wtsize*sizeof(bignum));'
            assert text.count(allocation) == 1
            text = text.replace(allocation, allocation+'''
if (oldweight) {
  long test_i; int test_j;
  for (test_i=0;test_i<wtsize;test_i++) for (test_j=0;test_j<maxprec;test_j++)
    oldweight[test_i].val[test_j]=7;
}
''')
            source.write_text(text)
            subprocess.run(['ctangle', str(source), '-', str(generated)], cwd=GRAPHBASE,
                           check=True, capture_output=True)
            subprocess.run(['gcc', *cls.flags, str(generated), *objects, '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_factorial_counts_across_precision_growth(self):
        for mode in MODES:
            for blocks in [3, 24]:
                with self.subTest(mode=mode, blocks=blocks):
                    directed = mode in ['dynadiham', 'dynabidiham']
                    edges = []
                    for block in range(blocks):
                        left, right = 5*block, 5*block+4
                        if directed:
                            edges += [(left, v) for v in range(left+1, right)]
                            edges += list(permutations(range(left+1, right), 2))
                            edges += [(v, right) for v in range(left+1, right)]
                        else:
                            edges += list(combinations(range(left, right+1), 2))
                        if block+1 < blocks:
                            edges.append((right, right+1))
                    if mode != 'dynahamp':
                        edges.append((5*blocks-1, 0))
                    path = self.work/'factorial.gb'
                    made = subprocess.run([str(self.writer), str(5*blocks), str(int(directed)), str(path)],
                                          input=''.join(f'{i} {j}\n' for i, j in edges).encode(),
                                          capture_output=True, timeout=5, env=ENV)
                    self.assertEqual(made.returncode, 0, made.stderr.decode())
                    result = subprocess.run([str(self.programs[mode]), str(path)],
                                            capture_output=True, timeout=20, env=ENV)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    counts = {int(n): int(c) for c, n in re.findall(
                        rb'There are (\d+) Hamiltonian (\d+)-(?:cycles|paths)', result.stdout)}
                    expected = (factorial(4)**2*factorial(3)**(blocks-2)
                                if mode == 'dynahamp' else factorial(3)**blocks)
                    self.assertEqual(counts.get(5*blocks, 0), expected)


if __name__ == '__main__':
    unittest.main()
