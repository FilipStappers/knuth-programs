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

    def test_base_unary_input_does_not_read_missing_clause_literals(self):
        for data in [b'x\n', b'~x\n', b'x\n~x\n', b'x\nx y\n']:
            with self.subTest(data=data):
                self.check_formula(data)

    def test_base_all_two_variable_clause_families(self):
        pool = [[('~' if sign < 0 else '')+f'x{i}'
                 for i, sign in enumerate(signs) if sign]
                for signs in itertools.product([0, 1, -1], repeat=2) if any(signs)]
        for mask in range(1, 1 << len(pool)):
            data = ''.join(' '.join(c)+'\n' for i, c in enumerate(pool)
                           if mask & (1 << i)).encode()
            with self.subTest(mask=mask):
                self.check_formula(data)

    def test_k_short_clause_temporary_tail_after_big_clauses(self):
        for data in [b'x\nx y z\n', b'x y\nx y z\n', b'~x\nx y z\n']:
            with self.subTest(data=data):
                self.check_formula(data, 'k')

    def test_k_two_variable_families_with_one_big_clause(self):
        pool = [[('~' if sign < 0 else '')+f'x{i}'
                 for i, sign in enumerate(signs) if sign]
                for signs in itertools.product([0, 1, -1], repeat=2) if any(signs)]
        for mask in range(1, 1 << len(pool)):
            data = (''.join(' '.join(c)+'\n' for i, c in enumerate(pool)
                            if mask & (1 << i))+'x0 x1 z\n').encode()
            with self.subTest(mask=mask):
                self.check_formula(data, 'k')


if __name__ == '__main__':
    unittest.main()
