"""BUG-060: gap admission precedes statistics in both Ulam word sizes."""
from collections import Counter
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_ulam_gibbs import ulam_numbers

ROOT = Path(__file__).resolve().parents[1] / 'programs/programs'


class UlamGapCapacity(unittest.TestCase):
    def test_short_histograms_and_exact_neighbor_sequences(self):
        expected = ulam_numbers(1000)
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            for longword in [False, True]:
                for gsize, nsize in [(1, 8), (2, 8), (1000, 8), (1000, 32), (1000, 128)]:
                    with self.subTest(longword=longword, gsize=gsize, nsize=nsize):
                        text = (ROOT / 'ulam.w').read_text()
                        text = text.replace('@d gsize 1000', f'@d gsize {gsize}')
                        text = text.replace('@d nsize (1<<14)', f'@d nsize {nsize}')
                        text = text.replace('@d m 10000', '@d m 1').replace('main()', 'int main()')
                        source = work / 'ulam.w'
                        generated = source.with_suffix('.c')
                        program = source.with_suffix('')
                        source.write_text(text)
                        subprocess.run(['ctangle', str(source),
                                        str(ROOT / 'ulam-longlong.ch') if longword else '-', str(generated)],
                                       capture_output=True, check=True)
                        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=undefined,bounds',
                                        '-fno-sanitize-recover=all', str(generated), '-o', str(program)],
                                       capture_output=True, check=True)
                        result = subprocess.run([str(program)], capture_output=True, timeout=10)
                        self.assertNotIn(b'runtime error', result.stderr)
                        if gsize < 3:
                            self.assertNotEqual(result.returncode, 0)
                            self.assertIn(b'Unexpectedly large gap', result.stderr)
                            continue
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        self.assertEqual(result.stderr, b'')
                        limit = nsize * (64 if longword else 32)
                        terms = [x for x in expected if x < limit]
                        self.assertLess(limit, expected[-1])
                        printed = [(int(n), int(value)) for n, value in
                                   re.findall(rb'(?m)^U_(\d+)=(\d+) is', result.stdout)]
                        self.assertEqual(printed, list(enumerate(terms[2:], 3)))
                        self.assertIn(f'There are {len(terms)} Ulam numbers less than {limit}.'.encode(),
                                      result.stdout)
                        gaps = Counter(b - a for a, b in zip(terms[1:], terms[2:]))
                        rows = re.findall(rb'gap (\d+) occurred (\d+) times?, last was (\d+)', result.stdout)
                        self.assertEqual({int(g): int(count) for g, count, _ in rows}, dict(gaps))
                        for gap, _, last in rows:
                            self.assertEqual(int(last), max(b for a, b in zip(terms[1:], terms[2:])
                                                            if b - a == int(gap)))


if __name__ == '__main__':
    unittest.main()
