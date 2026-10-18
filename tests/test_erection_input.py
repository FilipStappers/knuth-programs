"""B037: malformed sets reject; valid constraints retain exact circuits."""
from pathlib import Path
import itertools
import re
import subprocess
import tempfile
import unittest
from graph_native import ROOT, FLAGS


class ErectionInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        source=Path(cls.temp.name)/'erection.w'
        source.write_text((ROOT/'programs/programs/erection.w').read_text())
        generated=source.with_suffix('.c')
        cls.program=source.with_suffix('')
        subprocess.run(['ctangle',str(source),'-',str(generated)],check=True,capture_output=True)
        subprocess.run(['gcc',*FLAGS,str(generated),'-o',str(cls.program)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def run_input(self,data):
        return subprocess.run([str(self.program)],input=data.encode(),capture_output=True,timeout=5)

    def test_invalid_universe_and_sets_reject(self):
        for data in ['','-1','17','999999999999999999999999999','4x',
                     '4 10000','4 10','4 -1','4 xyz','4 fz','4 0x',
                     '4 '+'f'*200]:
            with self.subTest(data=data):
                result=self.run_input(data)
                self.assertNotEqual(result.returncode,0)
                self.assertTrue(result.stderr,result.stdout)
                self.assertNotIn(b'The circuits are:',result.stdout)

    def test_small_matroid_oracle_and_implicit_zeroes(self):
        # Enumerate hereditary families satisfying augmentation, with no loops
        # or parallel points. No production closure algorithm is reused.
        optional=[s for s in range(16) if bin(s).count("1")>2]
        matroids=[]
        for choices in itertools.product([False,True],repeat=len(optional)):
            family={s for s in range(16) if bin(s).count("1")<=2}|{s for s,take in zip(optional,choices) if take}
            if any((s^(1<<i)) not in family for s in family for i in range(4) if s>>i&1): continue
            if any(not any((a|(1<<i)) in family for i in range(4) if (b&~a)>>i&1)
                   for a in family for b in family if bin(a).count("1")<bin(b).count("1")): continue
            matroids.append(family)
        self.assertEqual(len(matroids),7)
        sets=[7,11,13,14,15]
        for bits in range(64):
            constraints=[s for i,s in enumerate(sets) if bits>>i&1]
            rank3=bool(bits&32)
            admissible=[family for family in matroids if all(
                max(bin(t).count("1") for t in family if t&s==t)<=2 for s in constraints)
                and (not rank3 or 15 not in family)]
            greatest=set.union(*admissible)
            self.assertIn(greatest,admissible)
            circuits={s for s in range(1,16) if s not in greatest and all(
                (s^(1<<i)) in greatest for i in range(4) if s>>i&1)}
            data='4 '+' '.join(format(s,'x') for s in constraints)+' 0'+(' f' if rank3 else '')
            result=self.run_input(data)
            self.assertEqual(result.returncode,0,result.stderr)
            actual={sum(1<<int(c,16) for c in word) for word in
                    re.search(r'The circuits are:(.*)',result.stdout.decode())[1].split()}
            self.assertEqual(actual,circuits,(bits,data))
        for data in ['0','1','4','4 0','4 0 0 0']:
            result=self.run_input(data)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(result.stdout.endswith(b'The circuits are:\n'))


if __name__=='__main__': unittest.main()
