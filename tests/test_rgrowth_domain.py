"""Restricted-growth BDDL domain and independent partition assignment semantics."""
from itertools import product
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'programs/programs/bddl-rgrowth.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class RgrowthDomain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'growth.c'
        cls.program = work/'growth'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def generate(self, *args):
        return subprocess.run([str(self.program), *args], capture_output=True, timeout=5, env=ENV)

    def test_unsupported_sizes_reject_before_output(self):
        for args in [(), ('0',), ('-1',), ('45',), ('500',), ('501',), ('2147483647',),
                     ('4294967297',), ('9'*100,), ('2x',), ('',), ('1', '2')]:
            with self.subTest(args=args):
                result = self.generate(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(result.stdout)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_maximum_stock_bdd14_variable_and_root_bounds(self):
        result = self.generate('44')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        variables = list(map(int, re.findall(rb'x(\d+)', result.stdout)))
        self.assertEqual(max(variables), 989)
        roots = set(map(int, re.findall(rb'f(\d+)', result.stdout)))
        self.assertEqual(roots, set(range(45)) | {500, 501})

    def test_small_partition_assignment_sets(self):
        for n in range(1, 6):
            result = self.generate(str(n))
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            registers = {'c0': False, 'c1': True}
            for line in result.stdout.decode().splitlines():
                if line.startswith(('#', '!')):
                    continue
                target, expr = line.split('=')
                match = re.fullmatch(r'x(\d+)\?([fc]\d+):([fc]\d+)', expr)
                registers[target] = ((int(match[1]), registers[match[2]], registers[match[3]])
                                     if match else registers[expr])
            def evaluate(node, bits):
                while isinstance(node, tuple):
                    variable, yes, no = node
                    node = yes if bits >> variable & 1 else no
                return node
            actual = {bits for bits in range(1 << (n*(n+1)//2)) if evaluate(registers['f1'], bits)}
            expected = set()
            for sequence in product(*[range(k) for k in range(1, n+1)]):
                if any(sequence[k] > max(sequence[:k])+1 for k in range(1, n)):
                    continue
                bits, offset = 0, 0
                for k in range(n, 0, -1):
                    bits |= 1 << (offset+sequence[k-1])
                    offset += k
                expected.add(bits)
            self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
