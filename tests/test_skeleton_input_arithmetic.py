"""Skeleton input prerequisites and fixed decimal-array capacity/alias contracts."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'programs/programs/back-skeleton.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class SkeletonInputArithmetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'skeleton.c'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)], check=True, capture_output=True)
        harness = cls.work/'arithmetic.c'
        harness.write_text('''#define main skeleton_main
#include "skeleton.c"
#undef main
void encode(bignum a,char *s) {
  int i,len=strlen(s); a[0]=len;
  for(i=1;i<=len;i++) a[i]=s[len-i]-'0';
}
int main(int argc,char **argv) {
  bignum a={0},b={0},c={0}; int i,p=atoi(argv[3]);
  encode(b,argv[1]); encode(c,argv[2]);
  if(argv[4][0]=='a') {add(b,b,c,p); copy(a,b);}
  else if(argv[4][0]=='b') add(a,b,b,p);
  else add(a,b,c,p);
  for(i=a[0];i;i--) printf("%d",a[i]);
  return 0;
}
'''.replace('#include "skeleton.c"', '#include <string.h>\n#include "skeleton.c"'))
        cls.arithmetic = cls.work/'arithmetic'
        cls.compile(harness, cls.arithmetic)
        source = cls.work/'input.w'
        source.write_text(SOURCE.read_text().replace('@<Build the table of constants@>;', 'return 0;'))
        generated = cls.work/'input.c'
        subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
        cls.input_program = cls.work/'input'
        cls.compile(generated, cls.input_program)

    @classmethod
    def compile(cls, source, output):
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(source), '-o', str(output)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_invalid_input_prerequisites_reject(self):
        cases = [('2', '-1', b'*\n'), ('2', '2147483647', b'*\n'),
                 ('4294967298', '0', b'*\n'), ('2x', '0', b'*\n'),
                 ('2', '0', b''), ('2', '0', b'....\n'), ('2', '0', b'\n'),
                 ('2', '0', b'*\0\n'), ('2', '0', b'.'*100+b'*\n')]
        for m, z, pattern in cases:
            with self.subTest(m=m, z=z, pattern=pattern[:20]):
                result = subprocess.run([str(self.input_program), m, z], input=pattern,
                                        capture_output=True, timeout=5, env=ENV)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_valid_pattern_record_forms(self):
        for pattern in [b'*\n', b'*', b'*\r\n', b'*.......\n']:
            result = subprocess.run([str(self.input_program), '2', '0'], input=pattern,
                                    capture_output=True, timeout=5, env=ENV)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn(b'1 rows and 1 asterisks', result.stderr)

    def test_decimal_addition_and_supported_aliases(self):
        for b in [1, 9, 10, 99, 1234567]:
            for c in [1, 9, 10, 99, 7654321]:
                for p in [0, 1, 4]:
                    for mode in ['none', 'a', 'b']:
                        result = subprocess.run([str(self.arithmetic), str(b), str(c), str(p), mode],
                                                capture_output=True, timeout=5, env=ENV)
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        self.assertEqual(int(result.stdout), b+10**p*(b if mode == 'b' else c))
        result = subprocess.run([str(self.arithmetic), '1', '1', '20', 'none'],
                                capture_output=True, timeout=5, env=ENV)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(int(result.stdout), 10**20+1)

    def test_decimal_overflow_rejects_before_writing(self):
        for b, c, p in [('9'*21, '1', '0'), ('1', '1', '21')]:
            result = subprocess.run([str(self.arithmetic), b, c, p, 'none'],
                                    capture_output=True, timeout=5, env=ENV)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'overflow', result.stderr)
            self.assertNotIn(b'runtime error', result.stderr)
            self.assertNotIn(b'AddressSanitizer', result.stderr)


if __name__ == '__main__':
    unittest.main()
