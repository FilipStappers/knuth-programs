"""B050: actual heuristic sections at the signed counter boundary."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SparseCoverCounters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for heuristic counter sections')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for base_name, change in [('ssxcc', 'ssxcc-frb0'), ('ssxcc', 'ssxcc-wtd0'),
                                  ('xccdc', 'xccdc-frb'), ('xccdc', 'xccdc-wtd')]:
            base = (ROOT/'programs/programs'/(base_name+'.w')).read_text()
            for key, value in [('max_level', 64), ('max_stage', 32), ('max_cols', 128),
                               ('max_nodes', 8192), ('savesize', 8192), ('poolsize', 65536)]:
                base, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', base)
                assert count <= 1
            text = base
            if '-frb' in change:
                text += '''
@c
int regression_step(int initial,int failed) {
  int best_itm=10;
  assigns(best_itm)=initial; fails(best_itm)=0;
  if (failed) {
    @<Take account of a failure for |best_itm|@>;
  }@+else {
    @<Take account of a nonfailure for |best_itm|@>;
  }
  return assigns(best_itm);
}
'''
            else:
                text += '''
@c
int regression_step(int initial,int failed) {
  int tough_itm=10;
  wt(tough_itm)=initial;
  @<Increase the weight of |tough_itm|@>;
  return wt(tough_itm);
}
'''
            source = cls.work/'section.w'
            source.write_text(text)
            generated = cls.work/'section.c'
            subprocess.run(['ctangle', str(source), str(ROOT/'programs/programs'/(change+'.ch')),
                            str(generated)], check=True, capture_output=True)
            driver = cls.work/'driver.c'
            driver.write_text(r'''
#include <stdlib.h>
#include <limits.h>
#define main published_main
#include "section.c"
#undef main
int main(int argc,char **argv) {
  return regression_step(atoi(argv[1]),atoi(argv[2]))==INT_MAX?0:1;
}
''')
            program = cls.work/change
            subprocess.run(['gcc', '-std=gnu99', '-fgnu89-inline', '-Wno-implicit-int',
                            '-O1', '-I'+sgb, '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(driver), str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[change] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_last_representable_increment_and_both_assignment_paths(self):
        for name, program in self.programs.items():
            for failed in ([0, 1] if '-frb' in name else [0]):
                with self.subTest(change=name, failed=failed):
                    result = subprocess.run([str(program), '2147483646', str(failed)],
                                            capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    result = subprocess.run([str(program), '2147483647', str(failed)],
                                            capture_output=True, timeout=5)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertTrue(b'Too many assignments' in result.stderr or b'Weight overflow' in result.stderr)


if __name__ == '__main__':
    unittest.main()
