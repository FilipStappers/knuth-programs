"""Solved and nearby 15-puzzle positions, checked by shortest-path enumeration."""
from collections import deque
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GOAL = tuple(range(1, 16))+(0,)


def nearby(depth):
    distances = {GOAL: 0}
    pending = deque([GOAL])
    while pending:
        board = pending.popleft()
        distance = distances[board]
        if distance == depth:
            continue
        blank = board.index(0)
        for target in range(16):
            if abs(blank//4-target//4)+abs(blank%4-target%4) == 1:
                child = list(board)
                child[blank], child[target] = child[target], child[blank]
                child = tuple(child)
                if child not in distances:
                    distances[child] = distance+1
                    pending.append(child)
    return distances


class FifteenPuzzleZero(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        clock = cls.work/'clock.c'
        clock.write_text('''#include <time.h>
time_t deterministic_time(time_t *out) {
  if(out)*out=500000;
  return 500000;
}
''')
        obj = cls.work/'clock.o'
        subprocess.run(['gcc', '-c', str(clock), '-o', str(obj)], check=True, capture_output=True)
        cls.programs = {}
        for mode in [0, 1]:
            generated = cls.work/(f'korf{mode}.c')
            subprocess.run(['ctangle', str(ROOT/f'programs/programs/15puzzle-korf{mode}.w'),
                            '-', str(generated)], check=True, capture_output=True)
            program = cls.work/f'korf{mode}'
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int',
                            '-include', 'stdlib.h', '-Dtime=deterministic_time',
                            '-ftrivial-auto-var-init=pattern', '-fsanitize=undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated), str(obj), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, mode, board):
        result = subprocess.run([str(self.programs[mode]), ''.join(format(x, 'x') for x in board)],
                                text=True, capture_output=True, timeout=5)
        self.assertNotIn('runtime error', result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        match = re.search(r'Solution in (\d+)\+(\d+) moves: ([0-9a-f]*)(?:\s+\((\d+) sec\))?', result.stdout)
        self.assertIsNotNone(match, result.stdout+result.stderr)
        happy, sad, steps, elapsed = match.groups()
        replay = list(board)
        for step in steps:
            blank, tile = replay.index(0), replay.index(int(step, 16))
            self.assertEqual(abs(blank//4-tile//4)+abs(blank%4-tile%4), 1)
            replay[blank], replay[tile] = replay[tile], replay[blank]
        self.assertEqual(tuple(replay), GOAL)
        self.assertEqual(len(steps), int(happy)+int(sad))
        return len(steps), elapsed

    def test_solved_timer_is_zero(self):
        self.assertEqual(self.solve(1, GOAL), (0, '0'))

    def test_zero_path_needs_no_move_bookkeeping(self):
        self.assertEqual(self.solve(0, GOAL)[0], 0)

    def test_nearby_shortest_paths(self):
        family = nearby(6)
        self.assertEqual(len(family), 202)
        for board, distance in family.items():
            if not distance:
                continue
            for mode in self.programs:
                with self.subTest(mode=mode, board=board):
                    self.assertEqual(self.solve(mode, board)[0], distance)


if __name__ == '__main__':
    unittest.main()
