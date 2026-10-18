"""BUG-007: solution output at full edge capacity and complete small families."""
from itertools import combinations, permutations
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class HamdanceClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.native = GraphNative(Path(cls.temp.name))
        cls.program = cls.native.build('dance',(ROOT/'programs/programs/hamdance.w').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_graph(self,n,edges):
        graph = self.native.graph(n,edges)
        result = subprocess.run([str(self.program),str(graph),'1'],capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        actual = set()
        allowed = {frozenset(e) for e in edges}
        rows = result.stdout.decode().splitlines()
        for row in rows:
            if not row.startswith('v'):
                continue
            cycle = list(map(int,re.findall(r'v(\d+)',row)))
            self.assertEqual(len(cycle),n+1)
            self.assertEqual(cycle[0],cycle[-1])
            self.assertEqual(set(cycle),set(range(n)))
            self.assertTrue(all(frozenset(e) in allowed for e in zip(cycle,cycle[1:])))
            body = cycle[:-1]
            p = body.index(0)
            body = body[p:]+body[:p]
            actual.add(min(tuple(body),tuple([0]+body[:0:-1])))
        self.assertEqual(len(actual),sum(row.startswith('v') for row in rows))
        if actual or result.stderr:
            self.assertRegex(result.stderr.decode(),rf'Altogether {len(actual)} solutions?[, ]')
        return actual

    def test_default_maximum_cycle(self):
        n=20000
        actual = self.run_graph(n,[(i,(i+1)%n) for i in range(n)])
        self.assertEqual(actual,{tuple(range(n))})

    def test_small_complete_and_seeded_families(self):
        rng=random.Random(7)
        for n in range(3,8):
            pairs=list(combinations(range(n),2))
            for edges in [pairs,[(i,(i+1)%n) for i in range(n)],
                          [e for e in pairs if rng.randrange(3)],
                          [e for e in pairs if rng.randrange(2)]]:
                with self.subTest(n=n,edges=edges):
                    allowed={frozenset(e) for e in edges}
                    expected={(0,)+p for p in permutations(range(1,n)) if p[0]<p[-1]
                              and all(frozenset(e) in allowed
                                      for e in zip((0,)+p,p+(0,)))}
                    self.assertEqual(self.run_graph(n,edges),expected)


if __name__ == '__main__':
    unittest.main()
