"""B030: real bounded addition-chain runs against independent minima."""
import os
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from test_achain3_search import minimum

ROOT = Path(__file__).resolve().parents[1]
NMAX = 256


def chains(n, length, strong=False):
    """Exhaust pair sums, pruning only by the remaining doublings."""
    def visit(chain, left):
        if chain[-1] == n:
            if left == 0:
                yield tuple(chain)
            return
        if left == 0 or chain[-1]*(1 << left) < n:
            return
        candidates = {x+y for x in chain for y in chain
                      if chain[-1] < x+y <= n
                      and (not strong or x == y or abs(x-y) in chain)}
        for value in sorted(candidates, reverse=True):
            yield from visit(chain+[value], left-1)
    yield from visit([1], length)


def canonical(chain):
    """Check every sum decomposition against the stated tail criterion."""
    choices = [[(i, j) for i in range(s) for j in range(i+1)
                if chain[i]+chain[j] == chain[s]] for s in range(1, len(chain))]
    for decomposition in itertools.product(*choices):
        degree, consumer = [0]*len(chain), [0]*len(chain)
        tails = [0]+[chain[j] for i, j in decomposition]
        for s, (i, j) in enumerate(decomposition, 1):
            for k in (i, j):
                degree[k] += 1
                consumer[k] = s
        if all(degree[s] != 1 or tails[s] >= tails[consumer[s]]
               for s in range(1, len(chain))):
            return True
    return False


class AdditionChainBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def compile_program(self, name):
        if name in self.programs:
            return self.programs[name]
        text = (ROOT/'programs/programs'/(name+'.w')).read_text()
        text, count = re.subn(r'(?m)^@d nmax [^\n]+', f'@d nmax {NMAX}', text)
        self.assertEqual(count, 1)
        source = self.work/(name+'.w')
        source.write_text(text)
        generated = self.work/(name+'.c')
        subprocess.run(['ctangle', str(source), '-', str(generated)],
                       check=True, capture_output=True)
        program = self.work/name
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(program)], check=True, capture_output=True)
        self.programs[name] = program
        return program

    def check_table(self, name):
        empty = self.work/'empty'
        empty.write_bytes(b'')
        output = self.work/(name+'.out')
        result = subprocess.run([str(self.compile_program(name)), str(empty), str(output)],
                                capture_output=True, timeout=15,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'runtime error', result.stderr)
        expected = bytes((0 if n == 1 else minimum(n, 1))+32 for n in range(1, NMAX))
        self.assertEqual(output.read_bytes(), expected)

    def test_achain2_sparse_summand_power_requires_a_valid_position(self):
        self.check_table('achain2')

    def test_achain4_rejects_exhausted_candidates_before_scanning_positions(self):
        self.check_table('achain4')

    def test_strongchain_stops_at_its_results_table_boundary(self):
        text = (ROOT/'programs/programs/strongchain.w').read_text()
        text, count = re.subn(r'(?m)^@d maxn [^\n]+', '@d maxn 64', text)
        self.assertEqual(count, 1)
        source = self.work/'strongchain.w'
        source.write_text(text)
        generated = self.work/'strongchain.c'
        subprocess.run(['ctangle', str(source), '-', str(generated)],
                       check=True, capture_output=True)
        program = self.work/'strongchain'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(program)], check=True, capture_output=True)
        result = subprocess.run([str(program)], capture_output=True, timeout=15,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        actual = [(int(n), int(m)) for n, m in
                  re.findall(rb'L\((\d+)\)=(\d+):', result.stdout)]
        expected = []
        for n in range(1, 64):
            for length in range((n-1).bit_length(), 2*n.bit_length()+1):
                if next(chains(n, length, strong=True), None) is not None:
                    expected.append((n, length))
                    break
        self.assertEqual(actual, expected)

    def test_achain_all_preserves_every_canonical_value_sequence(self):
        truth = self.work/'truth'
        truth.write_bytes(bytes((0 if n == 1 else minimum(n, 1))+32
                                for n in range(1, NMAX)))
        program = self.compile_program('achain-all')
        for n, count in [(3, 1), (7, 2), (15, 2), (23, 2), (31, 15),
                         (47, 37), (63, 24), (132, 3)]:
            with self.subTest(target=n):
                expected = {c for c in chains(n, minimum(n, 1)) if canonical(c)}
                self.assertEqual(len(expected), count)
                result = subprocess.run([str(program), str(truth), str(n)],
                                        capture_output=True, timeout=15,
                                        env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                actual = {tuple(map(int, line.split()))
                          for line in result.stdout.splitlines() if line.strip()}
                self.assertEqual(actual, expected)

    def test_sparse_sections_guard_all_positions_and_preserve_forced_moves(self):
        harness_text = r'''
#define main algorithm_main
#include "sparse.c"
#undef main
int main(void) {
  int position,operand;
  for (operand=0;operand<2;operand++) {
    for (position=0;position<128;position++)
      if (!regression_sparse(position,1,operand)) return 1;
    if (!regression_sparse(8,132,operand) || a[4]!=16 || a[3]!=8) return 2;
    if (!regression_sparse(24,(1<<23)+1,operand) || a[22]!=(1<<22)) return 3;
  }
  return 0;
}
'''
        for name in ['achain2', 'achain3', 'achain4', 'achain-all']:
            with self.subTest(program=name):
                text = (ROOT/'programs/programs'/(name+'.w')).read_text()
                text = re.sub(r'(?m)^@d nmax [^\n]+', '@d nmax 256', text)
                text += '''
@c
int regression_sparse(int position,int value,int is_p) {
  int i,j,ubp=position,ubq=position,p=value,q=value;
  ptr=0;
  for (j=0;j<128;j++) a[j]=1,b[j]=0xffffff;
  if (is_p) {
    @<Make forced moves if |p| has a special form@>;
  }@+else {
    @<Make forced moves if |q| has a special form@>;
  }
  return 1;
failp: return 0;
failq: return 0;
}
'''
                source = self.work/'sparse.w'
                source.write_text(text)
                generated = self.work/'sparse.c'
                subprocess.run(['ctangle', str(source), '-', str(generated)],
                               check=True, capture_output=True)
                harness = self.work/'sparse-harness.c'
                harness.write_text(harness_text)
                program = self.work/(name+'-sparse')
                subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                                str(harness), '-o', str(program)], check=True, capture_output=True)
                result = subprocess.run([str(program)], capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == '__main__':
    unittest.main()
