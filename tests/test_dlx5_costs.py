"""B049: checked decimal option costs and independently ranked covers."""
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from test_dlx6_memo import subsets

ROOT = Path(__file__).resolve().parents[1]


def final_costs(stderr):
    single = re.search(rb'The optimum cost is \$(\d+)', stderr)
    result = [int(single[1])] if single else []
    for value, repeat in re.findall(rb'^ \$(\d+)(?: \(repeated (\d+) times\))?$', stderr, re.M):
        result.extend([int(value)]*int(repeat or 1))
    return result


class DlxCosts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for min-cost cover checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        text = (ROOT/'programs/programs/dlx5.w').read_text()
        for key, value in [('max_level', 128), ('max_cols', 256), ('max_nodes', 8192)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        source = cls.work/'cost.w'
        source.write_text(text)
        generated = cls.work/'cost.c'
        subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
        cls.program = cls.work/'cost'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-I'+sgb,
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), str(Path(sgb)/'gb_flip.c'), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, data, k=1):
        return subprocess.run([str(self.program), 'm1', 'v17', 'k'+str(k)], input=data,
                              capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_decimal_overflow_and_infinity_sentinel_costs_reject(self):
        for cost in ['18446744073709551616', '18446744073709551615',
                     '999999999999999999999999999999999999',
                     '18446744073709551614 |1', '18446744073709551614 |2']:
            with self.subTest(cost=cost):
                result = self.solve(('A\nA |'+cost+'\n').encode())
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'cost', result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_largest_finite_option_cost_and_repeated_tokens(self):
        for tokens, expected in [('18446744073709551614', 2**64-2),
                                 ('18446744073709551613 |1', 2**64-2), ('9 |3', 12), ('0', 0)]:
            result = self.solve(('A\nA |'+tokens+'\n').encode())
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(final_costs(result.stderr), [expected])

    def test_independent_colored_cover_rankings(self):
        rng = random.Random(49055)
        for case in range(40):
            rows = set()
            for _ in range(rng.randrange(1, 10)):
                row = [p for p in ['A', 'B', 'C'] if rng.randrange(2)]
                if not row:
                    row = [rng.choice(['A', 'B', 'C'])]
                row += [name+color for name in ['X', 'Y']
                        if (color := rng.choice([None, '', ':a', ':b'])) is not None]
                rows.add(tuple(row))
            rows = sorted(rows)
            costs = [rng.randrange(50) for _ in rows]
            solutions = subsets(rows, ['A', 'B', 'C'])
            expected = sorted(sum(costs[i-1] for i in cover) for cover in solutions)
            data = ('A B C | X Y\n'+''.join(' '.join(row)+' |'+str(cost)+'\n'
                                           for row, cost in zip(rows, costs))).encode()
            for k in [1, 2, 5]:
                with self.subTest(case=case, k=k):
                    result = self.solve(data, k)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(final_costs(result.stderr), expected[:k])


if __name__ == '__main__':
    unittest.main()
