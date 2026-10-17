"""BUG-065: query projection over every completion, with a controlled cost table.

The native completion loop runs; full footprint-cost discovery is bypassed.
"""
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'programs/programs'


class DontcareCompletions(unittest.TestCase):
    def test_all_partial_assignments_including_the_top_bit(self):
        text = (ROOT / 'fchains4x.w').read_text()
        start = text.index('  @<Read the initial functions@>;')
        end = text.index('  @<Answer queries@>;', start)
        text = text[:start] + '''  mm=1;
  for (j=0;j<32;j++) sprintf(name[j],"b%d",j);
  for (j=0;j<0x8000;j++) {
    unsigned int bits=j;
    for (r=0;bits;bits>>=1) r+=bits&1;
    func[j].cost=r%8;
    func[j].footprint[0]=1U<<(j%32);
  }
''' + text[end:]
        # Keep the change-file main match intact; this historical main reaches
        # implicit successful termination with the compiler used by this test.
        cases = []
        positions = [0, 1, 7, 14, 15]
        for states in itertools.product(range(3), repeat=len(positions)):
            a = sum(1 << bit for bit, state in zip(positions, states) if state == 2)
            b = sum(1 << bit for bit, state in zip(positions, states) if state == 1)
            cases.append((a, b))
        cases += [(0xffff, 0), (0x8000, 0x7fff), (0, 0xffff)]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'dontcare.w'
            generated = source.with_suffix('.c')
            program = source.with_suffix('')
            source.write_text(text)
            subprocess.run(['ctangle', str(source), str(ROOT / 'fchains4x-dontcares.ch'), str(generated)],
                           capture_output=True, check=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], capture_output=True, check=True)
            for a, b in cases:
                with self.subTest(a=a, b=b):
                    result = subprocess.run([str(program)], input=f'{a:x} {b:x}\n'.encode(),
                                            capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(result.stderr, b'')
                    match = re.search(rb'([0-9a-f]+) has cost (\d+), parents .* and footprint([^\n]*)',
                                      result.stdout)
                    self.assertIsNotNone(match, result.stdout)
                    completions = set()
                    free = [bit for bit in range(16) if a & (1 << bit)]
                    for values in itertools.product([0, 1], repeat=len(free)):
                        table = b | sum(value << bit for bit, value in zip(free, values))
                        completions.add(table ^ (0xffff if table & 0x8000 else 0))
                    best = min(table.bit_count() % 8 for table in completions)
                    winners = {table for table in completions if table.bit_count() % 8 == best}
                    self.assertIn(int(match[1], 16), winners)
                    self.assertEqual(int(match[2]), best)
                    footprint = {int(bit) for bit in re.findall(rb'b(\d+)', match[3])}
                    self.assertEqual(footprint, {table % 32 for table in winners})
            for data in [b'10000 0\n', b'0 10000\n', b'1 1\n']:
                result = subprocess.run([str(program)], input=data, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertIn(b'disjoint 16-bit', result.stderr)
                self.assertNotIn(b'has cost', result.stdout)
                self.assertNotIn(b'runtime error', result.stderr)


if __name__ == '__main__':
    unittest.main()
