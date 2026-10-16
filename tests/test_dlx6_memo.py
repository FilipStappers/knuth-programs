"""B049: dirty allocator and independent expanded memoized-cover families."""
import itertools
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def subsets(rows, primary):
    result = set()
    for mask in range(1 << len(rows)):
        occurrences = {}
        chosen = []
        for i, row in enumerate(rows):
            if mask >> i & 1:
                chosen.append(i+1)
                for token in row:
                    name, _, color = token.partition(':')
                    occurrences.setdefault(name, []).append(color)
        if any(len(occurrences.get(p, [])) != 1 for p in primary):
            continue
        if any(len(colors) > 1 and ('' in colors or len(set(colors)) > 1)
               for name, colors in occurrences.items() if name not in primary):
            continue
        result.add(tuple(chosen))
    return result


def expanded_zdd(output):
    nodes, root = {}, None
    for line in output.decode().splitlines():
        match = re.fullmatch(r'([0-9a-f]+): \(~(\d+)\?([0-9a-f]+):([0-9a-f]+)\)', line)
        if match:
            root = int(match[1], 16)
            nodes[root] = (int(match[2]), int(match[3], 16), int(match[4], 16))
    memo = {0: set(), 1: {()}}
    def visit(k):
        if k not in memo:
            value, low, high = nodes[k]
            memo[k] = visit(low) | {tuple(sorted(s+((value,) if value else ())))
                                     for s in visit(high)}
        return memo[k]
    assert root is not None, output
    return visit(root)


class DlxMemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for memoized-cover checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = []
        text = (ROOT/'programs/programs/dlx6.w').read_text()
        for key, value in [('max_level', 64), ('max_cols', 128), ('max_nodes', 8192),
                           ('max_inx', 2048), ('max_cache', 65536), ('loghashsize', 12)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        source = cls.work/'memo.w'
        source.write_text(text)
        for mode in ['base', 'noMRV']:
            generated = cls.work/'memo.c'
            change = '-' if mode == 'base' else str(ROOT/'programs/programs/dlx6-noMRV.ch')
            subprocess.run(['ctangle', str(source), change, str(generated)],
                           check=True, capture_output=True)
            # Only the source's hash-sized malloc request receives dirty bytes.
            # Runtime allocation and every other requested size retain libc behavior.
            driver = cls.work/'driver.c'
            driver.write_text(r'''
#include <stdlib.h>
#include <string.h>
static void *dirty_malloc(size_t n);
#define malloc dirty_malloc
#include "memo.c"
#undef malloc
static void *dirty_malloc(size_t n) {
  void *p=malloc(n);
  if (p && n==hashsize*sizeof(hashentry)) memset(p,0xa5,n);
  return p;
}
''')
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-I'+sgb,
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(driver), str(Path(sgb)/'gb_flip.c'), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_family(self, rows, primary, seed=None):
        secondary = sorted({token.split(':')[0] for row in rows for token in row}-set(primary))
        data = (' '.join(primary)+(' | '+' '.join(secondary) if secondary else '')+'\n'+
                ''.join(' '.join(row)+'\n' for row in rows)).encode()
        expected = subsets(rows, primary)
        for program in self.programs:
            args = ['m1', 'v1']+(['s'+str(seed)] if seed is not None else [])
            result = subprocess.run([str(program), *args], input=data,
                                    capture_output=True, timeout=5,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(expanded_zdd(result.stdout), expected)
            self.assertEqual(int(re.search(rb'Altogether (\d+) solutions?', result.stderr)[1]), len(expected))

    def test_dirty_hash_storage_does_not_manufacture_a_cache_entry(self):
        self.check_family([('A',), ('B',)], ['A', 'B'])

    def test_all_64_uncolored_families_expand_to_exact_option_subsets(self):
        options = [('A',), ('B',), ('A', 'B'), ('A', 'X'), ('B', 'X'), ('A', 'B', 'X')]
        for mask in range(64):
            self.check_family([r for i, r in enumerate(options) if mask >> i & 1], ['A', 'B'])

    def test_seeded_colored_families_preserve_every_option_identity(self):
        rng = random.Random(49042)
        for case in range(40):
            rows = []
            for _ in range(rng.randrange(1, 10)):
                row = [p for p in ['A', 'B', 'C'] if rng.randrange(2)]
                if not row:
                    row = [rng.choice(['A', 'B', 'C'])]
                row += [name+color for name in ['X', 'Y']
                        if (color := rng.choice([None, '', ':a', ':b'])) is not None]
                rows.append(tuple(row))  # duplicate rows are distinct option identities
            self.check_family(rows, ['A', 'B', 'C'], case+1)


if __name__ == '__main__':
    unittest.main()
