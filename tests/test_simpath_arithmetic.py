"""BUG-008: defined frontier hashes/stamps with complete edge-family oracles."""
from itertools import combinations, permutations
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT
from simpath_native import diagram

SOURCES=ROOT/'programs/programs'


def expected_family(n,edges,kind):
    directed=kind=='directed'
    edge=lambda a,b:(a,b) if directed else tuple(sorted((a,b)))
    allowed={edge(a,b) for a,b in edges}
    paths=[]
    if kind in ['cycles','ham-cycles','directed']:
        for size in ([n] if kind=='ham-cycles' else range(2 if directed else 3,n+1)):
            for subset in combinations(range(n),size):
                for rest in permutations(subset[1:]):
                    if not directed and rest[0]>rest[-1]:
                        continue
                    path=(subset[0],)+rest
                    paths.append(tuple(edge(a,b) for a,b in zip(path,path[1:]+path[:1])))
    elif kind=='ham-any':
        paths=[tuple(edge(a,b) for a,b in zip((0,)+rest,rest)) for rest in permutations(range(1,n))]
    else:
        for size in ([n] if kind=='ham' else range(2,n+1)):
            for middle in permutations(range(1,n-1),size-2):
                path=(0,)+middle+(n-1,)
                paths.append(tuple(edge(a,b) for a,b in zip(path,path[1:])))
    return {frozenset(path) for path in paths if all(e in allowed for e in path)}


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class SimpathArithmetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        combined=cls.native.work/'combined.ch'
        combined.write_text((SOURCES/'simpath-cycles.ch').read_text()+'\n'+(SOURCES/'simpath-ham.ch').read_text())
        cls.programs={}
        for mode,change in [('paths',None),('cycles',SOURCES/'simpath-cycles.ch'),
                            ('ham',SOURCES/'simpath-ham.ch'),('ham-cycles',combined),
                            ('ham-any',SOURCES/'simpath-ham-any.ch'),('directed',None)]:
            name='simpath-directed-cycles' if mode=='directed' else 'simpath'
            text=(SOURCES/(name+'.w')).read_text()
            text=text.replace('@d logmemsize 27','@d logmemsize 18').replace('@d loghtsize 24','@d loghtsize 16')
            cls.programs[mode]=cls.native.build(mode,text,change)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_small_edge_families(self):
        cases=[(4,list(combinations(range(4),2))),(6,list(combinations(range(6),2))),
               (5,[(i,(i+1)%5) for i in range(5)]),(5,[(i,i+1) for i in range(4)])]
        for mode,program in self.programs.items():
            selected=[(n,list(permutations(range(n),2))) for n in [3,5]] if mode=='directed' else cases
            for n,edges in selected:
                with self.subTest(mode=mode,n=n,edges=edges):
                    graph=self.native.graph(n,edges,mode=='directed')
                    args=[str(program),str(graph)]+([] if mode=='directed' else ['v0',f'v{n-1}'])
                    result=subprocess.run(args,capture_output=True,timeout=15)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    arcs,family=diagram(result.stdout)
                    projected={frozenset((a,b) if mode=='directed' else tuple(sorted((a,b)))
                                         for a,b in (arcs[i] for i in members) if a is not None and b is not None)
                               for members in family}
                    self.assertEqual(len(projected),len(family))
                    self.assertEqual(projected,expected_family(n,edges,mode))

    def test_default_timestamp_high_bit_is_defined(self):
        for name in ['simpath','simpath-directed-cycles']:
            with self.subTest(name=name):
                text=(SOURCES/(name+'.w')).read_text()
                expression=re.search(r'boundary=head,htcount=0,htid=(.*);',text)[1]
                source=self.native.work/(name+'-stamp.c')
                source.write_text('''#include <stdio.h>
#include <stdint.h>
#define logmemsize 27
int main(void) { int i,wrap=1,steps[]={0,7,15,31,63,1023}; unsigned int htid;
for(int j=0;j<6;j++) { i=steps[j]; htid='''+expression+'''; printf("%u\\n",htid); }
return 0; }
''')
                program=source.with_suffix('')
                subprocess.run(['gcc','-std=gnu99','-O1','-fsanitize=undefined',
                                '-fsanitize-undefined-trap-on-error',str(source),'-o',str(program)],
                               check=True,capture_output=True)
                result=subprocess.run([str(program)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                self.assertEqual(list(map(int,result.stdout.split())),
                                 [((i+1)<<27)%(2**32) for i in [0,7,15,31,63,1023]])


if __name__ == '__main__':
    unittest.main()
