"""BUG-061: five-input masks and canonical tables against all cube symmetries."""
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'programs/archives/boolchains'


def cube_maps():
    return [tuple(sum((((point >> axis) & 1) ^ ((flips >> j) & 1)) << j
                      for j, axis in enumerate(permutation)) for point in range(32))
            for permutation in itertools.permutations(range(5)) for flips in range(32)]


def canonical(table, maps):
    return min(min(value, value ^ 0xffffffff)
               for mapping in maps
               for value in [sum(((table >> mapping[point]) & 1) << point for point in range(32))])


class BoolchainMasks(unittest.TestCase):
    def test_complete_symmetry_oracles(self):
        tables = sorted({0, 0xffffffff, 0x16686880, 0x12345678, 0xdeadbeef,
                         *[1 << i for i in [0, 1, 15, 16, 30, 31]],
                         *[sum((point.bit_count() >= threshold) << point for point in range(32))
                           for threshold in range(1, 6)],
                         *[((i * 0x9e3779b9) ^ (i << 17)) & 0xffffffff for i in range(1, 13)]})
        maps = cube_maps()
        expected = {table: canonical(table, maps) for table in tables}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            for name in ['boolcode', '5chains0', '5chainsx', '5chainsy']:
                with self.subTest(name=name):
                    text = (ROOT / (name + '.w')).read_text()
                    if name == 'boolcode':
                        text = text.replace('#include <stdio.h>', '#include <stdio.h>\n#include <stdlib.h>')
                        text = text.replace('main(int argc,char *argv[])', 'int main(int argc,char *argv[])')
                    else:
                        text = re.sub(r'\bmain\(', 'original_main(', text, count=1)
                        init = '@<Initialize the |delta| table@>' if name == '5chains0' else \
                            '@<Initialize the |delta| table and other tables@>'
                        text += '''
@c
int main(void) {
  int i,j,k,s,cmp;
  truthtab input,t,tt,d;
  ''' + init + ''';
  while (scanf("%x",&input)==1) {
    t=input,tt=mask,cmp=0;
    for (j=0;j<nnn;j++) {
      switch(delta[j]) { @<Cases to move to the next truth table@> }
      if (t<tt) tt=t;
    }
    printf("%08x\\n",tt);
  }
  return 0;
}
'''
                    source = work / (name + '.w')
                    generated = source.with_suffix('.c')
                    program = source.with_suffix('')
                    source.write_text(text)
                    subprocess.run(['ctangle', str(source), '-', str(generated)],
                                   capture_output=True, check=True)
                    subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                    '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                                    str(generated), '-o', str(program)], capture_output=True, check=True)
                    if name != 'boolcode':
                        result = subprocess.run([str(program)], input=''.join(f'{t:x}\n' for t in tables).encode(),
                                                capture_output=True, timeout=10)
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        self.assertEqual(result.stderr, b'')
                        self.assertEqual([int(t, 16) for t in result.stdout.split()],
                                         [expected[t] for t in tables])
                    else:
                        for table in tables:
                            result = subprocess.run([str(program), f'{table:x}'], capture_output=True, timeout=10)
                            self.assertEqual(result.returncode, 0, result.stderr.decode())
                            self.assertEqual(result.stderr, b'')
                            match = re.search(rb'is (-?)([0-9a-f]{8})\(([^)]+)\)', result.stdout)
                            self.assertIsNotNone(match, result.stdout)
                            code = int(match[2], 16)
                            self.assertEqual(code, expected[table])
                            permutation = list(map(int, re.findall(rb'[+-]\d+', match[3])))
                            self.assertEqual(sorted(map(abs, permutation)), [1, 2, 3, 4, 5])
                            for point in range(32):
                                args = [(point >> (5 - abs(p))) & 1 ^ (p < 0) for p in permutation]
                                image = sum(bit << (4 - i) for i, bit in enumerate(args))
                                self.assertEqual((table >> (31 - point)) & 1,
                                                 ((code >> (31 - image)) & 1) ^ bool(match[1]))


if __name__ == '__main__':
    unittest.main()
