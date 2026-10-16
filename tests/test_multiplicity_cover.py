"""B051: multiplicity covering storage and complete independent subsets."""
from collections import Counter
import itertools
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from test_sparse_cover_colors import sparse_covers

ROOT = Path(__file__).resolve().parents[1]


class MultiplicityCover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for multiplicity cover checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        text = (ROOT/'programs/programs/ssmcc.w').read_text()
        for key, value in [('max_level', 128), ('max_stage', 32), ('max_cols', 128),
                           ('max_nodes', 8192), ('savesize', 8192)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        source = cls.work/'multiplicity.w'
        source.write_text(text)
        for mode in ['base', 'frb', 'wtd']:
            generated = cls.work/(mode+'.c')
            change = '-' if mode == 'base' else str(ROOT/'programs/programs'/('ssmcc-'+mode+'.ch'))
            subprocess.run(['ctangle', str(source), change, str(generated)],
                           check=True, capture_output=True)
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-fgnu89-inline', '-Wno-implicit-int',
                            '-O1', '-I'+sgb, '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated),
                            str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, mode, data, args=()):
        return subprocess.run([str(self.programs[mode]), 'm1', 'v1', *args], input=data,
                              capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_primary_colors_reject(self):
        for mode in self.programs:
            for data in [b'A B | X\nA:a\nB\n', b'A B C D | X\nD:a\n']:
                with self.subTest(mode=mode, data=data):
                    result = self.solve(mode, data)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b'Primary item must be uncolored', result.stderr)
                    self.assertNotIn(b'runtime error', result.stderr)

    def test_independent_multiplicity_families(self):
        rng = random.Random(51002)
        for case in range(60):
            bounds = [(rng.randrange(3), rng.randrange(1, 4)) for _ in range(3)]
            bounds = [(min(a, b), b) for a, b in bounds]
            rows = []
            for _ in range(rng.randrange(1, 10)):
                row = [p for p in ['A', 'B', 'C'] if rng.randrange(2)]
                if not row:
                    row = [rng.choice(['A', 'B', 'C'])]
                row += [name+color for name in ['X', 'Y']
                        if (color := rng.choice([None, '', ':a', ':b'])) is not None]
                rows.append(tuple(row))
            expected = Counter()
            for mask in itertools.product([False, True], repeat=len(rows)):
                chosen = [row for row, use in zip(rows, mask) if use]
                counts = Counter(token for row in chosen for token in row)
                if any(not lo <= counts[p] <= hi for p, (lo, hi) in zip(['A', 'B', 'C'], bounds)):
                    continue
                colors = {name: [t.partition(':')[2] for row in chosen for t in row
                                 if t.partition(':')[0] == name] for name in ['X', 'Y']}
                if any(len(c) > 1 and ('' in c or len(set(c)) > 1) for c in colors.values()):
                    continue
                expected[tuple(sorted(tuple(sorted(row)) for row in chosen))] += 1
            header = ' '.join(f'{lo}:{hi}|{p}' for p, (lo, hi) in zip(['A', 'B', 'C'], bounds))
            data = (header+' | X Y\n'+''.join(' '.join(row)+'\n' for row in rows)).encode()
            for mode in self.programs:
                with self.subTest(mode=mode, case=case):
                    result = self.solve(mode, data)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(Counter(sparse_covers(result.stdout)), expected)


if __name__ == '__main__':
    unittest.main()
