"""B059: upper-search coordinate arithmetic and fixed board capacity."""
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable
from test_dimacs_empty_clause import native_clauses

ROOT = Path(__file__).resolve().parents[1]


class UpperBounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = []
        for index, location in enumerate(['sat-life', 'SATexamples/sources']):
            directory = ROOT/'programs/archives'/location
            generated = work/f'upper{index}.c'
            program = work/f'upper{index}'
            subprocess.run(['ctangle', str(directory/'sat-life.w'),
                            str(directory/'sat-life-upper.ch'), str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-include', 'stdlib.h', '-include', 'string.h',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, program, x, y):
        return subprocess.run([str(program), str(x), str(y)],
                              capture_output=True, timeout=5)

    def test_oversized_and_overflowing_coordinates_reject_before_output(self):
        for index, program in enumerate(self.programs):
            first_oversize = (-1, 13) if index == 0 else (0, 25)
            for x, y in [first_oversize, (2147483647, 1), (0, 2147483647),
                         (-2147483647, 2147483647), (-2147483648, 2147483647)]:
                result = self.encode(program, x, y)
                with self.subTest(copy=index, x=x, y=y):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertEqual(result.stdout, b'')

    def test_small_search_projects_to_direct_life_evolution(self):
        # x0=0,y0=1 gives two rounds on a 5x5 dependency board. Initial
        # cells may be live only in the lower-left quadrant (six positions).
        cells = list(itertools.product([4, 5], [1, 2, 3]))
        for program in self.programs:
            result = self.encode(program, 0, 1)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            clauses = native_clauses(result.stdout.decode())
            for bits in itertools.product([False, True], repeat=6):
                live = {cell for cell, bit in zip(cells, bits) if bit}
                for _ in range(2):
                    neighbors = {}
                    for x, y in live:
                        for i, j in itertools.product([-1, 0, 1], repeat=2):
                            if i or j:
                                p = (x+i, y+j)
                                neighbors[p] = neighbors.get(p, 0)+1
                    live = {p for p, count in neighbors.items()
                            if count == 3 or (count == 2 and p in live)}
                units = [[('' if bit else '~')+f'{x}a{y}']
                         for (x, y), bit in zip(cells, bits)]
                with self.subTest(copy=program.name, bits=bits):
                    self.assertEqual(satisfiable(clauses+units), (3, 3) in live)


if __name__ == '__main__':
    unittest.main()
