"""B056: SAT13 storage and auxiliary-input regressions with Boolean oracles."""
import itertools
import os
import random
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Sat13Boundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for SAT13 checks')
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.source = (ROOT/'programs/programs/sat13.w').read_text()
        cls.sgb = sgb
        cls.programs = {}
        for name, source in [('normal', cls.source),
                             ('sanity', cls.source.replace('@d sanity_checking 0',
                                                           '@d sanity_checking 1'))]:
            literate = cls.work/(name+'.w')
            literate.write_text(source)
            generated = cls.work/(name+'.c')
            program = cls.work/name
            subprocess.run(['ctangle', str(literate), '-', str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-I'+sgb, '-fsanitize=address,undefined,bounds',
                            '-fno-sanitize-recover=all', str(generated),
                            str(Path(sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_solver(self, data, options=(), build='normal'):
        # This parser resolves repeated options to the leftmost occurrence.
        return subprocess.run([str(self.programs[build]), *options, 'v0', 'm18'],
                              input=data, capture_output=True, timeout=5,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))

    def check_formula(self, data, options=(), build='normal'):
        clauses = [line.split() for line in data.decode().splitlines()]
        names = sorted({lit.lstrip('~') for c in clauses for lit in c})
        expected = any(all(any(assignment[lit.lstrip('~')] != lit.startswith('~')
                               for lit in clause) for clause in clauses)
                       for bits in itertools.product([False, True], repeat=len(names))
                       for assignment in [dict(zip(names, bits))])
        result = self.run_solver(data, options, build)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        model = set(result.stdout.decode().split())
        if expected:
            self.assertTrue(model)
            self.assertTrue(all(any(lit in model for lit in clause) for clause in clauses))
            self.assertFalse(any(name in model and '~'+name in model for name in names))
        else:
            self.assertEqual(model, {'~'})
        return result

    def test_root_unary_level_sentinel(self):
        for data in [b'x\n', b'~x\n', b'x\ny\n', b'x\n~x\n']:
            with self.subTest(data=data):
                self.check_formula(data, build='sanity')

    def test_full_depth_and_full_run_level_sentinels(self):
        for size in range(1, 5):
            clauses = [' '.join(('~' if bit else '')+f'v{i}'
                                for i, bit in enumerate(bits))
                       for bits in itertools.product([False, True], repeat=size)]
            for last in [False, True]:
                data = ('\n'.join(clauses if last else clauses[:-1])+'\n').encode()
                for build in self.programs:
                    for options in [('w0',), ('w2', 'j1000', 'J1000')]:
                        with self.subTest(size=size, last=last, build=build, options=options):
                            self.check_formula(data, options, build)

    def test_every_nonempty_two_variable_clause_family(self):
        pool = [[('~' if sign < 0 else '')+f'x{i}'
                 for i, sign in enumerate(signs) if sign]
                for signs in itertools.product([0, 1, -1], repeat=2) if any(signs)]
        for mask in range(1, 1 << len(pool)):
            data = ''.join(' '.join(c)+'\n' for i, c in enumerate(pool)
                           if mask & (1 << i)).encode()
            with self.subTest(mask=mask):
                self.check_formula(data)

    def test_recycling_when_no_old_clause_has_a_scored_range(self):
        data = '\n'.join(' '.join(('~' if bit else '')+f'v{i}'
                                  for i, bit in enumerate(bits))
                         for bits in itertools.product([False, True], repeat=3))+'\n'
        for build in self.programs:
            with self.subTest(build=build):
                self.check_formula(data.encode(), ('w2', 'j2', 'J2'), build)

    def check_learned_proof(self, data, build):
        path = self.work/'learned.sat'
        self.check_formula(data, ('w2', 'j2', 'J2', 't1', 's37', 'l'+str(path)), build)
        known = [line.split() for line in data.decode().splitlines()]
        for clause in [line.split() for line in path.read_text().splitlines()]:
            # Reverse unit propagation: negate this clause, then derive conflict.
            assigned = {lit.lstrip('~'): lit.startswith('~') for lit in clause}
            conflict = any(name in clause and '~'+name in clause for name in assigned)
            changed = True
            while changed and not conflict:
                changed = False
                for old in known:
                    if any(lit.lstrip('~') in assigned and
                           assigned[lit.lstrip('~')] != lit.startswith('~') for lit in old):
                        continue
                    free = [lit for lit in old if lit.lstrip('~') not in assigned]
                    if not free:
                        conflict = True
                        break
                    if len(free) == 1:
                        lit = free[0]
                        assigned[lit.lstrip('~')] = not lit.startswith('~')
                        changed = True
            self.assertTrue(conflict, f'Failed RUP: {clause}')
            known.append(clause)

    def test_saved_recycling_witness_and_aggressive_learned_proofs(self):
        saved = (b'~v6 v2 v4\nv3 ~v7 v6\n~v7 ~v4 v5\n~v2 v3 v4\n'
                 b'~v3 ~v2 ~v6\n~v7 ~v8 ~v2\nv1 ~v8 v6\nv1 ~v7 v8\n'
                 b'~v7 ~v6 ~v5\nv6 ~v3 ~v1\n')
        rng = random.Random(56013)
        cases = [saved]
        for _ in range(32):
            clauses = []
            for _ in range(rng.randint(20, 36)):
                clauses.append(' '.join(('~' if rng.getrandbits(1) else '')+f'v{i}'
                                        for i in rng.sample(range(1, 9), 3)))
            cases.append(('\n'.join(clauses)+'\n').encode())
        for case, data in enumerate(cases):
            for build in self.programs:
                with self.subTest(case=case, build=build):
                    self.check_learned_proof(data, build)

    def test_duplicate_polarity_variables_are_rejected_before_heap_corruption(self):
        path = self.work/'duplicate.polarity'
        for text in ['x x\n', 'x ~x\n', 'y x y\n']:
            path.write_text(text)
            result = self.run_solver(b'x y\n~x y\nx ~y\n', ['z'+str(path)])
            with self.subTest(text=text):
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'Duplicate polarity variable', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_partial_polarity_heap_initializes_fallback_activity(self):
        # Poison only the activity slots in fresh vmem before ordinary setup.
        # Observe the independently stated nonnegative initial-activity invariant.
        setup = 'for (k=1;k<=vars;k++) o,vmem[k].value=unset,vmem[k].tloc=-1;'
        self.assertEqual(self.source.count(setup), 1)
        source = self.source.replace(setup,
                                    'for (k=1;k<=vars;k++) vmem[k].activity=-123.0;\n'+setup)
        insertion = 'else @<Initialize the heap randomly@>;'
        self.assertEqual(source.count(insertion), 1)
        source = source.replace(insertion, insertion+'''
for (k=1;k<=vars;k++) if (vmem[k].activity<0.0) {
  fprintf(stderr,"Uninitialized fallback activity!\\n");
  exit(90);
}
''')
        literate = self.work/'activity-observer.w'
        literate.write_text(source)
        generated = self.work/'activity-observer.c'
        program = self.work/'activity-observer'
        subprocess.run(['ctangle', str(literate), '-', str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-I'+self.sgb, '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated),
                        str(Path(self.sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                       check=True, capture_output=True)
        path = self.work/'partial.polarity'
        for text in ['', 'x\n', '~y\n', 'obsolete\nx\n']:
            path.write_text(text)
            result = subprocess.run([str(program), 'v0', 'm18', 'z'+str(path)],
                                    input=b'x y\n~x y\nx ~y\n', capture_output=True,
                                    timeout=5, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
            with self.subTest(text=text):
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(set(result.stdout.decode().split()), {'x', 'y'})

    def test_partial_and_complete_polarity_files_preserve_formula_models(self):
        data = b'x y z\n~x y\n~y z\n~z x\n'
        path = self.work/'valid.polarity'
        for text in ['', 'x\n', '~y\n', 'obsolete\nx\n', 'z ~y x\n', 'y z ~x\n']:
            path.write_text(text)
            for build in self.programs:
                with self.subTest(text=text, build=build):
                    self.check_formula(data, ['z'+str(path)], build)

    def test_polarity_tokens_are_bounded_independently_of_clause_buffer(self):
        path = self.work/'long.polarity'
        for size in [9, 1024, 4096]:
            for prefix in ['', '~']:
                path.write_text(prefix+'x'*size+'\n')
                result = self.run_solver(b'x\n', ['b3', 'z'+str(path)])
                with self.subTest(size=size, prefix=prefix):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(b'AddressSanitizer', result.stderr)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertEqual(result.stdout, b'')

    def test_polarity_grammar_and_complete_eight_character_names(self):
        path = self.work/'tokens.polarity'
        for token in [b'~', b'a~', b'x\0junk', b'\x7f', b'\xff']:
            path.write_bytes(token+b'\n')
            result = self.run_solver(b'x\n', ['z'+str(path)])
            with self.subTest(token=token):
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
        for token in [b'abcdefgh', b'~abcdefgh', b'abcdefgh\t~ijklmnop']:
            path.write_bytes(token)  # EOF may terminate a token.
            with self.subTest(token=token):
                self.check_formula(b'abcdefgh ijklmnop\n', ['z'+str(path)])
        # An unknown eight-byte name must also fit when the clause buffer is tiny.
        path.write_bytes(b'abcdefgh')
        self.check_formula(b'x\n', ['b3', 'z'+str(path)])

    def test_largest_memory_exponent_uses_unsigned_shift(self):
        self.check_formula(b'x\n', ['m31'])

    def test_learned_storage_checks_capacity_before_the_sentinel_write(self):
        # Simulate exhaustion at the first learned allocation by shrinking only
        # the unused tail. The original data and learning logic remain intact.
        marker = 'c=max_learned; /* this will be the address of the new clause */'
        self.assertEqual(self.source.count(marker), 1)
        source = self.source.replace(marker, '''
memsize=max_learned+learned_size;
max_cells_used=max_learned;
mem=(cel*)realloc(mem,memsize*sizeof(cel));
if (!mem) exit(91);
'''+marker)
        literate = self.work/'exhausted.w'
        literate.write_text(source)
        generated = self.work/'exhausted.c'
        program = self.work/'exhausted'
        subprocess.run(['ctangle', str(literate), '-', str(generated)],
                       check=True, capture_output=True)
        subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                        '-I'+self.sgb, '-fsanitize=address,undefined,bounds',
                        '-fno-sanitize-recover=all', str(generated),
                        str(Path(self.sgb)/'gb_flip.c'), '-lm', '-o', str(program)],
                       check=True, capture_output=True)
        data = '\n'.join(' '.join(('~' if bit else '')+f'v{i}'
                                  for i, bit in enumerate(bits))
                         for bits in itertools.product([False, True], repeat=3))+'\n'
        result = subprocess.run([str(program), 'v0', 'm18', 'w0'], input=data.encode(),
                                capture_output=True, timeout=5,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        self.assertGreater(result.returncode, 0)
        self.assertIn(b'Memory overflow', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertEqual(result.stdout, b'')


if __name__ == '__main__':
    unittest.main()
