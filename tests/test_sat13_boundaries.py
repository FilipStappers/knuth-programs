"""B056: SAT13 storage and auxiliary-input regressions with Boolean oracles."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Sat13Boundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for SAT13 checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.source = (ROOT/'programs/programs/sat13.w').read_text()
        cls.programs = {}
        for name, source in [('normal', cls.source),
                             ('sanity', cls.source.replace('@d sanity_checking 0',
                                                           '@d sanity_checking 1'))]:
            literate = cls.work/(name+'.w')
            literate.write_text(source)
            generated = cls.work/(name+'.c')
            program = cls.work/name
            subprocess.run(['ctangle', str(literate), '-', str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-I'+sgb, '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated),
                            str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_solver(self, data, options=(), build='normal'):
        return subprocess.run([str(self.programs[build]), 'v0', 'm18', *options],
                              input=data, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def check_formula(self, data, options=(), build='normal'):
        clauses = [line.split() for line in data.decode().splitlines()]
        names = sorted({lit.lstrip('~') for c in clauses for lit in c})
        expected = any(all(any(assignment[lit.lstrip('~')] != lit.startswith('~')
                               for lit in clause) for clause in clauses)
                       for bits in itertools.product([False, True], repeat=len(names))
                       for assignment in [dict(zip(names, bits))])
        result = self.run_solver(data, options, build)
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
        return result

    def test_root_unary_level_sentinel(self):
        for data in [b'x\n', b'~x\n', b'x\ny\n', b'x\n~x\n']:
            with self.subTest(data=data):
                self.check_formula(data, build='sanity')

    def test_full_depth_and_full_run_level_sentinels(self):
        for size in range(1, 5):
            clauses = [' '.join(('~' if bit else '')+f'v{i}'
                                for i, bit in enumerate(bits))
                       for bits in itertools.product([False, True], repeat=size)]
            for last in [False, True]:
                data = ('\n'.join(clauses if last else clauses[:-1])+'\n').encode()
                for build in self.programs:
                    for options in [('w0',), ('w2', 'j1000', 'J1000')]:
                        with self.subTest(size=size, last=last, build=build, options=options):
                            self.check_formula(data, options, build)

    def test_every_nonempty_two_variable_clause_family(self):
        pool = [[('~' if sign < 0 else '')+f'x{i}'
                 for i, sign in enumerate(signs) if sign]
                for signs in itertools.product([0, 1, -1], repeat=2) if any(signs)]
        for mask in range(1, 1 << len(pool)):
            data = ''.join(' '.join(c)+'\n' for i, c in enumerate(pool)
                           if mask & (1 << i)).encode()
            with self.subTest(mask=mask):
                self.check_formula(data)


if __name__ == '__main__':
    unittest.main()
