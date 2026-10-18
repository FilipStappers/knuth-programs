"""BUG-002: compressed-word writes must respect byte allocation capacities."""
from itertools import combinations, permutations
from math import factorial
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class DynamicCompressedCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        cls.programs={}
        for name in ['dynaham','dynahamp','dynadiham','dynabidiham']:
            text=(ROOT/f'programs/programs/{name}.w').read_text()
            for macro,value in [('memsize','200000'),('wtsize','30000'),
                                ('oldmemsize','test_oldmemsize')]:
                text,count=re.subn(r'(?m)^@d '+macro+r'\s+\S+', '@d '+macro+' '+value,text)
                assert count==1
            text=text.replace('@c','@c\nint test_oldmemsize;')
            allocation='oldmem=(unsigned long long*)malloc(oldmemsize);'
            assert text.count(allocation)==1
            text=text.replace(allocation,
                              'test_oldmemsize=atoi(getenv("TEST_OLDMEM"));\n'
                              +allocation)
            # Before either actual heap write, independently stop if its full
            # word would leave the requested byte allocation. No OOB write runs.
            for needle in ['oldmem[omp++]=pack','oldmem[omp]=pack']:
                assert text.count(needle)==1
                text=text.replace(needle,'if(omp>=test_oldmemsize/sizeof(*oldmem)) {\n'
                                  'fprintf(stderr,"UNGUARDED compressed write\\n"); exit(71);\n}\n'+needle)
            cls.programs[name]=cls.native.build(name,text)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_small_allocations_reject_before_writes(self):
        for name,program in self.programs.items():
            directed=name in ['dynadiham','dynabidiham']
            edges=list(permutations(range(7),2) if directed else combinations(range(7),2))
            graph=self.native.graph(7,edges,directed)
            for size in [7,8,16]:
                with self.subTest(name=name,bytes=size):
                    result=subprocess.run([str(program),str(graph)],capture_output=True,timeout=10,
                                          env=dict(os.environ,TEST_OLDMEM=str(size)))
                    self.assertNotEqual(result.returncode,0)
                    self.assertNotEqual(result.returncode,71,result.stderr.decode())
                    self.assertIn(b'oldmem overflow',result.stderr)

    def test_generous_storage_retains_exact_counts_and_byte_units(self):
        for name,program in self.programs.items():
            directed=name in ['dynadiham','dynabidiham']
            for n in [4,7]:
                with self.subTest(name=name,n=n):
                    edges=list(permutations(range(n),2) if directed else combinations(range(n),2))
                    graph=self.native.graph(n,edges,directed)
                    result=subprocess.run([str(program),str(graph)],capture_output=True,timeout=15,
                                          env=dict(os.environ,TEST_OLDMEM='100000'))
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    counts={int(k):int(v) for v,k in re.findall(
                        rb'There are (\d+) Hamiltonian (\d+)-(?:cycles|paths)',result.stdout)}
                    expected=factorial(n)//2 if name=='dynahamp' else factorial(n-1)//(1 if directed else 2)
                    self.assertEqual(counts[n],expected)
                    usage=re.search(rb'(\d+) oldmemsize bytes',result.stderr)
                    self.assertIsNotNone(usage,result.stderr.decode())
                    self.assertEqual(int(usage[1])%8,0)


if __name__ == '__main__':
    unittest.main()
