"""B048: bounded clue-comment parsing, including real generator output."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SudokuClues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for Sudoku renderer integration')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        text = (ROOT/'programs/programs/dlx1.w').read_text()
        for key, value in [('max_level', 128), ('max_cols', 256), ('max_nodes', 8192)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        source = cls.work/'dlx1.w'
        source.write_text(text)
        generated = cls.work/'sudoku.c'
        subprocess.run(['ctangle', str(source), str(ROOT/'programs/programs/dlx1-sudoku.ch'),
                        str(generated)], check=True, capture_output=True)
        cls.program = cls.work/'sudoku'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-I'+sgb,
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), str(Path(sgb)/'gb_flip.c'), '-o', str(cls.program)],
                       check=True, capture_output=True)
        generated = cls.work/'generator.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/sudoku-general-dlx.w'),
                        '-', str(generated)], check=True, capture_output=True)
        cls.generator = cls.work/'generator'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-include', 'stdlib.h',
                        '-O1', str(generated), '-o', str(cls.generator)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, data):
        return subprocess.run([str(self.program), 'm1', 'v1'], input=data,
                              capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_malformed_clue_shapes_reject_before_board_reads_or_writes(self):
        for comment in [b'|sudoku!bad\n', b'|sudoku!\n', b'|sudoku!!\n',
                        b'|sudoku!..!.\n', b'|sudoku!..!xx!extra\n',
                        b'|sudoku'+(b'!'+b'.'*33)*33+b'\n']:
            with self.subTest(comment=comment[:50]):
                result = self.solve(comment+b'A\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'clue', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)

    def test_well_formed_clue_comments_at_supported_sizes(self):
        for n in [1, 2, 9, 32]:
            for trailing in [b'', b'!']:
                comment = b'|sudoku'+(b'!'+b'.'*n)*n+trailing+b'\n'
                result = self.solve(comment+b'A\n')
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertIn(b'Altogether 0 solutions', result.stderr)

    def test_real_one_cell_generator_comment_and_solution(self):
        generated = subprocess.run([str(self.generator)], input=b'.\n', capture_output=True, timeout=5)
        self.assertEqual(generated.returncode, 0, generated.stderr.decode())
        self.assertTrue(generated.stdout.startswith(b'|sudoku!.\n'))
        result = self.solve(generated.stdout)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout, b'1:\n 1\n')


if __name__ == '__main__':
    unittest.main()
