"""B052: polyform input boundaries with independently constructed placements."""
from collections import Counter
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def matrix(output):
    lines = [line.split() for line in output.decode().splitlines()
             if line.strip() and not line.startswith('|')]
    return lines[0], Counter(tuple(sorted(row)) for row in lines[1:])


class PolyformParsers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for name in ['polyomino', 'polyiamond', 'polycube']:
            generated = cls.work/(name+'.c')
            source = ROOT/'programs/programs'/(name+'-dlx.w')
            subprocess.run(['ctangle', str(source), '-', str(generated)],
                           check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, name, data):
        return subprocess.run([str(self.programs[name])], input=data, capture_output=True,
                              timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_unprefixed_piece_line_exceeds_multiplicity_scratch(self):
        for name in ['polyomino', 'polyiamond']:
            with self.subTest(name=name):
                result = self.solve(name, b'00 01 02\nD 00 01 02\n')
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                header, options = matrix(result.stdout)
                self.assertEqual(set(header), {'00', '01', '02', 'D'})
                self.assertTrue(options)
                self.assertTrue(all(set(row) <= set(header) for row in options))

    def test_explicit_multiplicity_capacity(self):
        for name in ['polyomino', 'polyiamond']:
            result = self.solve(name, b'00\n1234567|D 00\n')
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn('1234567|D', matrix(result.stdout)[0])
            for prefix in [b'12345678', b'9'*100]:
                with self.subTest(name=name, prefix=prefix):
                    result = self.solve(name, b'00\n'+prefix+b'|D 00\n')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b'Multiplicity too long', result.stderr)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_full_piece_table_allows_existing_names_and_rejects_new_names(self):
        names = {f'P{i:03}' for i in range(100)}
        for name in self.programs:
            cell = '000' if name == 'polycube' else '00'
            data = cell+'\n'+''.join(piece+' '+cell+'\n' for piece in sorted(names))
            for repeated in [False, True]:
                with self.subTest(name=name, repeated=repeated):
                    result = self.solve(name, (data+('P000 '+cell+'\n' if repeated else '')).encode())
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(set(matrix(result.stdout)[0]), names | {cell})
            with self.subTest(name=name, extra=True):
                result = self.solve(name, (data+'Extra '+cell+'\n').encode())
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'maxpieces', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_short_name_after_reused_long_scratch_has_no_stale_suffix(self):
        for name in self.programs:
            with self.subTest(name=name):
                cell = '000' if name == 'polycube' else '00'
                data = cell+'\n'+''.join(piece+' '+cell+'\n' for piece in ['ABCDEFGH', 'ABCDEFGH', 'Q'])
                result = self.solve(name, data.encode())
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(set(matrix(result.stdout)[0]), {'ABCDEFGH', 'Q', cell})

    def test_square_suffix_capacity_and_reused_tags(self):
        for size in [1, 9, 10]:
            tags = {f'00s{i}' for i in range(size)}
            data = '00 '+' '.join(sorted(tags))+'\nD 00 '+f'00s{size-1}\n'
            with self.subTest(size=size):
                result = self.solve('polyomino', data.encode())
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                header, options = matrix(result.stdout)
                self.assertEqual(set(header), tags | {'00', 'D', '|'})
                self.assertEqual(options, Counter({tuple(sorted(['00', 'D', f'00s{size-1}'])): 1}))
        data = '00 '+' '.join(f'00s{i}' for i in range(11))+'\nD 00\n'
        result = self.solve('polyomino', data.encode())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'maxsuffixes', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_cube_domino_placements(self):
        cells = {f'{x}{y}{z}' for x in range(2) for y in range(2) for z in range(2)}
        expected = Counter(tuple(sorted(['D', f'{x}{y}{z}', f'{x+dx}{y+dy}{z+dz}']))
                           for x in range(2) for y in range(2) for z in range(2)
                           for dx, dy, dz in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
                           if f'{x+dx}{y+dy}{z+dz}' in cells)
        result = self.solve('polycube', (' '.join(sorted(cells))+'\nD 000 001\n').encode())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        header, options = matrix(result.stdout)
        self.assertEqual(set(header), cells | {'D'})
        self.assertEqual(options, expected)

    def test_square_domino_placements(self):
        cells = {f'{x}{y}' for x in range(2) for y in range(3)}
        expected = Counter(tuple(sorted(['D', f'{x}{y}', f'{x+dx}{y+dy}']))
                           for x in range(2) for y in range(3) for dx, dy in [(1, 0), (0, 1)]
                           if f'{x+dx}{y+dy}' in cells)
        result = self.solve('polyomino', (' '.join(sorted(cells))+'\nD 00 01\n').encode())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        header, options = matrix(result.stdout)
        self.assertEqual(set(header), cells | {'D'})
        self.assertEqual(options, expected)

    def test_single_triangle_placements(self):
        cells = {'00', "00'", '01', "01'"}
        result = self.solve('polyiamond', (' '.join(sorted(cells))+'\nD 00\n').encode())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        header, options = matrix(result.stdout)
        self.assertEqual(set(header), cells | {'D'})
        self.assertEqual(options, Counter(tuple(sorted(['D', cell])) for cell in cells))


if __name__ == '__main__':
    unittest.main()
