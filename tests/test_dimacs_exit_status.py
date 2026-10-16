"""B053: conversion status must not depend on the legacy C dialect."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConverterStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'converter.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/dimacs-to-sat.w'),
                        '-', str(generated)], check=True, capture_output=True)
        cls.programs = []
        for dialect in ['gnu89', 'gnu99']:
            program = work/dialect
            subprocess.run(['gcc', '-std='+dialect, '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_success_has_zero_status_in_both_dialects(self):
        for program in self.programs:
            result = subprocess.run([str(program)], input=b'p cnf 1 1\n1 0\n',
                                    capture_output=True, timeout=3)
            with self.subTest(dialect=program.name):
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stdout, b' 1\n')

    def test_buffered_output_failure_has_failure_status(self):
        for program in self.programs:
            with open('/dev/full', 'wb') as sink:
                result = subprocess.run([str(program)], input=b'p cnf 1 1\n1 0\n',
                                        stdout=sink, stderr=subprocess.PIPE, timeout=3)
            with self.subTest(dialect=program.name):
                self.assertNotEqual(result.returncode, 0)

    def test_malformed_headers_are_rejected(self):
        headers = ['p cnf -1 1', 'p cnf 1 -1', 'p cnf 4294967297 1',
                   'p cnf 1 4294967297', 'p cnf '+'9'*100+' 1',
                   'p cnf 1 1 junk', 'p cnf1 1', 'p cnf 1', 'p cnf x 1',
                   'p cnf 1 1\0', 'p cnf 1 1'+' '*1024]
        for program in self.programs:
            for header in headers:
                result = subprocess.run([str(program)], input=(header+'\n0\n').encode(),
                                        capture_output=True, timeout=3)
                with self.subTest(dialect=program.name, header=header):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, b'')

    def test_decimal_header_counts_and_whitespace(self):
        for program in self.programs:
            result = subprocess.run([str(program)], input=b'p cnf 08 01 \t\n8 0\n',
                                    capture_output=True, timeout=3)
            with self.subTest(dialect=program.name):
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stdout, b' 8\n')

    def test_long_opening_comments_keep_their_physical_line(self):
        for program in self.programs:
            for size in [1021, 1022, 1023, 1024, 2048, 10000]:
                comment = b'c' + b'x'*size + b'p cnf 99 99'
                data = comment + b'\nc second\np cnf 1 1\n1 0\n'
                result = subprocess.run([str(program)], input=data,
                                        capture_output=True, timeout=3)
                with self.subTest(dialect=program.name, size=size):
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(result.stdout,
                                     b'~ '+comment[1:]+b'\n~  second\n 1\n')

    def test_comment_at_eof_cannot_replace_a_header(self):
        for program in self.programs:
            for data in [b'c', b'c'+b'x'*10000]:
                result = subprocess.run([str(program)], input=data,
                                        capture_output=True, timeout=3)
                with self.subTest(dialect=program.name, size=len(data)):
                    self.assertNotEqual(result.returncode, 0)

    def test_malformed_or_truncated_clause_streams_fail(self):
        cases = ['p cnf 1 2\n1 0\n', 'p cnf 1 1\n1\n',
                 'p cnf 1 1\n1 0 junk\n', 'p cnf 1 2\n1 0\nc comment\n-1 0\n',
                 'p cnf 1 1\n4294967297 0\n',
                 'p cnf 1 1\n-4294967295 0\n',
                 'p cnf 1 1\n'+'9'*10000+' 0\n',
                 'p cnf 1 1\n1x 0\n', 'p cnf 1 1\n- 0\n',
                 'p cnf 2147483647 1\n-2147483648 0\n',
                 'p cnf 2147483647 1\n2147483648 0\n',
                 'p cnf 1 1\n1 0 0\n']
        for program in self.programs:
            for data in cases:
                result = subprocess.run([str(program)], input=data.encode(),
                                        capture_output=True, timeout=3)
                with self.subTest(dialect=program.name, data=data[:60]):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)

    def test_decimal_literals_and_flexible_whitespace(self):
        for program in self.programs:
            for data, expected in [(b'p cnf 8 1\n08 0\n', b' 8\n'),
                                   (b'p cnf 2 2\n1\n-2 0 +2 0\n', b' 1 ~2\n 2\n')]:
                result = subprocess.run([str(program)], input=data, capture_output=True, timeout=3)
                with self.subTest(dialect=program.name, data=data):
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(result.stdout, expected)

    def test_existing_detected_input_errors_remain_failures(self):
        for program in self.programs:
            result = subprocess.run([str(program)], input=b'bad header\n',
                                    capture_output=True, timeout=3)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
