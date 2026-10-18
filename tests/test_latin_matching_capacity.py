"""BUG-148: matching arcs are bounded by a bipartite square plus free boys."""
from itertools import permutations, product
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCES=Path(__file__).resolve().parents[1]/'programs/programs'
ALPHABET='123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


class LatinMatchingCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.work=Path(cls.temp.name)
        source=cls.work/'latin.w'
        text=(SOURCES/'partial-latin-gad.w').read_text()
        text=text.replace('@c','@c\nint test_peak_arcs;',1)
        call='@<Build the dag of shortest augmenting paths (SAPs)@>;'
        text=text.replace(call,call+'\nif(k>test_peak_arcs) test_peak_arcs=k;')
        call='@<Build the digraph for the current matching@>;'
        text=text.replace(call,call+'''\nif(originaln>=12) {
  printf("ARCS %d PEAK %d\\n",k,test_peak_arcs); exit(0);
}''')
        source.write_text(text)
        cls.programs={}
        for variant in ['base','swap']:
            generated=cls.work/(variant+'.c')
            subprocess.run(['ctangle',str(source),str(SOURCES/'partial-latin-gad-swap.ch') if variant=='swap' else '-',
                            str(generated)],check=True,capture_output=True)
            program=generated.with_suffix('')
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1','-include','string.h',
                            '-fsanitize=undefined,bounds','-fsanitize-undefined-trap-on-error',
                            str(generated),'-o',str(program)],check=True,capture_output=True)
            cls.programs[variant]=program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_board(self,variant,board):
        data='\n'.join(''.join(ALPHABET[x-1] if x else '.' for x in row) for row in board)+'\n'
        result=subprocess.run([str(self.programs[variant]),'show'],input=data.encode(),
                              cwd=self.work,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        return result

    def test_original_capacity_witnesses_and_default_maximum(self):
        swap=[[0]*14 for _ in range(14)]
        for i in range(1,5):
            for j in range(14):
                swap[i][j]=(i+j)%14+1
        for j in range(4):
            swap[5][j]=(5+j)%14+1
        for variant,board in [('base',[[0]*12 for _ in range(12)]),('swap',swap),
                              ('base',[[0]*61 for _ in range(61)])]:
            n=len(board)
            with self.subTest(variant=variant,n=n):
                result=self.run_board(variant,board)
                row=set(board[0])-{0}
                allowed=sum(value not in row and all(line[j]!=value for line in board)
                            for j in range(n) for value in range(1,n+1))
                match=re.search(rb'ARCS (\d+) PEAK (\d+)',result.stdout)
                self.assertIsNotNone(match,result.stdout.decode())
                arcs,peak=map(int,match.groups())
                self.assertEqual(arcs,allowed-n)
                self.assertLessEqual(peak,61*62)

    def test_small_completion_families(self):
        boards=[[[0]*3 for _ in range(3)],[[1,0,0],[0,0,0],[0,0,0]],
                [[1,0,0],[0,3,0],[0,0,2]]]
        family=[rows for rows in product(permutations([1,2,3]),repeat=3)
                if all(len({row[j] for row in rows})==3 for j in range(3))]
        for board in boards:
            expected={tuple(x for row in rows for x in row) for rows in family
                      if all(not board[i][j] or board[i][j]==rows[i][j] for i in range(3) for j in range(3))}
            for variant in self.programs:
                with self.subTest(board=board,variant=variant):
                    result=self.run_board(variant,board)
                    rows=re.findall(rb'Solution #\d+:\n((?:[1-3]{3}\n){3})',result.stdout)
                    actual={tuple(int(chr(c)) for c in row if c!=10) for row in rows}
                    self.assertEqual(len(actual),len(rows))
                    self.assertEqual(actual,expected)


if __name__ == '__main__':
    unittest.main()
