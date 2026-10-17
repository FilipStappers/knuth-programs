"""B059: clean EOF and a final unterminated assignment are normal input."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import re

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
        generated, cls.encoder = work/'encoder.c', work/'encoder'
        subprocess.run(['ctangle', str(SOURCES/'sat-tomography.w'), '-', str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.encoder)], check=True, capture_output=True)

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
            for number in ['100' if kind.startswith('life') else '201', '2147483648', '9'*10000]:
                for token in [number+mark+'1', '1'+mark+number]:
                    result = subprocess.run([str(self.programs[kind])],
                                            input=(' '+token+'\n').encode(),
                                            capture_output=True, timeout=3)
                    with self.subTest(kind=kind, length=len(number), token=token[:20]):
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn(b'runtime error', result.stderr)
                        expected = b'more than two digits' if kind.startswith('life') else b'out of range'
                        self.assertIn(expected, result.stderr)

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

    def test_complete_encoder_coordinate_domain(self):
        for m, n in [(100, 1), (200, 1), (1, 100), (200, 100)]:
            for ending in ['', '\n']:
                with self.subTest(m=m, n=n, ending=ending):
                    data = ''.join(' '+('' if (i+2*j) % 5 == 0 else '~')+f'{i}x{j}'
                                   for i in range(1, m+1) for j in range(1, n+1))
                    data += ' 297A0201 ~297B0201 295a0201 ~p297A01'+ending
                    expected = ''.join(''.join('*' if (i+2*j) % 5 == 0 else '.'
                                               for j in range(1, n+1))+'\n'
                                       for i in range(1, m+1))+'\n'
                    self.assertEqual(self.filter('tomography', data), expected)

    def test_tomography_pixel_ranges_and_ignored_auxiliaries(self):
        for token in ['0x1', '1x0', '201x1', '1x101', '000201x1', '1x000101']:
            result = subprocess.run([str(self.programs['tomography'])],
                                    input=(' '+token+'\n').encode(), capture_output=True, timeout=3)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b'runtime error', result.stderr)
            self.assertIn(b'out of range', result.stderr)
        self.assertEqual(self.filter('tomography', ' 299A0201 ~999999999A 1x1\n'), '*\n\n')

    def test_native_encoder_assignment_to_filter(self):
        for m, n in [(200, 1), (1, 100)]:
            bits = {(i, j): int((i+2*j) % 5 == 0) for i in range(1, m+1) for j in range(1, n+1)}
            groups = {f'r{i}': [(i, j) for j in range(1, n+1)] for i in range(1, m+1)}
            groups.update({f'c{j}': [(i, j) for i in range(1, m+1)] for j in range(1, n+1)})
            for d in range(1, m+n):
                groups[f'a{d}'] = [(i, j) for i, j in bits if i+j == d+1]
                groups[f'b{d}'] = [(i, j) for i, j in bits if i-j == d-n]
            data = ''.join(f'{key}={sum(bits[cell] for cell in cells)}\n' for key, cells in groups.items())
            encoded = subprocess.run([str(self.encoder)], input=data, text=True,
                                     capture_output=True, timeout=10)
            self.assertEqual(encoded.returncode, 0, encoded.stderr)
            self.assertNotIn('runtime error', encoded.stderr)
            clauses = [line.split() for line in encoded.stdout.splitlines()
                       if line and not line.startswith('~ ')]
            length = max(m, n)
            word = [bits[i, 1] for i in range(1, m+1)] if m > 1 else [bits[1, j] for j in range(1, n+1)]
            if sum(word) > length-sum(word):
                word = [1-bit for bit in word]
            counts = [0]*(2*length-1)
            counts[length-1:] = word
            for node in range(length-2, -1, -1):
                counts[node] = counts[2*node+1]+counts[2*node+2]
            values = {}
            for name in {literal.lstrip('~') for clause in clauses for literal in clause}:
                pixel = re.fullmatch(r'(\d+)x(\d+)', name)
                if pixel:
                    values[name] = bits[tuple(map(int, pixel.groups()))]
                else:
                    counter = re.fullmatch(r'1[RC]([0-9a-f]{2})([0-9a-f]{2})', name)
                    self.assertIsNotNone(counter, name)
                    node, threshold = (int(x, 16) for x in counter.groups())
                    values[name] = counts[node-1] >= threshold
            self.assertTrue(all(any(bool(values[literal.lstrip('~')]) != literal.startswith('~')
                                    for literal in clause) for clause in clauses))
            assignment = ''.join(' '+('' if value else '~')+name for name, value in sorted(values.items()))
            expected = ''.join(''.join('*' if bits[i, j] else '.' for j in range(1, n+1))+'\n'
                               for i in range(1, m+1))+'\n'
            self.assertEqual(self.filter('tomography', assignment), expected)


if __name__ == '__main__':
    unittest.main()
