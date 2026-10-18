"""BUG-034: deletion counts must leave a supported nonempty planted tree."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT
from test_matula_singleton import write_rectree


@unittest.skipUnless((GRAPHBASE/'gb_flip.c').exists(),'GraphBase sources required')
class MatulaDeletions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        cls.program=cls.native.build('planted',(ROOT/'programs/programs/matula.w').read_text(),
                                     ROOT/'programs/programs/matula-big-planted.ch')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_invalid_deletion_counts_reject(self):
        path=self.native.work/'tree.rectree'
        write_rectree((-1,0,1,2,3,4),path)
        for deletion in [-1,-2147483648,4,2147483647]:
            with self.subTest(deletion=deletion):
                result=subprocess.run([str(self.program),str(path),str(deletion),'0'],
                                      capture_output=True,timeout=5)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(b'delet',result.stderr)
                self.assertNotIn(b'confused',result.stderr)
                self.assertEqual(result.stdout,b'')

    def test_valid_zero_and_maximum_deletions_still_embed(self):
        path=self.native.work/'tree.rectree'
        for parents in [(-1,0,1,2,3,4),(-1,0,0,0,0,0),(-1,0,0,1,1,2)]:
            edges=write_rectree(parents,path)
            for deletion in [0,1,3]:
                for seed in [0,37]:
                    with self.subTest(parents=parents,deletion=deletion,seed=seed):
                        result=subprocess.run([str(self.program),str(path),str(deletion),str(seed)],
                                              capture_output=True,timeout=5)
                        self.assertEqual(result.returncode,0,result.stderr.decode())
                        vertices=list(map(int,result.stdout.split()))
                        self.assertEqual(len(vertices),6-deletion)
                        self.assertEqual(len(vertices),len(set(vertices)))
                        self.assertTrue(all(0<=v<6 for v in vertices))
                        # An image of a subtree of a tree is connected.
                        reached={vertices[0]}
                        while True:
                            more={v for v in vertices if any(tuple(sorted((u,v))) in edges for u in reached)}
                            if more<=reached:
                                break
                            reached|=more
                        self.assertEqual(reached,set(vertices))


if __name__ == '__main__':
    unittest.main()
