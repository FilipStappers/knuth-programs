"""Analyze every reachable tic-tac-toe position and every printed symmetry class."""
from collections import Counter
from functools import lru_cache
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/tictactoe'
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
SWAP = str.maketrans('XO', 'OX')


def winner(board):
    return any(all(board[i] == 'O' for i in line) for line in LINES)


@lru_cache(None)
def children(board):
    if winner(board):
        return ()
    return tuple((board[:i]+'X'+board[i+1:]).translate(SWAP)
                 for i, char in enumerate(board) if char == ' ')


@lru_cache(None)
def nobrainer(board):
    choices = children(board)
    if any(winner(child) for child in choices):
        return 1
    return -1 if any(nobrainer(child) == 1 for child in choices) else 0


@lru_cache(None)
def value(board):
    rank = 9-board.count(' ')
    if winner(board):
        return -rank, 0x0f0f0f0f
    choices = children(board)
    if not choices:
        return 0, 0x0f0f0f0f
    results = [value(child) for child in choices]
    score = min(s for s, _ in results)
    difficulty = max(d for s, d in results if s == score)
    worse = sum((s, d) != (score, difficulty) for s, d in results)
    if nobrainer(board) < 0 or score == -rank-1:
        worse = 0
    return -score, (worse << 28)+((0xffffffff-difficulty) >> 4)


def orbit(board):
    result = set()
    for flip in [False, True]:
        for turns in range(4):
            transformed = [' ']*9
            for i, char in enumerate(board):
                x, y = divmod(i, 3)
                if flip:
                    y = 2-y
                for _ in range(turns):
                    x, y = y, 2-x
                transformed[3*x+y] = char
            result.add(''.join(transformed))
    return result


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').exists(), 'GraphBase sources required')
class TictactoeAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        objects = []
        for name in ['gb_graph', 'gb_io', 'gb_save']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-w',
                            '-I'+str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')),
                            '-o', str(obj)], check=True, capture_output=True)
            objects.append(str(obj))
        cls.programs = {}
        for name in ['tictactoe1', 'tictactoe2']:
            source, generated, program = [cls.work/(name+suffix) for suffix in ['.w', '.c', '']]
            text = (SOURCES/(name+'.w')).read_text().replace('/tmp/tictactoe.gb', str(cls.work/'tictactoe.gb'))
            source.write_text(text)
            subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                            '-include', 'stdlib.h', '-include', 'string.h',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), *objects, '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_reachable_symmetry_classes(self):
        generated = subprocess.run([str(self.programs['tictactoe1'])], text=True,
                                   capture_output=True, timeout=10)
        self.assertNotIn('runtime error', generated.stderr)
        self.assertTrue((self.work/'tictactoe.gb').exists())
        result = subprocess.run([str(self.programs['tictactoe2'])], text=True,
                                capture_output=True, timeout=10)
        self.assertNotIn('runtime error', result.stderr)
        self.assertNotIn('I goofed', result.stdout)
        reached, pending = set(), [' '*9]
        while pending:
            board = pending.pop()
            if board not in reached:
                reached.add(board)
                pending.extend(children(board))
        self.assertEqual(len(reached), 5478)
        expected = {min(orbit(board)) for board in reached}
        self.assertEqual(len(expected), 765)
        actual, counts, terminals = set(), Counter(), Counter()
        for line in result.stdout.splitlines():
            match = re.fullmatch(r'(.../.../...) has score (-?\d+)\(([0-9a-f]{8})\), size (\d+)(?:, -> (.../.../...))?', line)
            if not match:
                continue
            name, score, difficulty, size, follower = match.groups()
            board = name.replace('/', '')
            self.assertIn(board, reached)
            self.assertEqual((int(score), int(difficulty, 16)^0x0f0f0f0f), value(board))
            self.assertEqual(int(size), len(orbit(board)))
            representative = min(orbit(board))
            self.assertNotIn(representative, actual)
            actual.add(representative)
            rank = 9-board.count(' ')
            counts[rank] += 1
            if follower:
                child = follower.replace('/', '').translate(SWAP)
                self.assertIn(child, children(board))
                best_score = min(value(c)[0] for c in children(board))
                best_diff = max(value(c)[1] for c in children(board) if value(c)[0] == best_score)
                self.assertEqual(value(child), (best_score, best_diff))
            else:
                self.assertFalse(children(board))
                terminals[rank] += 1
        self.assertEqual(actual, expected)
        summaries = re.findall(r'\((\d+),(\d+)\) classes after (\d+) moves', result.stdout)
        self.assertEqual(len(summaries), 10)
        for count, terminal, rank in summaries:
            self.assertEqual((int(count), int(terminal)), (counts[int(rank)], terminals[int(rank)]))


if __name__ == '__main__':
    unittest.main()
