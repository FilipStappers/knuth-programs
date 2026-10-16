"""B030: prefix-constrained addition-chain minima against pair-sum search."""
import functools
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NMAX = 128


@functools.lru_cache(None)
def minimum(n, k):
    prefix = tuple(1 << j for j in range(k+1))

    def visit(chain, left):
        if chain[-1] == n:
            return True
        if left == 0 or (chain[-1] << left) < n:
            return False
        choices = {a+b for a in chain for b in chain if chain[-1] < a+b <= n}
        return any(visit(chain+(value,), left-1) for value in sorted(choices, reverse=True))

    for length in range(k, n.bit_length()+n.bit_count()):
        if visit(prefix, length-k):
            return length
    raise AssertionError((n, k))


class PrefixChainSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        text = (ROOT/'programs/programs/achain3.w').read_text()
        text, count = re.subn(r'(?m)^@d nmax \(1<<20\)', f'@d nmax {NMAX}', text)
        assert count == 1
        source = cls.work/'small.w'
        source.write_text(text)
        generated = cls.work/'small.c'
        subprocess.run(['ctangle', str(source), '-', str(generated)],
                       check=True, capture_output=True)
        cls.programs = []
        for mode in ['signed', 'unsigned']:
            program = cls.work/mode
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-f'+mode+'-char',
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs.append(program)
        cls.expected = {k: bytes(minimum(n, k)+32 for n in range(1 << k, NMAX))
                        for k in range(1, NMAX.bit_length()-1)}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_search(self, program, payloads=None, long_prefixes=False):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            input_prefix = 'i'*150 if long_prefixes else 'input'
            output_prefix = 'o'*150 if long_prefixes else 'output'
            for k, data in (payloads or {}).items():
                (work/f'{input_prefix}-{k}').write_bytes(data)
            result = subprocess.run([str(program), input_prefix, output_prefix], cwd=work,
                                    capture_output=True, timeout=15,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertNotIn(b'AddressSanitizer', result.stderr)
            self.assertNotIn(b'runtime error', result.stderr)
            return {k: (work/f'{output_prefix}-{k}').read_bytes() for k in self.expected}

    def test_long_valid_input_and_output_prefixes(self):
        for payloads in [None, self.expected]:
            self.assertEqual(self.run_search(self.programs[0], payloads, True), self.expected)

    def test_fifteen_has_a_five_addition_chain_starting_with_one_two(self):
        result = self.run_search(self.programs[0])
        self.assertEqual(result[1][15-2]-32, 5)  # 1,2,3,5,10,15

    def test_all_642_prefix_minima_in_both_char_modes(self):
        self.assertEqual(sum(map(len, self.expected.values())), 642)
        for program in self.programs:
            with self.subTest(mode=program.name):
                self.assertEqual(self.run_search(program), self.expected)

    def test_valid_and_truncated_exact_caches_preserve_minima(self):
        for program in self.programs:
            for payloads in [self.expected, {k: values[:3] for k, values in self.expected.items()}]:
                with self.subTest(mode=program.name, truncated=payloads != self.expected):
                    self.assertEqual(self.run_search(program, payloads), self.expected)


if __name__ == '__main__':
    unittest.main()
