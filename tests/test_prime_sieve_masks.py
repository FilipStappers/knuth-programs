"""BUG-156: dense/sparse sieve bits versus exact trial division.

Reduced segments expose every bit. Gap reporting and RNG initialization are
omitted; no probabilistic primality helper or random generator is executed.
"""
import math
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'programs/programs'


def prime(n):
    return n >= 2 and all(n % d for d in range(2, math.isqrt(n) + 1))


class PrimeSieveMasks(unittest.TestCase):
    def test_all_represented_bits_across_segments_and_queue_wraps(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            primes = work / 'primes.bin'
            primes.write_bytes(b''.join(struct.pack('=I', p) for p in range(2, 1100) if prime(p)))
            for name, stride in [('prime-sieve', 2), ('prime-sieve-sparse', 4)]:
                text = (ROOT / (name + '.w')).read_text()
                for macro, value in [('del', '1024LL'), ('kmax', '10000'),
                                     ('ksmall', '100'), ('qsize', '4'), ('lsize', '4096')]:
                    text = re.sub(r'(?m)^@d ' + macro + r' .*$', '@d ' + macro + ' ' + value, text)
                text = text.replace('main(int argc, char*argv[])', 'int main(int argc, char*argv[])')
                text = text.replace('@<Initialize the random number generator@>;', ';')
                text = text.replace('@<Report the final prime@>;', ';')
                observer = '''{
  int word;
  printf("@@@@ %llu",s);
  for (word=0;word<del/''' + str(64 * stride) + ''';word++)
    printf(" %016llx",sieve[word]);
  printf("\\n");
}'''
                self.assertEqual(text.count('@<Look for large gaps@>;'), 1)
                text = text.replace('@<Look for large gaps@>;', observer)
                source = work / (name + '.w')
                generated = source.with_suffix('.c')
                program = source.with_suffix('')
                source.write_text(text)
                subprocess.run(['ctangle', str(source), '-', str(generated)],
                               capture_output=True, check=True)
                subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                                str(generated), '-o', str(program)], capture_output=True, check=True)
                for start in [128, 1024, 10000, 100000, 1000000]:
                    with self.subTest(name=name, start=start):
                        result = subprocess.run([str(program), str(start), '20', str(primes),
                                                 str(work / 'output.txt')],
                                                capture_output=True, timeout=10)
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        self.assertNotIn(b'runtime error', result.stderr)
                        rows = [line.split()[1:] for line in result.stdout.splitlines()
                                if line.startswith(b'@@ ')]
                        self.assertEqual(len(rows), 20)
                        for segment, row in enumerate(rows):
                            base = start + 1024 * segment
                            self.assertEqual(int(row[0]), base)
                            words = [int(word, 16) for word in row[1:]]
                            for bit in range(1024 // stride):
                                marked = bool(words[bit // 64] & (1 << (bit % 64)))
                                self.assertEqual(marked, not prime(base + stride * bit + 1),
                                                 (name, base, bit))


if __name__ == '__main__':
    unittest.main()
