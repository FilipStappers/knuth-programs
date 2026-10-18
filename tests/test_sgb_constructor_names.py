"""SGB-005: short names must not inherit a previous constructor's suffix."""
from functools import lru_cache
import itertools
from pathlib import Path
import tempfile
import unittest
from sgb_basic_native import BasicNative


@lru_cache(None)
def trees(n):
    if not n:return (None,)
    return tuple((a,b) for size in range(n) for a in trees(size) for b in trees(n-1-size))


def prefix(tree):
    return 'x' if tree is None else '.'+prefix(tree[0])+prefix(tree[1])


def rotations(tree):
    if tree is None:return set()
    a,b=tree;result=set()
    if a is not None:result.add((a[0],(a[1],b)))
    result|={(aa,b) for aa in rotations(a)}
    result|={(a,bb) for bb in rotations(b)}
    return result


class SgbConstructorNames(unittest.TestCase):
    def test_permutations_and_tree_names_after_another_constructor(self):
        with tempfile.TemporaryDirectory() as temp:
            native=BasicNative(Path(temp))
            for n in range(1,6):
                names,edges=native.graph('perms',n)
                expected={''.join(p) for p in itertools.permutations('01234'[:n])}
                self.assertEqual(names,expected)
                adjacent={(word,word[:i]+word[i+1]+word[i]+word[i+2:],1)
                          for word in expected for i in range(n-1)}
                self.assertEqual(set(edges),adjacent)
            for n in range(5):
                for directed in [0,1]:
                    names,edges=native.graph('binary',n,directed=directed)
                    expected={prefix(tree) for tree in trees(n)}
                    self.assertEqual(names,expected)
                    adjacent={(prefix(tree),prefix(other),1) for tree in trees(n) for other in rotations(tree)}
                    if not directed:adjacent|={(b,a,length) for a,b,length in adjacent}
                    self.assertEqual(set(edges),adjacent)


if __name__=='__main__':unittest.main()
