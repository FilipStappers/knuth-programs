"""B059: accepted 50-row/column patterns must use dead exterior safely."""
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable
from test_dimacs_empty_clause import native_clauses

ROOT = Path(__file__).resolve().parents[1]
COLLECTIONS = [ROOT/'programs/archives/sat-life', ROOT/'programs/archives/SATexamples/sources']


class PatternBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = []
        for index, collection in enumerate(COLLECTIONS):
            generated = work/f'life{index}.c'
            program = work/f'life{index}'
            subprocess.run(['ctangle', str(collection/'sat-life.w'), '-', str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs.append(program)
        cls.work = work

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_changed_base_still_accepts_all_distributed_changes(self):
        for collection in COLLECTIONS:
            for change in collection.glob('sat-life-*.ch'):
                with self.subTest(change=change):
                    result = subprocess.run(['ctangle', str(collection/'sat-life.w'), str(change),
                                             str(self.work/'composition.c')], capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stdout.decode())

    def test_boundary_triples_against_direct_evolution(self):
        for program in self.programs:
            for potential in [[(50, y) for y in range(1, 4)],
                              [(50, y) for y in range(48, 51)],
                              [(x, 50) for x in range(1, 4)],
                              [(x, 50) for x in range(48, 51)]]:
                pattern = ''.join(''.join('*' if (x, y) in potential else '.'
                                          for y in range(1, 51))+'\n' for x in range(1, 51))
                result = subprocess.run([str(program), '0'], input=pattern.encode(),
                                        capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                clauses = native_clauses(result.stdout.decode())
                future = {lit.lstrip('~') for clause in clauses for lit in clause
                          if re.fullmatch(r'~?\d+b\d+', lit)}
                self.assertTrue(future)
                for bits in itertools.product([False, True], repeat=3):
                    live = {cell for cell, bit in zip(potential, bits) if bit}
                    initial = [[('' if bit else '~')+f'{x}a{y}']
                               for (x, y), bit in zip(potential, bits)]
                    expected = {}
                    for name in future:
                        x, y = map(int, name.split('b'))
                        count = sum((x+i, y+j) in live for i, j in
                                    itertools.product([-1, 0, 1], repeat=2) if i or j)
                        expected[name] = count == 3 or (count == 2 and (x, y) in live)
                    with self.subTest(program=program.name, potential=potential, bits=bits):
                        self.assertTrue(satisfiable(clauses+initial+[
                            [('' if bit else '~')+name] for name, bit in expected.items()]))
                        for name, bit in expected.items():
                            self.assertFalse(satisfiable(clauses+initial+[
                                [('~' if bit else '')+name]]))


if __name__ == '__main__':
    unittest.main()
