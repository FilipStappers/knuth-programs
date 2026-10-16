"""B058: uncovered primary columns and full independent row-selection projections."""
import itertools
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'


class SatDanceEmptyColumns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        text = (SOURCES/'sat-dance.w').read_text()
        for key, value in [('max_cols', 64), ('max_nodes', 8192)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        source = work/'cover.w'
        source.write_text(text)
        for mode in ['base', 'aspvall', 'heule', 'prestwich']:
            generated = work/(mode+'.c')
            change = '-' if mode == 'base' else str(SOURCES/('sat-dance-'+mode+'.ch'))
            subprocess.run(['ctangle', str(source), change, str(generated)],
                           check=True, capture_output=True)
            program = work/mode
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, mode, data):
        return subprocess.run([str(self.programs[mode])], input=data, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_uncovered_primaries_encode_a_real_contradiction(self):
        for mode in self.programs:
            for data in [b'A\n', b'A B | C\nA\n', b'A | C D\nC\n']:
                with self.subTest(mode=mode, data=data):
                    result = self.encode(mode, data)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    formula = [line.split() for line in result.stdout.decode().splitlines() if line.strip()]
                    self.assertFalse(satisfiable(formula))

    def test_every_row_selection_matches_direct_column_coverage(self):
        universe = [tuple(column for bit, column in enumerate('ABC') if mask >> bit & 1)
                    for mask in range(1, 8)]
        families = [[row for bit, row in enumerate(universe) if mask >> bit & 1] for mask in range(128)]
        families += [[('A', 'B', 'C')]*n for n in range(1, 10)]
        for rows in families:
            data = ('A B | C D\n'+''.join(' '.join(row)+'\n' for row in rows)).encode()
            for mode in self.programs:
                result = self.encode(mode, data)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                formula = [line.split() for line in result.stdout.decode().splitlines() if line.strip()]
                for selected in itertools.product([False, True], repeat=len(rows)):
                    expected = all(sum(use and column in row for row, use in zip(rows, selected))
                                   in ([1] if column in 'AB' else [0, 1]) for column in 'ABCD')
                    fixed = [[('' if use else '~')+str(i)] for i, use in enumerate(selected, 1)]
                    with self.subTest(mode=mode, rows=rows, selected=selected):
                        self.assertEqual(satisfiable(formula+fixed), expected)


if __name__ == '__main__':
    unittest.main()
