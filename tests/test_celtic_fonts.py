"""Compare font segment endpoints to converter specifications; compile both fonts."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

PROGRAMS = Path(__file__).resolve().parents[1]/'programs/programs'


class CelticFonts(unittest.TestCase):
    def check_family(self, octal, expected):
        for font in ['celtica', 'celticb']:
            with self.subTest(font=font):
                match = re.search(r'doublechar(?:wbw|bwb)?\(oct"'+octal+r'",(\d),(\d),(\d),(\d)\);',
                                  (PROGRAMS/(font+'.mf')).read_text())
                self.assertIsNotNone(match)
                i, j, k, l = map(int, match.groups())
                self.assertEqual({frozenset((i, j)), frozenset((k, l))},
                                 {frozenset(edge) for edge in expected})

    def test_family_150_endpoints(self):
        self.check_family('150', [(0, 5), (1, 4)])

    @unittest.skipUnless(shutil.which('mf'), 'MetaFont is required for native font compilation')
    def test_native_fonts_compile(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            for font, count in [('celtica', 219), ('celticb', 211)]:
                for name in [font+'.mf', font+'13.mf']:
                    shutil.copyfile(PROGRAMS/name, work/name)
                result = subprocess.run(['mf', '-interaction=nonstopmode', '-halt-on-error',
                                         '\\mode:=proof; input '+font+'13'], cwd=work,
                                        capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout.decode(errors='replace'))
                self.assertIn(f'({count} characters'.encode(), result.stdout)
                outputs = list(work.glob(font+'13.*gf'))
                self.assertEqual(len(outputs), 1)
                self.assertGreater(outputs[0].stat().st_size, 0)


if __name__ == '__main__':
    unittest.main()
