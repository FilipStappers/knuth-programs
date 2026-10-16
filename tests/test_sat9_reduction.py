"""B054: bounded SAT9 error paths and residual-formula contracts."""
import os
import itertools
import random
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Sat9Reduction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for SAT9 checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        source = (ROOT/'programs/programs/sat9.w').read_text()
        cls.programs = {}
        # Relocate only the residual path into this test's owned directory.
        # The missing subdirectory exercises the original fopen failure branch.
        original = '/tmp/sat9-%d.dat'
        assert source.count(original) == 1
        for name, path in [('normal', 'residual-%d.dat'),
                           ('missing', 'missing/sat9-%d.dat')]:
            literate = cls.work/(name+'.w')
            literate.write_text(source.replace(original, path))
            generated = cls.work/(name+'.c')
            program = cls.work/(name+'-solver')
            subprocess.run(['ctangle', str(literate), '-', str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-I'+sgb, '-fsanitize=address,undefined,bounds,float-divide-by-zero',
                            '-fno-sanitize-recover=all', str(generated),
                            str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_solver(self, name, data, options):
        return subprocess.run([str(self.programs[name]), *options], input=data,
                              cwd=self.work, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_failed_residual_open_reports_its_filename(self):
        result = self.run_solver('missing', b'a b\n', ['v0', 's123'])
        self.assertGreater(result.returncode, 0)
        self.assertIn(b"I can't open `missing/sat9-123.dat' for writing!", result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)

    def test_contradictory_fields_are_reported_without_dividing_by_zero(self):
        data = b'a\n~a\n'
        quiet = self.run_solver('normal', data, ['v0', 't2', 'l0'])
        shown = self.run_solver('normal', data, ['v32', 't2', 'l0'])
        self.assertEqual(shown.returncode, 0, shown.stderr.decode())
        self.assertEqual(shown.stdout, quiet.stdout)
        self.assertIn(b'undefined (contradictory fields)', shown.stderr)
        self.assertNotIn(b'nan', shown.stderr.lower())
        self.assertNotIn(b'runtime error', shown.stderr)

    def check_residual(self, data, confidence, seed, allow_unknown=True):
        residual_path = self.work/f'residual-{seed}.dat'
        result = self.run_solver('normal', data,
                                 ['v0', 't100', 'l5', f'c{confidence}', f's{seed}'])
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        if result.stdout.split()[-1:] == [b'~~?']:
            self.assertTrue(allow_unknown)
            return False
        partial = result.stdout.decode().split()
        self.assertFalse(any('~'+lit in partial for lit in partial))
        assigned = {lit.lstrip('~'): not lit.startswith('~') for lit in partial}
        original = [line.split() for line in data.decode().splitlines()]
        residual = [line.split() for line in residual_path.read_text().splitlines()]
        names = {lit.lstrip('~') for clause in original for lit in clause}
        self.assertTrue(assigned.keys() <= names)
        self.assertTrue(all(lit.lstrip('~') in names-assigned.keys()
                            for clause in residual for lit in clause))
        free = sorted(names-assigned.keys())

        def value(clauses, assignment):
            return all(any(assignment[lit.lstrip('~')] != lit.startswith('~')
                           for lit in clause) for clause in clauses)

        for bits in itertools.product([False, True], repeat=len(free)):
            assignment = assigned | dict(zip(free, bits))
            self.assertEqual(value(original, assignment), value(residual, assignment))
        return True

    def test_ordinary_reduction_keeps_projected_semantics(self):
        self.check_residual(b'a b\n', 50, 123, allow_unknown=False)

    def test_zero_confidence_peer_crash(self):
        data = (b'abcdefgh ijklmnop ~qrstuvwx ~yzABCDEF\n'
                b'~abcdefgh ~ijklmnop ~qrstuvwx ~yzABCDEF\n'
                b'abcdefgh ~ijklmnop qrstuvwx ~yzABCDEF\n'
                b'abcdefgh ~ijklmnop ~qrstuvwx yzABCDEF\n')
        # Detecting a contradiction in a heuristic choice may return UNKNOWN.
        # A crash or a residual inconsistent with the printed choice may not.
        self.check_residual(data, 0, 980003)

    def test_confidence_boundaries_preserve_residual_truth_tables(self):
        rng = random.Random(54009)
        names = ['abcdefgh', 'ijklmnop', 'qrstuvwx', 'yzABCDEF']
        reduced = dict.fromkeys([0, 1, 50, 100], 0)
        for case in range(40):
            clauses = []
            for _ in range(rng.randint(1, 6)):
                clause = [(('~' if rng.getrandbits(1) else '')+name)
                          for name in rng.sample(names, rng.randint(1, 4))]
                clauses.append(' '.join(clause))
            data = ('\n'.join(clauses)+'\n').encode()
            for confidence in reduced:
                with self.subTest(case=case, confidence=confidence):
                    reduced[confidence] += self.check_residual(data, confidence,
                                                             990000+case*101+confidence)
        self.assertTrue(all(reduced.values()), reduced)


if __name__ == '__main__':
    unittest.main()
