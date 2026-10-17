"""B029: native halftone pixels, byte padding and GraphBase image ABI."""
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/togpap.w'
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')
M, N = 360, 250


def ordered_board():
    board = [[0]*8 for _ in range(8)]
    di, dj = [0, 1, 0, 1], [0, 1, 1, 0]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                x, y = 4*di[k]+2*di[j]+di[i]+2, 4*dj[k]+2*dj[j]+dj[i]+2
                board[7-(y % 8)][x % 8] = 16*i+4*j+k
    return board


def sharpen(image):
    return [[min(1., max(0., 9*image[i][j]-sum(image[ii][jj]
              for ii in range(i-1, i+2) for jj in range(j-1, j+2) if (ii, jj) != (i, j))))
             for j in range(1, N+1)] for i in range(1, M+1)]


def ordered_pixels(image, sharp):
    values = sharpen(image) if sharp else [row[1:N+1] for row in image[1:M+1]]
    board = ordered_board()
    return [[int(value >= (board[i % 8][j % 8]+.5)/64)
             for j, value in enumerate(row)] for i, row in enumerate(values)]


def sphere():
    image = [[0.]*(N+2) for _ in range(M+2)]
    for i in range(1, M+1):
        for j in range(1, N+1):
            x, y = (i-120.)/111.5, (j-120.)/111.5
            image[i][j] = ((1500.*i+j*j)/1000000. if x*x+y*y >= 1 else
                           (9+x-4*y-8*math.sqrt(1-x*x-y*y))/18.)
    return image


@unittest.skipUnless((GRAPHBASE/'gb_lisa.c').exists(), 'GraphBase sources required')
class TogpapPixels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'togpap.c'
        cls.program = cls.work/'togpap'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)], check=True, capture_output=True)
        objects = []
        for name in ['gb_graph', 'gb_lisa', 'gb_io', 'gb_flip']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-w', '-I'+str(GRAPHBASE),
                            '-c', str(GRAPHBASE/(name+'.c')), '-o', str(obj)], check=True, capture_output=True)
            objects.append(str(obj))
        subprocess.run(['gcc', '-std=gnu89', '-O1', '-fcommon', '-I'+str(GRAPHBASE),
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), *objects, '-lm', '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_image(self, image, sharp, method):
        result = subprocess.run([str(self.program), str(image), str(sharp), str(method)],
                                cwd=self.work, capture_output=True, timeout=10, env=ENV)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        rows = result.stdout.split(b'imagemask\n')[1].split(b'%%EOF')[0].splitlines()
        self.assertEqual(len(rows), M)
        self.assertTrue(all(len(row) == 64 for row in rows))
        bits = [[int(bit) for byte in bytes.fromhex(row.decode()) for bit in f'{byte:08b}']
                for row in rows]
        self.assertTrue(all(not any(row[N:]) for row in bits), 'padding must be zero')
        return [row[:N] for row in bits], result.stderr.decode()

    def test_sphere_all_methods_have_bounded_zero_padding(self):
        for sharp in [0, 1]:
            for method in range(1, 6):
                with self.subTest(sharp=sharp, method=method):
                    self.run_image(2, sharp, method)

    def test_sphere_ordered_pixels(self):
        for sharp in [0, 1]:
            pixels, _ = self.run_image(2, sharp, 2)
            self.assertEqual(pixels, ordered_pixels(sphere(), sharp))


if __name__ == '__main__':
    unittest.main()
