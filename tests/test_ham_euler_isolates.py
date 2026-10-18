"""BUG-006: isolated vertices leave their empty adjacency lists intact."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class HamEulerIsolates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.native = GraphNative(Path(cls.temp.name))
        text = (ROOT/'programs/programs/ham-euler.w').read_text()
        # Bound BFS resources, retaining the original path and adjacency code.
        text = text.replace('@d logmemsize 27','@d logmemsize 15')
        cls.program = cls.native.build('euler',text)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_isolated_starts_and_trailing_isolates(self):
        for n,edges,start in [(1,[],0),(4,[],0),(4,[],3),
                              (4,[(0,1),(1,2)],3),(4,[(0,1),(1,2)],0)]:
            with self.subTest(n=n,edges=edges,start=start):
                graph = self.native.graph(n,edges)
                result = subprocess.run([str(self.program),str(graph),'0',f'v{start}'],
                                        capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                size = 3 if edges and start == 0 else 1
                self.assertRegex(result.stderr.decode(),rf'0 cycles and \d+ noncycles? of size {size}\.')

    def test_connected_cycles_remain_valid(self):
        for n in range(3,9):
            edges = [(i,(i+1)%n) for i in range(n)]
            graph = self.native.graph(n,edges)
            result = subprocess.run([str(self.program),str(graph),'0','v0'],
                                    capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertRegex(result.stderr.decode(),rf'1 cycle and 0 noncycles of size {n}\.')
            # Every printed path follows real edges and repeats no vertex.
            allowed = {frozenset(e) for e in edges}
            for line in result.stdout.decode().splitlines():
                if not re.match(r'^v\d',line):
                    continue
                vertices = list(map(int,re.findall(r'v(\d+)',line)))
                self.assertEqual(len(vertices),len(set(vertices)))
                self.assertTrue(all(frozenset(e) in allowed for e in zip(vertices,vertices[1:])))


if __name__ == '__main__':
    unittest.main()
