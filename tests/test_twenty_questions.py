"""Twenty Questions answers independently graded from the printed statements."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

PROGRAMS = Path(__file__).resolve().parents[1]/'programs/programs'


def question15_matches(answer, variant):
    odds = {i for i, letter in enumerate(answer, 1) if i % 2 and letter.upper() == 'A'}
    option = ord(answer[14].upper())-ord('A')
    claim = odds != {11} if variant == 'base' and option == 2 else odds == {7+2*option}
    return claim == answer[14].isupper()


class TwentyQuestions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        for variant, change in [('base', None), ('modified', 'back-20q-backmod9,15.ch'),
                                ('indeterminate', 'back-20q-backmod9,15-indet.ch')]:
            generated, program = work/(variant+'.c'), work/variant
            subprocess.run(['ctangle', str(PROGRAMS/'back-20q.w'),
                            str(PROGRAMS/change) if change else '-', str(generated)],
                           check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O2',
                            str(generated), '-o', str(program)], check=True, capture_output=True)
            cls.programs[variant] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def answers(self, variant, first, second):
        result = subprocess.run([str(self.programs[variant]), str(first), str(second)],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return set(re.findall(r'^\d+: ([A-Ea-e]{20})$', result.stdout.decode(), re.M))

    def test_question15_false_negation_and_variant_statements(self):
        for variant in self.programs:
            for first, second in [(2, 15), (3, 15), (15, 19)]:
                with self.subTest(variant=variant, first=first, second=second):
                    answers = self.answers(variant, first, second)
                    for answer in answers:
                        self.assertTrue(question15_matches(answer, variant), answer)
                    if (variant, first, second) == ('base', 2, 15):
                        self.assertTrue({'AeCBABCECACADBdBDDCA', 'AeDBACDEBCDBDBdBACCA',
                                         'AeDBACAEBACBDBdBDCCA'} <= answers)

    def test_question18_false_answers_and_known_witnesses(self):
        witnesses = {'ACaBAEACBAABDBCBDeCA', 'ACaBAAACBDABDBCBEeCA', 'CCaBABACAAAEDBCBDbEA',
                     'CCaBAEACAAABDBCBDbEA', 'ACbBAAACADABDBCBEeCA', 'ACeBAEACBAABDBCBDaCA',
                     'ACeBAAACBAABDBCBDeCA', 'ECeBAAACBAABDBCBDaCA', 'ECeBABACAAABDBCBDaCA'}
        for variant in self.programs:
            for first, second in [(18, 3), (18, 2), (18, 0)]:
                answers = self.answers(variant, first, second)
                if (variant, second) == ('base', 3):
                    self.assertEqual(answers, witnesses)
                for answer in answers:
                    number = sum(answer[i-1].upper() in 'AE' for i in [2, 3, 5, 7, 11, 13, 17, 19])
                    claims = [number in [2, 3, 5, 7], number in [0, 1, 4],
                              number % 2 == 1, number % 2 == 0, number == 0]
                    option = ord(answer[17].upper())-ord('A')
                    self.assertEqual(claims[option], answer[17].isupper(), (variant, answer))
                    self.assertTrue(question15_matches(answer, variant), (variant, answer))


if __name__ == '__main__':
    unittest.main()
