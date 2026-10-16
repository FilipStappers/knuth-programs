"""B060: literal piece identity in older shape-encoder option rows."""
from collections import Counter
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LegacyShapeNames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        for name in ['polyominoes', 'polyiamonds', 'polysticks']:
            generated = work/(name+'.c')
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/(name+'.w')), '-', str(generated)],
                           check=True, capture_output=True)
            program = work/name
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, name, data):
        return subprocess.run([str(self.programs[name])], input=data, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_initial_eof_and_empty_c_string_records_reject_cleanly(self):
        for name in self.programs:
            records = [b'']
            if name == 'polysticks':
                records += [b'\x00\n', b'P\n\x00\n', b'P\nH00\n\x00\n']
            else:
                records += [b'\x00\n', b'00\n\x00\n', b'00\nP\n\x00\n']
            for data in records:
                with self.subTest(name=name, data=data):
                    result = self.solve(name, data)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_piece_names_survive_header_to_every_placement(self):
        for name in self.programs:
            for piece in ['P', 'AB', '%%']:
                if name == 'polysticks':
                    cells = ['H00', 'H10']
                    data = piece+'\n'+' '.join(cells)+'\n'+piece+' 1 1 H00\n'
                else:
                    cells = ['00', '10']
                    data = ' '.join(cells)+'\n'+piece+'\n'+piece+' 1 1 00\n'
                with self.subTest(name=name, piece=piece):
                    result = self.solve(name, data.encode())
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    lines = [line.split() for line in result.stdout.decode().splitlines()]
                    self.assertEqual(set(lines[0]), set(cells) | {piece})
                    self.assertEqual(Counter(tuple(sorted(row)) for row in lines[1:]),
                                     Counter(tuple(sorted([piece, cell])) for cell in cells))


if __name__ == '__main__':
    unittest.main()
