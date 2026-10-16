"""B059: raster width includes dead columns; compare all 2x3 projections."""
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'


class PrepWidth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        # Only relocate the historical shared /tmp/list output into our owned
        # temporary directory. The algorithm and all dimensions are unchanged.
        source = work/'prep.w'
        source.write_text((SOURCES/'sat-tomography-prep.w').read_text().replace(
            '/tmp/list', str(work/'list')))
        cls.programs = {}
        for second in [False, True]:
            generated = work/f'prep{second}.c'
            program = work/f'prep{second}'
            change = str(SOURCES/'sat-tomography-prep-2nd.ch') if second else '-'
            subprocess.run(['ctangle', str(source), change, str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[second] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, matrix, second, newline=True):
        data = '\n'.join(''.join('*' if x else '.' for x in row) for row in matrix)
        if newline:
            data += '\n'
        result = subprocess.run([str(self.programs[second]), str(len(matrix)),
                                 str(len(matrix[0]))], input=data.encode(),
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return dict(line.split('=') for line in result.stdout.decode().splitlines())

    def reference(self, matrix, second):
        m, n = len(matrix), len(matrix[0])
        lines = {}
        for j in range(m):
            lines[f'r{j+1}'] = matrix[j]
        for k in range(n):
            lines[f'c{k+1}'] = [matrix[j][k] for j in range(m)]
        for d in range(1, m+n):
            lines[f'a{d}'] = [matrix[j][d-1-j] for j in range(m) if 0 <= d-1-j < n]
            lines[f'b{d}'] = [matrix[j][j+n-d] for j in range(m) if 0 <= j+n-d < n]
        return {key: str(sum(v))+(','+str(sum(a*b for a, b in zip(v, v[1:])))
                                 if second else '') for key, v in lines.items()}

    def test_dead_final_column_and_all_dead_image(self):
        for matrix in [[[1, 1, 0], [0, 0, 0]], [[0]*3 for _ in range(2)]]:
            for second, newline in itertools.product([False, True], repeat=2):
                with self.subTest(matrix=matrix, second=second, newline=newline):
                    self.assertEqual(self.encode(matrix, second, newline),
                                     self.reference(matrix, second))

    def test_every_two_by_three_image(self):
        for bits in itertools.product([0, 1], repeat=6):
            matrix = [list(bits[:3]), list(bits[3:])]
            for second in [False, True]:
                with self.subTest(bits=bits, second=second):
                    self.assertEqual(self.encode(matrix, second), self.reference(matrix, second))

    def test_maximum_dead_image(self):
        matrix = [[0]*100 for _ in range(100)]
        for second in [False, True]:
            self.assertEqual(self.encode(matrix, second), self.reference(matrix, second))


if __name__ == '__main__':
    unittest.main()
