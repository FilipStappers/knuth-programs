"""Young-tableau representation boundaries and complete small group actions."""
from itertools import permutations
from math import factorial, prod
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def partitions(n, maximum=None):
    if not n:
        yield ()
    else:
        for first in range(min(n, maximum or n), 0, -1):
            for tail in partitions(n-first, first):
                yield (first, *tail)


def tableaux(shape):
    hooks = [row-j+sum(other > j for other in shape[i+1:])
             for i, row in enumerate(shape) for j in range(row)]
    return factorial(sum(shape))//prod(hooks)


def multiply(a, b):
    return tuple(tuple(sum(x*y for x, y in zip(row, column)) for column in zip(*b))
                 for row in a)


class StraightenRepresentations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'straighten.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/straighten.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = cls.work/'straighten'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int', '-include', 'stdlib.h',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def representations(self, shape, perms):
        data = ' '.join(map(str, (*shape, 0)))+'\n'
        data += ''.join(' '.join(map(str, perm))+'\n' for perm in perms)
        result = subprocess.run([str(self.program)], input=data, text=True,
                                capture_output=True, timeout=15)
        self.assertNotIn('runtime error', result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        lines = result.stdout.splitlines()
        match = re.match(r'There are (\d+) standard tableaux', lines[0])
        self.assertIsNotNone(match)
        size = int(match[1])
        self.assertEqual(size, tableaux(shape))
        actual = {}
        for start in range(1, len(lines), size+1):
            self.assertTrue(lines[start].startswith('Representation of '))
            perm = tuple(map(int, lines[start].removeprefix('Representation of ').removesuffix(':').split()))
            matrix = tuple(tuple(map(int, line.split())) for line in lines[start+1:start+size+1])
            self.assertEqual(len(matrix), size)
            self.assertTrue(all(len(row) == size for row in matrix))
            actual[perm] = matrix
        self.assertEqual(set(actual), set(perms))
        return actual

    def test_one_row_and_column_at_maximum_size(self):
        n = 100
        identity = tuple(range(1, n+1))
        perms = [identity, identity[::-1], identity[1:]+identity[:1],
                 (n, *identity[1:-1], 1)]
        for i in range(n-1):
            perm = list(identity)
            perm[i], perm[i+1] = perm[i+1], perm[i]
            perms.append(tuple(perm))
        for shape in [(n,), (1,)*n]:
            with self.subTest(shape=shape):
                matrices = self.representations(shape, perms)
                for perm, matrix in matrices.items():
                    inversions = sum(x > y for i, x in enumerate(perm) for y in perm[i+1:])
                    expected = 1 if len(shape) == 1 or inversions % 2 == 0 else -1
                    self.assertEqual(matrix, ((expected,),))

    def test_complete_small_permutation_actions(self):
        for n in range(1, 6):
            perms = list(permutations(range(1, n+1)))
            identity = tuple(range(1, n+1))
            for shape in partitions(n):
                with self.subTest(shape=shape):
                    matrices = self.representations(shape, perms)
                    size = tableaux(shape)
                    self.assertEqual(matrices[identity], tuple(tuple(int(i == j) for j in range(size))
                                                              for i in range(size)))
                    for perm in perms:
                        for i in range(n-1):
                            swap = list(identity)
                            swap[i], swap[i+1] = swap[i+1], swap[i]
                            composed = tuple(swap[x-1] for x in perm)
                            self.assertEqual(multiply(matrices[perm], matrices[tuple(swap)]), matrices[composed])
                        if len(shape) == 1:
                            self.assertEqual(matrices[perm], ((1,),))
                        if shape == (1,)*n:
                            inversions = sum(x > y for i, x in enumerate(perm) for y in perm[i+1:])
                            self.assertEqual(matrices[perm], ((-1 if inversions % 2 else 1,),))


if __name__ == '__main__':
    unittest.main()
