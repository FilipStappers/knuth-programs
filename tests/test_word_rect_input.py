"""B052: complete word records and independently constructed rectangle matrices."""
from collections import Counter
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WordRectangleInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'words.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/word-rect-dlx.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = cls.work/'words'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds,pointer-overflow', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, columns, rows, limits=('', '')):
        (self.work/'columns').write_bytes(columns)
        (self.work/'rows').write_bytes(rows)
        return subprocess.run([str(self.program), 'columns'+limits[0], 'rows'+limits[1]],
                              cwd=self.work, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_final_unterminated_words_are_complete_records(self):
        for columns, rows in [(b'ab', b'abc'), (b'ab\nba', b'abc\ncba'),
                              (b'ab\n', b'abc'), (b'ab', b'abc\n')]:
            with self.subTest(columns=columns, rows=rows):
                result = self.solve(columns, rows)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b'runtime error', result.stderr)

    def test_each_consumed_word_has_the_declared_length(self):
        for columns, rows in [(b'ab\nc\n', b'abc\n'), (b'ab\ncde\n', b'abc\n'),
                              (b'ab\n', b'abc\na\n'), (b'ab\n', b'abc\nabcd\n'),
                              (b'\n', b'abc\n'), (b'ab\n', b'\n'),
                              (b'a'*80+b'\n', b'abc\n'), (b'ab\n', b'a'*17+b'\n')]:
            with self.subTest(columns=columns, rows=rows):
                result = self.solve(columns, rows)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'word', result.stderr.lower())
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_complete_matrix_and_dictionary_limits(self):
        columns, rows = ['ab', 'ba', 'ab'], ['abc', 'cba']
        for limited in [False, True]:
            result = self.solve(('\n'.join(columns)+'\n').encode(),
                                ('\n'.join(rows)+'\n').encode(), (':1', ':1') if limited else ('', ''))
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            lines = [line.split() for line in result.stdout.decode().splitlines()
                     if not line.startswith('|')]
            expected = Counter()
            for word in columns[:1] if limited else columns:
                for j in range(3):
                    expected[tuple(sorted([f'C{j}']+[f'{i}{j}:{c}' for i, c in enumerate(word)]))] += 1
            for word in rows[:1] if limited else rows:
                for i in range(2):
                    expected[tuple(sorted([f'R{i}']+[f'{i}{j}:{c}' for j, c in enumerate(word)]))] += 1
            self.assertEqual(set(lines[0]), {'R0', 'R1', 'C0', 'C1', 'C2', '|', '00', '01', '02', '10', '11', '12'})
            self.assertEqual(Counter(tuple(sorted(line)) for line in lines[1:]), expected)

    def test_word_length_boundaries_and_limits_skip_unconsumed_records(self):
        for size in [1, 16]:
            result = self.solve(b'a'*size, b'b'*size)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            lines = [line for line in result.stdout.splitlines() if not line.startswith(b'|')]
            self.assertEqual(len(lines)-1, 2*size)
        result = self.solve(b'ab\nx\n', b'abc\nx\n', (':1', ':1'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        for columns, rows in [(b'a\x00b\n', b'abc\n'), (b'ab\n', b'ab\x00c')]:
            result = self.solve(columns, rows)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b'runtime error', result.stderr)


if __name__ == '__main__':
    unittest.main()
