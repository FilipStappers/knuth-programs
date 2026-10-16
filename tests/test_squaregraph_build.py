"""BUG-021: original build and bounded independent chord-matching families."""
import itertools
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/squaregraph.w'


def matchings(points):
    if not points:
        yield []
        return
    a, *rest = points
    for b in rest:
        for tail in matchings([v for v in rest if v != b]):
            yield [(a, b), *tail]


def reference(p):
    families = {}
    for pairs in matchings(list(range(2*p))):
        crossing = {(i, j) for i, (a, b) in enumerate(pairs)
                    for j, (c, d) in enumerate(pairs) if i < j and
                    ((a < c < b < d) or (c < a < d < b))}
        if any((i, j) in crossing and (i, k) in crossing and (j, k) in crossing
               for i, j, k in itertools.combinations(range(p), 3)):
            continue
        seen = {0}
        while True:
            more = {v for u, v in crossing if u in seen}
            more |= {u for u, v in crossing if v in seen}
            if more <= seen:
                break
            seen |= more
        if len(seen) != p:
            continue
        delta = [0]*(2*p)
        for a, b in pairs:
            delta[a], delta[b] = b-a, 2*p-(b-a)
        backward = [2*p-d for d in reversed(delta)]
        canonical = min(tuple(word[k:]+word[:k]) for word in [delta, backward]
                        for k in range(2*p))
        x = len(crossing)
        families[canonical] = (1+p+x, p+2*x, 1-p+x, x)
    return families


class SquaregraphBuild(unittest.TestCase):
    def test_default_source_builds_and_bounded_families_match_matchings(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            for bound in [10, 5]:
                source = SOURCE
                if bound == 5:
                    text = SOURCE.read_text()
                    assert text.count('@d maxp 10 ') == 1
                    source = work/'small.w'
                    source.write_text(text.replace('@d maxp 10 ', '@d maxp 5 '))
                generated = work/f'graph{bound}.c'
                program = work/f'graph{bound}'
                subprocess.run(['ctangle', str(source), '-', str(generated)],
                               check=True, capture_output=True)
                result = subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int',
                                         '-Wno-implicit-function-declaration', '-O1',
                                         '-fsanitize=address,undefined,bounds',
                                         '-fno-sanitize-recover=all', str(generated),
                                         '-o', str(program)], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                if bound == 10:
                    continue  # Link the original capacity; do not enumerate its huge domain.
                result = subprocess.run([str(program)], capture_output=True, timeout=5,
                                        env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                actual = {}
                for line in result.stdout.decode().splitlines():
                    m = re.fullmatch(r'\d+: ([\d ]+) \(\d+R?\), (\d+) v, (\d+) e, (\d+) iv, (\d+) sq', line)
                    if m:
                        delta = tuple(map(int, m[1].split()))
                        self.assertNotIn(delta, actual)
                        actual[delta] = tuple(map(int, m.groups()[1:]))
                expected = {}
                for p in range(3, 6):
                    expected.update(reference(p))
                self.assertEqual(actual, expected)
                self.assertEqual(len(actual), 12)


if __name__ == '__main__':
    unittest.main()
