"""BUG-009: reserve every dummy arc before reformatting Hamiltonian paths."""
from itertools import combinations
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class SimpathDummyCapacity(unittest.TestCase):
    def test_boundary_counts_include_all_dummy_arcs(self):
        with tempfile.TemporaryDirectory() as temp:
            native=GraphNative(Path(temp))
            text=(ROOT/'programs/programs/simpath.w').read_text()
            text=text.replace('  @<Do the algorithm@>;',
                              '  printf("EDGES %d\\n",m); return 0;')
            program=native.build('any',text,ROOT/'programs/programs/simpath-ham-any.ch')
            for n,removed,accepted in [(62,0,True),(63,16,True),(63,15,False),(63,0,False)]:
                with self.subTest(n=n,removed=removed):
                    edges=list(combinations(range(n),2))
                    if removed:
                        edges=edges[:-removed]
                    graph=native.graph(n,edges)
                    result=subprocess.run([str(program),str(graph),'v0',f'v{n-1}'],
                                          capture_output=True,timeout=10)
                    if accepted:
                        self.assertEqual(result.returncode,0,result.stderr.decode())
                        self.assertIn(f'EDGES {len(edges)+n}\n'.encode(),result.stdout)
                    else:
                        self.assertNotEqual(result.returncode,0)
                        self.assertIn(b'dummy',result.stderr)
                        self.assertEqual(result.stdout,b'')


if __name__ == '__main__':
    unittest.main()
