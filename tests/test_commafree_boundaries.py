"""B047: fixed capacities and independent commafree overlap checks."""
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EastmanCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.programs = []
        for name in ['commafree-eastman', 'commafree-eastman-new']:
            generated = cls.work/(name+'.c')
            subprocess.run(['ctangle', str(ROOT/'programs/programs'/(name+'.w')),
                            '-', str(generated)], check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_word(self, program, word):
        return subprocess.run([str(program), *map(str, word)], capture_output=True, timeout=5)

    def selected(self, program, word):
        result = self.run_word(program, word)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        if program == self.programs[0]:
            # The old interface prints a final phase with one boundary index.
            k = int(result.stdout.splitlines()[-1].split()[-1])
            return word[k:]+word[:k]
        return tuple(map(int, result.stdout.splitlines()[-1].split()))

    def test_over_capacity_is_rejected_before_array_access(self):
        for program in self.programs:
            for n in [107, 317]:
                with self.subTest(program=program.name, n=n):
                    result = self.run_word(program, (0,)*(n-1)+(1,))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b'at most 105', result.stderr)
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertEqual(result.stdout, b'')

    def test_largest_supported_primitive_word(self):
        word = (0,)*104+(1,)
        rotations = {word[k:]+word[:k] for k in range(len(word))}
        for program in self.programs:
            self.assertIn(self.selected(program, word), rotations)

    def test_multiphase_versions_can_choose_different_representatives(self):
        word = (1, 1, 2, 2, 0, 1, 1, 0, 2)
        old_reversed = self.selected(self.programs[0], word[::-1])[::-1]
        new = self.selected(self.programs[1], word)
        self.assertEqual(old_reversed, word)
        self.assertEqual(new, word[3:]+word[:3])
        self.assertNotEqual(new, old_reversed)

    def test_complete_small_codes_are_rotation_invariant_and_commafree(self):
        for n, alphabet in [(3, 3), (5, 3), (7, 2), (9, 2)]:
            for program in self.programs:
                by_necklace = {}
                for word in itertools.product(range(alphabet), repeat=n):
                    rotations = {word[k:]+word[:k] for k in range(n)}
                    if len(rotations) != n:
                        continue
                    output = self.selected(program, word)
                    self.assertIn(output, rotations)
                    key = min(rotations)
                    if key in by_necklace:
                        self.assertEqual(by_necklace[key], output)
                    by_necklace[key] = output
                code = set(by_necklace.values())
                self.assertEqual(len(code), len(by_necklace))
                for split in range(1, n):
                    suffixes = {w[-split:] for w in code}
                    prefixes = {w[:n-split] for w in code}
                    self.assertFalse(any(w[:split] in suffixes and w[split:] in prefixes
                                         for w in code))


if __name__ == '__main__':
    unittest.main()
