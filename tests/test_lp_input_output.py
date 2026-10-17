"""B031: exact one-variable LP certificates and format/input boundaries."""
from fractions import Fraction
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/lp.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class LpInputOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.generated = cls.work/'lp.c'
        cls.program = cls.work/'lp'
        subprocess.run(['ctangle', str(SOURCE), '-', str(cls.generated)],
                       check=True, capture_output=True)
        cls.flags = ['-std=gnu99', '-Wno-implicit-int', '-Wno-implicit-function-declaration',
                     '-O1', '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all']
        subprocess.run(['gcc', *cls.flags, str(cls.generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, text):
        return subprocess.run([str(self.program)], input=text.encode(), capture_output=True,
                              timeout=5, env=ENV)

    def test_exact_long_integer_certificate_fields(self):
        cases = [(b, c, a) for b in [1, 3] for c in [1, 2, 4294967296] for a in [1, 2, 3]]
        cases += [(4294967296, 1, 1), (4294967296, 2, 3)]
        for b, c, a in cases:
            with self.subTest(b=b, c=c, a=a):
                result = self.solve(f'{b}\n{c} {a}\n')
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                text = result.stdout.decode()
                lines = text.splitlines()
                value = next(line for line in lines if line.startswith('Optimal value '))
                primal = next(line for line in lines if line.startswith(" Optimal v's:"))
                dual = next(line for line in lines if line.startswith(" Optimal u's:"))
                def exact(line):
                    match = re.search(r'=(-?\d+)/(\d+)', line)
                    self.assertIsNotNone(match, line)
                    return Fraction(int(match[1]), int(match[2]))
                self.assertEqual(exact(value), Fraction(b*c, a))
                self.assertEqual(exact(primal), Fraction(c, a))
                self.assertEqual(exact(dual), Fraction(b, a))

    def test_variadic_formats_match_declared_types(self):
        result = subprocess.run(['gcc', *self.flags, '-Wformat=2', '-Werror=format',
                                 '-fsyntax-only', str(self.generated)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_negative_constraint_constants_reject(self):
        for text in ['1\n-1 1\n', '0\n-1 1\n', '3\n-5 2\n']:
            with self.subTest(text=text):
                result = self.solve(text)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'constant', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'Optimal value', result.stdout)

    def test_full_advertised_tableau_dimensions(self):
        text = ' '.join(['1']*100)+'\n'
        text += ''.join(str(c)+' '+' '.join(['1']*100)+'\n' for c in range(1, 11))
        result = self.solve(text)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'=1/1 found', result.stdout)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_malformed_tokens_and_capacity_reject_without_invalid_writes(self):
        cases = ['', '\n', 'x\n', '-\n', '1.2\n', '1x\n', '9'*100+'\n',
                 '1\n2 x\n', '1\n2 1 0\n', '1\n'+'1 '*10000+'\n',
                 '1\n2 1\0 3\n', ' '*100000+'1\n', '1 '*101+'\n']
        for text in cases:
            with self.subTest(text=text[:60]):
                result = self.solve(text)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertNotIn(b'Optimal value', result.stdout)

    def test_final_record_and_signed_decimal_grammar(self):
        for text in ['+3\n+2 +3', '  +3 \t\r\n  +2 +3\r\n']:
            result = self.solve(text)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            match = re.search(rb'Optimal value [^=]+=(-?\d+)/(\d+)', result.stdout)
            self.assertIsNotNone(match)
            self.assertEqual(Fraction(int(match[1]), int(match[2])), 2)

    def test_input_stream_read_error_rejects(self):
        descriptor = os.open(self.work, os.O_RDONLY)
        try:
            result = subprocess.run([str(self.program)], stdin=descriptor, capture_output=True,
                                    timeout=5, env=ENV)
        finally:
            os.close(descriptor)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'input', result.stderr.lower())


if __name__ == '__main__':
    unittest.main()
