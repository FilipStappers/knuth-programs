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

    def test_existing_detected_input_errors_remain_failures(self):
        for program in self.programs:
            result = subprocess.run([str(program)], input=b'bad header\n',
                                    capture_output=True, timeout=3)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
