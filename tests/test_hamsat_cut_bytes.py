"""BUG-153: charge cut storage by clause address rather than cycle identifier."""
from itertools import combinations
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class HamsatCutBytes(unittest.TestCase):
    def test_created_cut_pair_matches_allocated_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            native=GraphNative(Path(temp))
            text=(ROOT/'programs/programs/hamsat.w').read_text()
            section='@<Check for memory overflow@>='
            before,body=text.split(section)
            charge,after=body.split('@ @<Append the same clause but with arcs reversed@>=')
            # Observe only the accounting statement in the real cut-creation path.
            charge=re.sub(r'(?m)^(bytes\+=.*;)$',r'''{
  ullng observed_before=bytes;
  \1
  fprintf(stderr,"CHARGE "O"llu "O"lu\\n",bytes-observed_before,
          (unsigned long)(2*kk*sizeof(cel)));
}
''',charge)
            program=native.build('cutbytes',before+section+charge+
                                 '@ @<Append the same clause but with arcs reversed@>='+after)
            triangles=list(combinations(range(3),2))+list(combinations(range(3,6),2))
            observations=[]
            for links in [[(0,3),(0,4)],[(0,3),(0,4),(0,5)],[(0,3),(1,4)]]:
                graph=native.graph(6,triangles+links)
                for seed in [0,37]:
                    result=subprocess.run([str(program),str(graph),'m18','v1',f's{seed}'],
                                          capture_output=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    for charged,allocated in re.findall(rb'CHARGE (\d+) (\d+)',result.stderr):
                        observations.append((int(charged),int(allocated)))
            self.assertTrue(observations,'Fixtures must actually create cut clause pairs')
            self.assertTrue(all(a==b for a,b in observations),observations)


if __name__ == '__main__':
    unittest.main()
