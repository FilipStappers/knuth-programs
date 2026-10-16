"""B039: fixed Adventure transcripts, ordinary lookup and input lifecycle."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'programs/programs/advent.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class AdventureInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        generated = cls.work/'advent.c'
        cls.program = cls.work/'advent'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)
        observed = cls.work/'observed.c'
        observed.write_text(r'''
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <limits.h>
static int checked_character(int value) {
  if (value != EOF && (value < 0 || value > UCHAR_MAX)) {
    fprintf(stderr,"ctype argument outside its declared domain: %d\n",value);
    exit(88);
  }
  return value;
}
#undef isspace
#undef tolower
#undef toupper
#define isspace(c) (isspace)(checked_character(c))
#define tolower(c) (tolower)(checked_character(c))
#define toupper(c) (toupper)(checked_character(c))
'''+generated.read_text())
        cls.observer = cls.work/'observed'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(observed), '-o', str(cls.observer)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_game(self, text, discard=False):
        return subprocess.run([str(self.program)], input=text, cwd=self.work,
                              stdout=subprocess.DEVNULL if discard else subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=0.3 if discard else 5, env=ENV)

    def test_unknown_and_known_say_operands_echo_without_invalid_lookup(self):
        for verb, word in [('say', 'zzzzz'), ('say', 'hello'), ('sing', 'zzzzz'),
                           ('say', 'keys'), ('say', 'north')]:
            with self.subTest(verb=verb, word=word):
                result = self.run_game(f'n\n{verb} {word}\nquit\ny\n'.encode())
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertIn(f'Okay, "{word}".'.encode(), result.stdout)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_magic_say_words_still_dispatch(self):
        for word in ['xyzzy', 'plugh', 'plover', 'fee']:
            with self.subTest(word=word):
                result = self.run_game(f'n\nsay {word}\nquit\ny\n'.encode())
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(f'Okay, "{word}".'.encode(), result.stdout)

    def test_initial_question_command_and_confirmation_eof_terminate(self):
        for text in [b'', b'n\n', b'n\nlook\n', b'n\nquit\n', b'n\nsay xyzzy\n']:
            with self.subTest(text=text):
                try:
                    result = self.run_game(text, discard=True)
                except subprocess.TimeoutExpired:
                    self.fail('Input exhaustion repeated an old command or question')
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_input_stream_error_exits_with_failure(self):
        descriptor = os.open(self.work, os.O_RDONLY)
        try:
            result = subprocess.run([str(self.program)], stdin=descriptor,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                    timeout=0.3, cwd=self.work, env=ENV)
        except subprocess.TimeoutExpired:
            self.fail('Read failure was retried as an answer')
        finally:
            os.close(descriptor)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'input', result.stderr.lower())

    def test_overlong_records_are_discarded_as_a_whole(self):
        for padding in [71, 72, 1000]:
            result = self.run_game(b'n\n'+b' '*padding+b'say zzzzz\nquit\ny\n')
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertNotIn(b'Okay, "zzzzz".', result.stdout)
            self.assertIn(b'71 characters', result.stdout)

    def test_exact_input_capacity_preserves_final_command(self):
        word = b'x'*67
        for ending in [b'\n', b'']:
            result = self.run_game(b'n\nsay '+word+ending)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn(b'Okay, "'+word+b'".', result.stdout)

    def test_high_bytes_stay_within_the_ctype_argument_domain(self):
        for text in [b'\x80\nn\nquit\ny\n', b'n\nsay \x80\nquit\ny\n',
                     b'n\n\x80\nquit\ny\n']:
            result = subprocess.run([str(self.observer)], input=text, capture_output=True,
                                    timeout=5, cwd=self.work, env=ENV)
            self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == '__main__':
    unittest.main()
