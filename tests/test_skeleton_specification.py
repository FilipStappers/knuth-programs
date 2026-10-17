"""Skeleton pattern-to-digit specification, before the large multiplication search."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'programs/programs/back-skeleton.w'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class SkeletonSpecification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        source, generated, cls.program = [work/('spec'+s) for s in ['.w', '.c', '']]
        text = SOURCE.read_text()
        marker = '    for (d=0;d<10;d++) {'
        assert text.count(marker) == 1
        probe = '''    printf("POS %d\\n",pos);
    for (i=0;i<=m;i++) {
      printf("OFF %d BITS ",off[i]);
      for (j=1;j<=constr[i][0];j++) printf("%d",constr[i][j]);
      printf("\\n");
    }
    return 0;
'''
        source.write_text(text.replace(marker, probe+marker))
        subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)
        # Give every fresh search a nonzero previous printed state, then inspect
        # its entry state instead of running the unbounded multiplier search.
        text = SOURCE.read_text().replace(marker, '    printed=1;\n'+marker)
        text = text.replace('@<Initialize the data structures@>;',
                            'printf("PRINTED %d\\n",printed); printed=1; continue;')
        source.write_text(text)
        subprocess.run(['ctangle', str(source), '-', str(generated)], check=True, capture_output=True)
        cls.printed_program = work/'printed'
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated), '-o', str(cls.printed_program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_each_digit_search_resets_printed_state(self):
        result = subprocess.run([str(self.printed_program), '2', '0'], input=b'*\n',
                                capture_output=True, timeout=5, env=ENV)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(re.findall(rb'PRINTED (\d+)', result.stdout), [b'0']*10)

    def test_pattern_rows_determine_offsets_and_constraints(self):
        for m in range(2, 8):
            for n in range(1, m+2):
                with self.subTest(m=m, n=n):
                    rows = [''.join('*' if (i+2*j) % 3 == 0 else '.' for j in range(8))
                            for i in range(n)]
                    result = subprocess.run([str(self.program), str(m), '0'],
                                            input=('\n'.join(rows)+'\n').encode(), capture_output=True,
                                            timeout=5, env=ENV)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    offsets = list(range(m))+[0]
                    pos = max(offsets[m+1-n+i]+row.rfind('*')+1
                              for i, row in enumerate(rows))-1
                    self.assertIn(f'POS {pos}\n'.encode(), result.stdout)
                    actual = re.findall(rb'OFF (\d+) BITS ([01]*)', result.stdout)
                    expected = []
                    for k, offset in enumerate(offsets):
                        row_index = k-(m+1-n)
                        positions = ({pos-offset-j for j, ch in enumerate(rows[row_index]) if ch == '*'}
                                     if row_index >= 0 else set())
                        bits = ''.join('1' if j in positions else '0'
                                       for j in range(max(positions, default=-1)+1))
                        expected.append((str(offset).encode(), bits.encode()))
                    self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
