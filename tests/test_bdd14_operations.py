"""B033/B035: both separately published BDD14 revisions follow truth tables."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Bdd14Operations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for BDD14 checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for name, relative in [('archive', 'archives/bdd-zdd-utils/bdd14.w'),
                               ('program', 'programs/bdd14.w')]:
            work = cls.work/name
            work.mkdir()
            generated = work/'bdd14.c'
            subprocess.run(['ctangle', str(ROOT/'programs'/relative), '-', str(generated)],
                           check=True, capture_output=True)
            text = generated.read_text()
            assert text.count('exit(0);') == 1
            (work/'bdd-under-test.c').write_text(text.replace('exit(0);', 'return 0;'))
            harness = work/'reference.c'
            harness.write_text((ROOT/'tests/bdd14_reference.c').read_text())
            program = work/'reference'
            # Original representation requires low 32-bit static addresses and
            # deliberate overlaid storage; preserve those documented assumptions.
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fno-strict-aliasing', '-no-pie', '-I'+sgb,
                            str(harness), str(Path(sgb)/'gb_flip.c'), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program
        cls.commands = cls.work/'quit.bddl'
        cls.commands.write_text('v0\nq\n')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_three_variable_fused_quantifications(self):
        for name, program in self.programs.items():
            result = subprocess.run([str(program), str(self.commands)],
                                    capture_output=True, timeout=30)
            with self.subTest(revision=name):
                self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
                self.assertIn(b'FUSED cases=524288 failures=0', result.stdout)
                self.assertNotIn(b'\n! ', result.stdout)

    def test_constant_composition_acquires_its_result_reference(self):
        for name, program in self.programs.items():
            result = subprocess.run([str(program), str(self.commands), 'compose'],
                                    capture_output=True, timeout=10)
            with self.subTest(revision=name):
                self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
                self.assertIn(b'COMPOSE failures=0', result.stdout)
                self.assertNotIn(b'\n! ', result.stdout)


if __name__ == '__main__':
    unittest.main()
