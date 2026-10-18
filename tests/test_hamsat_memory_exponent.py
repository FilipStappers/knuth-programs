"""BUG-152: accepted m31 reaches a defined allocation request."""
from itertools import combinations
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(),'GraphBase sources required')
class HamsatMemoryExponent(unittest.TestCase):
    def test_upper_exponents_with_refusing_allocator(self):
        with tempfile.TemporaryDirectory() as temp:
            native=GraphNative(Path(temp))
            text=(ROOT/'programs/programs/hamsat.w').read_text()
            allocation='mem=(cel*)malloc(memsize*sizeof(cel));'
            self.assertEqual(text.count(allocation),1)
            text=text.replace(allocation,
                'printf("REQUEST %llu\\n",(unsigned long long)(memsize*sizeof(cel))); mem=NULL;')
            program=native.build('memory',text)
            graph=native.graph(3,list(combinations(range(3),2)))
            for exponent in [18,30,31]:
                with self.subTest(exponent=exponent):
                    result=subprocess.run([str(program),str(graph),f'm{exponent}'],
                                          capture_output=True,timeout=10)
                    self.assertIn(b"can't allocate the big mem array",result.stderr)
                    self.assertNotEqual(result.returncode,0)
                    self.assertEqual(result.stdout,f'REQUEST {4*2**exponent}\n'.encode())


if __name__ == '__main__':
    unittest.main()
