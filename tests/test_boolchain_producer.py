"""BUG-062: native producer substitutions and allocation-size admission.

Observers bypass database traversal and recursive/classification updates;
allocation is refused deliberately, without reserving a two-gigabyte table.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'programs/archives/boolchains/5chainsi.w'


class BoolchainProducer(unittest.TestCase):
    def compile_observer(self, work, observer, refuse=False):
        text = SOURCE.read_text().replace('main(int argc,char *argv[])', 'original_main(int argc,char *argv[])')
        text = text.replace('#include <stdio.h>', '#include <stdio.h>\n#include <stdlib.h>')
        if refuse:
            text = text.replace('#include <stdlib.h>', '''#include <stdlib.h>
static void *refuse(size_t bytes) { printf("REQUEST %zu\\n",bytes); return NULL; }
#define malloc refuse''', 1)
        else:
            text = text.replace('if (dist[tt]>r)', 'if (0)').replace('if (dist[tt]>r+1)', 'if (0)')
        text += '\n@c\n' + observer
        source = work / ('allocation.w' if refuse else 'substitute.w')
        generated = source.with_suffix('.c')
        program = source.with_suffix('')
        source.write_text(text)
        subprocess.run(['ctangle', str(source), '-', str(generated)], capture_output=True, check=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(program)], capture_output=True, check=True)
        return program

    def test_exact_allocation_request_without_allocating(self):
        with tempfile.TemporaryDirectory() as tmp:
            program = self.compile_observer(Path(tmp), '''int main(void) {
  int j,k,r;
  truthtab t,d;
  fclass *c;
  printf("MASK %08x\\n",mask);
  @<Make the |dist| table@>;
  return 0;
}
''', refuse=True)
            result = subprocess.run([str(program)], capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b'runtime error', result.stderr)
            self.assertIn(b'allocate the dist array', result.stderr)
            self.assertEqual(result.stdout, b'MASK ffffffff\nREQUEST 2147483648\n')

    def test_all_six_native_substitutions(self):
        sections = [r'$x_1$ by $x_1\land x_2$', r'$x_1$ by $x_1\xor x_2$',
                    r'$x_1$ by $x_2\land x_3$', r'$x_1$ by $x_2\xor x_3$',
                    r'$(x_1,x_2)$ by $(x_1\land x_2,x_1\lor x_2)$',
                    r'$(x_1,x_2)$ by $(x_1\land x_2,x_1\xor x_2)$']
        observer = '''int main(void) {
  int j=0,r=0;
  truthtab t,tt,input;
  fclass *c=NULL,*cc=NULL;
  while (scanf("%x",&input)==1) {
'''
        for section in sections:
            observer += 't=input; @<Try replacing ' + section + '@>; printf("%08x\\n",tt);\n'
        observer += '} return 0; }\n'
        tables = sorted({0, 0xffffffff, 0x16686880, 0x12345678,
                         *[1 << i for i in range(32)],
                         *[sum(((point >> axis) & 1) << (31 - point) for point in range(32))
                           for axis in range(5)]})
        with tempfile.TemporaryDirectory() as tmp:
            program = self.compile_observer(Path(tmp), observer)
            result = subprocess.run([str(program)], input=''.join(f'{t:x}\n' for t in tables).encode(),
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stderr, b'')
            actual = [int(value, 16) for value in result.stdout.split()]
            self.assertEqual(len(actual), len(tables) * 6)
            for table_index, table in enumerate(tables):
                for op in range(6):
                    expected = 0
                    for point in range(32):
                        a,b,c,d,e = [(point >> i) & 1 for i in range(4,-1,-1)]
                        x,y = [(a&b,b),(a^b,b),(b&c,b),(b^c,b),(a&b,a|b),(a&b,a^b)][op]
                        image = (x<<4)|(y<<3)|(c<<2)|(d<<1)|e
                        expected |= ((table >> (31-image)) & 1) << (31-point)
                    self.assertEqual(actual[6*table_index+op], expected, (table,op))


if __name__ == '__main__':
    unittest.main()
