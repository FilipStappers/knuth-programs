"""BUG-064: actual initialized cost families, accounting, and bounded queries.

The expensive cost-discovery loop is replaced by a table observer. Initial
function parsing, list mutation, footprints, and the original query loop run.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'programs/programs'


class FchainsInitialization(unittest.TestCase):
    def test_full_discovery_is_unchanged_by_duplicate_or_zero_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'full.w'
            generated = source.with_suffix('.c')
            program = source.with_suffix('')
            source.write_text((ROOT / 'fchains4x.w').read_text().replace(
                'main(int argc,char *argv[])', 'int main(int argc,char *argv[])'))
            subprocess.run(['ctangle', str(source), '-', str(generated)], capture_output=True, check=True)
            subprocess.run(['gcc', '-std=gnu99', '-O2', '-fsanitize=undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated), '-o', str(program)],
                           capture_output=True, check=True)
            outputs = []
            for arguments in [[], ['0'], ['ffff'], ['ff','ff']]:
                result = subprocess.run([str(program), *arguments],
                                        input=b'0\nff\n1668\n6996\nabcd\nffff\n',
                                        capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stderr, b'')
                outputs.append(result.stdout)
            self.assertEqual(len(set(outputs)), 1)

    def test_initial_families_and_query_domain(self):
        text = (ROOT / 'fchains4x.w').read_text()
        start = text.index('  for (r=2;c;r++)')
        end = text.index('  @<Answer queries@>;', start)
        text = text[:start] + '''  printf("@@@@COUNT %d\\n",c);
  for (t=0;t<0x8000;t++) {
    p=&func[t];
    if (p->next->prev!=p || p->prev->next!=p) return 97;
    if (p->cost<=1) {
      printf("@@@@FUNC %04x %d",t,p->cost);
      for (j=0;j<mm;j++) printf(" %08x",p->footprint[j]);
      printf("\\n");
    }
  }
''' + text[end:]
        text = text.replace('main(int argc,char *argv[])', 'int main(int argc,char *argv[])')
        fixtures = [[], ['0'], ['ffff'], ['ff','ff'], ['1668'],
                    ['1668','1668','0','ffff','ff']]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'initial.w'
            generated = source.with_suffix('.c')
            program = source.with_suffix('')
            source.write_text(text)
            subprocess.run(['ctangle', str(source), '-', str(generated)], capture_output=True, check=True)
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated), '-o', str(program)],
                           capture_output=True, check=True)
            projections = [0xffff // ((1 << (1 << (4-k))) + 1) for k in range(1,5)]
            for arguments in fixtures:
                with self.subTest(arguments=arguments):
                    result = subprocess.run([str(program), *arguments],
                                            input=b'10000\n0\nffff\n', capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertIn(b'16-bit', result.stderr)
                    initial = projections + [int(value,16) for value in arguments]
                    initial = [value ^ (0xffff if value & 0x8000 else 0) for value in initial]
                    known = {0, *initial}
                    expected = {table: (0,0) for table in known}
                    steps = 0
                    for r in range(len(initial)):
                        for k in range(r):
                            a,b = initial[k],initial[r]
                            for table in [a&b,a&~b,~a&b,a|b,a^b]:
                                if table not in expected:
                                    expected[table] = (1,1 << steps)
                                    steps += 1
                    count = re.search(rb'@@COUNT (\d+)',result.stdout)
                    self.assertIsNotNone(count,result.stdout)
                    self.assertEqual(int(count[1]), 0x8000-len(expected))
                    actual = {}
                    for line in result.stdout.splitlines():
                        if line.startswith(b'@@FUNC '):
                            _,table,cost,*words = line.split()
                            footprint = sum(int(word,16) << (32*i) for i,word in enumerate(words))
                            actual[int(table,16)] = int(cost),footprint
                    self.assertEqual(actual,expected)
                    self.assertIn(b'0000 has cost 0',result.stdout)
                    self.assertIn(b'ffff has cost 0',result.stdout)
            for arguments in [['10000'], ['ffffffff'], ['0']*96]:
                result = subprocess.run([str(program), *arguments],capture_output=True,timeout=10)
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn(b'runtime error',result.stderr)


if __name__ == '__main__':
    unittest.main()
