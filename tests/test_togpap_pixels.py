"""B029: native halftone pixels, byte padding and GraphBase image ABI."""
import math
import os
from pathlib import Path
import re
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


def smooth_reference(image, sharp, board):
    values = sharpen(image) if sharp else [row[1:N+1] for row in image[1:M+1]]
    def rank(i, j):
        return board[i % 8][j % 8]
    pixels = sorted((rank(i, j), i, j) for i in range(M) for j in range(N))
    leakage = 0.
    for level, i, j in pixels:
        bit = int(values[i][j] >= .5/(32-level))
        error = values[i][j]-bit
        values[i][j] = bit
        neighbors = [(i+di, j+dj) for dj in range(-3, 4)
                     for di in range(-3+abs(dj), 5-abs(dj)) if rank(i+di, j+dj) > level]
        assert len(neighbors) == 31-level
        for ii, jj in reversed(neighbors):
            share = error/len(neighbors)
            if 0 <= ii < M and 0 <= jj < N:
                values[ii][jj] += share
            else:
                leakage += abs(share)
    return values, leakage


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

    def test_lisa_ordered_pixels_from_direct_data_decoder(self):
        shutil.copyfile(GRAPHBASE/'lisa.dat', self.work/'lisa.dat')
        alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_^~&@,;.:?!%#$+-*/|\\<=>()[]{}`\'" \n'
        records = [line for line in (GRAPHBASE/'lisa.dat').read_text().splitlines()
                   if not line.startswith('*')]
        self.assertEqual(len(records), 1800)
        image = [[0.]*(N+2) for _ in range(M+2)]
        for i in range(M):
            chars = ''.join(records[5*i:5*i+5])
            self.assertEqual(len(chars), 313)
            values = []
            for start in range(0, len(chars), 5):
                value = 0
                group = chars[start:start+5]
                for char in group:
                    value = value*85+alphabet.index(char)
                values.extend(value.to_bytes(4 if len(group) == 5 else 2, 'big'))
            self.assertEqual(len(values), N)
            image[i+1][1:N+1] = [(1-(value+.5)/256)**2 for value in values]
        for sharp in [0, 1]:
            pixels, _ = self.run_image(1, sharp, 2)
            expected = ordered_pixels(image, sharp)
            mismatches = sum(a != b for row, other in zip(pixels, expected)
                             for a, b in zip(row, other))
            self.assertEqual(mismatches, 0, f'sharp={sharp}, incorrect image pixels')

    def test_smooth_pixels_and_physical_boundary_loss(self):
        for sharp in [0, 1]:
            pixels, diagnostic = self.run_image(2, sharp, 4)
            lines = diagnostic.splitlines()
            start = next(i for i, line in enumerate(lines)
                         if len(line.split()) == 8 and all(x.isdigit() for x in line.split()))
            board = [list(map(int, line.split())) for line in lines[start:start+8]]
            self.assertEqual(sorted(x for row in board for x in row), sorted(list(range(32))*2))
            expected, loss = smooth_reference(sphere(), sharp, board)
            self.assertEqual(pixels, expected)
            reported = float(re.search(r'Total leakage at boundaries: (\S+)', diagnostic)[1])
            self.assertAlmostEqual(reported, loss, places=7)


if __name__ == '__main__':
    unittest.main()
