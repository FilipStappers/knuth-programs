"""B059: clean EOF and a final unterminated assignment are normal input."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'


class PictureFilterEOF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        for kind in ['life', 'life-archive', 'tomography']:
            generated = work/(kind+'.c')
            program = work/kind
            subprocess.run(['ctangle', str(ROOT/'programs/archives/sat-life/sat-life-filter.w') if kind == 'life-archive' else str(SOURCES/f'sat-{kind}-filter.w'), '-',
                            str(generated)], check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[kind] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def filter(self, kind, data):
        result = subprocess.run([str(self.programs[kind])], input=data.encode(),
                                capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result.stdout.decode()

    def assignment(self, kind, opposite=False):
        mark = 'a' if kind.startswith('life') else 'x'
        return ''.join(' '+('' if (i == j) != opposite else '~')+f'{i}{mark}{j}'
                       for i in range(1, 3) for j in range(1, 3))

    def expected(self, kind, opposite=False):
        pixels = {(i, j) for i in range(1, 3) for j in range(1, 3)
                  if (i == j) != opposite}
        indices = range(4) if kind.startswith('life') else range(1, 3)
        return ''.join(''.join('*' if (i, j) in pixels else '.' for j in indices)+'\n'
                       for i in indices)+'\n'

    def test_valid_coordinate_boundaries_and_leading_zeros(self):
        for kind in self.programs:
            mark = 'a' if kind.startswith('life') else 'x'
            for number in ['1', '9', '10', '99', '00099']:
                value = int(number)
                output = self.filter(kind, ' '+number+mark+number+'\n')
                rows = output.splitlines()[:-1]
                size = value+2 if kind.startswith('life') else value
                with self.subTest(kind=kind, number=number):
                    self.assertEqual(len(rows), size)
                    self.assertTrue(all(len(row) == size for row in rows))
                    self.assertEqual(output.count('*'), 1)
                    index = value if kind.startswith('life') else value-1
                    self.assertEqual(rows[index][index], '*')

    def test_large_coordinates_reject_without_overflow(self):
        for kind in self.programs:
            mark = 'a' if kind.startswith('life') else 'x'
            for number in ['100', '2147483648', '9'*10000]:
                for token in [number+mark+'1', '1'+mark+number]:
                    result = subprocess.run([str(self.programs[kind])],
                                            input=(' '+token+'\n').encode(),
                                            capture_output=True, timeout=3)
                    with self.subTest(kind=kind, length=len(number), token=token[:20]):
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn(b'runtime error', result.stderr)
                        self.assertIn(b'more than two digits', result.stderr)

    def test_empty_file_has_no_picture_and_succeeds(self):
        for kind in self.programs:
            with self.subTest(kind=kind):
                self.assertEqual(self.filter(kind, ''), '')

    def test_complete_and_unterminated_final_lines_match(self):
        for kind in self.programs:
            for ending in ['', '\n', ' ', ' \n']:
                with self.subTest(kind=kind, ending=ending):
                    self.assertEqual(self.filter(kind, self.assignment(kind)+ending),
                                     self.expected(kind))

    def test_no_duplicate_picture_at_eof_after_two_assignments(self):
        for kind in self.programs:
            for ending in ['', '\n']:
                with self.subTest(kind=kind, ending=ending):
                    data = self.assignment(kind)+'\n'+self.assignment(kind, True)+ending
                    self.assertEqual(self.filter(kind, data),
                                     self.expected(kind)+self.expected(kind, True))


if __name__ == '__main__':
    unittest.main()
