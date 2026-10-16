"""B058: NFA variable identities and direct transition-set language projections."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]


def clauses(output):
    return [line.split() for line in output.decode().splitlines()
            if line.strip() and not line.startswith('~ ')]


def accepts(initial, final, transitions, word):
    states = set(initial)
    for bit in word:
        states = {t[2] for t in transitions if t[0] in states and t[1] == bit}
    return bool(states & set(final))


class NfaNames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'nfa.c'
        subprocess.run(['ctangle', str(ROOT/'programs/programs/sat-nfa.w'), '-', str(generated)],
                       check=True, capture_output=True)
        cls.program = work/'nfa'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, n, initial, final, transitions):
        return subprocess.run([str(self.program), str(n), initial, final, *transitions],
                              capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_state_transition_and_numeric_input_names_are_disjoint(self):
        for state, word in [('a', '0'*11), ('a', '0'+'1'*10), ('2', '0'*21)]:
            with self.subTest(state=state, word=word):
                transitions = [state+'0'+state, state+'1'+state]
                result = self.encode(len(word), state, state, transitions)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                formula = clauses(result.stdout)
                fixed = [[('~' if bit == '0' else '')+str(i)] for i, bit in enumerate(word, 1)]
                self.assertTrue(satisfiable(formula+fixed))

    def test_complete_small_language_projections(self):
        automata = [('a', 'a', ['a0a', 'a1a']),
                    ('a', 'c', ['a0a', 'a1b', 'b1c', 'c0c']),
                    ('a', 'a', ['a0a', 'a1b', 'b0b', 'b1a']),
                    ('a', 'b', ['a0a', 'a0b', 'a1a', 'b0b', 'b1b']),
                    ('ab', 'c', ['a0b', 'a1a', 'b0c', 'b1b', 'c0c', 'c1c'])]
        for initial, final, transitions in automata:
            for n in range(1, 6):
                result = self.encode(n, initial, final, transitions)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                formula = clauses(result.stdout)
                for bits in itertools.product('01', repeat=n):
                    with self.subTest(initial=initial, final=final, transitions=transitions, bits=bits):
                        fixed = [[('~' if bit == '0' else '')+str(i)] for i, bit in enumerate(bits, 1)]
                        self.assertEqual(satisfiable(formula+fixed), accepts(initial, final, transitions, bits))


if __name__ == '__main__':
    unittest.main()
