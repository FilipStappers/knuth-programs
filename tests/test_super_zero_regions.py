"""B052: zero-region edge suppression throughout an entire SuperSlitherlink region."""
import itertools
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SuperZeroRegions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        for name in ['superslitherlink', 'superslitherlink-general']:
            generated = work/'encoder.c'
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/(name+'-dlx.w')), '-', str(generated)],
                           check=True, capture_output=True)
            driver = work/'driver.c'
            # Preserve the original void entry point and inspect only its global edge map.
            driver.write_text('''
#define main published_main
#include "encoder.c"
#undef main
int main(void) {
  int i,j;
  published_main();
  for(i=0;i<2*maxn+1;i++) for(j=0;j<2*maxn+1;j++)
    if(edge[i][j]) fprintf(stderr,"EDGE %d %d\\n",i,j);
  return 0;
}
''')
            program = work/name
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(driver), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_zero_region_cell_suppresses_its_boundary_edges(self):
        boards = [''.join(chars) for chars in itertools.product('.a', repeat=4)]
        boards += ['aabb', 'abab', 'abba', 'baab']
        for board in boards:
            data = (board[:2]+'\n'+board[2:]+'\n'+('!a=0\n' if 'a' in board else '')
                    +('!b=1\n' if 'b' in board else '')).encode()
            expected = {(i, j) for i in range(5) for j in range(5) if (i+j) % 2}
            for i in range(2):
                for j in range(2):
                    label = board[i*2+j]
                    edges = {(2*i, 2*j+1), (2*i+2, 2*j+1), (2*i+1, 2*j), (2*i+1, 2*j+2)}
                    if label == 'a':
                        expected -= edges
                    if label in 'ab':
                        if j < 1 and board[i*2+j+1] == label:
                            expected.discard((2*i+1, 2*j+2))
                        if i < 1 and board[(i+1)*2+j] == label:
                            expected.discard((2*i+2, 2*j+1))
            for name, program in self.programs.items():
                with self.subTest(board=board, name=name):
                    result = subprocess.run([str(program)], input=data, capture_output=True, timeout=5,
                                            env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    actual = {tuple(map(int, match)) for match in re.findall(rb'^EDGE (\d+) (\d+)$',
                                                                            result.stderr, re.M)}
                    self.assertEqual(actual, expected)
                    lines = [line.split() for line in result.stdout.decode().splitlines()
                             if line.strip() and not line.startswith('|')]
                    names = {token.split('|')[-1] for token in lines[0] if token != '|'}
                    self.assertTrue(all(token.split(':')[0] in names for row in lines[1:] for token in row))


if __name__ == '__main__':
    unittest.main()
