"""B051: domain-consistent covering and checkpoint boundaries."""
from collections import Counter
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from test_dlx6_memo import subsets
from test_sparse_cover_colors import sparse_covers

ROOT = Path(__file__).resolve().parents[1]


class DomainCover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for domain cover checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        text = (ROOT/'programs/programs/xccdc.w').read_text()
        for key, value in [('max_level', 128), ('max_stage', 32), ('max_cols', 128),
                           ('max_nodes', 8192), ('savesize', 8192), ('poolsize', 65536),
                           ('part_file_name_size', 1024)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        # Checkpoint files stay in this test's owned working directory.
        text, count = re.subn(r'(?m)^@ @d part_file_prefix [^\n]+',
                              '@ @d part_file_prefix "part"', text)
        assert count == 1
        source = cls.work/'dc.w'
        source.write_text(text)
        for mode in ['base', 'frb', 'wtd']:
            generated = cls.work/(mode+'.c')
            change = '-' if mode == 'base' else str(ROOT/'programs/programs'/('xccdc-'+mode+'.ch'))
            subprocess.run(['ctangle', str(source), change, str(generated)],
                           check=True, capture_output=True)
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-fgnu89-inline', '-Wno-implicit-int',
                            '-ftrivial-auto-var-init=pattern', '-O1', '-I'+sgb,
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, mode, data, args=()):
        return subprocess.run([str(self.programs[mode]), 'm1', 'v1', *args], input=data,
                              cwd=self.work, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_initial_consistency_purge(self):
        data = b'P0 P1 | S0 S1\nP0 S1:1\nP0 P1 S0 S1\n'
        expected = Counter({(('P0', 'P1', 'S0', 'S1'),): 1})
        for mode in self.programs:
            with self.subTest(mode=mode):
                result = self.solve(mode, data)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(Counter(sparse_covers(result.stdout)), expected)

    def test_independent_complete_families(self):
        rng = random.Random(51001)
        families = [[], [('A',), ('B',), ('A', 'B')]]
        for _ in range(60):
            rows = []
            for _ in range(rng.randrange(1, 11)):
                row = [p for p in ['A', 'B', 'C'] if rng.randrange(2)]
                if not row:
                    row = [rng.choice(['A', 'B', 'C'])]
                row += [name+color for name in ['X', 'Y']
                        if (color := rng.choice([None, '', ':a', ':b'])) is not None]
                rows.append(tuple(row))
            families.append(rows)
        for case, rows in enumerate(families):
            expected = Counter(tuple(sorted(tuple(sorted(rows[i-1])) for i in cover))
                               for cover in subsets(rows, ['A', 'B', 'C']))
            data = ('A B C | X Y\n'+''.join(' '.join(row)+'\n' for row in rows)).encode()
            for mode in self.programs:
                with self.subTest(mode=mode, case=case):
                    result = self.solve(mode, data)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(Counter(sparse_covers(result.stdout)), expected)


if __name__ == '__main__':
    unittest.main()
