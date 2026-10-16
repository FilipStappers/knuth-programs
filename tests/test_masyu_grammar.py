"""B052: documented Masyu clues and the complete blank-square cycle family."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_dlx6_memo import subsets

ROOT = Path(__file__).resolve().parents[1]


class MasyuGrammar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'masyu.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/masyu-dlx.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = work/'masyu'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, data):
        return subprocess.run([str(self.program)], input=data, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_only_documented_clue_symbols_are_accepted(self):
        for symbol in '234':
            with self.subTest(symbol=symbol):
                result = self.solve(('...\n.'+symbol+'.\n...\n').encode())
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'illegal clue', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
        for data in [b'...\n.0.\n...\n', b'....\n.1..\n....\n....\n']:
            result = self.solve(data)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_blank_two_by_two_matrix_has_exactly_empty_and_square_cycles(self):
        result = self.solve(b'..\n..\n')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        lines = [line.split() for line in result.stdout.decode().splitlines()
                 if line.strip() and not line.startswith('|')]
        primary = lines[0][:lines[0].index('|')]
        rows = lines[1:]
        edge_sets = set()
        for choice in subsets(rows, primary):
            selected = set()
            for index in choice:
                selected |= {token.split(':')[0] for token in rows[index-1] if token.endswith(':1')}
            edge_sets.add(frozenset(selected))
        self.assertEqual(edge_sets, {frozenset(), frozenset({'01', '10', '12', '21'})})


if __name__ == '__main__':
    unittest.main()
