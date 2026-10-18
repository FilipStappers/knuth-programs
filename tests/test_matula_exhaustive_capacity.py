"""BUG-031: maximum trie boundary and temporary reroot records."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT
from test_matula_singleton import embeds


@unittest.skipUnless((GRAPHBASE/'gb_flip.c').exists(),'GraphBase sources required')
class MatulaExhaustiveCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        change=(ROOT/'programs/programs/matula-exhaustive.ch').read_text()
        observation='''make_sstring(mserial); make_tstring(nserial);
printf("CASE %s %s %d\\n",sstring,tstring,z>0);
'''
        cls.programs={}
        for first in [False,True]:
            path=cls.native.work/('first.ch' if first else 'all.ch')
            path.write_text(change.replace('      @<Record the solution@>;',
                observation+('exit(0);' if first else '      @<Record the solution@>;')))
            cls.programs[first]=cls.native.build('first' if first else 'all',
                (ROOT/'programs/programs/matula.w').read_text(),path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self,m,n,first=False):
        result=subprocess.run([str(self.programs[first]),str(m),str(n)],capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertNotIn(b'confused',result.stderr)
        return re.findall(rb'CASE ([.0-9a-f]+) ([.0-9a-f]+) ([01])',result.stdout)

    def test_admitted_maximum_first_pair(self):
        for n in [15,16]:
            with self.subTest(n=n):
                rows=self.run_case(n,n,True)
                self.assertEqual(len(rows),1)
                a,b,answer=rows[0]
                self.assertEqual(len(a),n)
                self.assertEqual(a,b)
                self.assertEqual(answer,b'1')

    def test_complete_small_families_against_injective_maps(self):
        counts={3:1,4:2,5:3,6:6}
        def edges(text):
            return {tuple(sorted((i,int(chr(parent),16)))) for i,parent in enumerate(text) if i}
        for m in range(3,7):
            for n in range(m,7):
                with self.subTest(m=m,n=n):
                    rows=self.run_case(m,n)
                    self.assertEqual(len(rows),counts[m]*counts[n])
                    self.assertEqual(len({(a,b) for a,b,_ in rows}),len(rows))
                    for a,b,answer in rows:
                        self.assertEqual(answer==b'1',embeds(m,edges(a),n,edges(b)))


if __name__ == '__main__':
    unittest.main()
