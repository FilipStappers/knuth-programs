"""BUG-055: bootstrap input must cover its copied prefix as well as the sieve."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from test_prime_sieve_masks import prime

ROOT = Path(__file__).resolve().parents[1] / 'programs/programs'


class PrimeBootstrapPrefix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        source = cls.work / 'boot.w'
        text = (ROOT / 'prime-sieve.w').read_text()
        text = text.replace('@d del 100000000LL', '@d del 1024LL')
        text = text.replace('main(int argc, char*argv[])', 'int main(int argc, char*argv[])')
        source.write_text(text)
        generated = source.with_suffix('.c')
        cls.program = source.with_suffix('')
        subprocess.run(['ctangle', str(source), str(ROOT / 'prime-sieve-boot.ch'), str(generated)],
                       capture_output=True, check=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], capture_output=True, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_bootstrap(self, start, segments, last_input):
        source = self.work / 'input.bin'
        output = self.work / 'output.bin'
        source.write_bytes(b''.join(struct.pack('=I', p) for p in range(2, last_input + 1) if prime(p)))
        result = subprocess.run([str(self.program), str(start), str(segments), str(source), str(output)],
                                capture_output=True, timeout=10)
        return result, output.read_bytes()

    def test_base_sufficient_prefix_rejects_when_bootstrap_prefix_is_missing(self):
        result, output = self.run_bootstrap(128, 4, 67)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'prematurely', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertEqual(output, b'')

    def test_complete_binary_prime_lists(self):
        for start, segments in [(128, 4), (128, 16), (1024, 3), (10000, 2)]:
            with self.subTest(start=start, segments=segments):
                result, output = self.run_bootstrap(start, segments, 10009)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stderr, b'')
                actual = [p for p, in struct.iter_unpack('=I', output)]
                expected = [p for p in range(2, start + 1024 * segments) if prime(p)]
                self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
