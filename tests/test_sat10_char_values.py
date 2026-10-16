"""B053: SAT10 unknown values must survive unsigned plain-char builds."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SAT10Values(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE to compile SAT10 in both char modes')
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'sat10.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/sat10.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.programs = []
        for mode in ['signed', 'unsigned']:
            program = work/mode
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-f'+mode+'-char', '-I'+sgb,
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), str(Path(sgb)/'gb_flip.c'), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_formula(self, clauses):
        variables = sorted({lit.lstrip('~') for clause in clauses for lit in clause})
        expected = any(all(any(bits[variables.index(lit.lstrip('~'))] != lit.startswith('~')
                                   for lit in clause) for clause in clauses)
                       for bits in itertools.product([False, True], repeat=len(variables)))
        data = ''.join(' '.join(clause)+'\n' for clause in clauses)
        for program in self.programs:
            result = subprocess.run([str(program), 'v0'], input=data.encode(),
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertNotIn(b'runtime error', result.stderr)
            model = set(result.stdout.decode().split())
            with self.subTest(mode=program.name, clauses=clauses):
                if not expected:
                    self.assertEqual(model, {'~'})
                else:
                    self.assertNotIn('~', model)
                    self.assertTrue(model)
                    self.assertTrue(all(any(lit in model for lit in clause) for clause in clauses))
                    self.assertFalse(any('~'+name in model and name in model for name in variables))

    def test_newly_watched_unknown_variable_is_activated(self):
        self.assert_formula([['x1'], ['x2', '~x1']])

    def test_every_nonempty_two_variable_clause_family(self):
        clauses = []
        for signs in itertools.product([0, 1, -1], repeat=2):
            if any(signs):
                clauses.append([('~' if sign < 0 else '')+f'x{i+1}'
                                for i, sign in enumerate(signs) if sign])
        for mask in range(1, 1 << len(clauses)):
            self.assert_formula([clause for i, clause in enumerate(clauses) if mask & (1 << i)])


if __name__ == '__main__':
    unittest.main()
