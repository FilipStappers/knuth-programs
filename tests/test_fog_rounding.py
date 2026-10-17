"""Fontographer metric/contour rounding, including negative coordinates."""
from fractions import Fraction
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'programs/programs/fog2mf.w'


def nearest(value):
    value = Fraction(value)
    return (1 if value >= 0 else -1)*int(abs(value)+Fraction(1, 2))


class FogRounding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated, cls.program = work/'fog.c', work/'fog'
        subprocess.run(['ctangle', str(SOURCE), '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-Wno-implicit-function-declaration',
                        '-O1', str(generated), '-o', str(cls.program)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def convert(self, depth, contour='0 0 moveto\nclosepath\n'):
        text = f'''C 36 ; WX 482 ; N dollar ; B 23 {depth} 437 751 ;
/dollar{{482 0 0 0 0 0 Cache
{contour}0 FillStroke
}}def
'''
        result = subprocess.run([str(self.program)], input=text.encode(), capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result.stdout.decode()

    def test_negative_metric_depth_and_half_units(self):
        for depth in ['-205', '-205.5', '-205.125', '-0.5', '-0.125', '0', '12.5']:
            text = self.convert(depth)
            self.assertIn(f'beginchar(36,482u#,751u#,{max(0, -nearest(depth))}u#);', text)

    def test_signed_contour_coordinates(self):
        for start in ['-10.5', '-0.5', '0.5', '10.5']:
            contour = f'{start} -11.5 moveto\n-2.125 1.5 rlineto\n'
            contour += '-1.5 2.125 -2.5 -3.5 4.125 -5.5 rrcurveto\nclosepath\n'
            text = self.convert('-205', contour)
            x, y = Fraction(start), Fraction('-11.5')
            expected = [(nearest(x), nearest(y))]
            x += Fraction('-2.125'); y += Fraction('1.5')
            expected.append((nearest(x), nearest(y)))
            curve = []
            for dx, dy in [('-1.5', '2.125'), ('-2.5', '-3.5'), ('4.125', '-5.5')]:
                x += Fraction(dx); y += Fraction(dy)
                curve.extend([nearest(x), nearest(y)])
            self.assertIn(f'stroke ({expected[0][0]},{expected[0][1]})', text)
            self.assertIn(f'--({expected[1][0]},{expected[1][1]})', text)
            self.assertIn('...('+','.join(map(str, curve))+')', text)

    def test_documented_positive_contour_is_preserved(self):
        text = self.convert('442', '187.702 623.194 moveto\n'
                            '-0.297607 -29.4158 -111.106 -124.124 -24 -28 rrcurveto\n'
                            '-19 10 rlineto\nclosepath\n')
        self.assertIn('stroke (188,623)', text)
        self.assertIn('...(187,594,76,470,52,442)', text)
        self.assertIn('--(33,452)', text)


if __name__ == '__main__':
    unittest.main()
