"""BUG-073: complete Narayana histograms and small ordered-tree bijections."""
from functools import lru_cache
import math
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'programs/programs/propp.w'


@lru_cache(None)
def binary_shapes(n):
    if not n:
        return (None,)
    return tuple((left, right) for size in range(n)
                 for left in binary_shapes(size) for right in binary_shapes(n - 1 - size))


def ordered_shapes(n):
    def visit(word, opened, closed):
        if closed == n - 1:
            stack = [[]]
            for char in word:
                if char == '(':
                    child = []
                    stack[-1].append(child)
                    stack.append(child)
                else:
                    stack.pop()
            def freeze(tree):
                return tuple(map(freeze, tree))
            yield freeze(stack[0])
        else:
            if opened < n - 1:
                yield from visit(word + '(', opened + 1, closed)
            if closed < opened:
                yield from visit(word + ')', opened, closed + 1)
    return set(visit('', 0, 0))


class ProppCounts(unittest.TestCase):
    def test_complete_counts_and_small_bijection_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in range(2, 12):
                with self.subTest(n=n):
                    text = SOURCE.read_text().replace('@d nodes 17', f'@d nodes {n}')
                    text = text.replace('@d vbose 0', f'@d vbose {int(n <= 7)}')
                    text = text.replace('main()', 'int main()')
                    source = Path(tmp) / 'propp.w'
                    generated = source.with_suffix('.c')
                    program = source.with_suffix('')
                    source.write_text(text)
                    subprocess.run(['ctangle', str(source), '-', str(generated)], capture_output=True, check=True)
                    subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                    '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                                    str(generated), '-o', str(program)], capture_output=True, check=True)
                    result = subprocess.run([str(program)], capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(result.stderr, b'')
                    self.assertNotIn(b'Mismatch', result.stdout)
                    counts = {int(k): int(count) for count, k in re.findall(
                        rb'Altogether (\d+) cases? with (\d+) nodes? at odd levels.', result.stdout)}
                    expected = {k: math.factorial(n - 1) * math.factorial(n - 2) //
                                (math.factorial(k) * math.factorial(k - 1) *
                                 math.factorial(n - k) * math.factorial(n - k - 1))
                                for k in range(1, n)}
                    self.assertEqual(counts, expected)
                    if n <= 7:
                        binaries, trees = [], []
                        for line in result.stdout.decode().splitlines():
                            if ' -> ' not in line:
                                continue
                            b, t = line.split(' -> ')
                            left, right = [[0] + [int(c, 36) for c in part] for part in b.split('|')]
                            child, sibling = [[0] + [int(c, 36) for c in part] for part in t.split('|')]
                            seen = set()
                            def binary(v):
                                if not v:
                                    return None
                                self.assertNotIn(v, seen)
                                seen.add(v)
                                return binary(left[v]), binary(right[v])
                            binaries.append(binary(1))
                            self.assertEqual(len(seen), n - 1)
                            seen = set()
                            def tree(v):
                                self.assertNotIn(v, seen)
                                seen.add(v)
                                answer = []
                                w = child[v]
                                while w:
                                    answer.append(tree(w))
                                    w = sibling[w]
                                return tuple(answer)
                            trees.append(tree(n))
                            self.assertEqual(len(seen), n)
                        self.assertEqual(set(binaries), set(binary_shapes(n - 1)))
                        self.assertEqual(set(trees), ordered_shapes(n))
                        self.assertEqual(len(trees), len(set(trees)))
                        self.assertEqual(len(binaries), len(set(binaries)))


if __name__ == '__main__':
    unittest.main()
