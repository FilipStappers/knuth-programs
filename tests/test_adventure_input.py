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


if __name__ == '__main__':
    unittest.main()
