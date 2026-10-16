"""B030: exercise the actual CWEB undo section and packed tags directly."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
#define main algorithm_main
#include "under-test.c"
#undef main
int main(void) {
  int j,k;
  unsigned int values[]={0,1,0xffffff};
  for (j=0;j<128;j++) for (k=0;k<3;k++) {
    a[j]=b[j]=values[k];
    ptr=0;
    newa(j,17);
    newb(j,19);
    regression_undo();
    regression_undo();
    if (a[j]!=values[k] || b[j]!=values[k] || ptr!=0) {
      fprintf(stderr,"Undo mismatch at position %d, value %u!\n",j,values[k]);
      return 1;
    }
  }
  printf("384 undo pairs passed.\n");
  return 0;
}
'''


class AdditionChainUndo(unittest.TestCase):
    def test_unsigned_packed_records_round_trip_all_128_positions(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            for name in ['achain1', 'achain2', 'achain3', 'achain4', 'achain-all']:
                with self.subTest(program=name):
                    source = (ROOT/'programs/programs'/(name+'.w')).read_text()
                    source, count = re.subn(r'(?m)^@d nmax [^\n]+', '@d nmax 128', source)
                    self.assertEqual(count, 1)
                    # Expose the actual literate section rather than copying its logic.
                    source += '\n@c\nvoid regression_undo(void) {\n  int i;\n  @<Undo a change@>;\n}\n'
                    literate = work/'under-test.w'
                    literate.write_text(source)
                    generated = work/'under-test.c'
                    subprocess.run(['ctangle', str(literate), '-', str(generated)],
                                   check=True, capture_output=True)
                    harness = work/'harness.c'
                    harness.write_text(HARNESS)
                    program = work/name
                    subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                    '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                                    str(harness), '-o', str(program)], check=True, capture_output=True)
                    result = subprocess.run([str(program)], capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(result.stdout, b'384 undo pairs passed.\n')


if __name__ == '__main__':
    unittest.main()
