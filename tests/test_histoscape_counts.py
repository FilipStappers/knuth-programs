"""Exact histoscape counts from an independent whole-row transfer."""
from functools import lru_cache
from itertools import product
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/programs'


def bad(a, b, c, d):
    heights = sorted((a, b, c, d))
    return (min(a, d) > max(b, c) or min(b, c) > max(a, d) or
            heights[0] < heights[1] == heights[2] < heights[3])


@lru_cache(None)
def row_counts(width, alphabet):
    rows = list(product(range(alphabet), repeat=width))
    neighbors = [[j for j, other in enumerate(rows)
                  if all(not bad(a, b, c, d) for a, b, c, d in
                         zip(row, row[1:], other, other[1:]))] for row in rows]
    counts = [1]*len(rows)
    totals = [sum(counts)]
    for _ in range(9):
        counts = [sum(counts[j] for j in adjacent) for adjacent in neighbors]
        totals.append(sum(counts))
    return totals


class HistoscapeCounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for mode in ['count', 'unrank']:
            generated = cls.work/(mode+'.c')
            subprocess.run(['ctangle', str(SOURCES/('histoscape-'+mode+'.w')),
                            '-', str(generated)], cwd=SOURCES, check=True, capture_output=True)
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-O1', str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program
        probe = cls.work/'arithmetic.c'
        probe.write_text('#define main count_main\n#include "'+str(cls.work/'count.c')+'''"
#undef main
int main(int argc,char **argv) {
  bignum a,b; int k,skipped; unsigned long long rank;
  if(argc>1) {
    while(scanf("%llu",&rank)==1) {
      for(k=0;k<count_digits;k++)if(scanf("%llu",&a.digit[k])!=1)return 1;
      skipped=skip_count(&rank,&a);printf("%d %llu\\n",skipped,rank);
    }
    return 0;
  }
  while(scanf("%llu",&a.digit[0])==1) {
    for(k=1;k<count_digits;k++)if(scanf("%llu",&a.digit[k])!=1)return 1;
    for(k=0;k<count_digits;k++)if(scanf("%llu",&b.digit[k])!=1)return 1;
    add_count(&a,&b);print_count(stdout,&a);puts("");
  }
  return 0;
}
''')
        cls.probe = cls.work/'arithmetic'
        subprocess.run(['gcc', '-std=gnu99', '-O1', str(probe), '-o', str(cls.probe)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def count(self, m, n, t):
        result = subprocess.run([str(self.programs['count']), str(m), str(n), str(t)],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        total = re.search(r'Altogether (-?\d+) 3VPs', result.stdout)
        self.assertIsNotNone(total)
        return int(total[1])

    def test_large_exact_binary_totals(self):
        totals = row_counts(10, 2)
        self.assertEqual(totals[7], 1360654834588676117974)
        for m in [6, 7, 8, 9, 10]:
            with self.subTest(m=m):
                self.assertEqual(self.count(m, 10, 2), totals[m-1])

    def test_small_binary_and_multilevel_counts(self):
        for n, t in [(2, 2), (3, 2), (4, 2), (2, 3), (3, 3), (2, 4), (2, 5)]:
            for m in range(2, 6):
                with self.subTest(m=m, n=n, t=t):
                    self.assertEqual(self.count(m, n, t), row_counts(n, t)[m-1])

    def test_count_arithmetic_through_proven_bound(self):
        values = [0, 1, (1 << 64)-1, 1 << 128, 1 << 256, 1 << 399]
        values += [(10**18)**k-1 for k in range(1, 7)]
        pairs = [(a, b) for a in values for b in (1, a)]
        def digits(a):
            result = []
            for _ in range(7):
                a, digit = divmod(a, 10**18)
                result.append(digit)
            self.assertEqual(a, 0)
            return result
        data = ''.join(' '.join(map(str, digits(a)+digits(b)))+'\n' for a, b in pairs)
        result = subprocess.run([str(self.probe)], input=data, text=True,
                                check=True, capture_output=True)
        self.assertEqual(list(map(int, result.stdout.split())), [a+b for a, b in pairs])

    def test_unranker_exact_large_frontier(self):
        # A zero bottom row is compatible with every preceding binary row.
        # Fixing its preceding corner to zero keeps half of the 9-row family,
        # by bit-complement symmetry. This is exactly the zero frontier entry.
        expected = row_counts(10, 2)[8]//2
        self.assertGreater(expected, (1 << 64)-1)
        result = subprocess.run([str(self.programs['unrank']), '10', '10', '2', '0'],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = re.search(r'done with 9,9 \.\.(-?\d+),', result.stderr)
        self.assertIsNotNone(first)
        self.assertEqual(int(first[1]), expected)
        self.assertEqual(list(map(int, result.stdout.split())), [0]*100)

    def test_exact_block_skip_with_full_width_rank(self):
        pairs = [(rank, value) for rank in [0, 1, 10**18-1, 10**18, (1 << 64)-1]
                 for value in [0, 1, rank, rank+1, 1 << 400]]
        lines = []
        for rank, value in pairs:
            digits = []
            for _ in range(7):
                value, digit = divmod(value, 10**18)
                digits.append(digit)
            lines.append(' '.join(map(str, [rank, *digits])))
        result = subprocess.run([str(self.probe), 'skip'], input='\n'.join(lines),
                                text=True, check=True, capture_output=True)
        actual = [tuple(map(int, line.split())) for line in result.stdout.splitlines()]
        self.assertEqual(actual, [(1, rank-value) if value <= rank else (0, rank)
                                  for rank, value in pairs])

    def test_complete_small_unranked_families(self):
        for m, n, t in [(2, 2, 2), (2, 2, 3), (2, 2, 4), (2, 3, 2), (3, 2, 2), (3, 3, 2)]:
            expected = {matrix for matrix in product(range(t), repeat=m*n)
                        if all(not bad(matrix[(i-1)*n+j-1], matrix[(i-1)*n+j],
                                       matrix[i*n+j-1], matrix[i*n+j])
                               for i in range(1, m) for j in range(1, n))}
            actual = []
            for rank in range(len(expected)):
                result = subprocess.run([str(self.programs['unrank']), str(m), str(n), str(t), str(rank)],
                                        text=True, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual.append(tuple(map(int, result.stdout.split())))
            with self.subTest(m=m, n=n, t=t):
                self.assertEqual(len(set(actual)), len(expected))
                self.assertEqual(set(actual), expected)
                result = subprocess.run([str(self.programs['unrank']), str(m), str(n), str(t), str(len(expected))],
                                        text=True, capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('exceeds the total', result.stderr)


if __name__ == '__main__':
    unittest.main()
