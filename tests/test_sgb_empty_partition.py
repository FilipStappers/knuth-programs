"""SGB-008: the empty partition is the sole partition of zero."""
from pathlib import Path
import tempfile
import unittest
from sgb_basic_native import BasicNative


def partitions(n,limit=None):
    if n==0:return {()}
    return {(first,)+rest for first in range(1,min(n,n if limit is None else limit)+1)
            for rest in partitions(n-first,first)}


def name(p):return '+'.join(map(str,p))


class SgbEmptyPartition(unittest.TestCase):
    def test_empty_and_small_partition_graphs(self):
        with tempfile.TemporaryDirectory() as temp:
            native=BasicNative(Path(temp))
            for n in range(8):
                for bound in [0,1,2,3]:
                    for directed in [0,1]:
                        allowed={p for p in partitions(n) if not bound or len(p)<=bound}
                        pairs=set()
                        for p in allowed:
                            for i,part in enumerate(p):
                                for a in range(1,part):
                                    q=tuple(sorted(p[:i]+p[i+1:]+(a,part-a),reverse=True))
                                    if q in allowed:pairs.add((name(p),name(q),1))
                        if not directed:pairs|={(b,a,l) for a,b,l in pairs}
                        names,edges=native.graph('parts',n,bound,directed)
                        self.assertEqual(names,{name(p) for p in allowed},(n,bound))
                        self.assertEqual(set(edges),pairs,(n,bound,directed))
                        self.assertEqual(len(edges),len(pairs))


if __name__=='__main__':unittest.main()
