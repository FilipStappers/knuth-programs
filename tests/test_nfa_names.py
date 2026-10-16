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
        driver = work/'short-transition.c'
        driver.write_text('''
#include <stdlib.h>
#include <string.h>
#define main published_main
#include "nfa.c"
#undef main
int main(int argc,char **argv) {
  char *transition=malloc(strlen(argv[1])+1);
  char *args[]={"nfa","1","a","a",transition,NULL};
  strcpy(transition,argv[1]);
  return published_main(5,args);
}
''')
        cls.short_program = work/'short-transition'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                        str(driver), '-o', str(cls.short_program)], check=True, capture_output=True)

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

    def test_empty_word_checks_initial_final_state_intersection(self):
        for initial, final in itertools.product(['a', 'b', 'ab'], repeat=2):
            for transitions in [[], ['a0a', 'b1b']]:
                with self.subTest(initial=initial, final=final, transitions=transitions):
                    result = self.encode(0, initial, final, transitions)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(satisfiable(clauses(result.stdout)),
                                     accepts(initial, final, transitions, ''))

    def test_state_sets_must_be_nonempty(self):
        for initial, final in [('', 'a'), ('a', ''), ('', '')]:
            with self.subTest(initial=initial, final=final):
                result = self.encode(0, initial, final, [])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'nonempty', result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_short_transition_is_checked_before_indexing(self):
        for transition in ['', 'a', 'a0', 'a0aa', 'a2a']:
            with self.subTest(transition=transition):
                result = subprocess.run([str(self.short_program), transition], capture_output=True,
                                        timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'Improper transition', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_length_bounds_keep_every_variable_within_native_name_capacity(self):
        for n in [-2147483648, -1, 10000, 2147483647]:
            with self.subTest(n=n):
                result = self.encode(n, 'a', 'a', ['a0a'])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'length', result.stderr)
                self.assertEqual(result.stdout, b'')
        result = self.encode(9999, 'a', 'a', ['a0a'])
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        names = {lit.removeprefix('~') for row in clauses(result.stdout) for lit in row}
        self.assertTrue(all(1 <= len(name) <= 8 for name in names))
        self.assertIn('T6109999', names)
        self.assertIn('S619999', names)
        self.assertIn('9999', names)

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
