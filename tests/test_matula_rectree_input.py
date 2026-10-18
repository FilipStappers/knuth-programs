"""BUG-032: validate complete rectree extents before storing child metadata."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import ROOT, GraphNative
from test_matula_singleton import write_rectree


class MatulaRectreeInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        text=(ROOT/'programs/programs/matula.w').read_text()
        text=text.replace('@<Input the tree $S$@>;', '''n=read_rectree(argv[1]);
printf("N %d\\n",n);
for(p=0;p<n;p++) for(q=tnode[p].child;q;q=tnode[q].sib) printf("%d %d\\n",p,q);
return 0;''',1)
        cls.programs=[cls.native.build(name,text,ROOT/('programs/programs/'+name+'.ch'))
                      for name in ['matula-big','matula-big-planted']]

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def run_file(self,program,path):
        args=[str(path),str(path)] if program.name=='matula-big' else [str(path),'0','0']
        return subprocess.run([str(program),*args],capture_output=True,timeout=5)

    def test_invalid_decimal_and_subtree_extents(self):
        bad=['T2147483648_0.\n','T'+'9'*5000+'_0.\n',
             'T3_2147483648.\n','T3_0.\nT3_0=+2147483648T1_1.\n',
             'T3_0.\nT3_0=+2000T2000_1.\n',
             'T3_0.\nT3_0=+2T1_1+1T1_3.\n',
             'T3_0.\nT3_0=+2000T1_1+1T1_2001.\n',
             '2T2000_0.\n','T2000_0,T2000_2000.\n',
             'T3_.\nT3_0=+2T1_1.\n']
        path=self.native.work/'bad.rectree'
        for data in bad:
            path.write_text(data)
            for program in self.programs:
                with self.subTest(program=program.name,data=data[:60]):
                    result=self.run_file(program,path)
                    self.assertNotEqual(result.returncode,0)
                    self.assertTrue(result.stderr,result.stdout)
                    self.assertEqual(result.stdout,b'')

    def test_valid_trees_and_clones_preserve_exact_edges(self):
        path=self.native.work/'valid.rectree'
        fixtures=[(-1,),(-1,0),(-1,0,0,1,1,2),tuple([-1]+[(i-1)//2 for i in range(1,2000)])]
        for parents in fixtures:
            expected=write_rectree(parents,path)
            for program in self.programs:
                result=self.run_file(program,path)
                self.assertEqual(result.returncode,0,result.stderr)
                lines=result.stdout.decode().splitlines()
                self.assertEqual(lines[0],f'N {len(parents)}')
                self.assertEqual({tuple(sorted(map(int,line.split()))) for line in lines[1:]},expected)
        for data,expected in [
                ('2T2_0.\n',{(0,1),(0,2),(2,3)}),
                ('T2_0,T3_2.\nT3_2=+2T1_3.\n',{(0,1),(0,2),(2,3),(2,4)}),
                ('T7_0.\nT7_0=+2T3_1.\nT3_1=+2T1_2.\n',
                 {(0,1),(0,4),(1,2),(1,3),(4,5),(4,6)})]:
            path.write_text(data)
            for program in self.programs:
                result=self.run_file(program,path)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual({tuple(sorted(map(int,line.split()))) for line in
                                  result.stdout.decode().splitlines()[1:]},expected)


if __name__=='__main__': unittest.main()
