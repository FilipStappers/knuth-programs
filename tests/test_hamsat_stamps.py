"""BUG-013: initialized redundancy stamps and Hamiltonian clause entailment."""
from itertools import combinations, permutations
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class HamsatStamps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        text=(ROOT/'programs/programs/hamsat.w').read_text()
        needle='vmem=(variable*)malloc((vars+1)*sizeof(variable));'
        assert text.count(needle)==1
        # Make indeterminate allocator contents deterministic, leaving all
        # production initialization, inference and conflict logic in place.
        poisoned=text.replace(needle,needle+'\nif(vmem) memset(vmem,0xa5,(vars+1)*sizeof(variable));')
        cls.program=cls.native.build('hamsat',poisoned)
        check='''for(k=2;k<=vars;k++) if(vmem[k].stamp!=0) {
  fprintf(stderr,"nonzero initial stamp\\n"); exit(70);
}
'''
        cls.observer=cls.native.build('stampcheck',poisoned.replace(
            'heap=(uint*)malloc(vars*sizeof(uint));',check+'heap=(uint*)malloc(vars*sizeof(uint));'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_variable_initialization(self):
        graph=self.native.graph(6,list(combinations(range(6),2)))
        result=subprocess.run([str(self.observer),str(graph),'m18','v1','s0'],
                              capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr.decode())

    def test_decisions_witnesses_and_learned_entailment(self):
        rng=random.Random(13)
        cases=[(6,[(0,1),(0,4),(0,5),(1,2),(1,3),(1,4),(2,3),(2,4),(3,4),(3,5),(4,5)])]
        for n in range(3,9):
            pairs=list(combinations(range(n),2))
            cases.extend((n,[e for e in pairs if rng.randrange(4)]) for _ in range(4))
        for n,edges in cases:
            allowed={frozenset(e) for e in edges}
            tours=[(0,)+p for p in permutations(range(1,n))
                   if all(frozenset(e) in allowed for e in zip((0,)+p,p+(0,)))]
            models=[set(zip(t,t[1:]+t[:1])) for t in tours]
            graph=self.native.graph(n,edges)
            for seed in [0,37]:
                with self.subTest(n=n,edges=edges,seed=seed):
                    learned=self.native.work/'learned.txt'
                    if learned.exists():
                        learned.unlink()
                    result=subprocess.run([str(self.program),str(graph),'m18','v1',f's{seed}',
                                           'l'+str(learned)],capture_output=True,timeout=10)
                    if result.returncode == 250:
                        self.assertFalse(tours)
                        self.assertIn(b'Not Hamiltonian',result.stderr)
                        self.assertEqual(result.stdout,b'')
                        continue
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    rows=[row for row in result.stdout.decode().splitlines()
                          if re.fullmatch(r'v\d+(?: v\d+)+',row.strip())]
                    self.assertEqual(bool(rows),bool(tours),result.stdout.decode())
                    for row in rows:
                        vertices=tuple(map(int,re.findall(r'v(\d+)',row)))
                        self.assertEqual(len(vertices),n+1)
                        self.assertEqual(vertices[0],vertices[-1])
                        self.assertIn(vertices[:-1],tours)
                    if learned.exists():
                        for clause in learned.read_text().splitlines():
                            if not clause.strip() or clause.startswith('~ '):
                                continue
                            literals=re.findall(r'(~?)v(\d+)>v(\d+)',clause)
                            self.assertTrue(literals,clause)
                            for model in models:
                                self.assertTrue(any(((int(a),int(b)) in model)!=bool(neg)
                                                    for neg,a,b in literals),clause)
                        learned.unlink()


if __name__ == '__main__':
    unittest.main()
