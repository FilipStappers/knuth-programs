"""B053: reject empty C strings before inspecting a line's last byte."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeLineNull(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for native-reader AddressSanitizer checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for source in sorted((ROOT/'programs/programs').glob('*.w')):
            if 'hash_bits[93][8]' not in source.read_text():
                continue
            generated = cls.work/(source.stem+'.c')
            program = cls.work/source.stem
            subprocess.run(['ctangle', str(source), '-', str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-I'+sgb, '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated),
                            str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[source.stem] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_clean_error(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertIn(b'clause', result.stderr)

    def test_nul_at_start_of_a_formula_or_erp_clause(self):
        for name, program in self.programs.items():
            args, data = ['v0'], b'\0\n'
            if name in ['sat12', 'sat12-erp']:
                erp = self.work/(name+'.erp')
                args.append('e'+str(erp))
                if name.endswith('-erp'):
                    args.remove('v0')
                    erp.write_bytes(b'seed <-1\n\0\n')
                    data = b''
            result = subprocess.run([str(program), *args], input=data,
                                    capture_output=True, timeout=5,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
            with self.subTest(reader=name):
                self.assert_clean_error(result)

    def test_nul_at_start_of_primary_variable_file(self):
        primary = self.work/'primary'
        primary.write_bytes(b'\0\n')
        for name in ['sat10', 'sat11']:
            result = subprocess.run([str(self.programs[name]), 'v0', 'V'+str(primary)],
                                    input=b'x y\n', capture_output=True, timeout=5,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
            with self.subTest(reader=name):
                self.assert_clean_error(result)


if __name__ == '__main__':
    unittest.main()
