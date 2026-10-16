"""B054-F1: ERP reconstruction must preserve eight-byte symbolic names."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ErpNames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for ERP reconstruction checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.sgb = sgb
        cls.programs = {}
        for name in ['sat12', 'sat12-erp']:
            generated = cls.work/(name+'.c')
            program = cls.work/name
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/ (name+'.w')),
                            '-', str(generated)], check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-I'+sgb, '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated),
                            str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def reconstruct(self, erp, solution, expected):
        path = self.work/'groups.erp'
        path.write_text(erp)
        result = subprocess.run([str(self.programs['sat12-erp']), 'e'+str(path)],
                                input=solution.encode(), capture_output=True, timeout=5,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(sorted(result.stdout.decode().split()), sorted(expected))
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)

    def test_echoed_solution_preserves_all_supported_name_lengths(self):
        for size in range(1, 9):
            a, b = 'abcdefgh'[:size], 'ijklmnop'[:size]
            with self.subTest(size=size):
                self.reconstruct('', a+' ~'+b+'\n', [a, '~'+b])

    def test_zero_rhs_groups_preserve_names(self):
        self.reconstruct('abcdefgh <-0\nijklmnop <-0\n', '\n',
                         ['abcdefgh', 'ijklmnop'])

    def test_arbitrary_rhs_value_preserves_names(self):
        self.reconstruct('abcdefgh <-1\nijklmnop\n', '\n',
                         ['abcdefgh', 'ijklmnop'])

    def test_false_reconstructed_value_preserves_names(self):
        self.reconstruct('abcdefgh <-1\nijklmnop\n', '~ijklmnop\n',
                         ['~abcdefgh', '~ijklmnop'])

    def test_real_preprocessor_pipeline_covers_both_original_units(self):
        path = self.work/'producer.erp'
        result = subprocess.run([str(self.programs['sat12']), 'v0', 'e'+str(path)],
                                input=b'abcdefgh\nijklmnop\n', capture_output=True,
                                timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout.strip(), b'')
        self.reconstruct(path.read_text(), '\n', ['abcdefgh', 'ijklmnop'])

    def test_literal_array_allocation_failure_exits_before_use(self):
        source = (ROOT/'programs/programs/sat12-erp.w').read_text()
        allocation = 'lmem=(char*)malloc((vars+vars+2)*sizeof(char));'
        self.assertEqual(source.count(allocation), 1)
        injected = self.work/'erp-no-lmem.w'
        injected.write_text(source.replace(allocation, 'lmem=(char*)0;'))
        generated = self.work/'erp-no-lmem.c'
        program = self.work/'erp-no-lmem'
        subprocess.run(['ctangle', str(injected), '-', str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-I'+self.sgb, '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated),
                        str(Path(self.sgb)/'gb_flip.c'), '-o', str(program)],
                       check=True, capture_output=True)
        path = self.work/'allocation.erp'
        path.write_text('x <-0\n')
        result = subprocess.run([str(program), 'e'+str(path)], input=b'\n',
                                capture_output=True, timeout=5,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertGreater(result.returncode, 0)  # a deliberate exit, not a signal
        self.assertIn(b"can't allocate the lmem array", result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertEqual(result.stdout, b'')


if __name__ == '__main__':
    unittest.main()
