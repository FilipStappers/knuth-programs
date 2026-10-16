"""B053: conversion must preserve empty-clause semantics, including in pipelines."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def models(clauses, assignments):
    return all(any(a[str(abs(lit))] == (lit > 0) for lit in clause)
               for clause in clauses for a in [assignments])


def native_clauses(text):
    return [line.split() for line in text.splitlines()
            if line.strip() and not line.startswith('~ ') and line != '~']


def native_has_extension(clauses, assigned):
    names = {lit.lstrip('~') for c in clauses for lit in c}
    free = sorted(names - assigned.keys())
    for bits in itertools.product([False, True], repeat=len(free)):
        a = assigned | dict(zip(free, bits))
        if all(any(a[lit.lstrip('~')] != lit.startswith('~') for lit in c)
               for c in clauses):
            return True
    return False


class EmptyClauseConversion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.converter = cls.work / 'dimacs-to-sat'
        source = ROOT / 'programs/programs/dimacs-to-sat.w'
        generated = cls.work / 'dimacs-to-sat.c'
        subprocess.run(['ctangle', str(source), '-', str(generated)], check=True,
                       capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', str(generated), '-o',
                        str(cls.converter)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def convert(self, text):
        return subprocess.run([str(self.converter)], input=text.encode(),
                              capture_output=True, check=True).stdout.decode()

    def test_empty_clause_remains_contradictory(self):
        output = self.convert('p cnf 1 2\n0\n1 0\n')
        self.assertFalse(native_has_extension(native_clauses(output), {}), output)

    def test_all_one_and_two_clause_two_variable_projections(self):
        # Include the empty clause and all non-tautological two-variable clauses.
        pool = [tuple(sign * i for i, sign in enumerate(choice, 1) if sign)
                for choice in itertools.product([-1, 0, 1], repeat=2)]
        for length in [1, 2]:
            for clauses in itertools.product(pool, repeat=length):
                data = f'p cnf 2 {length}\n' + ''.join(
                    ' '.join(map(str, clause)) + ' 0\n' for clause in clauses)
                output = native_clauses(self.convert(data))
                for bits in itertools.product([False, True], repeat=2):
                    a = dict(zip(['1', '2'], bits))
                    with self.subTest(clauses=clauses, assignment=a):
                        self.assertEqual(native_has_extension(output, a),
                                         models(clauses, a))

    def test_large_indices_use_injective_native_names(self):
        for index in [99999999, 100000000, 100000001, 134217728,
                      268435455, 268435456, 1073741824, 2147483647]:
            data = f'p cnf {index} 2\n{index} -1 0\n-{index} 1 0\n'
            clauses = native_clauses(self.convert(data))
            names = {lit.lstrip('~') for clause in clauses for lit in clause}
            self.assertTrue(all(len(name) <= 8 for name in names), names)
            decoded = {name: int(name[1:], 36) if name.startswith('v') else int(name)
                       for name in names}
            self.assertEqual(set(decoded.values()), {1, index})
            self.assertEqual(len(names), 2)
            for low, high in itertools.product([False, True], repeat=2):
                assigned = {name: high if variable == index else low
                            for name, variable in decoded.items()}
                with self.subTest(index=index, low=low, high=high):
                    self.assertEqual(native_has_extension(clauses, assigned), low == high)

    def test_ordinary_translation_is_unchanged(self):
        self.assertEqual(self.convert('c example\np cnf 2 2\n1 -2 0\n2 0\n'),
                         '~  example\n 1 ~2\n 2\n')

    def test_real_sat0_pipeline(self):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            self.skipTest('Set GRAPHBASE to run the optional native SAT0 pipeline')
        generated = self.work / 'sat0.c'
        solver = self.work / 'sat0'
        subprocess.run(['ctangle', str(ROOT / 'programs/programs/sat0.w'), '-',
                        str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu89', '-O1', '-I'+sgb, str(generated),
                        str(Path(sgb)/'gb_flip.c'), '-o', str(solver)], check=True,
                       capture_output=True)
        output = self.convert('p cnf 1 2\n0\n1 0\n')
        result = subprocess.run([str(solver), 'v0'], input=output.encode(),
                                capture_output=True, timeout=5)
        self.assertEqual(result.stdout.strip(), b'~', result.stderr.decode())
        for index in [100000000, 2147483647]:
            output = self.convert(f'p cnf {index} 2\n{index} 0\n1 -{index} 0\n')
            clauses = native_clauses(output)
            result = subprocess.run([str(solver), 'v0'], input=output.encode(),
                                    capture_output=True, timeout=5)
            model = set(result.stdout.decode().split())
            self.assertTrue(all(any(lit in model for lit in clause) for clause in clauses),
                            result.stderr.decode())



if __name__ == '__main__':
    unittest.main()
