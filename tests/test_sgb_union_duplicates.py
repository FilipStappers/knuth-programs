"""SGB-011: minimum duplicate weights belong to their actual target arc."""
import itertools
from pathlib import Path
import tempfile
import unittest
from sgb_multigraph_native import MultigraphNative,expected


class SgbUnionDuplicates(unittest.TestCase):
    def test_interleaved_duplicates(self):
        fixture=[(0,1,60),(0,1,80),(0,2,200),(0,1,100)]
        with tempfile.TemporaryDirectory() as temp:
            native=MultigraphNative(Path(temp))
            for order in itertools.permutations(fixture):
                for directed in [0,1]:
                    for split in [0,2,4]:
                        g,h=order[:split],order[split:]
                        self.assertEqual(native.graph('union',g,h,directed),expected('union',g,h,directed))
            g=[(0,0,70),(0,1,90),(0,0,30),(3,2,50),(3,2,20)]
            h=[(0,1,10),(2,3,40),(0,0,60)]
            for directed in [0,1]:
                for multi in [0,1]:
                    self.assertEqual(native.graph('union',g,h,directed,multi),expected('union',g,h,directed,multi))


if __name__=='__main__':unittest.main()
