"""B048: distributed cutoff composition and independent minimax witnesses."""
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from test_dlx6_memo import subsets
from test_historical_dance_boundaries import printed_covers

ROOT = Path(__file__).resolve().parents[1]


class DlxCutoffs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for cutoff integration checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        text = (ROOT/'programs/programs/dlx2.w').read_text()
        for key, value in [('max_level', 128), ('max_cols', 256), ('max_nodes', 8192)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        source = cls.work/'dlx2.w'
        source.write_text(text)
        for change in ['dlx2-cutoff', 'dlx2-cutoff-kludge']:
            generated = cls.work/(change+'.c')
            tangled = subprocess.run(['ctangle', str(source),
                                      str(ROOT/'programs/programs'/(change+'.ch')),
                                      str(generated)], capture_output=True)
            assert tangled.returncode == 0, tangled.stdout+tangled.stderr
            program = cls.work/change
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-I'+sgb,
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), str(Path(sgb)/'gb_flip.c'), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[change] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_family(self, rows, primary, program, args=()):
        secondary = sorted({token.split(':')[0] for row in rows for token in row}-set(primary))
        matrix = (' '.join(primary)+(' | '+' '.join(secondary) if secondary else '')+'\n'+
                  ''.join(' '.join(row)+'\n' for row in rows)).encode()
        expected = subsets(rows, primary)
        optimum = min(map(max, expected)) if expected else None
        optimal = {s for s in expected if max(s) == optimum}
        result = subprocess.run([str(program), 'm1', 'v1', *args], input=matrix,
                                capture_output=True, timeout=5,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        lookup = {tuple(sorted(row)): i+1 for i, row in enumerate(rows)}
        actual = [tuple(sorted(lookup[row] for row in cover))
                  for cover in printed_covers(result.stdout)]
        self.assertEqual(len(actual), len(set(actual)))
        self.assertTrue(set(actual) <= expected, (rows, actual, expected))
        self.assertTrue(optimal <= set(actual), (rows, actual, optimal))
        return actual

    def test_both_changes_compose_and_preserve_deterministic_minimax_families(self):
        rng = random.Random(48054)
        for case in range(70):
            rows = set()
            for _ in range(rng.randrange(1, 10)):
                row = [p for p in ['A', 'B', 'C'] if rng.randrange(2)]
                if not row:
                    row = [rng.choice(['A', 'B', 'C'])]
                row += [name+color for name in ['X', 'Y']
                        if (color := rng.choice([None, ':a', ':b'])) is not None]
                rows.add(tuple(row))
            # Colored secondaries leave the combined variant's special kludge inactive.
            for name, program in self.programs.items():
                with self.subTest(case=case, change=name):
                    self.check_family(sorted(rows), ['A', 'B', 'C'], program)


if __name__ == '__main__':
    unittest.main()
