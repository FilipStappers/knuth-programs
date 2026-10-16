"""Addition-chain cache EOF/invalid data must fall back to computation."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NMAX = 8


def shortest_chain(n, prefix_power):
    prefix = tuple(1 << i for i in range(prefix_power+1))
    frontier = {prefix}
    while frontier:
        if any(chain[-1] == n for chain in frontier):
            return len(next(iter(frontier)))-1
        following = set()
        for chain in frontier:
            for a in chain:
                for b in chain:
                    value = a+b
                    if chain[-1] < value <= n:
                        following.add(chain+(value,))
        frontier = following
    raise AssertionError('No addition chain')


class AdditionChainCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        text = (ROOT/'programs/programs/achain3.w').read_text()
        text, count = re.subn(r'(?m)^@d nmax \(1<<20\)', f'@d nmax {NMAX}', text)
        assert count == 1
        source = cls.work/'achain3-small.w'
        source.write_text(text)
        generated = cls.work/'achain3-small.c'
        subprocess.run(['ctangle', str(source), '-', str(generated)],
                       check=True, capture_output=True)
        cls.programs = []
        for mode in ['signed', 'unsigned']:
            program = cls.work/('achain3-'+mode)
            subprocess.run(['gcc', '-std=gnu99', '-O1', '-f'+mode+'-char',
                            str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs.append(program)
        cls.expected = {k: bytes(shortest_chain(n, k)+32 for n in range(1 << k, NMAX))
                        for k in range(1, NMAX.bit_length()-1)}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_cache(self, payloads):
        for program in self.programs:
            with tempfile.TemporaryDirectory() as td:
                work = Path(td)
                for k, data in payloads.items():
                    (work/f'in-{k}').write_bytes(data)
                subprocess.run([str(program), 'in', 'out'], cwd=work,
                               check=True, capture_output=True, timeout=10)
                actual = {k: (work/f'out-{k}').read_bytes() for k in self.expected}
                self.assertEqual(actual, self.expected, program.name)

    def test_truncated_cache_falls_back_for_current_entry(self):
        self.check_cache({k: data[:1] for k, data in self.expected.items()})

    def test_empty_cache_falls_back(self):
        self.check_cache({k: b'' for k in self.expected})

    def test_nonpositive_cache_entry_disables_remaining_input(self):
        for invalid in [b' ', b'\x00']:
            with self.subTest(invalid=invalid):
                self.check_cache({k: data[:1]+invalid+b'~'*len(data)
                                  for k, data in self.expected.items()})

    def test_missing_cache_and_complete_valid_cache(self):
        self.check_cache({})
        self.check_cache(self.expected)


if __name__ == '__main__':
    unittest.main()
