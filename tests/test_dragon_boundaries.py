"""Dragon calculator table boundaries and independent Gaussian congruence checks."""
from itertools import product
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/dragon-calc.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class DragonBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.program = cls.work/'dragon'
        generated = cls.work/'dragon.c'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu89', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def calculate(self, commands):
        return subprocess.run([str(self.program)], input=commands.encode(), capture_output=True,
                              cwd=self.work, timeout=10, env=ENV)

    def test_zero_modulus_rejects_and_recovers(self):
        result = self.calculate('p0123\nc1,0\np0\nc1,0\nq\n')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'zero', result.stdout.lower())
        self.assertRegex(result.stdout, rb'1,0 is \d_\d')

    def test_supported_congruence_matches_gaussian_lattice(self):
        tiles = [(x, y) for x, y in product(range(-3, 4), repeat=2) if (x+y) % 2]
        for path in ['0', '01', '010', '01012', '030', '010101', '01210']:
            result = self.calculate('p'+path+'\n'+''.join(f'c{x},{y}\n' for x, y in tiles)+'q\n')
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            answers = re.findall(rb'(-?\d+),(-?\d+) is (\d+)_(\d)', result.stdout)
            self.assertEqual(len(answers), len(tiles))
            classes = {(int(x), int(y)): int(c) for x, y, c, _ in answers}
            steps = [(1, 0), (0, 1), (-1, 0), (0, -1)]
            zx = sum(steps[int(d)][0] for d in path)
            zy = sum(steps[int(d)][1] for d in path)
            a, b = 2*(zx-zy), 2*(zx+zy)
            norm = a*a+b*b
            for first in tiles:
                for second in tiles:
                    x, y = second
                    equivalent = False
                    for _ in range(4):
                        dx, dy = first[0]-x, first[1]-y
                        equivalent |= (dx*a+dy*b) % norm == 0 and (dy*a-dx*b) % norm == 0
                        x, y = -y, x
                    self.assertEqual(classes[first] == classes[second], equivalent,
                                     (path, first, second))


if __name__ == '__main__':
    unittest.main()
