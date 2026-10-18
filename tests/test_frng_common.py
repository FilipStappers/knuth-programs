"""BUG-088: the published test reads shared double state, not a function."""
from pathlib import Path
import tempfile
import unittest
from fortran_native import ROOT, COMPILER, build, run


@unittest.skipUnless(COMPILER,'Native gfortran required')
class FrngCommon(unittest.TestCase):
    def test_published_double_state_driver_links_and_matches_both_blockings(self):
        with tempfile.TemporaryDirectory() as temp:
            program=Path(temp)/'frngdb'
            build(ROOT/'programs/programs/frngdb.f',program)
            result=run(program)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.decode().split(),['0.36410514377569680455']*2)


if __name__=='__main__': unittest.main()
