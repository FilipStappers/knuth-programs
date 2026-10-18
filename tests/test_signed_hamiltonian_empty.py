"""BUG-004: reject empty selected domains before sparse-set initialization."""
from itertools import combinations, permutations
from math import factorial
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class SignedHamiltonianEmpty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        cls.programs={name:cls.native.build(name,(ROOT/f'programs/programs/{name}.w').read_text())
                      for name in ['ssham','ssdiham','ssbidiham']}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_empty_graphs_reject(self):
        graph=self.native.graph(0,[])
        for name,program in self.programs.items():
            with self.subTest(name=name):
                result=subprocess.run([str(program),str(graph)],capture_output=True,timeout=5)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(b'at least one selected vertex',result.stderr)
                self.assertEqual(result.stdout,b'')

    def test_empty_and_negative_selected_prefix_reject(self):
        graph=self.native.graph(4,list(combinations(range(4),2)))
        for prefix in ['n0','n-1']:
            result=subprocess.run([str(self.programs['ssham']),str(graph),prefix],
                                  capture_output=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'at least one selected vertex',result.stderr)
            self.assertEqual(result.stdout,b'')

    def test_nonempty_complete_graph_counts(self):
        for name,program in self.programs.items():
            for n in range(1,7):
                with self.subTest(name=name,n=n):
                    directed=name!='ssham'
                    edges=list(permutations(range(n),2) if directed else combinations(range(n),2))
                    graph=self.native.graph(n,edges,directed)
                    result=subprocess.run([str(program),str(graph)],capture_output=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    expected=0 if n<3 else factorial(n-1)//(1 if directed else 2)
                    # Directed two-cycles also are admitted by both directed solvers.
                    if directed and n==2:
                        expected=1
                    if expected:
                        self.assertIn(f'Altogether {expected} solution'.encode(),result.stderr)
                    else:
                        self.assertIn(b'There are no Hamiltonian cycles',result.stdout)


if __name__ == '__main__':
    unittest.main()
