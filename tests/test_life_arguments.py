"""B059: grid and torus arguments must fit fixed storage and time codes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LifeArguments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        directories = [ROOT/'programs/archives/sat-life',
                       ROOT/'programs/archives/SATexamples/sources']
        for directory in directories:
            for change in directory.glob('sat-life-*.ch'):
                if 'sscanf(argv[3]' not in change.read_text():
                    continue
                name = change.stem+('-SATexamples' if directory.name == 'sources' else '')
                generated = cls.work/(name+'.c')
                program = cls.work/name
                subprocess.run(['ctangle', str(directory/'sat-life.w'), str(change),
                                str(generated)], check=True, capture_output=True)
                subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                '-include', 'stdlib.h', '-include', 'string.h',
                                '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                                str(generated), '-o', str(program)],
                               check=True, capture_output=True)
                cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, name, m, n, rounds, shift=1):
        args = [str(m), str(n), str(rounds)]
        if 'spaceships' in name:
            args.append(str(shift))
        return subprocess.run([str(self.programs[name]), *args],
                              capture_output=True, timeout=5)

    def test_dimensions_outside_storage_reject_before_output(self):
        for name in self.programs:
            for size in [0, -1, 51, -2147483648, 2147483647]:
                result = self.encode(name, size, size, 1)
                with self.subTest(variant=name, size=size):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertEqual(result.stdout, b'')

    def test_rounds_must_fit_time_codes(self):
        for name in self.programs:
            limit = 84 if '-cycle' in name else 83
            for rounds in [0, -1, limit+1, -2147483648, 2147483647]:
                result = self.encode(name, 2, 2, rounds)
                with self.subTest(variant=name, rounds=rounds):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertEqual(result.stdout, b'')

    def test_last_supported_time_code_has_no_nul(self):
        for name in self.programs:
            limit = 84 if '-cycle' in name else 83
            result = self.encode(name, 2, 2, limit)
            with self.subTest(variant=name):
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'\x00', result.stdout)
                self.assertTrue(result.stdout)

    def test_spaceship_shift_fits_the_board(self):
        for name in self.programs:
            if 'spaceships' not in name:
                continue
            for shift in [0, -1, 4, -2147483648, 2147483647]:
                result = self.encode(name, 3, 3, 1, shift)
                with self.subTest(variant=name, shift=shift):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertEqual(result.stdout, b'')
            for shift in [1, 2, 3]:
                result = self.encode(name, 3, 3, 1, shift)
                with self.subTest(variant=name, shift=shift):
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertNotIn(b'runtime error', result.stderr)

    def test_largest_grid_dimensions_fit_storage(self):
        self.assertEqual(len(self.programs), 12)
        for name in self.programs:
            with self.subTest(variant=name):
                result = self.encode(name, 50, 50, 1)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertTrue(result.stdout)


if __name__ == '__main__':
    unittest.main()
