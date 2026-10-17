"""Exact distinct-pair Ulam prefixes across residue and compression choices."""
from collections import Counter
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def ulam_numbers(n):
    terms = [1, 2]
    pairs = Counter({3: 1})
    candidate = 3
    while len(terms) < n:
        while pairs[candidate] != 1:
            candidate += 1
        for term in terms:
            pairs[candidate+term] += 1
        terms.append(candidate)
        candidate += 1
    return terms[:n]


class UlamGibbs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.expected = ulam_numbers(1000)
        cls.program = cls.work/'ulam-gibbs'
        generated = cls.work/'ulam-gibbs.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/ulam-gibbs.w'),
                        '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int',
                        str(generated), '-lm', '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_prefix(self, count, options):
        result = subprocess.run([str(self.program), 'v0', 'm1', *options, str(count)],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        pairs = [(int(index), int(value)) for index, value in
                 re.findall(r'(?m)^U(\d+)=(\d+)$', result.stdout)]
        self.assertEqual([index for index, _ in pairs], list(range(1, count+1)), result.stderr)
        self.assertEqual([value for _, value in pairs], self.expected[:count])

    def test_equal_addend_regression(self):
        self.assertEqual(self.expected[629], 7459)
        self.assertFalse(any(a+b == 7446 for i, a in enumerate(self.expected[:629])
                             for b in self.expected[i+1:629]))
        self.run_prefix(650, ['p22', 'q9', 'w5000'])

    def test_residue_and_compression_neighbors(self):
        for residue in [[], ['p22', 'q9'], ['p540', 'q221'], ['p5', 'q2'], ['p3', 'q1']]:
            for compression in [[], ['b4', 'B4']]:
                with self.subTest(residue=residue, compression=compression):
                    self.run_prefix(1000, [*residue, *compression, 'w5000'])


if __name__ == '__main__':
    unittest.main()
