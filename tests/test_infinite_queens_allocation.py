"""BUG-151: wide allocation arithmetic and independent greedy queen prefixes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'programs/programs/infty-queens.w'


class InfiniteQueensAllocation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.work=Path(cls.temp.name)
        text=SOURCE.read_text()
        cls.programs={}
        for refusing in [False,True]:
            source=cls.work/('refuse.w' if refusing else 'queens.w')
            body=text
            if refusing:
                body=body.replace('a=(char*)calloc(maxmema,sizeof(char));',
                    'printf("REQUEST %lld %lld %lld\\n",maxmema,maxmemb,minmemc+maxmemc); a=NULL;')
            source.write_text(body)
            generated=source.with_suffix('.c')
            program=source.with_suffix('')
            subprocess.run(['ctangle',str(source),'-',str(generated)],check=True,capture_output=True)
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1',
                            '-fsanitize=undefined,bounds,float-cast-overflow',
                            '-fsanitize-undefined-trap-on-error',str(generated),'-o',str(program)],
                           check=True,capture_output=True)
            cls.programs[refusing]=program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_maximum_goal_reaches_checked_allocation(self):
        goal=2147483647
        result=subprocess.run([str(self.programs[True]),str(goal)],capture_output=True,timeout=5)
        self.assertIn(b"Can't allocate array a",result.stderr)
        self.assertNotEqual(result.returncode,0)
        a=int(1.6180339887498948482*goal)+10
        self.assertEqual(result.stdout,f'REQUEST {a} {a+goal} {goal+20}\n'.encode())

    def test_invalid_goal_domain_rejects(self):
        for goal in ['0','-1','2147483648','4294967297','9'*100,'1x']:
            with self.subTest(goal=goal):
                result=subprocess.run([str(self.programs[True]),goal],capture_output=True,timeout=5)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(result.stdout,b'')
                self.assertIn(b'positive int',result.stderr)

    def test_small_prefixes_against_independent_greedy_sets(self):
        columns,sums,differences=set(),set(),set()
        expected=[]
        for row in range(1,1001):
            col=1
            while col in columns or row+col in sums or col-row in differences:
                col+=1
            expected.append(col)
            columns.add(col); sums.add(row+col); differences.add(col-row)
        for size in [1,2,10,100,1000]:
            with self.subTest(size=size):
                result=subprocess.run([str(self.programs[False]),str(size)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                self.assertEqual(list(map(int,result.stdout.split())),expected[:size])


if __name__ == '__main__':
    unittest.main()
