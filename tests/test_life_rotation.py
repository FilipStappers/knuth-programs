"""B059: rotational canonicalization must terminate at an odd grid center."""
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable
from test_dimacs_empty_clause import native_clauses

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/sat-life'


def orbit(x, y, n):
    result = []
    for _ in range(4):
        result.append((x, y))
        x, y = n+1-y, x
    return result


class LifeRotation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'grid90.c'
        cls.program = work/'grid90'
        subprocess.run(['ctangle', str(SOURCES/'sat-life.w'),
                        str(SOURCES/'sat-life-grid90.ch'), str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-include', 'stdlib.h', '-include', 'string.h',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, n):
        result = subprocess.run([str(self.program), str(n), str(n), '1'],
                                capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return native_clauses(result.stdout.decode())

    def test_odd_center_terminates(self):
        self.encode(3)

    def test_initial_names_are_unique_rotation_representatives(self):
        for n in range(2, 8):
            clauses = self.encode(n)
            for lit in {s.lstrip('~') for c in clauses for s in c}:
                m = re.fullmatch(r'(\d+)a(\d+)', lit)
                if m:
                    x, y = map(int, m.groups())
                    self.assertEqual((x, y), min(orbit(x, y, n)))

    def test_complete_three_by_three_symmetric_successors(self):
        n = 3
        clauses = self.encode(n)
        cells = list(itertools.product(range(1, n+1), repeat=2))
        reps = sorted({min(orbit(x, y, n)) for x, y in cells})
        names = {s.lstrip('~') for c in clauses for s in c}
        future = {s: tuple(map(int, re.fullmatch(r'(\d+)b(\d+)', s).groups()))
                  for s in names if re.fullmatch(r'(\d+)b(\d+)', s)}
        self.assertIn('2a2', names)
        self.assertIn('2b2', future)
        for bits in itertools.product([False, True], repeat=len(reps)):
            values = dict(zip(reps, bits))
            live = {(x, y) for x, y in cells if values[min(orbit(x, y, n))]}
            initial = [[('' if value else '~')+f'{x}a{y}']
                       for (x, y), value in values.items()]
            expected = {}
            for name, (x, y) in future.items():
                count = sum((x+i, y+j) in live for i, j in
                            itertools.product([-1, 0, 1], repeat=2) if i or j)
                expected[name] = count == 3 or (count == 2 and (x, y) in live)
            self.assertTrue(satisfiable(clauses+initial+[
                [('' if value else '~')+name] for name, value in expected.items()]))
            for name, value in expected.items():
                self.assertFalse(satisfiable(clauses+initial+[
                    [('~' if value else '')+name]]), (live, name))


if __name__ == '__main__':
    unittest.main()
