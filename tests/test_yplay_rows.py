"""Schensted Y triangles: native rows and direct triangular-majority layers."""
from itertools import product
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def rows(n, bits):
    return [' '*(n-j)+' '.join(bits[j*(j+1)//2:(j+1)*(j+2)//2])+' '*(n-j)
            for j in range(n+1)]


def expected_output(n, bits):
    layers = [[list(bits[j*(j+1)//2:(j+1)*(j+2)//2]) for j in range(n+1)]]
    for level in range(1, n+1):
        previous = layers[-1]
        layers.append([['o' if sum(x == 'o' for x in
                                  (previous[j][i], previous[j+1][i], previous[j+1][i+1])) >= 2 else 'x'
                        for i in range(j+1)] for j in range(n-level+1)])
    result = []
    for row in range(n+1):
        parts = []
        for level in range(row+1):
            j = row-level
            parts.append(' '*(n-level-j)+' '.join(layers[level][j])+' '*(n-level-j))
        result.append('  '.join(parts))
    return '\n'.join(result)+'\n'


class YplayRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'yplay.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/yplay.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = cls.work/'yplay'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_triangle(self, n, bits, newline='\n'):
        data = newline.join(rows(n, bits))+newline
        result = subprocess.run([str(self.program)], input=data, text=True,
                                capture_output=True, timeout=10)
        self.assertNotIn('runtime error', result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_maximum_row_terminator(self):
        n = 100
        self.run_triangle(n, 'x'*((n+1)*(n+2)//2))


if __name__ == '__main__':
    unittest.main()
