"""B058: Zarankiewicz cardinality endpoints and direct finite matrix predicates."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'


class ZarankCardinality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        for mode in ['base', 'symm']:
            generated = work/(mode+'.c')
            change = '-' if mode == 'base' else str(SOURCES/'sat-zarank-symm.ch')
            subprocess.run(['ctangle', str(SOURCES/'sat-zarank.w'), change, str(generated)],
                           check=True, capture_output=True)
            program = work/mode
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, mode, parameters):
        return subprocess.run([str(self.programs[mode]), *map(str, parameters)], capture_output=True,
                              timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_parameter_ranges_reject_before_product_and_array_arithmetic(self):
        cases = [[0, 0, 0, 0, 0], [-1, -1, 0, 0, 0], [46341, 46341, 0, 0, 0],
                      [2, 2, -1, 0, 0], [2, 2, 5, 0, 0], [2, 2, 1, -1, 0],
                      [2, 2, 1, 0, -1], [2, 2, 1, 3, 0], [2, 2, 1, 0, 3]]
        for mode in self.programs:
            for parameters in cases:
                with self.subTest(mode=mode, parameters=parameters):
                    result = self.encode(mode, parameters)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertNotIn(b'AddressSanitizer', result.stderr)
                    self.assertEqual(result.stdout, b'')

    def test_parameter_capacity_uses_all_supported_tree_storage_safely(self):
        for m, n in [(1, 1000), (1000, 1)]:
            result = self.encode('base', [m, n, 1, 0, 0])
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            formula = [line.split() for line in result.stdout.decode().splitlines()
                       if line.strip() and not line.startswith('~ ')]
            names = {f'{i}.{j}' for i in range(m) for j in range(n)}
            fixed = [['~'+name] for name in sorted(names)]
            self.assertFalse(satisfiable(formula+fixed))
            fixed[0] = [fixed[0][0][1:]]
            self.assertTrue(satisfiable(formula+fixed))

    def test_cardinality_and_single_cell_match_every_small_matrix(self):
        for m, n in [(1, 1), (1, 2), (2, 1), (2, 2), (2, 3), (3, 2)]:
            for mode in self.programs:
                if mode == 'symm' and m != n:
                    continue
                for r in range(m*n+1):
                    for p, q in itertools.product(sorted({0, n}), sorted({0, m})):
                        with self.subTest(m=m, n=n, mode=mode, r=r, p=p, q=q):
                            result = self.encode(mode, [m, n, r, p, q])
                            self.assertEqual(result.returncode, 0, result.stderr.decode())
                            formula = [line.split() for line in result.stdout.decode().splitlines()
                                       if line.strip() and not line.startswith('~ ')]
                            for values in itertools.product([0, 1], repeat=m*n):
                                grid = [values[i*n:(i+1)*n] for i in range(m)]
                                expected = sum(values) >= r
                                expected &= not any(grid[i][j] and grid[ii][j] and grid[i][jj] and grid[ii][jj]
                                                    for i, ii in itertools.combinations(range(m), 2)
                                                    for j, jj in itertools.combinations(range(n), 2))
                                expected &= all(grid[i-1][:p] >= grid[i][:p] for i in range(1, m))
                                expected &= all(tuple(grid[i][j-1] for i in range(q)) >=
                                                tuple(grid[i][j] for i in range(q)) for j in range(1, n))
                                if mode == 'symm':
                                    expected &= all(grid[i][j] == grid[j][i] for i in range(m) for j in range(n))
                                fixed = [[('' if grid[i][j] else '~')+f'{i}.{j}'] for i in range(m) for j in range(n)]
                                self.assertEqual(satisfiable(formula+fixed), expected, (values, r, p, q))


if __name__ == '__main__':
    unittest.main()
