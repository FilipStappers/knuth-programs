"""BUG-022: every native refinement word matches arithmetic modulo 2^64."""
from collections import defaultdict, deque
from itertools import combinations
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class GraphSignatureArithmetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        text=(ROOT/'programs/programs/graph-sig-v0.w').read_text()
        line=next(line for line in text.splitlines() if line.startswith('x=') and 'gb_next_rand' in line)
        text=text.replace(line,line+'\nprintf("X %llx\\n",(unsigned long long)x);')
        cls.program=cls.native.build('signature',text)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_native_refinements(self):
        rng=random.Random(22)
        cases=[(1,[]),(7,list(combinations(range(7),2))),
               (8,[(i,i^(1<<b)) for i in range(8) for b in range(3) if i<(i^(1<<b))]),
               (7,[(i,(i+1)%7) for i in range(7)]),(5,[(0,1),(1,2)])]
        cases += [(n,[e for e in combinations(range(n),2) if rng.randrange(2)]) for n in range(4,10)]
        mask=2**64-1
        for n,edges in cases:
            with self.subTest(n=n,edges=edges):
                graph=self.native.graph(n,edges)
                result=subprocess.run([str(self.program),str(graph),'v0'],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                adjacency=[set() for _ in range(n)]
                for a,b in edges:
                    adjacency[a].add(b); adjacency[b].add(a)
                distance={0:0}
                queue=deque([0])
                while queue:
                    v=queue.popleft()
                    for u in adjacency[v]-distance.keys():
                        distance[u]=distance[v]+1
                        queue.append(u)
                groups=defaultdict(set)
                for v,d in distance.items():
                    groups[d].add(v)
                groups=list(groups.values())
                values=dict(distance)
                frozen=set()
                rounds=[]
                for line in result.stdout.decode().splitlines():
                    if line.startswith('Round '):
                        rounds.append({'values':{},'fixed':set()})
                    elif line.startswith('X '):
                        rounds[-1]['x']=int(line[2:],16)
                    elif re.fullmatch(r' v\d+ [0-9a-f]+',line):
                        v,word=line.split()
                        rounds[-1]['values'][int(v[1:])]=int(word,16)
                    elif re.fullmatch(r' v\d+ is fixed',line):
                        rounds[-1]['fixed'].add(int(line.split()[0][1:]))
                self.assertTrue(rounds)
                for number,observed in enumerate(rounds):
                    old=values.copy()
                    newgroups=[]
                    expected={}
                    fixed=set()
                    changed=False
                    for group in groups:
                        if len(group)==1:
                            v=next(iter(group))
                            if v not in frozen:
                                fixed.add(v); frozen.add(v)
                            newgroups.append(group)
                            continue
                        split=defaultdict(set)
                        for v in group:
                            word=1
                            for u in adjacency[v]:
                                word=word*(observed['x']-old[u]) & mask
                            expected[v]=values[v]=word
                            split[word].add(v)
                        changed|=len(split)>1
                        newgroups+=list(split.values())
                    self.assertEqual(observed['values'],expected)
                    self.assertEqual(observed['fixed'],fixed)
                    self.assertEqual(changed,number+1<len(rounds))
                    groups=newgroups


if __name__ == '__main__':
    unittest.main()
