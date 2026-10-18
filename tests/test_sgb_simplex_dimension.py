"""SGB-007: zero-dimensional simplex/subsets terminate after their single point."""
from pathlib import Path
import tempfile
import unittest
from sgb_basic_native import BasicNative


class SgbSimplexDimension(unittest.TestCase):
    def test_zero_and_one_dimensional_graphs(self):
        with tempfile.TemporaryDirectory() as temp:
            native=BasicNative(Path(temp))
            for kind in ['simplex','subsets']:
                for n in range(1,6):
                    for directed in [0,1]:
                        self.assertEqual(native.graph(kind,n,0,directed),({str(n)},[]))
                        names,edges=native.graph(kind,n,n,directed)
                        expected={str(i)+'.'+str(n-i) for i in range(n+1)}
                        if kind=='simplex':
                            pairs={(str(i)+'.'+str(n-i),str(i+1)+'.'+str(n-i-1),1)
                                   for i in range(n)}
                        else:pairs={(str(0)+'.'+str(n),str(n)+'.0',1)}
                        if not directed:pairs|={(b,a,l) for a,b,l in pairs}
                        self.assertEqual(names,expected)
                        self.assertEqual(set(edges),pairs)


if __name__=='__main__':unittest.main()
