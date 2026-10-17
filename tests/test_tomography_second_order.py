"""Second-order tomography: exact adjacent-pair and matrix projections."""
from itertools import product
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable
from test_dimacs_empty_clause import native_clauses

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'


def matrix_lines(m, n):
    result = {}
    for i in range(m):
        result[f'r{i+1}'] = [i*n+j for j in range(n)]
    for j in range(n):
        result[f'c{j+1}'] = [i*n+j for i in range(m)]
    for d in range(1, m+n):
        result[f'a{d}'] = [i*n+j for i in range(m) for j in range(n) if i+j == d-1]
        result[f'b{d}'] = [i*n+j for i in range(m) for j in range(n) if i-j == d-n]
    return result


def sums(bits, lines):
    return [(sum(bits[i] for i in line), sum(bits[i]*bits[j] for i, j in zip(line, line[1:])))
            for line in lines.values()]


class TomographySecondOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def build(self):
        if hasattr(self, 'program'):
            return
        generated = self.work/'tomography.c'
        result = subprocess.run(['ctangle', str(SOURCES/'sat-tomography.w'),
                                 str(SOURCES/'sat-tomography-2nd.ch'), str(generated)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.program = self.work/'tomography'
        flags = ['-std=gnu99', '-O1', '-Wno-implicit-int', '-fsanitize=undefined,bounds',
                 '-fno-sanitize-recover=all']
        subprocess.run(['gcc', *flags, str(generated), '-o', str(self.program)],
                       check=True, capture_output=True)
        driver = self.work/'line.c'
        driver.write_text('#define main tomography_main\n#include "'+str(generated)+'''"
#undef main
int main(int argc,char **argv) {
  int length=atoi(argv[1]),ones=atoi(argv[2]),pairs=atoi(argv[3]),j;
  strcpy(buf,argc>4? argv[4]:"1R");
  for(j=1;j<=length;j++)sprintf(name[j],"%dx1",j);
  gen_clauses(length,ones);
  gen_second_order(length,pairs);
  return 0;
}
''')
        self.line_program = self.work/'line'
        subprocess.run(['gcc', *flags, str(driver), '-o', str(self.line_program)],
                       check=True, capture_output=True)

    def line_clauses(self, length, ones, pairs, prefix='1R'):
        self.build()
        result = subprocess.run([str(self.line_program), str(length), str(ones), str(pairs), prefix],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('runtime error', result.stderr)
        clauses = native_clauses(result.stdout)
        self.assertTrue(all(len(literal.lstrip('~')) <= 8 for clause in clauses for literal in clause))
        return clauses

    def test_complete_line_projections(self):
        for length in range(1, 9):
            words = list(product((0, 1), repeat=length))
            for ones in range(length+1):
                for pairs in range(length):
                    clauses = self.line_clauses(length, ones, pairs)
                    for bits in words:
                        fixed = [[('' if bit else '~')+f'{i+1}x1'] for i, bit in enumerate(bits)]
                        expected = sum(bits) == ones and sum(a*b for a, b in zip(bits, bits[1:])) == pairs
                        self.assertEqual(satisfiable(clauses+fixed), expected, (length, ones, pairs, bits))

    def test_complete_small_matrix_projections(self):
        self.build()
        for m, n in [(1, 1), (1, 4), (2, 2), (2, 3), (3, 2)]:
            lines = matrix_lines(m, n)
            matrices = list(product((0, 1), repeat=m*n))
            for original in matrices:
                target = sums(original, lines)
                data = ''.join(f'{key}={first},{second}\n' for key, (first, second) in zip(lines, target))
                result = subprocess.run([str(self.program)], input=data, text=True,
                                        capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('runtime error', result.stderr)
                clauses = native_clauses(result.stdout)
                for candidate in matrices:
                    fixed = [[('' if bit else '~')+f'{i//n+1}x{i%n+1}'] for i, bit in enumerate(candidate)]
                    self.assertEqual(satisfiable(clauses+fixed), sums(candidate, lines) == target,
                                     (m, n, original, candidate))

    def test_large_line_names_and_fixed_word(self):
        bits = (1,)*100+(0,)*100
        clauses = self.line_clauses(200, 100, 99, '100C')
        fixed = [[('' if bit else '~')+f'{i+1}x1'] for i, bit in enumerate(bits)]
        self.assertTrue(satisfiable(clauses+fixed))
        self.assertFalse(satisfiable(self.line_clauses(200, 100, 98, '100C')+fixed))

    def test_longer_rows_columns_and_diagonals(self):
        self.build()
        for m, n in [(4, 4), (4, 5), (5, 4), (5, 5)]:
            lines = matrix_lines(m, n)
            matrices = [tuple(value(i, j) for i in range(m) for j in range(n)) for value in
                        [lambda i, j: 0, lambda i, j: 1,
                         lambda i, j: (i+j) % 2, lambda i, j: i % 2,
                         lambda i, j: j % 2, lambda i, j: int((i*i+2*j+i*j) % 5 < 3)]]
            for original in matrices:
                target = sums(original, lines)
                data = ''.join(f'{key}={first},{second}\n' for key, (first, second) in zip(lines, target))
                result = subprocess.run([str(self.program)], input=data, text=True,
                                        capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                clauses = native_clauses(result.stdout)
                self.assertTrue(all(len(literal.lstrip('~')) <= 8 for clause in clauses for literal in clause))
                for candidate in matrices:
                    fixed = [[('' if bit else '~')+f'{i//n+1}x{i%n+1}'] for i, bit in enumerate(candidate)]
                    self.assertEqual(satisfiable(clauses+fixed), sums(candidate, lines) == target)

    def test_second_order_input_errors(self):
        self.build()
        cases = ['r1=0\n', 'r1=0,\n', 'r1=0,-1\n', 'r1=0,2147483648\n',
                 'r1=0,'+'9'*60+'\n', 'r1=0,0\nr1=0,0\n',
                 'r1=1,1\nc1=1,0\na1=1,0\nb1=1,0\n']
        for data in cases:
            with self.subTest(data=data):
                result = subprocess.run([str(self.program)], input=data, text=True,
                                        capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('runtime error', result.stderr)


if __name__ == '__main__':
    unittest.main()
