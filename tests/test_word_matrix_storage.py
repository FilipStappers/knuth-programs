"""One-based word matrix storage, including exact-capacity ordinary dictionaries."""
from itertools import product
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/back-mxn-words-new.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class WordMatrixStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for capacity in [2, 20000]:
            source, generated, program = [cls.work/(str(capacity)+s) for s in ['.w', '.c', '']]
            source.write_text(SOURCE.read_text().replace('@d maxmwds 20000 ', f'@d maxmwds {capacity} '))
            subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[capacity] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rectangles(self, capacity, rows, columns):
        mfile, nfile = self.work/'mwords', self.work/'nwords'
        mfile.write_text(''.join(word+'\n' for word in rows))
        nfile.write_text(''.join(word+'\n' for word in columns))
        return subprocess.run([str(self.programs[capacity]), str(mfile), str(nfile)],
                              capture_output=True, timeout=10, env=ENV)

    def test_exact_default_capacity(self):
        result = self.rectangles(20000, ['aa']*20000, ['zz'])
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'read 20000 words', result.stderr)
        self.assertIn(b'Altogether 0 solutions', result.stderr)

    def test_reduced_capacity_and_independent_rectangle_sets(self):
        for words in [['aa'], ['ab', 'ba']]:
            result = self.rectangles(2, words, words)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            actual = set(re.findall(rb'(?m)^\d+: ([a-z]+) ([a-z]+) \(', result.stdout))
            expected = {tuple(word.encode() for word in matrix) for matrix in product(words, repeat=2)
                        if all(''.join(word[j] for word in matrix) in words for j in range(2))}
            self.assertEqual(actual, expected)
        words = ['aa', 'ab', 'ba', 'bb']
        result = self.rectangles(20000, words, words)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        actual = set(re.findall(rb'(?m)^\d+: ([a-z]+) ([a-z]+) \(', result.stdout))
        self.assertEqual(actual, set(product([word.encode() for word in words], repeat=2)))


if __name__ == '__main__':
    unittest.main()
