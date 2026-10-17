"""BUG-078: bounded nonempty words and complete small multiset posets."""
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'programs/programs/domination.w'


class DominationDomain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        source = Path(cls.temp.name) / 'domination.w'
        source.write_text(SOURCE.read_text().replace('#include <stdio.h>',
                          '#include <stdio.h>\n#include <stdlib.h>').replace(
                          'main(int argc, char*argv[])', 'int main(int argc, char*argv[])'))
        generated = source.with_suffix('.c')
        cls.program = source.with_suffix('')
        subprocess.run(['ctangle',str(source),'-',str(generated)],capture_output=True,check=True)
        subprocess.run(['gcc','-std=gnu99','-O1','-fsanitize=undefined,bounds',
                        '-fno-sanitize-recover=all',str(generated),'-o',str(cls.program)],
                       capture_output=True,check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_word(self, word):
        return subprocess.run([str(self.program),word],capture_output=True,timeout=5)

    def test_empty_and_oversized_words_reject(self):
        for word in ['', '1'*64, '1'*65]:
            with self.subTest(length=len(word)):
                result = self.run_word(word)
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn(b'runtime error',result.stderr)
                self.assertEqual(result.stdout,b'')

    def test_maximum_word_with_one_permutation(self):
        for length in [1,62,63]:
            word = '1'*length
            result = self.run_word(word)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertEqual(result.stderr,b'')
            self.assertEqual(result.stdout,(word+' <\n').encode())

    def test_all_small_three_digit_multisets(self):
        for n in range(1,6):
            for digits in itertools.combinations_with_replacement('012',n):
                word = ''.join(digits)
                with self.subTest(word=word):
                    permutations = sorted(set(map(''.join,itertools.permutations(word))))
                    less = {(a,b) for a in permutations for b in permutations if a != b
                            and all(sum(x >= threshold for x in a[:length]) <=
                                    sum(x >= threshold for x in b[:length])
                                    for threshold in '012' for length in range(1,n+1))}
                    expected = {a: {b for b in permutations if (a,b) in less
                                    and not any((a,c) in less and (c,b) in less for c in permutations)}
                                for a in permutations}
                    result = self.run_word(word)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertEqual(result.stderr,b'')
                    actual = {}
                    for line in result.stdout.decode().splitlines():
                        a, rest = line.split(' <')
                        actual[a] = set(rest.split())
                    self.assertEqual(actual,expected)


if __name__ == '__main__':
    unittest.main()
