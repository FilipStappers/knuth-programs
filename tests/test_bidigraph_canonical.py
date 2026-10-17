"""Canonical upper triangles checked against every vertex complementation."""
from itertools import product
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
LOOPS = (0, 1, 2, 3, 12, 13, 14, 15)


def complement(code, left, right):
    # Edge ends in the source's <<, >>, <>, >< bit order.
    ends = ((0, 1), (1, 0), (0, 0), (1, 1))
    result = 0
    for bit, (u, v) in zip((8, 4, 2, 1), ends):
        if code & bit:
            result |= (8, 4, 2, 1)[ends.index((u ^ left, v ^ right))]
    return result


def canonical(n, triangle):
    pairs = list((i, j) for i in range(n) for j in range(i, n))
    return max(tuple(complement(code, signs[i], signs[j])
                     for code, (i, j) in zip(triangle, pairs))
               for signs in product((0, 1), repeat=n))


@unittest.skipUnless((GRAPHBASE/'gb_types.w').exists(), 'GraphBase sources required')
class BidigraphCanonical(unittest.TestCase):
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
        source = cls.work/'canonical.w'
        text = (ROOT/'programs/programs/canonize-bidigraph.w').read_text()
        old = 'save_graph(gg,"/tmp/makegraph.gb");'
        assert text.count(old) == 1
        text = text.replace(old, 'save_graph(gg,"'+str(cls.work/'canonical.gb')+'");')
        source.write_text(text)
        generated = cls.work/'canonical.c'
        subprocess.run(['ctangle', str(source), '-', str(generated)], cwd=GRAPHBASE,
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        str(generated), *objects, '-o', str(cls.work/'canonical')],
                       check=True, capture_output=True)
        fixture = cls.work/'fixture.c'
        fixture.write_text('''#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  Graph *g; Vertex *v; Arc *a; int n,i,j,c,code,reverse,mat[100][100]={0}; char name[16];
  if(argc==3) {
    n=atoi(argv[1]);g=gb_new_graph(n);if(!g)return 1;
    for(i=0;i<n;i++){sprintf(name,"v%d",i);g->vertices[i].name=gb_save_string(name);}
    for(i=0;i<n;i++)for(j=i;j<n;j++) {
      if(scanf("%d",&c)!=1)return 2;
      if(c&8)gb_new_arc(g->vertices+i,g->vertices+j,1);
      if(c&4)gb_new_arc(g->vertices+i,g->vertices+j,3);
      if(c&2)gb_new_arc(g->vertices+i,g->vertices+j,0);
      if(c&1)gb_new_arc(g->vertices+i,g->vertices+j,2);
    }
    return save_graph(g,argv[2]);
  }
  g=restore_graph(argv[1]);if(!g)return 3;
  for(i=0;i<g->n;i++)for(a=g->vertices[i].arcs;a;a=a->next) {
    j=a->tip-g->vertices;
    switch(a->len&3) {
      case 0:code=reverse=2;break;
      case 1:code=8;reverse=4;break;
      case 2:code=reverse=1;break;
      default:code=4;reverse=8;
    }
    mat[i][j]|=code;mat[j][i]|=reverse;
  }
  for(i=0;i<g->n;i++)for(j=i;j<g->n;j++)printf("%d ",mat[i][j]);
  puts("");return 0;
}
''')
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        str(fixture), *objects, '-o', str(cls.work/'fixture')],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_canonical(self, n, triangle):
        saved = self.work/'input.gb'
        subprocess.run([str(self.work/'fixture'), str(n), str(saved)],
                       input=' '.join(map(str, triangle)), text=True,
                       check=True, capture_output=True)
        result = subprocess.run([str(self.work/'canonical'), str(saved)],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        output = subprocess.run([str(self.work/'fixture'), str(self.work/'canonical.gb')],
                                check=True, capture_output=True)
        return tuple(map(int, output.stdout.split()))

    def test_later_diagonal_resolves_earlier_sign(self):
        for triangle in [(0, 3, 2), (0, 12, 2)]:
            with self.subTest(triangle=triangle):
                self.assertEqual(self.run_canonical(2, triangle), (0, 12, 2))

    def test_all_one_and_two_vertex_matrices(self):
        for n, triangles in [(1, [(c,) for c in LOOPS]),
                             (2, product(LOOPS, range(16), LOOPS))]:
            for triangle in triangles:
                with self.subTest(n=n, triangle=triangle):
                    self.assertEqual(self.run_canonical(n, triangle), canonical(n, triangle))

    def test_larger_matrices(self):
        # A deterministic arithmetic corpus, with no random generator dependency.
        for n, count in [(3, 512), (4, 128), (5, 32)]:
            for case in range(count):
                value = (case+1)*0x9e3779b97f4a7c15
                triangle = []
                for i in range(n):
                    for j in range(i, n):
                        value = (value*6364136223846793005+1442695040888963407) & ((1 << 64)-1)
                        code = value >> 60
                        triangle.append(LOOPS[code & 7] if i == j else code)
                with self.subTest(n=n, case=case):
                    self.assertEqual(self.run_canonical(n, triangle), canonical(n, triangle))

    def test_long_deferred_component(self):
        n = 99
        triangle = tuple(2 if i == j == n-1 else 3 if j == i+1 else 0
                         for i in range(n) for j in range(i, n))
        expected = tuple(2 if i == j == n-1 else 12 if j == i+1 else 0
                         for i in range(n) for j in range(i, n))
        self.assertEqual(self.run_canonical(n, triangle), expected)


if __name__ == '__main__':
    unittest.main()
