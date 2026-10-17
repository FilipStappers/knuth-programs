"""Antislide3 reporting interval validation on a bounded 3-by-3-by-3 search."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'programs/programs/antislide3.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class AntislideSpacing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        source, generated, cls.program = [work/('anti'+s) for s in ['.w', '.c', '']]
        text = SOURCE.read_text()
        for dimension in ['ll', 'mm', 'nn']:
            text = text.replace('@d '+dimension+' 4 ', '@d '+dimension+' 3 ')
        source.write_text(text)
        subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-Wno-implicit-function-declaration',
                        '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_search(self, *args):
        return subprocess.run([str(self.program), *args], capture_output=True, timeout=10, env=ENV)

    def test_invalid_reporting_intervals_reject(self):
        for argument in ['0', '-1', 'x', '1x', '', '2147483648', '4294967297', '9'*100]:
            with self.subTest(argument=argument):
                result = self.run_search(argument)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'spacing', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertNotIn(b'Altogether', result.stdout)

    def test_spacing_preserves_count_and_selects_solution_rows(self):
        for spacing in [None, 1, 2, 3, 2147483647]:
            result = self.run_search(*([] if spacing is None else [str(spacing)]))
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn(b'Altogether 2 solutions.', result.stdout)
            labels = list(map(int, re.findall(rb'(?m)^(\d+):', result.stdout)))
            self.assertEqual(labels, [] if spacing is None else
                             [k for k in [1, 2] if k % spacing == 0])


if __name__ == '__main__':
    unittest.main()
