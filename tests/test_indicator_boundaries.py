"""B052: relation-coordinate storage and independent indicator matrices."""
from collections import Counter
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IndicatorBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'indicator.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/indicator-dlx.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = work/'indicator'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, d, k, tuples):
        return subprocess.run([str(self.program), str(d), str(k), *tuples], capture_output=True,
                              timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_excess_relation_arity_rejects_before_tuple_writes(self):
        for tuples in [['0'*11], ['0'*100], ['0'*11, '/', '0'], ['0', '/', '0'*11]]:
            with self.subTest(tuples=tuples):
                result = self.solve(2, 1, tuples)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'Relation arity', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_domain_must_fit_injective_hexadecimal_argument_names(self):
        for d in [-1, 0, 17, 33, 2147483647]:
            with self.subTest(d=d):
                result = self.solve(d, 1, ['0'])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'd must', result.stderr)
                self.assertEqual(result.stdout, b'')
        for d, k in [(1, 1), (1, 7), (16, 1), (16, 2)]:
            result = self.solve(d, k, ['0'])
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            header = result.stdout.decode().splitlines()[1].split()
            args = header[header.index('|')+1:]
            self.assertEqual(len(args), d**k)
            self.assertEqual(len(set(args)), d**k)
            self.assertTrue(all(len(arg) == k for arg in args))

    def test_covers_enumerate_total_operations_including_unseen_arguments(self):
        for arity in [1, 2]:
            universe = [''.join(t) for t in itertools.product('01', repeat=arity)]
            for mask in range(1, 1 << len(universe)):
                relation = [t for i, t in enumerate(universe) if mask >> i & 1]
                for k in [1, 2]:
                    args = [''.join(t) for t in itertools.product('01', repeat=k)]
                    expected = Counter()
                    for values in itertools.product([0, 1], repeat=len(args)):
                        operation = dict(zip(args, values))
                        if all(''.join(str(operation[''.join(t[j] for t in inputs)]) for j in range(arity))
                               in relation for inputs in itertools.product(relation, repeat=k)):
                            expected[values] += 1
                    with self.subTest(relation=relation, k=k):
                        result = self.solve(2, k, relation)
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        lines = [line.split() for line in result.stdout.decode().splitlines()
                                 if not line.startswith('|')]
                        primary = sorted(lines[0][:lines[0].index('|')])
                        choices = {item: [row for row in lines[1:] if item in row] for item in primary}
                        actual = Counter()
                        def visit(index, colors):
                            if index == len(primary):
                                actual[tuple(int(colors.get(arg, '-1')) for arg in args)] += 1
                                return
                            for row in choices[primary[index]]:
                                additions = dict(token.split(':') for token in row if ':' in token)
                                if all(name not in colors or colors[name] == value for name, value in additions.items()):
                                    visit(index+1, colors | additions)
                        visit(0, {})
                        self.assertEqual(actual, expected)

    def test_all_supported_relation_arities_match_independent_matrices(self):
        for arity in range(1, 11):
            tuples = [''.join(str((i+j) % 2) for j in range(arity)) for i in range(2)]
            for k in [1, 2]:
                with self.subTest(arity=arity, k=k):
                    expected = Counter()
                    primary = set()
                    for indices in itertools.product(range(2), repeat=k):
                        item = 'a'+''.join(map(str, indices))
                        primary.add(item)
                        for output in tuples:
                            mapping = {}
                            for j in range(arity):
                                args = ''.join(tuples[index][j] for index in indices)
                                mapping.setdefault(args, set()).add(output[j])
                            if all(len(values) == 1 for values in mapping.values()):
                                expected[tuple(sorted([item]+[args+':'+next(iter(values))
                                                               for args, values in mapping.items()]))] += 1
                    for vector in itertools.product('01', repeat=k):
                        arg = ''.join(vector)
                        primary.add('F'+arg)
                        for value in '01':
                            expected[tuple(sorted(['F'+arg, arg+':'+value]))] += 1
                    result = self.solve(2, k, tuples)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    lines = [line.split() for line in result.stdout.decode().splitlines()
                             if not line.startswith('|')]
                    separator = lines[0].index('|')
                    self.assertEqual(set(lines[0][:separator]), primary)
                    self.assertEqual(set(lines[0][separator+1:]),
                                     {''.join(args) for args in itertools.product('01', repeat=k)})
                    self.assertEqual(Counter(tuple(sorted(row)) for row in lines[1:]), expected)


if __name__ == '__main__':
    unittest.main()
