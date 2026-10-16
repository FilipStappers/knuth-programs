"""B034: diagram arithmetic and reader-state regressions."""
import functools
import os
from collections import Counter
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/bdd-zdd-utils'


class Diagram:
    def __init__(self, zdd):
        self.zdd, self.nodes, self.unique = zdd, {}, {}

    def node(self, variable, low, high):
        if self.zdd and high == 0:
            return low
        if not self.zdd and low == high:
            return low
        key = variable, low, high
        if key not in self.unique:
            pointer = len(self.nodes)+2
            self.unique[key] = pointer
            self.nodes[pointer] = key
        return self.unique[key]

    def write(self, path):
        path.write_text(''.join(f'{p:x}: (~{v}?{low:x}:{high:x})\n'
                                for p, (v, low, high) in sorted(self.nodes.items(),
                                                              key=lambda row: row[1][0])))


class DiagramReaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        cls.generated = {}
        for name in ['zddread-count', 'zddread-gf', 'bddread-gf', 'bddread-count']:
            base = name.split('-')[0]
            literate = cls.work/(base+'.w')
            # Each fixture fits these reduced capacities. No arithmetic changes.
            literate.write_text((SOURCES/(base+'.w')).read_text().replace(
                '@d memsize 40000000', '@d memsize 4096'))
            change = cls.work/(name+'.ch')
            change.write_text((SOURCES/(name+'.ch')).read_text().replace(
                '@d gfsize 85000000', '@d gfsize 65536'))
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(literate), str(change), str(generated)],
                           check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program
            cls.generated[name] = generated

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_reader(self, name, path):
        result = subprocess.run([str(self.programs[name]), str(path)],
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'runtime error', result.stderr)
        return result.stdout.decode()

    def test_exact_carry_boundary_in_count_and_polynomial(self):
        dd = Diagram(True)

        @functools.lru_cache(None)
        def interval(count, variable, bits):
            # Integers 0..count-1 map bijectively to one choice from each pair.
            if count == 0:
                return 0
            if bits == 0:
                return 1
            half = 1 << (bits-1)
            low = interval(min(count, half), variable+2, bits-1)
            high = interval(max(0, count-half), variable+2, bits-1)
            return dd.node(variable, dd.node(variable+1, 0, high), low)

        lower = 1500000000000000000
        upper = 500000000000000000
        root = dd.node(0, dd.node(1, 0, interval(lower, 2, 61)), interval(upper, 2, 61))
        zdd = self.work/'carry.zdd'
        dd.write(zdd)
        bd = Diagram(False)

        @functools.lru_cache(None)
        def convert(pointer, variable):
            if pointer == 0:
                return 0
            if variable == 124:
                return int(pointer == 1)
            rank, low, high = dd.nodes[pointer] if pointer > 1 else (124, 0, 0)
            if variable < rank:
                return bd.node(variable, convert(pointer, variable+1), 0)
            return bd.node(variable, convert(low, variable+1), convert(high, variable+1))

        convert(root, 0)
        bdd = self.work/'carry.bdd'
        bd.write(bdd)
        self.assertLess(max(dd.nodes), 4096)
        self.assertLess(max(bd.nodes), 4096)
        expected = str(lower+upper)
        for name in self.programs:
            if name == 'bddread-count':
                continue  # This reader deliberately rejects counts beyond double precision.
            output = self.run_reader(name, bdd if name.startswith('bdd') else zdd)
            with self.subTest(reader=name):
                if name.endswith('count'):
                    self.assertEqual(output.strip(), expected+' solutions.')
                else:
                    self.assertIn('coefficients are '+expected+' (* z^62..z^62)', output)

    def test_small_singleton_count_and_coefficient(self):
        path = self.work/'one.diagram'
        path.write_text('2: (~2?0:1)\n')
        for name in self.programs:
            output = self.run_reader(name, path)
            with self.subTest(reader=name):
                if name.endswith('count'):
                    self.assertEqual(output.strip(), '1 solutions.')
                else:
                    self.assertIn('coefficients are 1 (* z^1..z^1)', output)

    def test_memoized_readers_initialize_marks_on_dirty_allocations(self):
        path = self.work/'two.diagram'
        path.write_text('2: (~1?0:1)\n3: (~0?2:1)\n')
        for name, generated in self.generated.items():
            wrapper = self.work/(name+'-dirty.c')
            wrapper.write_text('''#include <stdlib.h>
#include <string.h>
static void *dirty_malloc(size_t n) {
  void *p=malloc(n);
  if (p) memset(p,1,n);
  return p;
}
#define malloc dirty_malloc
'''+f'#include "{generated.name}"\n')
            program = self.work/(name+'-dirty')
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=undefined,bounds',
                            '-fno-sanitize-recover=all', str(wrapper), '-o', str(program)],
                           check=True, capture_output=True)
            result = subprocess.run([str(program), str(path)], capture_output=True, timeout=5)
            with self.subTest(reader=name):
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                output = result.stdout.decode()
                if name.endswith('count'):
                    self.assertEqual(output.strip(), ('3' if name.startswith('bdd') else '2')+
                                     ' solutions.')
                elif name.startswith('zdd'):
                    self.assertIn('coefficients are 2 (* z^1..z^1)', output)
                else:
                    self.assertIn('coefficients are 2 1 (* z^1..z^2)', output)

    def test_all_distributed_reader_changes_still_tangle_and_compile(self):
        for change in sorted(SOURCES.glob('*read*.ch')):
            base = change.name.split('-')[0]
            generated = self.work/(change.stem+'-composition.c')
            with self.subTest(change=change.name):
                result = subprocess.run(['ctangle', str(SOURCES/(base+'.w')),
                                         str(change), str(generated)], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
                sgb = os.environ.get('GRAPHBASE')
                if change.name == 'zddread-random.ch' and not sgb:
                    continue  # Tangle checked; optional syntax check needs GraphBase headers.
                result = subprocess.run(['gcc', '-std=gnu99', '-fsyntax-only',
                                         *(['-I'+sgb] if sgb else []), str(generated)],
                                        capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_all_nonconstant_three_variable_counts_and_polynomials(self):
        path = self.work/'small.diagram'
        for name in self.programs:
            zdd = name.startswith('zdd')
            for mask in (range(2, 256) if zdd else range(1, 255)):
                dd = Diagram(zdd)

                def construct(variable, assignment):
                    if variable == 3:
                        return (mask >> assignment) & 1
                    return dd.node(variable, construct(variable+1, assignment),
                                   construct(variable+1, assignment | (1 << variable)))

                construct(0, 0)
                dd.write(path)
                support = {v for v, _, _ in dd.nodes.values()}
                support_mask = sum(1 << v for v in support)
                counts = Counter((a if zdd else a & support_mask).bit_count()
                                 for a in range(8) if mask & (1 << a))
                if not zdd:
                    divisor = 1 << (3-len(support))
                    counts = Counter({degree: count//divisor for degree, count in counts.items()})
                output = self.run_reader(name, path)
                with self.subTest(reader=name, mask=mask):
                    if name.endswith('count'):
                        self.assertEqual(output.strip(), str(sum(counts.values()))+' solutions.')
                    else:
                        low, high = min(counts), max(counts)
                        coefficients = ' '.join(str(counts[k]) for k in range(low, high+1))
                        self.assertIn(f'coefficients are {coefficients} (* z^{low}..z^{high})', output)


if __name__ == '__main__':
    unittest.main()
