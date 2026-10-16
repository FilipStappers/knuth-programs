"""B059: Heule state exclusions must handle exactly two control states."""
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from test_dimacs_empty_clause import native_clauses, native_has_extension

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'
VARIANTS = ['sat-mutex', 'sat-mutex-distinct', 'sat-mutex-distinct-lemmas',
            'sat-mutex-starve', 'sat-mutex-starve-lemmas']


class MutexExclusion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = {}
        for name in VARIANTS:
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(SOURCES/'sat-mutex.w'),
                            str(SOURCES/(name+'.ch')) if name != 'sat-mutex' else '-',
                            str(generated)], capture_output=True, check=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True,
                           capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, name, n, raw=False):
        data = ''.join(f'{p}{k} {"critical" if k else "maybe"} goto {p}{(k+1)%n}\n'
                       for p in 'AB' for k in range(n))
        lemmas = self.work/'states.lemmas'
        lemmas.write_text(''.join(' '.join(f'{p}{k}' for k in range(n))+'\n'
                                 for p in 'AB'))
        # The starvation variant folds its final time back to p and deliberately
        # emits no exclusion at that final time. Use a nonfinal time-one layer.
        args = ['2' if name == 'sat-mutex-starve' else '1']
        if name.endswith('-lemmas'):
            args.append(str(lemmas))
        elif name == 'sat-mutex-starve':
            args.append('0')
        result = subprocess.run([str(self.programs[name]), *args], input=data.encode(),
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'runtime error', result.stderr)
        return result.stdout.decode() if raw else native_clauses(result.stdout.decode())

    def test_distinct_lemma_header_uses_the_supplied_path(self):
        output = self.encode('sat-mutex-distinct-lemmas', 3, raw=True)
        self.assertIn(str(self.work/'states.lemmas'), output.splitlines()[0])

    def test_two_states_all_variants(self):
        for name in VARIANTS:
            with self.subTest(variant=name):
                self.encode(name, 2)

    def test_exact_at_most_one_projection_for_one_through_eight_states(self):
        for name in VARIANTS:
            for n in range(1, 9):
                clauses = self.encode(name, n)
                for process in 'AB':
                    # Isolate this process's time-one exclusion clauses. The
                    # transition/goal/lemma clauses have other names or positive
                    # control-state literals and are excluded from this oracle.
                    pattern = rf'~?001(?:{process}\d+|_{process}\d+)'
                    exclusions = [c for c in clauses
                                  if all(re.fullmatch(pattern, lit) for lit in c)
                                  and not any(re.fullmatch(rf'001{process}\d+', lit)
                                              for lit in c)]
                    for bits in itertools.product([False, True], repeat=n):
                        values = {f'001{process}{k}': v for k, v in enumerate(bits)}
                        with self.subTest(variant=name, n=n, process=process, bits=bits):
                            self.assertEqual(native_has_extension(exclusions, values),
                                             sum(bits) <= 1)


if __name__ == '__main__':
    unittest.main()
