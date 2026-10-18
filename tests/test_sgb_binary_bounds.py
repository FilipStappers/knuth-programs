"""SGB-006: impossible height constraints must not overrun coefficient storage."""
from pathlib import Path
import tempfile
import unittest
from sgb_basic_native import BasicNative
from test_sgb_constructor_names import trees, prefix, rotations


def height(tree):
    return 0 if tree is None else 1+max(map(height,tree))


class SgbBinaryBounds(unittest.TestCase):
    def test_empty_and_neighboring_height_restricted_graphs(self):
        with tempfile.TemporaryDirectory() as temp:
            native=BasicNative(Path(temp))
            for n,h in [(92,1),(91,1),(2000,1),(2000,2),(32,5),(64,6)]:
                self.assertEqual(native.graph('binary',n,h),(set(),[]))
            for n in range(6):
                for h in range(1,6):
                    for directed in [0,1]:
                        allowed={t for t in trees(n) if height(t)<=h}
                        expected={prefix(t) for t in allowed}
                        adjacent={(prefix(t),prefix(u),1) for t in allowed
                                  for u in rotations(t) if u in allowed}
                        if not directed:adjacent|={(b,a,l) for a,b,l in adjacent}
                        names,edges=native.graph('binary',n,h,directed)
                        self.assertEqual(names,expected,(n,h,directed))
                        self.assertEqual(set(edges),adjacent,(n,h,directed))
            for h in [5,6]:
                tree=None
                for _ in range(h):tree=(tree,tree)
                self.assertEqual(native.graph('binary',(1<<h)-1,h),({prefix(tree)},[]))


if __name__=='__main__':unittest.main()
