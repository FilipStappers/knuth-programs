"""Parade unranking at the last Stirling row and beyond 32-bit ranks."""
from itertools import permutations
from math import factorial
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STIRLING = [[0]*26 for _ in range(26)]
STIRLING[0][0] = 1
for n in range(1, 26):
    for k in range(1, n+1):
        STIRLING[n][k] = k*STIRLING[n-1][k]+STIRLING[n-1][k-1]


def parade_rank(parade, m, n):
    groups = {'g': [0]*(m+1), 'b': [0]*(n+1)}
    order, previous = 0, 'g'
    for person in parade:
        sex, label = person[0], int(person[1:])
        if sex == 'b' and previous == 'g':
            order += 1
        groups[sex][label] = order
        previous = sex
    if previous == 'b':
        groups['b'] = [0 if x == order else x for x in groups['b']]
        order -= 1
    ranks = {}
    for sex in ('g', 'b'):
        names, perm, rgs = {0: 0}, [], []
        for block in groups[sex][1:]:
            if block not in names:
                names[block] = len(names)
                perm.append(block)
            rgs.append(names[block])
        permutation_rank = sum(sum(y < x for y in perm[j+1:])*factorial(order-j-1)
                               for j, x in enumerate(perm))
        partition_rank, maximum = 0, 0
        for j, x in enumerate(rgs, 1):
            if x > maximum:
                maximum += 1
                partition_rank += (maximum+1)*STIRLING[j][maximum+1]
            else:
                partition_rank += x*STIRLING[j][maximum+1]
        ranks[sex] = permutation_rank, partition_rank
    earlier = sum(factorial(k)**2*STIRLING[m+1][k+1]*STIRLING[n+1][k+1]
                  for k in range(order))
    gp, gs = ranks['g']
    bp, bs = ranks['b']
    return earlier+((gp*STIRLING[m+1][order+1]+gs)*factorial(order)+bp)*STIRLING[n+1][order+1]+bs


class ParadeUnranking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'parade.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/unrank-parade1.w'),
                        '-', str(generated)], check=True, capture_output=True)
        cls.program = cls.work/'parade'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_rank(self, m, n, rank):
        result = subprocess.run([str(self.program), str(m), str(n), str(rank)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        parade = tuple(result.stdout.split())
        expected = {f'g{i}' for i in range(1, m+1)} | {f'b{i}' for i in range(1, n+1)}
        self.assertEqual(len(parade), m+n)
        self.assertEqual(set(parade), expected)
        self.assertTrue(all(a[0] != b[0] or int(a[1:]) < int(b[1:])
                            for a, b in zip(parade, parade[1:])))
        self.assertEqual(parade_rank(parade, m, n), rank)
        return parade

    def test_last_stirling_row(self):
        for m, n in [(24, 0), (0, 24), (24, 1), (1, 24)]:
            total = sum(factorial(k)**2*STIRLING[m+1][k+1]*STIRLING[n+1][k+1]
                        for k in range(min(m, n)+1))
            for rank in sorted({0, total//2, total-1}):
                with self.subTest(m=m, n=n, rank=rank):
                    self.run_rank(m, n, rank)

    def test_complete_small_families(self):
        for m in range(4):
            for n in range(4):
                labels = tuple(f'g{i}' for i in range(1, m+1))+tuple(f'b{i}' for i in range(1, n+1))
                expected = {p for p in permutations(labels)
                            if all(a[0] != b[0] or int(a[1:]) < int(b[1:])
                                   for a, b in zip(p, p[1:]))}
                with self.subTest(m=m, n=n):
                    actual = {self.run_rank(m, n, r) for r in range(len(expected))}
                    self.assertEqual(actual, expected)

    def test_wide_partition_rank(self):
        for m, n in [(15, 5), (5, 15)]:
            first = sum(factorial(k)**2*STIRLING[m+1][k+1]*STIRLING[n+1][k+1]
                        for k in range(5))
            total = first+factorial(5)**2*STIRLING[m+1][6]*STIRLING[n+1][6]
            ranks = [first, total-1]
            for component in [(1 << 31)-1, 1 << 31, (1 << 31)+1]:
                ranks.append(first+component*(factorial(5) if m == 15 else 1))
            for rank in ranks:
                with self.subTest(m=m, n=n, rank=rank):
                    self.run_rank(m, n, rank)

if __name__ == '__main__':
    unittest.main()
