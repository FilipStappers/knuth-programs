"""Both word-matrix dictionary interfaces reject invalid records before storage."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class WordMatrixRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = []
        for variant in ['new', 'mxn']:
            source = ROOT/('programs/programs/back-mxn-words-'+variant+'.w')
            generated, program = [cls.work/(variant+s) for s in ['.c', '']]
            subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, program, mdata, ndata, mlimit='', nlimit=''):
        mfile, nfile = self.work/'rows', self.work/'columns'
        mfile.write_bytes(mdata)
        nfile.write_bytes(ndata)
        return subprocess.run([str(program), str(mfile)+mlimit, str(nfile)+nlimit],
                              capture_output=True, timeout=5, env=ENV)

    def test_invalid_dictionary_records_reject(self):
        invalid = [b'', b'\n', b'a'*8+b'\n', b'a'*100+b'\n', b'aa\0\n', b'Aa\n', b'aa!\n']
        for program in self.programs:
            for record in invalid:
                with self.subTest(program=program.name, record=record[:20]):
                    result = self.solve(program, record, b'aa\n')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertNotIn(b'AddressSanitizer', result.stderr)
            for record in [b'', b'\n', b'a'*11+b'\n', b'aa\0\n', b'Aa\n']:
                result = self.solve(program, b'aa\n', record)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_invalid_record_limits_reject(self):
        for program in self.programs:
            for limit in [':0', ':-1', ':x', ':1x', ':2147483647', ':4294967297', ':'+'9'*100]:
                for mlimit, nlimit in [(limit, ''), ('', limit)]:
                    with self.subTest(program=program.name, mlimit=mlimit, nlimit=nlimit):
                        result = self.solve(program, b'aa\n', b'aa\n', mlimit, nlimit)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn(b'runtime error', result.stderr)
                        self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_valid_record_forms_and_limits(self):
        for program in self.programs:
            for ending in [b'\n', b'\r\n', b'']:
                result = self.solve(program, b'aa'+ending, b'aa'+ending)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertIn(b'Altogether 1 solutions', result.stderr)
            result = self.solve(program, b'aa\nab\n', b'aa\nab\n', ':1', ':1')
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn(b'Altogether 1 solutions', result.stderr)

    def test_exact_word_lengths_and_complete_small_dictionary(self):
        for program in self.programs:
            for m, n in [(1, 1), (7, 10)]:
                result = self.solve(program, b'a'*m+b'\n', b'a'*n+b'\n')
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertIn(b'Altogether 1 solutions', result.stderr)
            words = b'aa\nab\nba\nbb\n'
            result = self.solve(program, words, words)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn(b'Altogether 16 solutions', result.stderr)
            self.assertEqual(len(re.findall(rb'(?m)^\d+:', result.stdout)), 16)

    def test_dictionary_read_errors_reject(self):
        valid = self.work/'valid'
        valid.write_bytes(b'aa\n')
        for program in self.programs:
            for paths in [(self.work, valid), (valid, self.work)]:
                result = subprocess.run([str(program), *map(str, paths)], capture_output=True,
                                        timeout=5, env=ENV)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b"couldn't read", result.stderr)


if __name__ == '__main__':
    unittest.main()
