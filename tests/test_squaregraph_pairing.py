"""BUG-019: contract adjacent boundary positions using circular indices."""
from collections import Counter
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_flip.c').exists(),'GraphBase sources required')
class SquaregraphPairing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        cls.program=cls.native.build('squaregraph',(ROOT/'programs/programs/squaregraph-rand.w').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_reported_wraparound_and_seeded_boundaries(self):
        cases=[(103,2),(225,11)]+[(n,s) for n in [0,1,2,16,103,225,500] for s in range(5)]
        for steps,seed in cases:
            with self.subTest(steps=steps,seed=seed):
                result=subprocess.run([str(self.program),str(steps),str(seed)],
                                      capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                self.assertEqual(result.stderr,b'')
                counts=Counter(map(int,result.stdout.split()))
                self.assertTrue(counts)
                self.assertEqual(set(counts.values()),{2})
                self.assertTrue(all(0<=k<=steps+1 for k in counts))


if __name__ == '__main__':
    unittest.main()
