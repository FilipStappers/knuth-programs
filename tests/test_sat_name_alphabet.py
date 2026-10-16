"""B053: shared native-name scanners must reject tilde before hashing."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeNameAlphabet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE to compile the shared native SAT readers')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for source in sorted((ROOT/'programs/programs').glob('*.w')):
            if 'hash_bits[93][8]' not in source.read_text():
                continue
            generated = cls.work/(source.stem+'.c')
            program = cls.work/source.stem
            subprocess.run(['ctangle', str(source), '-', str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-I'+sgb, '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[source.stem] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_reader(self, name, text):
        args = [] if name == 'sat12-erp' else ['v0']
        if name in ['sat12', 'sat12-erp']:
            erp = self.work/(name+'.erp')
            if name.endswith('-erp'):
                erp.write_text('seed <-0\n')
            args.append('e'+str(erp))
        return subprocess.run([str(self.programs[name]), *args], input=text.encode(),
                              capture_output=True, timeout=5)

    def test_internal_tilde_rejects_before_hash_lookup(self):
        self.assertEqual(len(self.programs), 10)
        for name in self.programs:
            for token in ['a~', 'a~b', '1234567~', '~a~']:
                result = self.run_reader(name, token+'\n')
                with self.subTest(reader=name, token=token):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertIn(b'variable name', result.stderr)

    def test_leading_negation_and_eight_character_names_still_work(self):
        for name in self.programs:
            text = '~abcdefgh\n'
            if name != 'sat12-erp':
                text = '~ comment\n'+text
            result = self.run_reader(name, text)
            with self.subTest(reader=name):
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'Illegal', result.stderr)

    def test_every_documented_name_character_still_works(self):
        names = [chr(code) for code in range(ord('!'), ord('}')+1)]
        for name in self.programs:
            text = ' '.join(names)+'\n' if name.endswith('-erp') else ''.join(x+'\n' for x in names)
            result = self.run_reader(name, text)
            with self.subTest(reader=name):
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'Illegal', result.stderr)


if __name__ == '__main__':
    unittest.main()
