"""Compare small starvation cycles against explicit process semantics."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable
from test_dimacs_empty_clause import native_clauses

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'


class MutexStarvation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'starve.c'
        cls.program = work/'starve'
        subprocess.run(['ctangle', str(SOURCES/'sat-mutex.w'),
                        str(SOURCES/'sat-mutex-starve.ch'), str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(generated), '-o', str(cls.program)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, data, r, p):
        return subprocess.run([str(self.program), str(r), str(p)], input=data.encode(),
                              capture_output=True, timeout=5)

    def assert_cycle(self, data, r, p, expected):
        result = self.encode(data, r, p)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(satisfiable(native_clauses(result.stdout.decode())), expected)

    def test_zero_selects_b_and_rejects_a_maybe_only_cycle(self):
        self.assert_cycle('A0 maybe goto A0\nB0 maybe goto B0\n', 2, 0, False)

    def test_busy_b_can_starve_but_maybe_b_cannot(self):
        data = 'A0 maybe goto A0\nB0 b=0 goto B0\n'
        self.assert_cycle(data, 2, 0, True)
        self.assert_cycle(data, 3, 1, True)
        # Negative p selects A, whose every execution is a maybe step.
        self.assert_cycle(data, 3, -1, False)

    def test_busy_a_can_starve_only_when_selected(self):
        data = 'A0 a=0 goto A0\nB0 maybe goto B0\n'
        self.assert_cycle(data, 3, -1, True)
        self.assert_cycle(data, 3, 1, False)
        self.assert_cycle(data, 2, 0, False)

    def test_cycle_start_is_checked_before_absolute_value(self):
        data = 'A0 a=0 goto A0\nB0 b=0 goto B0\n'
        for r, p in [(3, 3), (3, -3), (3, 4), (3, -4),
                     (3, -2147483648), (2147483647, -2147483648),
                     (0, -2147483648), (-2147483648, -2147483648)]:
            with self.subTest(r=r, p=p):
                result = self.encode(data, r, p)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertEqual(result.stdout, b'')


if __name__ == '__main__':
    unittest.main()
