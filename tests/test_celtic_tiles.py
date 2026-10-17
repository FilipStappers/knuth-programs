"""Celtic converter: complete legal tile alphabet and closed-layout checks."""
from itertools import combinations
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/celtic-paths.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')
FIXTURE = [['35  ', '3547', '3657', '57  '],
           ['13  ', '1427', '0316', '17  '],
           ['    ', '25  ', '03  ', '57  '],
           ['    ', '13  ', '37  ', '17  ']]


def legal_tiles():
    edges = [e for e in combinations(range(8), 2)
             if e[1]-e[0] not in (1, 7) and any(k % 2 for k in e)]
    return {(), *((e,) for e in edges),
            *((a, b) for a, b in combinations(edges, 2) if len(set(a+b)) == 4)}


def serialize(rows):
    return ''.join(' '.join(row)+'.\n' for row in rows)


def validate(rows):
    """Check legal segments and equality at every shared/boundary endpoint."""
    masks = []
    for row in rows:
        maskrow = []
        for tile in row:
            digits = tile.strip()
            edges = tuple(tuple(map(int, digits[k:k+2])) for k in range(0, len(digits), 2))
            assert edges in legal_tiles(), tile
            maskrow.append(sum(1 << k for edge in edges for k in edge))
        masks.append(maskrow)
    m, n = len(rows), len(rows[0])
    for i in range(m+1):
        for j in range(n):
            above, below = (masks[i-1][j] if i else 0), (masks[i][j] if i < m else 0)
            assert all((above >> a & 1) == (below >> b & 1)
                       for a, b in [(4, 2), (5, 1), (6, 0)])
    for i in range(m):
        for j in range(n+1):
            left, right = (masks[i][j-1] if j else 0), (masks[i][j] if j < n else 0)
            assert all((left >> a & 1) == (right >> b & 1)
                       for a, b in [(2, 0), (3, 7), (4, 6)])


class CelticTiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.program = cls.work/'celtic'
        generated = cls.work/'celtic.c'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, text):
        return subprocess.run([str(self.program)], input=text.encode(), capture_output=True,
                              timeout=5, env=ENV)

    def test_complete_unique_legal_mapping(self):
        assignments = re.findall(r'codetable\[(0x[0-9a-fA-F]+|0)\]=(0[0-7]*);?', SOURCE.read_text())
        keys = [int(key, 0) for key, _ in assignments]
        expected = {int(''.join(str(k) for e in tile for k in e).ljust(4, '0'), 16)
                    for tile in legal_tiles()}
        self.assertEqual(len(expected), 62)
        self.assertEqual(len(keys), len(set(keys)), 'duplicate tile mapping')
        self.assertEqual(set(keys), expected)
        self.assertEqual(len({int(code, 8) for _, code in assignments}), 62)

    def test_closed_layout_with_missing_tile(self):
        validate(FIXTURE)
        result = self.solve(serialize(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertRegex(result.stdout, rb'[+-]27[4-7]')
        for rows in [[['    ']], [['35  ', '57  '], ['13  ', '17  ']]]:
            validate(rows)
            result = self.solve(serialize(rows))
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_row_capacity_rejects_before_store(self):
        result = self.solve(serialize([['    ']]*101))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertIn(b'rows', result.stderr)

    def test_records_and_column_capacity(self):
        for text in ['    .extra\n', '    .\0\n', ' '*505+'.\n',
                     ' '*10000+'\n', '    \n', '   .\n', '    .\n    ',
                     '    .\n         .\n', '    .\n\n', '    .    .\n',
                     '    !    .\n', 'xxxx.\n', '9999.\n']:
            with self.subTest(text=text[:40]):
                result = self.solve(text)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertFalse(result.stdout)

    def test_supported_dimensions_and_line_endings(self):
        for m, n in [(1, 100), (100, 1), (100, 100)]:
            result = self.solve(serialize([['    ']*n]*m))
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn(f'{m} rows and {n} columns'.encode(), result.stderr)
        expected = self.solve(serialize(FIXTURE)).stdout
        for text in [serialize(FIXTURE).rstrip('\n'), serialize(FIXTURE).replace('\n', '\r\n')]:
            result = self.solve(text)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout, expected)

    def test_input_read_error_rejects(self):
        descriptor = os.open(self.work, os.O_RDONLY)
        try:
            result = subprocess.run([str(self.program)], stdin=descriptor,
                                    capture_output=True, timeout=5, env=ENV)
        finally:
            os.close(descriptor)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'read standard input', result.stderr)


if __name__ == '__main__':
    unittest.main()
