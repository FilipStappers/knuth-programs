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

    def encode(self, name, m, n, rounds):
        args = [str(m), str(n), str(rounds)]
        if 'spaceships' in name:
            args.append('1')
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
