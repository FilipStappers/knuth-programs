"""BUG-012: invariant full cycles, including the two fixed-edge reflections."""
from pathlib import Path
import itertools
import json
import re
import subprocess
import tempfile
import unittest
from graph_native import ROOT, GraphNative


def invariant_cycles(n,edges):
    edges=set(map(lambda e:tuple(sorted(e)),edges))
    result=set()
    for tail in itertools.permutations(range(1,n)):
        if tail[0]>tail[-1]:continue
        cycle=(0,*tail)
        chosen=frozenset(tuple(sorted((cycle[i],cycle[(i+1)%n]))) for i in range(n))
        if chosen<=edges and {tuple(sorted((n-1-u,n-1-v))) for u,v in chosen}==chosen:
            result.add(chosen)
    return result


class ShamSymmetries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        cls.text=(ROOT/'programs/programs/sham.w').read_text()
        cls.text=cls.text.replace('#include "gb_basic.h"','#include "gb_save.h"\n#include "gb_basic.h"')
        cls.text=cls.text.replace('main()','main(int argc,char **argv)',1)
        cls.text=re.sub(r'Graph \*g=board\([^;]+;', 'Graph *g=restore_graph(argv[1]);',cls.text,count=1)
        cls.program=cls.native.build('sham',cls.text)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def check_graph(self,n,edges):
        graph=self.native.graph(n,edges)
        result=subprocess.run([str(self.program),str(graph)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        count=re.search(rb'Altogether (\d+) solutions',result.stdout)
        self.assertIsNotNone(count,result.stdout)
        self.assertEqual(int(count[1]),len(invariant_cycles(n,edges)),(n,edges,result.stdout))

    def test_saved_parity_duplicate_and_reflection_counterexamples(self):
        records=json.loads((ROOT/'tests/fixtures/sham-cases.json').read_text())['cases']
        cases=[(6,[(0,3),(0,4),(1,2),(1,5),(2,5),(3,4)])]
        cases += [(row['n'],row['edges']) for row in records if row['n']==8 and row['case']==47]
        # Central inversion reflects this ring through the opposite mate edges.
        cycle=[0,1,2,3,4,5]
        cases.append((6,[(cycle[i],cycle[(i+1)%6]) for i in range(6)]))
        for n,edges in cases:
            with self.subTest(n=n,edges=edges):self.check_graph(n,edges)

    def test_complete_small_involution_graph_families(self):
        for n in [4,6]:
            orbits=sorted({tuple(sorted({(u,v),tuple(sorted((n-1-u,n-1-v)))}))
                           for u in range(n) for v in range(u+1,n)})
            for bits in range(1<<len(orbits)):
                edges=[edge for i,orbit in enumerate(orbits) if bits>>i&1 for edge in orbit]
                with self.subTest(n=n,bits=bits):self.check_graph(n,edges)
        records=json.loads((ROOT/'tests/fixtures/sham-cases.json').read_text())['cases']
        for row in [r for r in records if r['n']==8][:60]:
            self.check_graph(8,row['edges'])
        self.check_graph(8,list(itertools.combinations(range(8),2)))

    def test_full_eight_by_nine_board_finds_a_reflection_witness(self):
        witness=json.loads((ROOT/'tests/fixtures/sham-board-witness.json').read_text())
        path=witness['half_path']; n=72
        edges={tuple(sorted((u,v))) for u in range(n) for v in range(u+1,n)
               if sorted([abs(u//9-v//9),abs(u%9-v%9)])==[1,2]}
        preferred=[]
        for u,v in zip(path,path[1:]):preferred += [tuple(sorted((u,v))),tuple(sorted((71-u,71-v)))]
        ordered=sorted(edges-set(preferred))+preferred
        graph=self.native.graph(n,ordered)
        text=self.text.replace('@d solution_mod 100000','@d solution_mod 1')
        marker='printf("\\n"); /* reflection witness */'
        self.assertIn(marker,text)
        text=text.replace(marker,marker+' exit(0);',1)
        program=self.native.build('board-first',text)
        result=subprocess.run([str(program),str(graph)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        line=next(line for line in result.stdout.decode().splitlines() if 'reflection:' in line)
        cycle=[int(word[1:]) for word in line.split('reflection:')[1].split()]
        self.assertEqual(set(cycle),set(range(n)))
        chosen={tuple(sorted((cycle[i],cycle[(i+1)%n]))) for i in range(n)}
        self.assertTrue(chosen<=edges)
        self.assertEqual({tuple(sorted((71-u,71-v))) for u,v in chosen},chosen)
        self.assertEqual(sum(u+v==71 for u,v in chosen),2)


if __name__=='__main__': unittest.main()
