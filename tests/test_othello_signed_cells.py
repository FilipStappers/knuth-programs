"""BUG-150: explicit signed cell/ray types under both plain-char ABIs."""
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'programs/programs/othello.w'
DIRECTIONS=[(i,j) for i in [-1,0,1] for j in [-1,0,1] if i or j]


def game(size,players,seed):
    rng=random.Random(seed)
    board=[[-1]*size for _ in range(size)]
    move,player=1-players**2,0
    moves,states,passes=[],[],[]
    def flips(i,j,who):
        captured=[]
        for di,dj in DIRECTIONS:
            line=[]
            a,b=i+di,j+dj
            while 0<=a<size and 0<=b<size and board[a][b]>=0 and board[a][b]!=who:
                line.append((a,b)); a+=di; b+=dj
            if line and 0<=a<size and 0<=b<size and board[a][b]==who:
                captured+=line
        return captured
    while True:
        for _ in range(players):
            legal=[(i,j) for i in range(size) for j in range(size)
                   if board[i][j]<0 and (move<=0 or flips(i,j,player))]
            if legal:
                break
            passes.append(player)
            player=(player+1)%players
        else:
            break
        i,j=rng.choice(legal)
        changed=flips(i,j,player) if move>0 else []
        board[i][j]=player
        for a,b in changed:
            board[a][b]=player
        moves.append(chr(97+j)+str(i+1)+'!\n')
        states.append(tuple(''.join('.' if c<0 else str(c) for c in row) for row in board))
        move+=1
        player=(player+1)%players
    return ''.join(moves).encode(),states+[states[-1]],passes


class OthelloSignedCells(unittest.TestCase):
    def test_complete_games_and_passes_under_both_char_modes(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            for size,players in [(4,2),(4,3),(8,2)]:
                for mode in ['signed','unsigned']:
                    source=work/f'game-{size}-{players}-{mode}.w'
                    text=SOURCE.read_text().replace('@d m 8 ',f'@d m {size} ')
                    text=text.replace('@d n 8 ',f'@d n {size} ').replace('@d p 2 ',f'@d p {players} ')
                    # Normalize only the legacy entry-point return convention.
                    text=text.replace('void main(void)','int main(void)').replace(
                        '  print_board();\n}','  print_board();\n  return 0;\n}')
                    source.write_text(text)
                    generated=source.with_suffix('.c')
                    program=source.with_suffix('')
                    subprocess.run(['ctangle',str(source),'-',str(generated)],check=True,capture_output=True)
                    subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1','-f'+mode+'-char',
                                    '-fsanitize=undefined,bounds','-fsanitize-undefined-trap-on-error',
                                    str(generated),'-o',str(program)],check=True,capture_output=True)
                    for seed in range(4):
                        with self.subTest(size=size,players=players,mode=mode,seed=seed):
                            moves,expected,passes=game(size,players,seed)
                            result=subprocess.run([str(program)],input=moves,capture_output=True,timeout=5)
                            self.assertEqual(result.returncode,0,result.stderr.decode())
                            self.assertEqual(result.stderr,b'')
                            rows=[]
                            pattern=rf'([.012]{{{size}}})(?: \d+){{0,{players}}}$'
                            for line in result.stdout.decode().splitlines():
                                match=re.search(pattern,line)
                                if match:
                                    rows.append(match[1])
                            self.assertEqual([tuple(rows[k:k+size]) for k in range(0,len(rows),size)],expected)
                            actual_passes=list(map(int,re.findall(rb'player (\d) cannot move',result.stdout)))
                            self.assertEqual(actual_passes,passes)


if __name__ == '__main__':
    unittest.main()
