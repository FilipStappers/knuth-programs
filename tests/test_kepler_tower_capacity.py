"""BUG-077: supported tower depth and independent complete small families."""
from functools import lru_cache
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'programs/programs/back-kepler-towers.w'


def tower_family(n):
    @lru_cache(None)
    def layers(width, previous, remaining):
        answer = []
        for size in range(1,min(width//2,remaining)+1):
            for layer in itertools.combinations(range(1,width+1),size):
                if any((x % width)+1 in layer for x in layer):
                    continue
                if all(any((x-y)%width in (0,1,width-1) for y in previous) for x in layer):
                    answer.append(layer)
        return answer

    answer = set()
    def visit(walls, used):
        if used == n:
            answer.add(walls)
            return
        width = 1 << len(walls)
        for layer in layers(width,walls[-1][-1],n-used):
            visit(walls[:-1]+(walls[-1]+(layer,),),used+len(layer))
        if used+width <= n:
            bottom = tuple(range(1,2*width,2))
            visit(walls+((bottom,),),used+width)
    visit((((1,),),),1)
    return answer


class KeplerTowerCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.programs = []
        original = SOURCE.read_text().replace('main (int argc,char*argv[])', 'int main (int argc,char*argv[])')
        for first_only in [False,True]:
            text = original
            if first_only:
                text = text.replace('if (n<=10)', 'if (1)')
                old = '  t[l-1]=1; /* complete the top layer */\n  goto b5;'
                assert text.count(old)==1
                text = text.replace(old,'  t[l-1]=1; /* complete the top layer */\n  exit(0);')
            source = Path(cls.temp.name)/('first.w' if first_only else 'full.w')
            generated = source.with_suffix('.c')
            program = source.with_suffix('')
            source.write_text(text)
            subprocess.run(['ctangle',str(source),'-',str(generated)],capture_output=True,check=True)
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1','-fsanitize=undefined,bounds',
                            '-fno-sanitize-recover=all',str(generated),'-o',str(program)],
                           capture_output=True,check=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_first_supported_maximum_tower(self):
        result = subprocess.run([str(self.programs[1]),'40'],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertEqual(result.stderr,b'')
        self.assertEqual(result.stdout,(';'.join(['1']*40)+'\n').encode())

    def test_complete_small_tower_families(self):
        for n in range(1,9):
            with self.subTest(n=n):
                result = subprocess.run([str(self.programs[0]),str(n)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                actual = [tuple(tuple(tuple(map(int,layer.split(','))) for layer in wall.split(';'))
                                for wall in line.split(':'))
                          for line in result.stdout.decode().splitlines()]
                expected = tower_family(n)
                self.assertEqual(set(actual),expected)
                self.assertEqual(len(actual),len(expected))
                self.assertEqual(result.stderr,f'Altogether {len(expected)} towers generated.\n'.encode())

    def test_invalid_sizes_reject(self):
        for argument in ['0','-1','41']:
            result = subprocess.run([str(self.programs[0]),argument],capture_output=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn(b'runtime error',result.stderr)
            self.assertEqual(result.stdout,b'')


if __name__ == '__main__':
    unittest.main()
