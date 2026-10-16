"""B049: null/empty choices and an independent occupied-cell connectivity oracle."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WordcrossRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for wordcross rendering')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        text = (ROOT/'programs/programs/dlx3.w').read_text()
        for key, value in [('max_level', 128), ('max_cols', 256), ('max_nodes', 8192)]:
            text, count = re.subn(r'(?m)^@d '+key+r' [^\n]+', f'@d {key} {value}', text)
            assert count == 1
        source = cls.work/'dlx3.w'
        source.write_text(text)
        generated = cls.work/'wordcross.c'
        subprocess.run(['ctangle', str(source), str(ROOT/'programs/programs/dlx3-sharp-wordcross.ch'),
                        str(generated)], check=True, capture_output=True)
        cls.program = cls.work/'wordcross'
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-I'+sgb,
                        '-ftrivial-auto-var-init=pattern', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), str(Path(sgb)/'gb_flip.c'),
                        '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def solve(self, data):
        return subprocess.run([str(self.program), 'm1', 'v1'], input=data,
                              capture_output=True, timeout=3,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def test_null_and_all_dot_solutions_have_no_nonempty_connected_board(self):
        for matrix in [b'0:1|#A\n', b'#A | 00\n#A 00:.\n']:
            with self.subTest(matrix=matrix):
                result = self.solve(matrix)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertIn(b'Altogether 1 solution', result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_optional_word_preserves_its_nonempty_board(self):
        result = self.solve(b'0:1|#A | 00\n#A 00:a\n')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'Altogether 2 solutions', result.stderr)
        self.assertRegex(result.stdout, rb'^a #[12]\n$')

    def test_all_two_by_three_occupancies_use_four_neighbor_connectivity(self):
        cells = [(x, y) for x in range(2) for y in range(3)]
        header = ' '.join('#'+str(i) for i in range(6))+' | '+' '.join(f'{x}{y}' for x, y in cells)
        lines = [header]
        for i, (x, y) in enumerate(cells):
            for color in ['.', 'a']:
                lines.append(f'#{i} {x}{y}:{color}')
        expected = set()
        for mask in range(1, 64):
            occupied = {v for i, v in enumerate(cells) if mask >> i & 1}
            todo = [next(iter(occupied))]
            seen = set(todo)
            while todo:
                x, y = todo.pop()
                for neighbor in [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]:
                    if neighbor in occupied and neighbor not in seen:
                        seen.add(neighbor)
                        todo.append(neighbor)
            if seen == occupied:
                expected.add('|'.join(''.join('a' if (x, y) in occupied else '.'
                                              for y in range(3)) for x in range(2)))
        result = self.solve(('\n'.join(lines)+'\n').encode())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'Altogether 64 solutions', result.stderr)
        actual = [line.rsplit(' #', 1)[0] for line in result.stdout.decode().splitlines()]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))


if __name__ == '__main__':
    unittest.main()
