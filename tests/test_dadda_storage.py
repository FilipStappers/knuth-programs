"""Dadda row/queue capacities and direct bounded factor feasibility."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

SOURCES = Path(__file__).resolve().parents[1]/'programs/archives/SATexamples/sources'
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


class DaddaStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs, cls.small, cls.initial = {}, {}, {}
        for mode in ['fifo', 'lifo', 'miter']:
            generated = cls.work/(mode+'.c')
            change = '-' if mode == 'fifo' else str(SOURCES/('sat-dadda-'+mode+'.ch'))
            subprocess.run(['ctangle', str(SOURCES/'sat-dadda.w'), change, str(generated)],
                           check=True, capture_output=True)
            cls.programs[mode] = cls.build(generated, mode)
            text = generated.read_text()
            assert '#include <stdlib.h>' in text
            quiet = text.replace('#include <stdlib.h>', '#include <stdlib.h>\n#define printf(...) (0)')
            limited = cls.work/(mode+'-small.c')
            limited.write_text(quiet.replace('#define nmax 1000', '#define nmax 8'))
            cls.small[mode] = cls.build(limited, mode+'-small')
            marker = r'for\s*\(\s*k\s*=\s*3\s*;\s*k\s*<=\s*m\s*\+\s*n\s*;\s*k\s*\+\+\s*\)'
            assert len(re.findall(marker, quiet)) == 1
            initial = cls.work/(mode+'-initial.c')
            initial.write_text(re.sub(marker, lambda match: 'return 0;\n'+match[0], quiet))
            cls.initial[mode] = cls.build(initial, mode+'-initial')

    @classmethod
    def build(cls, source, name):
        program = cls.work/name
        subprocess.run(['gcc', '-std=gnu99', '-O1', '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(source), '-o', str(program)],
                       check=True, capture_output=True)
        return program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_encoder(self, programs, mode, m, n, z=0):
        args = [str(programs[mode]), str(m), str(n)]
        if mode != 'miter':
            args.append(str(z))
        return subprocess.run(args, capture_output=True, timeout=15, env=ENV)

    def test_default_maximum_initial_product_rows(self):
        for mode in self.initial:
            result = self.run_encoder(self.initial, mode, 1000, 1000)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_reduced_capacity_carry_queues(self):
        for mode in self.small:
            for n in range(2, 9):
                for m in range(2, n+1):
                    result = self.run_encoder(self.small, mode, m, n)
                    self.assertEqual(result.returncode, 0, (mode, m, n, result.stderr.decode()))

    def test_factor_feasibility_and_miters(self):
        for m, n in [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]:
            possible = {x*y for x in range(1 << m) for y in range(1 << n)}
            for mode in ['fifo', 'lifo']:
                for z in range(1 << (m+n)):
                    result = self.run_encoder(self.programs, mode, m, n, z)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    formula = [row.split() for row in result.stdout.decode().splitlines()
                               if row.strip() and not row.startswith('~ ')]
                    self.assertEqual(satisfiable(formula), z in possible, (mode, m, n, z))
            result = self.run_encoder(self.programs, 'miter', m, n)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            formula = [row.split() for row in result.stdout.decode().splitlines()
                       if row.strip() and not row.startswith('~ ')]
            self.assertFalse(satisfiable(formula), (m, n))


if __name__ == '__main__':
    unittest.main()
