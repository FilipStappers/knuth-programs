"""Queenon physical drawing positions against exact rectangle/strip geometry."""
from fractions import Fraction as F
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

PROGRAMS = Path(__file__).resolve().parents[1]/'programs/programs'


def expected_colors(N, n):
    colors = {}
    for y in range(n):
        for x in range(n):
            I = math.floor(F(N*(x+y), n))+1
            ymax = min(F(y+1, n), F(I, N)-F(x, n))
            J = math.ceil(N*(1+ymax-F(x, n)))
            color = 'WRGB'[2*(I % 2)+(J % 2)]
            if color != 'W':
                colors[x, y] = color
    return colors


@unittest.skipUnless(all(shutil.which(tool) for tool in ('mpost', 'kpsewhich', 'ctangle', 'gcc')),
                     'MetaPost, kpsewhich, CWEB ctangle and GCC required')
class QueenonDrawing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        locate = subprocess.run(['kpsewhich', 'plain.mp'], capture_output=True, text=True)
        if locate.returncode or not locate.stdout.strip():
            raise unittest.SkipTest('MetaPost plain base inputs are required')
        base = Path(locate.stdout.strip()).parent
        if not (base/'mpost.mp').exists():
            raise unittest.SkipTest('MetaPost plain base inputs are required')
        cls.env = dict(os.environ, MPINPUTS=str(base)+'//:', MPMEMS=str(cls.work)+':')
        result = subprocess.run(['mpost', '-ini', '-interaction=nonstopmode', '-halt-on-error',
                                 '-jobname=mpost', str(base/'mpost.mp')], cwd=cls.work,
                                capture_output=True, timeout=30, env=cls.env)
        if result.returncode:
            raise RuntimeError(result.stdout.decode()+result.stderr.decode())
        source, generated, cls.program = [cls.work/('queen'+s) for s in ['.w', '.c', '']]
        source.write_text((PROGRAMS/'queenon-partition.w').read_text().replace(
            '/tmp/queenon-partition-%d-%d.mp', str(cls.work/'queen-%d-%d.mp')))
        subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', str(generated),
                        '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def physical_colors(self, text):
        # Observe actual native picture corners after the original translation;
        # neither the row order nor the draw operation is replaced.
        draw = r'draw pic\[ASCII ch\] shifted (\([^;]+\));'
        def observe(match):
            picture = '(pic[ASCII ch] shifted '+match[1]+')'
            return match[0]+'\n if ch<>"W": message "CELL " & decimal(xpart(llcorner'+picture+')/h)'+\
                ' & " " & decimal(ypart(llcorner'+picture+')/h) & " " & ch; fi;'
        self.assertEqual(len(re.findall(draw, text)), 1)
        observed = re.sub(draw, observe, text)
        path = self.work/'observed.mp'
        path.write_text(observed)
        result = subprocess.run(['mpost', '-interaction=nonstopmode', '-halt-on-error', path.name],
                                cwd=self.work, capture_output=True, timeout=30, env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
        colors = {}
        for x, y, color in re.findall(r'CELL (-?[\d.]+) (-?[\d.]+) ([RGB])', result.stdout.decode()):
            xx, yy = float(x), float(y)
            self.assertAlmostEqual(xx, round(xx), places=2)
            self.assertAlmostEqual(yy, round(yy), places=2)
            self.assertNotIn((round(xx), round(yy)), colors)
            colors[round(xx), round(yy)] = color
        return colors

    def test_generated_picture_coordinates(self):
        for N in range(1, 6):
            for n in sorted({1, N*N, N*N+1, 2*N*N+1}):
                result = subprocess.run([str(self.program), str(N), str(n)],
                                        capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                text = (self.work/f'queen-{N}-{n}.mp').read_text()
                self.assertEqual(self.physical_colors(text), expected_colors(N, n), (N, n))

    def test_companion_example_coordinates(self):
        text = (PROGRAMS/'queenon-partition.mp').read_text()
        # Figure 0 is a separate labeled partition. Retain the actual figure-1
        # row macro and data; omit figure 0 to avoid unrelated font dependencies.
        text = re.sub(r'beginfig\(0\).*?endfig;', '', text, count=1, flags=re.S)
        self.assertEqual(self.physical_colors(text), expected_colors(4, 17))


if __name__ == '__main__':
    unittest.main()
