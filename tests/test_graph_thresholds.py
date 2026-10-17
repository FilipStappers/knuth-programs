"""Graph-named threshold clauses checked by complete fixed-assignment projection."""
from itertools import product
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(), 'GraphBase sources required')
class GraphThresholds(unittest.TestCase):
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
        for mode in ['bb', 'sinz', 'bb-double']:
            base = 'sinz' if mode == 'sinz' else 'bb'
            change = 'sat-threshold-'+base+'-graphs'+('-double' if mode.endswith('double') else '')+'.ch'
            generated = cls.work/(mode+'.c')
            subprocess.run(['ctangle', str(SOURCES/('sat-threshold-'+base+'.w')),
                            str(SOURCES/change), str(generated)], check=True, capture_output=True)
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-Wno-implicit-int',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            '-I'+str(GRAPHBASE), str(generated), *objects, '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program
        fixture = cls.work/'fixture.c'
        fixture.write_text('''#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  int n=atoi(argv[1]),i;char name[16];Graph *g=gb_new_graph(n);
  if(!g)return 1;
  for(i=0;i<n;i++){sprintf(name,"v%d",i);g->vertices[i].name=gb_save_string(name);}
  return save_graph(g,argv[2]);
}
''')
        writer = cls.work/'fixture'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        str(fixture), *objects, '-o', str(writer)], check=True, capture_output=True)
        for n in range(7):
            subprocess.run([str(writer), str(n), str(cls.work/f'{n}.gb')], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, mode, n, r, colors, actual=None):
        return subprocess.run([str(self.programs[mode]), str(n), str(r),
                               str(self.work/f'{n if actual is None else actual}.gb'), str(colors)],
                              text=True, capture_output=True, timeout=5)

    def clauses(self, mode, n, r, colors):
        result = self.encode(mode, n, r, colors)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('runtime error', result.stderr)
        return [line.split() for line in result.stdout.splitlines() if line and not line.startswith('~ ')]

    def test_graph_size_must_match(self):
        for mode in self.programs:
            for n in range(1, 4):
                for actual in range(5):
                    if actual == n:
                        continue
                    with self.subTest(mode=mode, n=n, actual=actual):
                        result = self.encode(mode, n, 1 if mode.endswith('double') else 0, 2, actual)
                        self.assertNotIn('runtime error', result.stderr)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('graph has', result.stderr.lower())
                        self.assertEqual(result.stdout, '')

    def test_at_most_color_count(self):
        for mode in ['bb', 'sinz']:
            for n in range(1, 7):
                for r in range(n):
                    clauses = self.clauses(mode, n, r, 2)
                    for bits in product((0, 1), repeat=n):
                        fixed = [[('' if bit else '~')+f'v{v}.2'] for v, bit in enumerate(bits)]
                        self.assertEqual(satisfiable(clauses+fixed), sum(bits) <= r, (mode, n, r, bits))

    def test_positive_multicolor_threshold(self):
        for n in range(1, 4):
            for colors in [2, 3]:
                for r in range(1, n+1):
                    clauses = self.clauses('bb-double', n, r, colors)
                    for bits in product((0, 1), repeat=n*colors):
                        fixed = [[('' if bit else '~')+f'v{v}.{color+1}']
                                 for v in range(n) for color in range(colors)
                                 for bit in [bits[v*colors+color]]]
                        multicolored = sum(sum(bits[v*colors:(v+1)*colors]) >= 2 for v in range(n))
                        self.assertEqual(satisfiable(clauses+fixed), multicolored >= r,
                                         (n, colors, r, bits))


if __name__ == '__main__':
    unittest.main()
