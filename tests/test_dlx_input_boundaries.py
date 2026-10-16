"""B048: deterministic diagnostics and neighboring exact-cover input checks."""
import itertools
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DlxInputBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for DLX integration checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for name in ['dlx1', 'dlx2']:
            text = (ROOT/'programs/programs'/(name+'.w')).read_text()
            for key, value in [('max_level', 128), ('max_cols', 256), ('max_nodes', 8192)]:
                text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
                assert count == 1
            source = cls.work/(name+'.w')
            source.write_text(text)
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(source), '-', str(generated)],
                           check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-ftrivial-auto-var-init=pattern', '-I'+sgb,
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), str(Path(sgb)/'gb_flip.c'), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_matrix(self, name, matrix):
        return subprocess.run([str(self.programs[name]), 'm1', 'v1'], input=matrix,
                              capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_empty_file_diagnostic_has_an_initialized_position(self):
        for name in self.programs:
            with self.subTest(program=name):
                result = self.run_matrix(name, b'')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stderr, b'No items!\n0: \n')

    def test_all_64_primary_bearing_uncolored_families(self):
        options = [('A',), ('B',), ('A', 'B'), ('A', 'X'), ('B', 'X'), ('A', 'B', 'X')]
        for mask in range(64):
            rows = [row for i, row in enumerate(options) if mask >> i & 1]
            expected = 0
            for flags in itertools.product([False, True], repeat=len(rows)):
                counts = {x: sum(x in row for row, used in zip(rows, flags) if used)
                          for x in ['A', 'B', 'X']}
                expected += counts['A'] == counts['B'] == 1 and counts['X'] <= 1
            data = ('A B | X\n'+''.join(' '.join(row)+'\n' for row in rows)).encode()
            for name in self.programs:
                result = self.run_matrix(name, data)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(int(re.search(rb'Altogether (\d+) solutions?', result.stderr)[1]), expected)

    def test_compatible_distributed_changes_still_tangle(self):
        # The two historical cutoff mismatches are tracked separately in B048.
        for base, changes in [('dlx1', ['sudoku']),
                              ('dlx2', ['sharp', 'kludge', 'loop', 'polyom', 'wordsearch'])]:
            for change in changes:
                name = base+'-'+change
                with self.subTest(change=name):
                    subprocess.run(['ctangle', str(self.work/(base+'.w')),
                                    str(ROOT/'programs/programs'/(name+'.ch')),
                                    str(self.work/(name+'.c'))], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
