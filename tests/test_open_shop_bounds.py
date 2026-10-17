"""Open-shop encoder argument domains and direct bounded scheduling feasibility."""
from itertools import product
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

SOURCES = Path(__file__).resolve().parents[1]/'programs/archives/SATexamples/sources'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


def feasible(weights, m, n, makespan):
    tasks = [(i, j, weights[i*n+j]) for i in range(m) for j in range(n) if weights[i*n+j]]
    def place(k, assigned):
        if k == len(tasks):
            return True
        i, j, duration = tasks[k]
        for start in range(makespan-duration+1):
            if all((i != ii and j != jj) or start+duration <= begin or begin+length <= start
                   for ii, jj, length, begin in assigned):
                if place(k+1, assigned+[(i, j, duration, start)]):
                    return True
        return False
    return place(0, [])


class OpenShopBounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for mode in ['base', 'sym', 'scaled']:
            generated, program = [cls.work/(mode+s) for s in ['.c', '']]
            change = '-' if mode == 'base' else str(SOURCES/('sat-oss-sym'+('-scaled' if mode == 'scaled' else '')+'.ch'))
            subprocess.run(['ctangle', str(SOURCES/'sat-oss.w'), change, str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, mode, m, n, t, weights, scale=1):
        arguments = [str(self.programs[mode]), str(m), str(n), str(t)]
        if mode == 'scaled':
            arguments.append(str(scale))
        return subprocess.run(arguments, input=(' '.join(map(str, weights))+'\n').encode(),
                              capture_output=True, timeout=5, env=ENV)

    def test_nonpositive_scale_rejects_before_division(self):
        for scale in [0, -1, -2147483648]:
            result = self.encode('scaled', 1, 1, 1, [1], scale)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'scale', result.stderr)
            self.assertNotIn(b'runtime error', result.stderr)
            self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_parameter_and_weight_domains(self):
        for mode in self.programs:
            for m, n, t in [(0, 1, 1), (-1, 1, 1), (1, 0, 1), (79, 1, 1),
                            (1, 79, 1), (1, 1, -1), (1, 1, 100001), (1, 1, 2147483647),
                            ('4294967297', 1, 1), ('1x', 1, 1)]:
                with self.subTest(mode=mode, m=m, n=n, t=t):
                    result = self.encode(mode, m, n, t, [0])
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertNotIn(b'AddressSanitizer', result.stderr)
            for weight in ['4294967297', '9'*100, '1x', '-1']:
                result = self.encode(mode, 1, 1, 1, [weight], 2)
                self.assertNotEqual(result.returncode, 0, (mode, weight))
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_load_and_makespan_boundaries(self):
        for mode in self.programs:
            result = self.encode(mode, 1, 1, 100000, [100000])
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            result = self.encode(mode, 1, 2, 100000, [100000, 100000])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Unsatisfiable', result.stderr)
            for m, n in [(78, 1), (1, 78)]:
                result = self.encode(mode, m, n, 0, [0]*(m*n))
                self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_scaling_matches_symmetric_encoder(self):
        for weights in [(0, 1, 2, 0), (1, 1, 1, 1), (2, 0, 0, 2)]:
            expected = self.encode('sym', 2, 2, 3, weights)
            self.assertEqual(expected.returncode, 0, expected.stderr.decode())
            for scale in [1, 2, 7]:
                result = self.encode('scaled', 2, 2, 3, [scale*w+scale-1 for w in weights], scale)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                clauses = lambda text: [row for row in text.splitlines() if row and not row.startswith(b'~ ')]
                self.assertEqual(clauses(result.stdout), clauses(expected.stdout))

    def test_small_scheduling_decisions(self):
        for weights in product(range(3), repeat=4):
            for t in range(1, 5):
                expected = feasible(weights, 2, 2, t)
                for mode in self.programs:
                    result = self.encode(mode, 2, 2, t, weights)
                    if result.returncode:
                        self.assertTrue(b'Unsatisfiable' in result.stderr or
                                        (max(weights)>t and b'should be between' in result.stderr),
                                        result.stderr.decode())
                        actual = False
                    else:
                        formula = [row.split() for row in result.stdout.decode().splitlines()
                                   if row.strip() and not row.startswith('~ ')]
                        actual = satisfiable(formula)
                    self.assertEqual(actual, expected, (weights, t, mode))


if __name__ == '__main__':
    unittest.main()
