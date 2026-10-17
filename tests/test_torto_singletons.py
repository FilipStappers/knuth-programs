"""Torto singleton occurrence constraints against direct fixed-grid predicates."""
from itertools import product
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'programs/programs/torto-dlx.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


def parse_problem(text):
    lines = [row.split() for row in text.splitlines() if row.strip() and not row.startswith('|')]
    header = lines[0]
    primary = set(header[:header.index('|')])
    options = []
    for row in lines[1:]:
        entries = dict(token.split(':', 1) if ':' in token else (token, None) for token in row)
        options.append((set(entries) & primary, entries))
    return primary, options


def cover_exists(problem, grid):
    primary, options = problem
    def search(left, colors):
        if not left:
            return True
        candidates = []
        for chosen, entries in options:
            if chosen and chosen <= left and all(name not in colors or
                    (color is not None and colors[name] == color) for name, color in entries.items()
                    if name not in primary):
                candidates.append((chosen, entries))
        item = min(left, key=lambda name: sum(name in chosen for chosen, _ in candidates))
        for chosen, entries in candidates:
            if item in chosen and search(left-chosen, colors | {name: color for name, color in entries.items()
                                                                if name not in primary}):
                return True
        return False
    return search(primary, grid)


class TortoSingletons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        source, generated, cls.program = [work/('torto'+s) for s in ['.w', '.c', '']]
        source.write_text(SOURCE.read_text().replace('@d rows 6', '@d rows 2'))
        subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, words):
        result = subprocess.run([str(self.program), *words], capture_output=True, timeout=5, env=ENV)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return parse_problem(result.stdout.decode())

    def test_single_letter_requires_an_occurrence(self):
        problem = self.encode(['A'])
        self.assertTrue(cover_exists(problem, dict.fromkeys('abcdef', 'A')))
        self.assertFalse(cover_exists(problem, dict.fromkeys('abcdef', 'B')))

    def test_empty_word_rejects(self):
        result = subprocess.run([str(self.program), ''], capture_output=True, timeout=5, env=ENV)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'empty', result.stderr)
        self.assertFalse(result.stdout)

    def test_all_fixed_grids_with_singleton_and_transition_words(self):
        problems = {words: self.encode(words) for words in [('A',), ('A', 'B'), ('AB', 'C')]}
        for values in product('ABC', repeat=6):
            grid = dict(zip('abcdef', values))
            for words, problem in problems.items():
                if words == ('AB', 'C'):
                    # First word's one transition obeys the advertised reflection
                    # restriction: top half, left/middle column, no right move
                    # from the middle column.
                    expected = 'C' in values and any(values[j] == 'A' and values[3*i+k] == 'B'
                        for j in [0, 1] for i in [0, 1] for k in range(3)
                        if (i, k) != (0, j) and abs(k-j) <= 1 and (j == 0 or k <= j))
                else:
                    expected = all(word in values for word in words)
                self.assertEqual(cover_exists(problem, grid), expected, (values, words))


if __name__ == '__main__':
    unittest.main()
