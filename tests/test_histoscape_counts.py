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
int main(void) {
  bignum a,b; int k;
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


if __name__ == '__main__':
    unittest.main()
