"""BUG-089: size/admission and allocation failures, without random experiments."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_flip.c').exists(),'GraphBase sources required')
class ExperimentAllocations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        cls.programs={}
        for name in ['ran-prim','rost']:
            text=(ROOT/f'programs/programs/{name}.w').read_text()
            text=text.replace('@c','''@c
#include <stdio.h>
#include <stdlib.h>
void *test_malloc(size_t bytes) {
  static int calls;
  printf("ALLOC %llu\\n",(unsigned long long)bytes);
  if(getenv("TEST_REFUSE") && ++calls==atoi(getenv("TEST_REFUSE"))) return NULL;
  return malloc(bytes);
}
#define malloc test_malloc
''',1)
            if name=='ran-prim':
                original='  while (t) @<Move@>;'
                observer='''for(k=1;k<=n;k++) if(perm[k]!=n+1-k) exit(71);
if(perm[0]!=0 || perm[n+1]!=n+1) exit(71);
for(k=1;k<n;k++) if(list[k-1]!=k) exit(71);
puts("READY"); return 0;'''
            else:
                original='  for (r=0;r<n;r++) @<Move@>;'
                observer='''for(k=0;k<=n;k++) if(bit[k]!=1) exit(71);
for(;k<=2*n+1;k++) if(bit[k]!=0) exit(71);
if(list[0]!=n || t!=1) exit(71);
puts("READY"); return 0;'''
            assert text.count(original)==1
            cls.programs[name]=cls.native.build(name,text.replace(original,observer))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_nonpositive_unrepresentable_and_oversized_inputs(self):
        for name,program in self.programs.items():
            for n in ['0','-1','2147483647','4294967297','9'*100,'1x']:
                with self.subTest(name=name,n=n):
                    result=subprocess.run([str(program),n,'0'],capture_output=True,timeout=5,
                                          env=dict(os.environ,TEST_REFUSE='1'))
                    self.assertNotEqual(result.returncode,0)
                    self.assertEqual(result.stdout,b'')
                    self.assertTrue(result.stderr)

    def test_small_initialization_and_actual_element_sizes(self):
        for name,program in self.programs.items():
            for n in [1,2,10]:
                with self.subTest(name=name,n=n):
                    result=subprocess.run([str(program),str(n),'0'],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    actual=list(map(int,re.findall(rb'ALLOC (\d+)',result.stdout)))
                    self.assertEqual(actual,[4*(n+2),4*n] if name=='ran-prim' else [2*n+2,4*(n+1)])
                    self.assertIn(b'READY',result.stdout)

    def test_each_allocation_failure_is_checked_before_initialization(self):
        for name,program in self.programs.items():
            for refused in [1,2]:
                with self.subTest(name=name,refused=refused):
                    result=subprocess.run([str(program),'10','0'],capture_output=True,timeout=5,
                                          env=dict(os.environ,TEST_REFUSE=str(refused)))
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn(b'allocate',result.stderr)
                    self.assertNotIn(b'READY',result.stdout)

    def test_largest_supported_size_reaches_refusing_allocator(self):
        for name,program in self.programs.items():
            n=2147483645 if name=='ran-prim' else 1073741822
            result=subprocess.run([str(program),str(n),'0'],capture_output=True,timeout=5,
                                  env=dict(os.environ,TEST_REFUSE='1'))
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'allocate',result.stderr)
            request=4*(n+2) if name=='ran-prim' else 2*n+2
            self.assertEqual(result.stdout,f'ALLOC {request}\n'.encode())


if __name__ == '__main__':
    unittest.main()
