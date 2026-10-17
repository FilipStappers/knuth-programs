"""BUG-059: complete binary-palindromic square families across bit 31."""
import math
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'programs/programs/squarepal.w'


class SquarepalMasks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        generated = Path(cls.temp.name) / 'squarepal.c'
        cls.program = generated.with_suffix('')
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)],
                       capture_output=True, check=True)
        subprocess.run(['gcc', '-O1', '-fsanitize=undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.program)],
                       capture_output=True, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_families_through_36_bits(self):
        for n in range(15, 37):
            with self.subTest(n=n):
                result = subprocess.run([str(self.program), str(n)],
                                        capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stderr, b'')
                actual = []
                for line in result.stdout.decode().splitlines()[1:]:
                    root, square = (int(x, 16) for x in line.split('^2='))
                    self.assertEqual(root * root, square)
                    self.assertEqual(square.bit_length(), n)
                    actual.append(root)
                expected = set()
                half = (n + 1) // 2
                for prefix in range(1 << (half - 1), 1 << half):
                    left = f'{prefix:b}'
                    word = left + (left[:-1] if n % 2 else left)[::-1]
                    square = int(word, 2)
                    root = math.isqrt(square)
                    if root * root == square:
                        expected.add(root)
                self.assertEqual(set(actual), expected)
                self.assertEqual(len(actual), len(expected))


if __name__ == '__main__':
    unittest.main()
