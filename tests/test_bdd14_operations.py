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
        cls.cache_programs = {}
        cls.fault_programs = {}
        for name, relative in [('archive', 'archives/bdd-zdd-utils/bdd14.w'),
                               ('program', 'programs/bdd14.w'),
                               ('zdd', 'archives/bdd-zdd-utils/bdd15.w')]:
            work = cls.work/name
            work.mkdir()
            generated = work/'bdd14.c'
            subprocess.run(['ctangle', str(ROOT/'programs'/relative), '-', str(generated)],
                           check=True, capture_output=True)
            text = generated.read_text()
            assert text.count('exit(0);') == 1
            (work/'bdd-under-test.c').write_text(text.replace('exit(0);', 'return 0;'))
            harness = work/'reference.c'
            harness.write_text(('#define ZDD\n' if name == 'zdd' else '')+
                               (ROOT/'tests/bdd14_reference.c').read_text())
            program = work/'reference'
            # Original representation requires low 32-bit static addresses and
            # deliberate overlaid storage; preserve those documented assumptions.
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fno-strict-aliasing', '-no-pie', '-I'+sgb,
                            str(harness), str(Path(sgb)/'gb_flip.c'), '-o', str(program)],
                           check=True, capture_output=True)
            cls.cache_programs[name] = program
            if name != 'zdd':
                cls.programs[name] = program
            else:
                for mode, statement in [('coprod-failure', 'r1=coprod_rec(node_(f->hi),node_(g->hi));'),
                                         ('quot-failure', 'f0=ezrem_rec(f,vg);')]:
                    source = (ROOT/'programs'/relative).read_text()
                    assert source.count(statement) == 1
                    fault = cls.work/mode
                    fault.mkdir()
                    result = 'r1' if mode.startswith('coprod') else 'f0'
                    literate = fault/'fault.w'
                    literate.write_text(source.replace(statement, result+'=NULL;'))
                    generated_fault = fault/'fault.c'
                    subprocess.run(['ctangle', str(literate), '-', str(generated_fault)],
                                   check=True, capture_output=True)
                    (fault/'bdd-under-test.c').write_text(generated_fault.read_text().replace(
                        'exit(0);', 'return 0;'))
                    harness = fault/'reference.c'
                    harness.write_text('#define ZDD\n'+(ROOT/'tests/bdd14_reference.c').read_text())
                    program = fault/'reference'
                    subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                                    '-fno-strict-aliasing', '-no-pie', '-I'+sgb,
                                    str(harness), str(Path(sgb)/'gb_flip.c'), '-o', str(program)],
                                   check=True, capture_output=True)
                    cls.fault_programs[mode] = program
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

    def test_cache_doubling_retains_relocated_memo(self):
        for name, program in self.cache_programs.items():
            result = subprocess.run([str(program), str(self.commands), 'cache'],
                                    capture_output=True, timeout=10)
            with self.subTest(revision=name):
                self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
                self.assertIn(b'CACHE before=1 after=1 pages=2', result.stdout)
                self.assertNotIn(b'\n! ', result.stdout)

    def test_zdd_coproduct_releases_low_result_after_high_failure(self):
        mode = 'coprod-failure'
        result = subprocess.run([str(self.fault_programs[mode]), str(self.commands), mode],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
        self.assertIn(b'COPROD_FAILURE returned_null=1', result.stdout)
        self.assertNotIn(b'\n! ', result.stdout)

    def test_all_three_element_zdd_coproduct_families(self):
        result = subprocess.run([str(self.cache_programs['zdd']), str(self.commands), 'coprod'],
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
        self.assertIn(b'COPROD cases=65536 failures=0', result.stdout)
        self.assertNotIn(b'\n! ', result.stdout)

    def test_zdd_quotient_releases_acquired_result_after_remainder_failure(self):
        mode = 'quot-failure'
        result = subprocess.run([str(self.fault_programs[mode]), str(self.commands), mode],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
        self.assertIn(b'QUOT_FAILURE returned_null=1', result.stdout)
        self.assertNotIn(b'\n! ', result.stdout)

    def test_all_three_element_zdd_quotient_families(self):
        result = subprocess.run([str(self.cache_programs['zdd']), str(self.commands), 'quot'],
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout.decode()+result.stderr.decode())
        self.assertIn(b'QUOT cases=65536 failures=0', result.stdout)
        self.assertNotIn(b'\n! ', result.stdout)


if __name__ == '__main__':
    unittest.main()
