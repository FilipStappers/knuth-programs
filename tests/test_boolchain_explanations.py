"""BUG-063: native bottom-up history decoding versus direct substitution.

Local history records bypass database I/O and the final canonical lookup;
the original history decoder, permutation tables and printed formulas run.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'programs/archives/boolchains/5chainsx.w'


class BoolchainExplanations(unittest.TestCase):
    def test_all_six_substitution_histories(self):
        text = SOURCE.read_text().replace('main(int argc,char *argv[])', 'original_main(int argc,char *argv[])')
        self.assertEqual(text.count('  c=classify(tt);'), 1)
        text = text.replace('  c=classify(tt);', '  c=&hash[1]; c->tt=tt;')
        text += '''
@c
int main(void) {
  int i,j,k,d,s,cmp,op;
  truthtab input,t,tt;
  fclass *c;
  @<Initialize the |delta| table and other tables@>;
  while (scanf("%x %d",&input,&op)==2) {
    c=&hash[1]; c->history1=op; c->parent=0; hash[0].tt=input;
    printf("CASE %08x %d\\n",input,op);
    @<Explain how to compute |c->tt|@>;
  }
  return 0;
}
'''
        tables = sorted({0, 0xffffffff, 0x16686880, 0x12345678,
                         *[1 << i for i in range(32)],
                         *[sum(((point >> axis) & 1) << (31 - point) for point in range(32))
                           for axis in range(5)]})
        cases = [(table, op) for table in tables for op in range(6)]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'explain.w'
            generated = source.with_suffix('.c')
            program = source.with_suffix('')
            source.write_text(text)
            subprocess.run(['ctangle', str(source), '-', str(generated)], capture_output=True, check=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], capture_output=True, check=True)
            result = subprocess.run([str(program)], input=''.join(f'{t:x} {op}\n' for t, op in cases).encode(),
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stderr, b'')
            rows = re.findall(rb'then ([0-9a-f]{8})=([0-9a-f]{8})\(([^)]+)\)', result.stdout)
            self.assertEqual(len(rows), len(cases))
            arguments = [b'1&2,2,3,4,5', b'1^2,2,3,4,5', b'2&3,2,3,4,5',
                         b'2^3,2,3,4,5', b'1&2,1|2,3,4,5', b'1&2,1^2,3,4,5']
            for (table, op), (value, parent, expression) in zip(cases, rows):
                with self.subTest(table=f'{table:08x}', op=op):
                    self.assertEqual(int(parent, 16), table)
                    self.assertEqual(expression, arguments[op])
                    expected = 0
                    for point in range(32):
                        a, b, c, d, e = [(point >> i) & 1 for i in range(4, -1, -1)]
                        images = [(a & b, b), (a ^ b, b), (b & c, b),
                                  (b ^ c, b), (a & b, a | b), (a & b, a ^ b)]
                        x, y = images[op]
                        image = (x << 4) | (y << 3) | (c << 2) | (d << 1) | e
                        expected |= ((table >> (31 - image)) & 1) << (31 - point)
                    self.assertEqual(int(value, 16), expected)


if __name__ == '__main__':
    unittest.main()
