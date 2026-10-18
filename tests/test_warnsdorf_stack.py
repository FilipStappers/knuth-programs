"""BUG-005: pending alternatives accumulate across all active depths."""
from itertools import combinations
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class WarnsdorfStack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.native = GraphNative(Path(cls.temp.name))
        text=(ROOT/'programs/programs/back-warnsdorf.w').read_text()
        cls.full=cls.native.build('warn',text)
        # Stop only after publishing a genuine complete path, avoiding 45! search.
        needle='if (l==g->n) hcount++,vcount[v-g->vertices]++,vpr[v-g->vertices]+=p;'
        assert text.count(needle)==1
        cls.first=cls.native.build('first',text.replace(needle,needle+'\n    if(l==g->n) exit(0);'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_46_first_path(self):
        n=46
        graph=self.native.graph(n,list(combinations(range(n),2)))
        result=subprocess.run([str(self.first),str(graph),'v0'],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertEqual(set(map(int,re.findall(rb'v(\d+)',result.stdout))),set(range(n)))
        self.assertEqual(len(re.findall(rb'v\d+',result.stdout)),n)

    def test_small_search_counts(self):
        rng=random.Random(5)
        for n in range(1,8):
            pairs=list(combinations(range(n),2))
            for edges in [pairs,[(i,i+1) for i in range(n-1)],
                          [e for e in pairs if rng.randrange(2)]]:
                with self.subTest(n=n,edges=edges):
                    adjacency=[set() for _ in range(n)]
                    for i,j in edges:
                        adjacency[i].add(j)
                        adjacency[j].add(i)
                    leaves=[]
                    def visit(path):
                        free=set(range(n))-set(path)
                        tips=adjacency[path[-1]] & free
                        if not tips:
                            leaves.append(tuple(path))
                            return
                        degrees={v:len(adjacency[v] & free) for v in tips}
                        for v in tips:
                            if degrees[v]==min(degrees.values()):
                                visit(path+[v])
                    visit([0])
                    graph=self.native.graph(n,edges)
                    result=subprocess.run([str(self.full),str(graph),'v0'],
                                          capture_output=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    match=re.search(rb'Altogether \d+ nodes, (\d+) paths, (\d+) hpaths',result.stderr)
                    self.assertIsNotNone(match,result.stderr.decode())
                    self.assertEqual(tuple(map(int,match.groups())),
                                     (len(leaves),sum(len(p)==n for p in leaves)))
                    known=set(leaves)
                    for line in result.stdout.splitlines():
                        path=tuple(map(int,re.findall(rb'v(\d+)',line)))
                        self.assertIn(path,known)


if __name__ == '__main__':
    unittest.main()
