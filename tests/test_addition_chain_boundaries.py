"""B030: real bounded addition-chain runs against independent minima."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from test_achain3_search import minimum

ROOT = Path(__file__).resolve().parents[1]
NMAX = 256


class AdditionChainBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def compile_program(self, name):
        if name in self.programs:
            return self.programs[name]
        text = (ROOT/'programs/programs'/(name+'.w')).read_text()
        text, count = re.subn(r'(?m)^@d nmax [^\n]+', f'@d nmax {NMAX}', text)
        self.assertEqual(count, 1)
        source = self.work/(name+'.w')
        source.write_text(text)
        generated = self.work/(name+'.c')
        subprocess.run(['ctangle', str(source), '-', str(generated)],
                       check=True, capture_output=True)
        program = self.work/name
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(program)], check=True, capture_output=True)
        self.programs[name] = program
        return program

    def check_table(self, name):
        empty = self.work/'empty'
        empty.write_bytes(b'')
        output = self.work/(name+'.out')
        result = subprocess.run([str(self.compile_program(name)), str(empty), str(output)],
                                capture_output=True, timeout=15,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'runtime error', result.stderr)
        expected = bytes((0 if n == 1 else minimum(n, 1))+32 for n in range(1, NMAX))
        self.assertEqual(output.read_bytes(), expected)

    def test_achain2_sparse_summand_power_requires_a_valid_position(self):
        self.check_table('achain2')

    def test_sparse_sections_guard_all_positions_and_preserve_forced_moves(self):
        harness_text = r'''
#define main algorithm_main
#include "sparse.c"
#undef main
int main(void) {
  int position,operand;
  for (operand=0;operand<2;operand++) {
    for (position=0;position<128;position++)
      if (!regression_sparse(position,1,operand)) return 1;
    if (!regression_sparse(8,132,operand) || a[4]!=16 || a[3]!=8) return 2;
    if (!regression_sparse(24,(1<<23)+1,operand) || a[22]!=(1<<22)) return 3;
  }
  return 0;
}
'''
        for name in ['achain2', 'achain3', 'achain4', 'achain-all']:
            with self.subTest(program=name):
                text = (ROOT/'programs/programs'/(name+'.w')).read_text()
                text = re.sub(r'(?m)^@d nmax [^\n]+', '@d nmax 256', text)
                text += '''
@c
int regression_sparse(int position,int value,int is_p) {
  int i,j,ubp=position,ubq=position,p=value,q=value;
  ptr=0;
  for (j=0;j<128;j++) a[j]=1,b[j]=0xffffff;
  if (is_p) {
    @<Make forced moves if |p| has a special form@>;
  }@+else {
    @<Make forced moves if |q| has a special form@>;
  }
  return 1;
failp: return 0;
failq: return 0;
}
'''
                source = self.work/'sparse.w'
                source.write_text(text)
                generated = self.work/'sparse.c'
                subprocess.run(['ctangle', str(source), '-', str(generated)],
                               check=True, capture_output=True)
                harness = self.work/'sparse-harness.c'
                harness.write_text(harness_text)
                program = self.work/(name+'-sparse')
                subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                                str(harness), '-o', str(program)], check=True, capture_output=True)
                result = subprocess.run([str(program)], capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == '__main__':
    unittest.main()
