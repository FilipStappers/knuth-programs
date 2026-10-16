"""B057: unused gates, exact wire counts and independent scalar circuit values."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
SOURCE = ROOT/'programs/archives/SATexamples/sources/gates-to-wires.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').is_file(), 'requires GRAPHBASE sources')
class GateWireCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        objects = []
        for name in ['gb_graph', 'gb_io', 'gb_save']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-fcommon',
                            '-I', str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')),
                            '-o', str(obj)], check=True, capture_output=True)
            objects.append(str(obj))
        flags = ['-std=gnu99', '-Wno-implicit-int', '-Wno-implicit-function-declaration',
                 '-O1', '-fcommon', '-fsanitize=address,undefined,bounds',
                 '-fno-sanitize-recover=all', '-I', str(GRAPHBASE)]
        generated = cls.work/'wires.c'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)], cwd=GRAPHBASE,
                       check=True, capture_output=True)
        cls.converter = cls.work/'wires'
        subprocess.run(['gcc', *flags, str(generated), *objects, '-o', str(cls.converter)],
                       check=True, capture_output=True)
        helper = cls.work/'fixture.c'
        helper.write_text(r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gb_graph.h"
#include "gb_gates.h"
#include "gb_save.h"
int main(int argc, char **argv) {
  Graph *g;
  Arc *a,*b;
  int n,i,j,d,t,index,outputs;
  char name[2]={0,0};
  if (argc==3) {
    if (scanf("%d",&n)!=1) return 1;
    g=gb_new_graph(n);
    if (!g) return 2;
    strcpy(g->util_types,"ZZZIIVZZZZZZZA");
    for (i=0;i<n;i++) {
      if (scanf(" %c%d",name,&d)!=2) return 3;
      t=name[0]; name[0]='a'+i;
      g->vertices[i].name=gb_save_string(name);
      g->vertices[i].typ=t;
      for (j=0;j<d;j++) {
        if (scanf("%d",&index)!=1) return 4;
        gb_new_arc(g->vertices+i,g->vertices+index,0);
      }
    }
    if (scanf("%d",&outputs)!=1) return 5;
    b=NULL;
    for (i=0;i<outputs;i++) {
      if (scanf("%d",&index)!=1) return 6;
      a=gb_virgin_arc(); a->tip=g->vertices+index;
      if (b) b->next=a; else g->outs=a;
      b=a;
    }
    return save_graph(g,argv[2]);
  }
  g=restore_graph(argv[1]);
  if (!g) return 7;
  for (i=0;i<g->n;i++) {
    printf("%d %s %c",i,g->vertices[i].name,(char)g->vertices[i].typ);
    for (a=g->vertices[i].arcs;a;a=a->next) printf(" %ld",a->tip-g->vertices);
    printf("\n");
  }
  printf("O");
  for (a=g->outs;a;a=a->next) printf(" %ld",a->tip-g->vertices);
  printf("\n");
  return 0;
}
''')
        cls.helper = cls.work/'fixture'
        subprocess.run(['gcc', *flags, str(helper), *objects, '-o', str(cls.helper)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def convert(self, nodes, outputs):
        original, target = self.work/'in.gb', self.work/'out.gb'
        text = str(len(nodes))+'\n'+''.join(f'{op} {len(args)} '+
                    ' '.join(map(str, args))+'\n' for op, args in nodes)
        text += str(len(outputs))+' '+' '.join(map(str, outputs))+'\n'
        subprocess.run([str(self.helper), 'build', str(original)], input=text.encode(),
                       check=True, capture_output=True, env=ENV)
        result = subprocess.run([str(self.converter), str(original), str(target)],
                                capture_output=True, timeout=5, env=ENV)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        result = subprocess.run([str(self.helper), str(target)], capture_output=True,
                                check=True, timeout=5, env=ENV)
        wires = []
        for line in result.stdout.decode().splitlines():
            parts = line.split()
            if parts[0] == 'O':
                out = list(map(int, parts[1:]))
            else:
                self.assertEqual(int(parts[0]), len(wires))
                wires.append((parts[2], list(map(int, parts[3:]))))
        return wires, out

    def test_unused_vertices_and_fanout_preserve_every_input_value(self):
        fixtures = [([('I', []), ('I', []), ('I', []), ('&', [0, 1])], [3]),
                    ([('I', []), ('I', []), ('&', [0, 1]), ('^', [0, 1])], [3]),
                    ([('I', []), ('I', []), ('I', [])], []),
                    ([('I', []), ('I', []), ('I', [])], [0, 1, 2]),
                    ([('I', [])], [0, 0, 0])]
        for first, second in itertools.product(['&', '|', '^'], repeat=2):
            for inputs in [[0, 1], [2, 3]]:
                fixtures.append(([('I', []), ('I', []), ('I', []),
                                  (first, [0, 1]), (second, inputs)], [4, 0]))
        def evaluate(nodes, bits):
            values, inputs = [], iter(bits)
            for op, args in nodes:
                if op == 'I':
                    values.append(next(inputs))
                elif op == 'F':
                    self.assertEqual(len(args), 1)
                    values.append(values[args[0]])
                else:
                    a,b = (values[k] for k in args)
                    values.append(a & b if op == '&' else a | b if op == '|' else a ^ b)
            return values
        for nodes, outputs in fixtures:
            with self.subTest(nodes=nodes, outputs=outputs):
                wires, out = self.convert(nodes, outputs)
                degree = [0]*len(nodes)
                for _, args in nodes:
                    for v in args:
                        degree[v] += 1
                for v in outputs:
                    degree[v] += 1
                expected = len(nodes)+2*sum(max(d-1, 0) for d in degree)
                self.assertEqual(len(wires), expected)
                for index, (_, args) in enumerate(wires):
                    self.assertTrue(all(0 <= k < index for k in args))
                for bits in itertools.product([0, 1], repeat=sum(op == 'I' for op, _ in nodes)):
                    before, after = evaluate(nodes, bits), evaluate(wires, bits)
                    self.assertEqual([before[k] for k in outputs], [after[k] for k in out])


if __name__ == '__main__':
    unittest.main()
