"""BUG-010: stop the first-arc boundary scan at the graph boundary."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT
from simpath_native import diagram


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class DirectedCyclesEmpty(unittest.TestCase):
    def test_edgeless_graphs_and_neighboring_two_cycle(self):
        with tempfile.TemporaryDirectory() as temp:
            native=GraphNative(Path(temp))
            text=(ROOT/'programs/programs/simpath-directed-cycles.w').read_text()
            text=text.replace('@d logmemsize 27','@d logmemsize 18').replace('@d loghtsize 24','@d loghtsize 16')
            program=native.build('directed',text)
            for n in [0,1,3,90]:
                with self.subTest(n=n):
                    graph=native.graph(n,[],True)
                    result=subprocess.run([str(program),str(graph)],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertEqual(diagram(result.stdout),({},set()))
                    self.assertIn(b'2:0,0\n',result.stdout)
            graph=native.graph(2,[(0,1),(1,0)],True)
            result=subprocess.run([str(program),str(graph)],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            arcs,family=diagram(result.stdout)
            self.assertEqual({frozenset(arcs[i] for i in selected) for selected in family},
                             {frozenset({(0,1),(1,0)})})


if __name__ == '__main__':
    unittest.main()
