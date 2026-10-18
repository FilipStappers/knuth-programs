"""BUG-003: geometry uses original board indices after vertex permutation."""
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


def exact_geometry(path):
    points=[(F(v%6),F(v//6)) for v in path]
    segments=list(zip(points,points[1:]))
    assert all(sorted((abs(a-c),abs(b-d)))==[1,2] for (a,b),(c,d) in segments)
    signed=sum(a*d-c*b for (a,b),(c,d) in segments)/2
    def winding(x,y):
        return sum((1 if c>a else -1) for (a,b),(c,d) in segments
                   if min(a,c)<x<max(a,c) and b+(x-a)*(d-b)/(c-a)<y)
    corners=[winding(F(i)-F(1,2),F(j)-F(1,2)) for i in range(1,6) for j in range(1,6)]
    assert sum(corners)==signed
    lines=[]
    cuts={x for x,y in points}
    for (a,b),(c,d) in segments:
        slope=(d-b)/(c-a)
        lines.append((min(a,c),max(a,c),slope,b-slope*a))
    for lo,hi,m,c in lines:
        for low,high,mm,cc in lines:
            if m!=mm:
                cross=(cc-c)/(m-mm)
                if max(lo,low)<cross<min(hi,high):
                    cuts.add(cross)
    ordered=sorted(cuts)
    odd=F(0)
    for left,right in zip(ordered,ordered[1:]):
        midpoint=(left+right)/2
        crossings=sorted(m*midpoint+c for lo,hi,m,c in lines if lo<midpoint<hi)
        assert len(crossings)%2==0
        odd+=(right-left)*sum(crossings[i+1]-crossings[i] for i in range(0,len(crossings),2))
    assert (120*odd).denominator==1
    return [int(120*odd),int(abs(signed)),corners.count(0),max(corners)-min(corners)]


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class WindingCoordinates(unittest.TestCase):
    def test_original_label_geometry_after_randomized_enumeration(self):
        with tempfile.TemporaryDirectory() as temp:
            native=GraphNative(Path(temp))
            program=native.build('winding',(ROOT/'programs/programs/ssham.w').read_text(),
                                 ROOT/'programs/programs/ssham-winding-prep.ch')
            edges=[(u,v) for u,v in combinations(range(36),2)
                   if sorted((abs(u%6-v%6),abs(u//6-v//6)))==[1,2]]
            graph=native.graph(36,edges)
            for seed in [None,0,37]:
                with self.subTest(seed=seed):
                    result=subprocess.run([str(program),str(graph),'m1','t5',
                                           *([] if seed is None else [f's{seed}'])],
                                          capture_output=True,timeout=15)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertNotIn(b"can't happen",result.stderr)
                    rows=[line for line in result.stdout.decode().splitlines() if ' #' in line]
                    self.assertEqual(len(rows),5)
                    for line in rows:
                        path=list(map(int,re.findall(r'v(\d+)',line)))
                        self.assertEqual(len(path),37)
                        self.assertEqual(path[0],path[-1])
                        self.assertEqual(set(path),set(range(36)))
                        actual=list(map(int,line.split('#')[0].split()[-1].split(',')))
                        self.assertEqual(actual,exact_geometry(path))


if __name__ == '__main__':
    unittest.main()
