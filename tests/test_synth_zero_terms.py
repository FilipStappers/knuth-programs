"""B058: zero-term DNF and independent unions of Boolean cubes."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'


class SynthZeroTerms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        for mode in ['base', 'trunc-kluj']:
            generated = work/(mode+'.c')
            change = '-' if mode == 'base' else str(SOURCES/'sat-synth-trunc-kluj.ch')
            subprocess.run(['ctangle', str(SOURCES/'sat-synth.w'), change, str(generated)],
                           check=True, capture_output=True)
            program = work/mode
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, n, k, data, mode='base', extra=()):
        return subprocess.run([str(self.programs[mode]), str(n), str(k), *extra], input=data,
                              capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_all_partial_two_variable_specifications_and_zero_one_two_terms(self):
        points = list(itertools.product([0, 1], repeat=2))
        cubes = {0}
        for pattern in itertools.product([None, 0, 1], repeat=2):
            cubes.add(sum(1 << i for i, point in enumerate(points)
                          if all(a is None or a == b for a, b in zip(pattern, point))))
        functions = {0}
        for k in range(3):
            if k:
                functions |= {f | cube for f in functions for cube in cubes}
            for observed in itertools.product([None, 0, 1], repeat=4):
                expected = any(all(value is None or (f >> i & 1) == value
                                   for i, value in enumerate(observed)) for f in functions)
                data = ''.join(''.join(map(str, point))+':'+str(value)+'\n'
                               for point, value in zip(points, observed) if value is not None).encode()
                with self.subTest(k=k, observed=observed):
                    result = self.encode(2, k, data)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    formula = [line.split() for line in result.stdout.decode().splitlines()
                               if line.strip() and not line.startswith('~ ')]
                    self.assertEqual(satisfiable(formula), expected)

    def test_distributed_specialized_change_still_composes(self):
        result = self.encode(20, 4, b'', 'trunc-kluj', ['0'])
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        formula = [line.split() for line in result.stdout.decode().splitlines()
                   if line.strip() and not line.startswith('~ ')]
        self.assertEqual(len(formula), 24)
        self.assertTrue(all(len(row) == 160 for row in formula))


if __name__ == '__main__':
    unittest.main()
