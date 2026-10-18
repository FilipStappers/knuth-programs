"""SGB-012: reverse duplicate scans must not update an unrelated edge pair."""
import itertools
from pathlib import Path
import tempfile
import unittest
from sgb_multigraph_native import MultigraphNative,expected


class SgbIntersectionDuplicates(unittest.TestCase):
    def test_duplicate_minimax_lengths_and_mates(self):
        g=[(0,2,60),(1,2,200)]
        h=[(0,2,60),(0,2,80),(0,2,100),(1,2,200)]
        with tempfile.TemporaryDirectory() as temp:
            native=MultigraphNative(Path(temp))
            for order in itertools.permutations(h):
                for directed in [0,1]:
                    self.assertEqual(native.graph('intersection',g,order,directed),
                                     expected('intersection',g,order,directed))
            g=[(0,0,70),(0,1,90),(0,0,30),(2,3,50),(2,3,20)]
            h=[(0,1,10),(2,3,40),(0,0,60),(2,3,10),(0,0,20)]
            for directed in [0,1]:
                for multi in [0,1]:
                    self.assertEqual(native.graph('intersection',g,h,directed,multi),
                                     expected('intersection',g,h,directed,multi))


if __name__=='__main__':unittest.main()
