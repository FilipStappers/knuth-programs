"""BUG-058: terminal depth and complete small perfect-digital-invariant families."""
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'programs/programs/back-pdi.w'


class PdiDepth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.programs = []
        original = SOURCE.read_text().replace('main(int argc,char*argv[])', 'int main(int argc,char*argv[])')
        for restricted in [False, True]:
            text = original
            if restricted:
                # Restrict the root's maximum digit to zero, a valid singleton
                # branch. Stop after its first solution, avoiding high-order search.
                text = text.replace('xl=9;', 'xl=0;')
                old = '  printf("\\n");\n  goto b5;'
                assert text.count(old) == 1
                text = text.replace(old, '  printf("\\n");\n  exit(0);')
            source = Path(cls.temp.name) / ('zero.w' if restricted else 'full.w')
            generated = source.with_suffix('.c')
            program = source.with_suffix('')
            source.write_text(text)
            subprocess.run(['ctangle', str(source), '-', str(generated)], capture_output=True, check=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], capture_output=True, check=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_maximum_orders_zero_branch_reaches_terminal_depth(self):
        for order in [998,999,1000]:
            result = subprocess.run([str(self.programs[1]), str(order)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stderr,b'')
            self.assertEqual(result.stdout, b'1: ' + b'0'*(order+1) + b'->' + b'0'*(order+1) + b'\n')

    def test_complete_small_families(self):
        for order in range(2,9):
            with self.subTest(order=order):
                expected = set()
                powers = [digit**order for digit in range(10)]
                for digits in itertools.combinations_with_replacement(range(10),order+1):
                    value = sum(powers[digit] for digit in digits)
                    if tuple(sorted(map(int,str(value).zfill(order+1)))) == digits:
                        expected.add(value)
                result = subprocess.run([str(self.programs[0]),str(order)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                self.assertNotIn(b'runtime error',result.stderr)
                rows = re.findall(rb'(?m)^\d+: (\d+)->(\d+)$',result.stdout)
                actual = [int(value) for _,value in rows]
                self.assertEqual(set(actual),expected)
                self.assertEqual(len(actual),len(expected))
                for digits,value in rows:
                    self.assertEqual(sorted(digits),sorted(value))
                self.assertIn(f'Altogether {len(expected)} solutions for m={order}'.encode(),result.stderr)


if __name__ == '__main__':
    unittest.main()
