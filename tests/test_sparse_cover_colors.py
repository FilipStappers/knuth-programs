"""B050: parser index units and complete sparse-set cover witnesses."""
from collections import Counter
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest
from test_dlx6_memo import subsets

ROOT = Path(__file__).resolve().parents[1]


def sparse_covers(output):
    result = []
    for block in re.split(r'(?m)^\d+:\n', output.decode())[1:]:
        rows = []
        for line in block.splitlines():
            if not line.startswith(' '):
                break
            # Binary variants omit the optional item-list position suffix.
            rows.append(tuple(sorted(line.split(' (')[0].split())))
        result.append(tuple(sorted(rows)))
    return result


class SparseCoverColors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for sparse-set cover checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        variants = [('ssxcc-binary', None), ('ssxcc-binary', 'ssxcc-frb'),
                    ('ssxcc-binary', 'ssxcc-wtd'), ('ssxcc', None),
                    ('ssxcc', 'ssxcc-frb0'), ('ssxcc', 'ssxcc-wtd0'), ('ssxcc0', None)]
        for base, change in variants:
            name = change or base
            text = (ROOT/'programs/programs'/(base+'.w')).read_text()
            for key, value in [('max_level', 64), ('max_stage', 32), ('max_cols', 128),
                               ('max_nodes', 8192), ('savesize', 8192)]:
                text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
                assert count <= 1
            source = cls.work/(base+'.w')
            source.write_text(text)
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(source),
                            str(ROOT/'programs/programs'/(change+'.ch')) if change else '-',
                            str(generated)], check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-fgnu89-inline', '-Wno-implicit-int',
                            '-O1', '-I'+sgb, '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated),
                            str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_matrix(self, program, matrix):
        return subprocess.run([str(program), 'm1', 'v1'], input=matrix,
                              capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_primary_color_uses_the_same_index_units_as_the_boundary(self):
        for name, program in self.programs.items():
            for data in [b'A B | X\nA:a\nB\n', b'A B C D | X\nD:a\n']:
                with self.subTest(program=name, matrix=data):
                    result = self.run_matrix(program, data)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b'Primary item must be uncolored', result.stderr)
                    self.assertNotIn(b'runtime error', result.stderr)

    def test_complete_colored_and_uncolored_families_with_duplicate_options(self):
        types = [('A',), ('B',), ('A', 'B'), ('A', 'X'), ('B', 'X'), ('A', 'B', 'X')]
        families = [[row for i, row in enumerate(types) if mask >> i & 1] for mask in range(64)]
        rng = random.Random(50042)
        for _ in range(40):
            rows = []
            for _ in range(rng.randrange(1, 10)):
                row = [p for p in ['A', 'B'] if rng.randrange(2)]
                if not row:
                    row = [rng.choice(['A', 'B'])]
                row += [name+color for name in ['X', 'Y']
                        if (color := rng.choice([None, '', ':a', ':b'])) is not None]
                rows.append(tuple(row))
            families.append(rows)
        for case, rows in enumerate(families):
            ids = subsets(rows, ['A', 'B'])
            expected = Counter(tuple(sorted(tuple(sorted(rows[i-1])) for i in choice))
                               for choice in ids)
            data = ('A B | X Y\n'+''.join(' '.join(row)+'\n' for row in rows)).encode()
            for name, program in self.programs.items():
                with self.subTest(program=name, case=case):
                    result = self.run_matrix(program, data)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(Counter(sparse_covers(result.stdout)), expected)
                    self.assertEqual(int(re.search(rb'Altogether (\d+) solutions?', result.stderr)[1]),
                                     sum(expected.values()))


if __name__ == '__main__':
    unittest.main()
