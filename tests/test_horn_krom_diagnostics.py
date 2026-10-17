"""Verbose forcing diagnostics and complete small Horn/Krom orbit families."""
from functools import lru_cache
from itertools import combinations, permutations
from math import factorial
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/programs'


@lru_cache(None)
def permutation_actions(n):
    return tuple(tuple(sum(1 << perm[i] for i in range(n) if subset & (1 << i))
                       for subset in range(1 << n)) for perm in permutations(range(n)))


def transform(family, action):
    return sum(1 << action[subset] for subset in range(len(action)) if family & (1 << subset))


@lru_cache(None)
def families(n, kind):
    nn = 1 << n
    valid = set()
    for mask in range(1 << (nn-1 if kind == 'horn' else nn)):
        if kind == 'horn':
            mask |= 1 << (nn-1)
        members = [subset for subset in range(nn) if mask & (1 << subset)]
        if kind == 'horn':
            closed = all(mask & (1 << (a & b)) for a, b in combinations(members, 2))
        else:
            closed = all(mask & (1 << ((a & b) | (a & c) | (b & c)))
                         for a, b, c in combinations(members, 3))
        if closed:
            valid.add(mask)
    return valid


class HornKromDiagnostics(unittest.TestCase):
    def test_verbose_forcings_and_complete_families(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for n in [3, 4]:
                for kind in ['horn', 'krom']:
                    text = (SOURCES/'horn-count.w').read_text()
                    text = text.replace('@d n 5\n', f'@d n {n}\n')
                    text = text.replace('@d nfactorial 120\n', f'@d nfactorial {factorial(n)}\n')
                    source, generated, program = [work/(f'{kind}{n}'+suffix) for suffix in ['.w', '.c', '']]
                    source.write_text(text)
                    change = str(SOURCES/'krom-count.ch') if kind == 'krom' else '-'
                    subprocess.run(['ctangle', str(source), change, str(generated)], check=True, capture_output=True)
                    compiled = subprocess.run(['gcc', '-std=gnu99', '-O1', '-Wno-implicit-int',
                                               '-Werror=format', str(generated), '-o', str(program)],
                                              text=True, capture_output=True)
                    with self.subTest(n=n, kind=kind):
                        self.assertEqual(compiled.returncode, 0, compiled.stderr)
                        result = subprocess.run([str(program)], text=True, capture_output=True, timeout=15)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stderr, '')
                        self.assertNotIn('error:', result.stdout)
                        level, forcings = None, 0
                        for line in result.stdout.splitlines():
                            entering = re.match(r'Entering level ([0-9a-f]+)', line)
                            if entering:
                                level = int(entering[1], 16)
                            forcing = re.match(r' f\[([0-9a-f]+)\]=1 will force f\[([0-9a-f]+)\]=0', line)
                            if forcing:
                                before, after = (int(x, 16) for x in forcing.groups())
                                self.assertEqual(before, level)
                                self.assertTrue(before < after < (1 << n))
                                forcings += 1
                        self.assertGreater(forcings, 0)
                        expected = families(n, kind)
                        actions = permutation_actions(n)
                        expected_orbits = {min(transform(mask, action) for action in actions) for mask in expected}
                        implicit = (1 << ((1 << n)-1)) if kind == 'horn' else 0
                        actual = {min(transform(implicit, action) for action in actions)}
                        rows = re.findall(r'(?m)^\d+:((?: [0-9a-f]+)*) \((\d+) auts?\)$', result.stdout)
                        for members, auts in rows:
                            mask = sum(1 << int(subset, 16) for subset in members.split())
                            if kind == 'horn':
                                mask |= implicit
                            self.assertIn(mask, expected)
                            images = [transform(mask, action) for action in actions]
                            representative = min(images)
                            self.assertNotIn(representative, actual)
                            actual.add(representative)
                            self.assertEqual(int(auts), images.count(mask))
                        self.assertEqual(actual, expected_orbits)
                        self.assertIn(f'Altogether {len(expected_orbits)} solutions (reduced from {len(expected)}).', result.stdout)


if __name__ == '__main__':
    unittest.main()
