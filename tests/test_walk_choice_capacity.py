"""BUG-030: eligible parallel arcs need arc-sized choice storage."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class WalkChoiceCapacity(unittest.TestCase):
    def test_parallel_multiplicities_and_zero_step_walk(self):
        with tempfile.TemporaryDirectory() as temp:
            native=GraphNative(Path(temp))
            text=(ROOT/'programs/programs/walk-random.w').read_text()
            text=text.replace('@c','@c\n#include <stdint.h>\n#include <stddef.h>',1)
            needle='    if (u->dist<infty) choice(d)=u,d++;'
            self.assertEqual(text.count(needle),1)
            text=text.replace(needle,'''    if (u->dist<infty) {
      if(d>=g->n+4 && (uintptr_t)&choice(d)==
         (uintptr_t)g->vertices+(size_t)d*sizeof(Vertex)+offsetof(Vertex,z)) {
        fprintf(stderr,"UNGUARDED vertex choice\\n"); exit(71);
      }
      choice(d)=u; d++;
    }''')
            program=native.build('walk',text)
            cases=[(1,[],0,0,0,1),(2,[(0,1)]*1,0,1,1,1),
                   (2,[(0,1)]*5,0,1,1,5),(2,[(0,1)]*10,0,1,1,10),
                   (3,[(0,1)]*2+[(1,2)]*3,0,2,2,6)]
            for n,edges,source,target,length,estimate in cases:
                for seed in [0,37]:
                    with self.subTest(n=n,arcs=len(edges),seed=seed):
                        graph=native.graph(n,edges)
                        result=subprocess.run([str(program),str(graph),f'v{source}',f'v{target}',str(seed)],
                                              capture_output=True,timeout=5)
                        self.assertEqual(result.returncode,0,result.stderr.decode())
                        match=re.search(rb'length (\d+), est\s+([\d.]+)',result.stdout)
                        self.assertIsNotNone(match,result.stdout.decode())
                        self.assertEqual((int(match[1]),float(match[2])),(length,float(estimate)))


if __name__ == '__main__':
    unittest.main()
