"""B060: literal piece identity in older shape-encoder option rows."""
from collections import Counter
import os
from pathlib import Path
import random
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

    def test_optional_stick_points_do_not_remove_edge_placements(self):
        for board, shape, expected in [
            ('H00', 'H00 I10', ['P', 'H00']),
            ('H00', 'H10 I00', ['P', 'H00']),
            ('Hz0', 'H00 I10', ['P', 'Hz0']),
            ('H00 H10 | I10', 'H00 I10', ['P', 'H00', 'I10']),
        ]:
            with self.subTest(board=board, shape=shape):
                result = self.solve('polysticks', f'P\n{board}\nP 1 1 {shape}\n'.encode())
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                rows = [tuple(sorted(line.split())) for line in result.stdout.decode().splitlines()[1:]]
                self.assertIn(tuple(sorted(expected)), rows)
        result = self.solve('polysticks', b'P\nH00\nP 1 1 I00\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'no required edges', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)

    def test_endpoint_geometry_with_optional_points_and_all_orientations(self):
        rng = random.Random(60002)
        shapes = [['H00'], ['H00', 'V00'], ['H00', 'I10'], ['V00', 'I01'], ['H10', 'I00'],
                  ['H00', 'V10', 'I10'], ['H00', 'H10', 'V20', 'I10', 'I20']]
        universe = [(x, y, direction) for x in range(3) for y in range(3) for direction in ['H', 'V']]
        for case in range(10):
            edges = {edge for edge in universe if rng.randrange(3)}
            if not edges:
                edges.add((0, 0, 'H'))
            junctions = {(x, y) for x in range(3) for y in range(3) if rng.randrange(2)}
            board = ' '.join(f'{direction}{x}{y}' for x, y, direction in sorted(edges))
            if junctions:
                board += ' | '+' '.join(f'I{x}{y}' for x, y in sorted(junctions))
            for shape in shapes:
                expected = Counter()
                for reflected in [False, True]:
                    for rotation in range(4):
                        def transform(p):
                            x, y = p
                            if reflected:
                                x, y = y, x
                            for _ in range(rotation):
                                x, y = -y, x
                            return x, y
                        required, optional = [], []
                        for token in shape:
                            kind, x, y = token[0], int(token[1]), int(token[2])
                            if kind == 'I':
                                optional.append(transform((x, y)))
                            else:
                                p = transform((x, y))
                                q = transform((x+(kind == 'H'), y+(kind == 'V')))
                                required.append((min(p[0], q[0]), min(p[1], q[1]), 'H' if p[1] == q[1] else 'V'))
                        anchor_x, anchor_y, anchor_kind = required[0]
                        for bx, by, kind in edges:
                            if kind != anchor_kind:
                                continue
                            dx, dy = bx-anchor_x, by-anchor_y
                            placed = {(x+dx, y+dy, direction) for x, y, direction in required}
                            if not placed <= edges:
                                continue
                            row = ['P']+[f'{direction}{x}{y}' for x, y, direction in placed]
                            row += [f'I{x+dx}{y+dy}' for x, y in optional if (x+dx, y+dy) in junctions]
                            expected[tuple(sorted(row))] += 1
                with self.subTest(case=case, shape=shape):
                    result = self.solve('polysticks', ('P\n'+board+'\nP 4 2 '+' '.join(shape)+'\n').encode())
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    actual = Counter(tuple(sorted(line.split())) for line in result.stdout.decode().splitlines()[1:])
                    self.assertEqual(actual, expected)

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
