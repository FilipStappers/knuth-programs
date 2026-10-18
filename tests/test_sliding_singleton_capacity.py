"""BUG-149: one-based piece identifiers include a full maxsize board."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_flip.c').exists(),'GraphBase sources required')
class SlidingSingletonCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        text=(ROOT/'programs/programs/sliding.w').read_text()
        text=text.replace('@d memsize (1<<25)','@d memsize (1<<15)')
        cls.program=cls.native.build('sliding',text)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_full_and_neighboring_singleton_boards_have_zero_distance(self):
        for rows,cols in [(1,1),(15,16),(16,16)]:
            for style in range(6):
                with self.subTest(rows=rows,cols=cols,style=style):
                    board='1'*(rows*cols)
                    data=f'{rows} x {cols}\n1 = 1\n{board}\n{board}\n'
                    result=subprocess.run([str(self.program),str(style)],input=data.encode(),
                                          capture_output=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertIn(b'Distance 0',result.stdout)
                    self.assertNotIn(b'Distance 1',result.stdout)
                    self.assertNotIn(b'Sorry',result.stderr)


if __name__ == '__main__':
    unittest.main()
