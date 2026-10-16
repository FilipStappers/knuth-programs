"""B054: bounded SAT9 error paths and residual-formula contracts."""
import os
import itertools
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
                            '-I'+sgb, '-fsanitize=address,undefined,bounds',
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

    def check_residual(self, data, confidence, seed, allow_unknown=True):
        residual_path = self.work/f'residual-{seed}.dat'
        result = self.run_solver('normal', data,
                                 ['v0', 't100', 'l5', f'c{confidence}', f's{seed}'])
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        if result.stdout.strip() == b'~~?':
            self.assertTrue(allow_unknown)
            return
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

    def test_ordinary_reduction_keeps_projected_semantics(self):
        self.check_residual(b'a b\n', 50, 123, allow_unknown=False)


if __name__ == '__main__':
    unittest.main()
