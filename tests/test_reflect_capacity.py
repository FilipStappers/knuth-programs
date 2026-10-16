"""B046: one-based permutation capacity and small commutation classes."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def representatives(n):
    def visit(p, word):
        if p == tuple(range(n)):
            yield word
        for i in range(n-1):
            if p[i] > p[i+1]:
                q = list(p)
                q[i], q[i+1] = q[i+1], q[i]
                yield from visit(tuple(q), word+(i,))
    remaining = set(visit(tuple(range(n-1, -1, -1)), ()))
    answer = set()
    while remaining:
        start = min(remaining)
        group, todo = {start}, [start]
        while todo:
            word = todo.pop()
            for i in range(len(word)-1):
                if abs(word[i]-word[i+1]) > 1:
                    other = word[:i]+(word[i+1], word[i])+word[i+2:]
                    if other not in group:
                        group.add(other)
                        todo.append(other)
        answer.add(max(group))
        remaining -= group
    return answer


class ReflectionCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def build(self, stripped, initialize_only=False):
        text = (ROOT/'programs/programs/reflect.w').read_text()
        if initialize_only:
            old = '  @<Initialize@>;'
            self.assertEqual(text.count(old), 1)
            text = text.replace(old, old+'''
  for (j=1;j<=n;j++) if (a[j]!=n+1-j) return 2;
  if (k!=n*(n-1)/2) return 3;
  return 0; /* observe initialization without enumerating B_10 */
''')
        source = self.work/'reflect.w'
        source.write_text(text)
        generated = self.work/'reflect.c'
        change = str(ROOT/'programs/programs/reflect.ch') if stripped else '-'
        subprocess.run(['ctangle', str(source), change, str(generated)],
                       check=True, capture_output=True)
        program = self.work/('stripped' if stripped else 'base')
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-include', 'stdlib.h',
                        '-O1', '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(program)], check=True, capture_output=True)
        return program

    def test_n10_initialization_in_base_and_stripped_variant(self):
        for stripped in [False, True]:
            with self.subTest(stripped=stripped):
                result = subprocess.run([str(self.build(stripped, True)), '10'],
                                        capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_small_complete_enumerations_preserve_commutation_classes(self):
        for stripped in [False, True]:
            program = self.build(stripped)
            for n in range(2, 6):
                with self.subTest(stripped=stripped, n=n):
                    expected = representatives(n)
                    result = subprocess.run([str(program), str(n)],
                                            capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(int(re.search(rb'B=(\d+)', result.stdout)[1]), len(expected))
                    if not stripped:
                        words = {tuple(map(int, re.match(rb'^\d+', line)[0].decode()))
                                 for line in result.stdout.splitlines() if re.match(rb'^\d+', line)}
                        self.assertEqual(words, expected)


if __name__ == '__main__':
    unittest.main()
