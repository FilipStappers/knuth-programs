"""B055: SAT11 and its distributed SAT11K composition boundary checks."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Sat11Boundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sgb = os.environ.get('GRAPHBASE')
        if not cls.sgb:
            raise unittest.SkipTest('Set GRAPHBASE for SAT11 checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def compile_variant(self, variant='base'):
        if variant in self.programs:
            return self.programs[variant]
        source = ROOT/'programs/programs/sat11.w'
        change = str(ROOT/'programs/programs/sat11k.ch') if variant == 'k' else '-'
        generated = self.work/(variant+'.c')
        result = subprocess.run(['ctangle', str(source), change, str(generated)],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
        program = self.work/variant
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-I'+self.sgb, '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated),
                        str(Path(self.sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                       check=True, capture_output=True)
        self.programs[variant] = program
        return program

    def check_formula(self, data, variant='base', options=()):
        clauses = [line.split() for line in data.decode().splitlines()]
        names = sorted({lit.lstrip('~') for clause in clauses for lit in clause})
        expected = any(all(any(assignment[lit.lstrip('~')] != lit.startswith('~')
                               for lit in clause) for clause in clauses)
                       for bits in itertools.product([False, True], repeat=len(names))
                       for assignment in [dict(zip(names, bits))])
        result = subprocess.run([str(self.compile_variant(variant)), *options, 'v0', 'm18'],
                                input=data, capture_output=True, timeout=5,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        model = set(result.stdout.decode().split())
        if expected:
            self.assertTrue(model)
            self.assertTrue(all(any(lit in model for lit in clause) for clause in clauses))
            self.assertFalse(any(name in model and '~'+name in model for name in names))
        else:
            self.assertEqual(model, {'~'})

    def test_distributed_sat11k_change_matches_and_compiles(self):
        self.compile_variant('k')


if __name__ == '__main__':
    unittest.main()
