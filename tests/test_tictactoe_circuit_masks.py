"""BUG-070: full circuit construction and independent geometric game oracle."""
from functools import lru_cache
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'programs/archives/tictactoe'
LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
PAIR_ORDER = [4,8,6,2,7,9,3,1,5]
PIN = [2,1,6,7,5,3,4,9,8]


def won(board):
    return any(board[a] != '.' and board[a] == board[b] == board[c] for a,b,c in LINES)


def successors(board):
    if won(board):
        return ()
    player = 'X' if board.count('X') == board.count('O') else 'O'
    return tuple((i,board[:i]+player+board[i+1:]) for i in range(9) if board[i] == '.')


@lru_cache(None)
def score(board):
    if won(board):
        return -1
    return max((-score(child) for _,child in successors(board)),default=0)


def game_data():
    reached = set()
    def visit(board):
        if board in reached:
            return
        reached.add(board)
        for _,child in successors(board):
            visit(child)
    visit('.'*9)
    boards = sorted(board for board in reached if successors(board))
    outputs, records = [], []
    for board in boards:
        moves = {i for i,child in successors(board) if -score(child) == score(board)}
        code = sum(('.OX'.index(board[position-1])) << (2*i)
                   for i,position in enumerate(PAIR_ORDER))
        bits = ''.join(str(int(i in moves)) for i in range(9))
        records.append(f'{code:05x}: {bits}\n')
        outputs.append(moves)
    return boards,outputs,''.join(records).encode()


def symmetry(flip,turns):
    mapping = []
    for i in range(9):
        x,y = divmod(i,3)
        if flip:
            y = 2-y
        for _ in range(turns):
            x,y = y,2-x
        mapping.append(3*x+y)
    return mapping


class TictactoeCircuitMasks(unittest.TestCase):
    def test_generated_circuits_on_every_playable_board(self):
        boards,outputs,data = game_data()
        self.assertEqual(len(boards),4520)
        with tempfile.TemporaryDirectory() as tmp:
            for number in [6,7]:
                with self.subTest(number=number):
                    text = (ROOT / f'tictactoe{number}.w').read_text()
                    text = text.replace('#include <stdio.h>','#include <stdio.h>\n#include <stdlib.h>')
                    text = text.replace('main()','int main()')
                    text = text.replace('  @<Check the results@>;', '''  {
    int observer;
    for (observer=1;observer<=g;observer++)
      printf("@@@@ %d %d %d %d\\n",observer,op[observer],jx[observer],kx[observer]);
  }
  @<Check the results@>;''')
                    source = Path(tmp)/f'circuit{number}.w'
                    generated = source.with_suffix('.c')
                    program = source.with_suffix('')
                    source.write_text(text)
                    subprocess.run(['ctangle',str(source),'-',str(generated)],capture_output=True,check=True)
                    subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1',
                                    '-fsanitize=undefined,bounds','-fno-sanitize-recover=all',
                                    str(generated),'-o',str(program)],capture_output=True,check=True)
                    result = subprocess.run([str(program)],input=data,capture_output=True,timeout=15)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertEqual(result.stderr,b'')
                    self.assertNotIn(b'Failure',result.stdout)
                    self.assertIn(b'4520 cases checked.',result.stdout)
                    gates = [tuple(map(int,line.split()[1:])) for line in result.stdout.splitlines()
                             if line.startswith(b'@@ ')]
                    self.assertGreater(len(gates),18)
                    transforms = [symmetry(f,t) for f in [False,True] for t in range(4)] \
                        if number == 6 else [list(range(9)),[0,3,6,1,4,7,2,5,8]]
                    allbits = (1 << len(boards))-1
                    answer = 0
                    for transform in transforms:
                        values = [0]*(len(gates)+1)
                        for gate in range(1,19):
                            physical = PIN[(gate-1)%9]-1
                            player = 'X' if gate <= 9 else 'O'
                            values[gate] = sum((board[transform[physical]] == player) << i
                                               for i,board in enumerate(boards))
                        for gate,op,left,right in gates[18:]:
                            self.assertLess(left,gate)
                            self.assertLess(right,gate)
                            a,b = values[left],values[right]
                            values[gate] = [0,a&b,a|b,a^b,a&~b,allbits^(a|b)][op]
                        answer |= values[-1]
                    target = 4 if number == 6 else 0
                    expected = sum((target in moves) << i for i,moves in enumerate(outputs))
                    self.assertEqual(answer,expected)


if __name__ == '__main__':
    unittest.main()
