"""B034: diagram arithmetic and reader-state regressions."""
import functools
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
        for name in ['zddread-count', 'zddread-gf', 'bddread-gf']:
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


if __name__ == '__main__':
    unittest.main()
