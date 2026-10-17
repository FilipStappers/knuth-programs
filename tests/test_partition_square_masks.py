"""BUG-054: enumerate actual first-level row/column placement families.

Only the top-level partition choice and verify callback are replaced, so the
native placement and cleanup loops run without the full recursive search.
"""
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'programs/programs/perfect-partition-square.w'


class PartitionSquareMasks(unittest.TestCase):
    def test_combination_successors_across_word_boundaries(self):
        text = SOURCE.read_text().replace('void main(void)', 'void original_main(void)')
        text += '''
@c
int main(void) {
  int n,k;
  unsigned long long mask;
  for (n=1;n<=49;n++) {
    if (n>16 && n!=31 && n!=32 && n!=33 && n!=42 && n!=49) continue;
    for (k=1;k<=(n<=16?n:2);k++) {
      for (mask=lobits(k);mask<(1ULL<<n);) {
        printf("%d %d %llx\\n",n,k,mask);
        gosper(mask);
      }
    }
  }
  return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'successors.w'
            generated = source.with_suffix('.c')
            program = source.with_suffix('')
            source.write_text(text)
            subprocess.run(['ctangle', str(source), '-', str(generated)],
                           capture_output=True, check=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], capture_output=True, check=True)
            result = subprocess.run([str(program)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stderr, b'')
            actual = {}
            for line in result.stdout.splitlines():
                n, k, mask = line.split()
                actual.setdefault((int(n), int(k)), []).append(int(mask, 16))
            for n in [*range(1, 17), 31, 32, 33, 42, 49]:
                for k in range(1, (n if n <= 16 else 2) + 1):
                    expected = {sum(1 << bit for bit in subset)
                                for subset in itertools.combinations(range(n), k)}
                    masks = actual[n, k]
                    self.assertEqual(len(masks), len(expected))
                    self.assertEqual(set(masks), expected)

    def test_complete_first_placement_families(self):
        original = SOURCE.read_text()
        with tempfile.TemporaryDirectory() as tmp:
            for name, initial, column in [('row', 63, False), ('column', 4096 + 31, True)]:
                with self.subTest(name=name):
                    text = original.replace('void main(void)', 'int main(void)')
                    old = 'for (bits=lobits(6);bits<1<<13;)'
                    self.assertEqual(text.count(old), 1)
                    text = text.replace(old, f'for (bits={initial};bits=={initial};)')
                    start = text.index('void verify(int l) {')
                    end = text.index('@ OK,', start)
                    text = text[:start] + '''void verify(int l) {
  unsigned long long mask=0;
  int i,j;
  for (i=0;i<7;i++) for (j=0;j<7;j++)
    if (a[i][j]==l) mask|=1ULL<<(7*i+j);
  printf("%llx\\n",mask);
}

''' + text[end:]
                    source = Path(tmp) / (name + '.w')
                    generated = source.with_suffix('.c')
                    program = source.with_suffix('')
                    source.write_text(text)
                    subprocess.run(['ctangle', str(source), '-', str(generated)],
                                   capture_output=True, check=True)
                    subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                    '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                                    str(generated), '-o', str(program)], capture_output=True, check=True)
                    result = subprocess.run([str(program)], capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertNotIn(b'runtime error', result.stderr)
                    actual = [int(line, 16) for line in result.stdout.splitlines()]
                    hard = {7*i if column else i for i in range(7)}
                    other = set(range(49)) - hard
                    expected = {sum(1 << bit for bit in (*six, extra))
                                for six in itertools.combinations(sorted(hard), 6)
                                for extra in other}
                    self.assertEqual(len(actual), 294)
                    self.assertEqual(set(actual), expected)


if __name__ == '__main__':
    unittest.main()
