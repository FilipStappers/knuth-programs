"""B059: obviously dead successors must remain constrained in grid formulas."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable
from test_dimacs_empty_clause import native_clauses

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/sat-life'


class DeadSuccessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        cls.programs = {}
        # Compile every change that replaces the grid dead-cell shortcut.
        for change in [*sorted(SOURCES.glob('*.ch')),
                       ROOT/'programs/archives/SATexamples/sources/sat-life-grid.ch']:
            if 'pp(x+1,y+1)<3)' not in change.read_text():
                continue
            name = change.stem+('-SATexamples' if change.parent.name == 'sources' else '')
            generated = work/(name+'.c')
            program = work/name
            subprocess.run(['ctangle', str(change.parent/'sat-life.w'), str(change),
                            str(generated)], check=True, capture_output=True)
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1',
                            '-include', 'stdlib.h', '-include', 'string.h',
                            '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                            str(generated), '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, name, rounds, size=1):
        result = subprocess.run([str(self.programs[name]), str(size), str(size), str(rounds)],
                                capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return native_clauses(result.stdout.decode())

    def test_one_cell_dies_for_either_initial_value(self):
        for name in ['sat-life-grid', 'sat-life-gridquad', 'sat-life-grid90', 'sat-life-grid-SATexamples']:
            for rounds in [1, 2, 3]:
                clauses = self.encode(name, rounds)
                for live in [False, True]:
                    initial = [[('' if live else '~')+'1a1']]
                    with self.subTest(variant=name, rounds=rounds, initial=live):
                        self.assertTrue(satisfiable(clauses+initial))
                        for t in range(1, rounds+1):
                            self.assertFalse(satisfiable(clauses+initial+[[f'1{chr(97+t)}1']]))

    def test_one_live_cell_cannot_be_a_cycle(self):
        for name in ['sat-life-grid-cycle', 'sat-life-gridquad-cycle', 'sat-life-grid90-cycle']:
            for rounds in [1, 2, 3]:
                with self.subTest(variant=name, rounds=rounds):
                    self.assertFalse(satisfiable(self.encode(name, rounds)+[['1a1']]))

    def test_empty_pattern_is_excluded_at_period_one(self):
        for name in ['sat-life-grid-cycle', 'sat-life-gridquad-cycle', 'sat-life-grid90-cycle']:
            for size in [1, 2, 3]:
                empty = [[f'~{x}a{y}'] for x in range(1, size+1)
                         for y in range(1, size+1)]
                with self.subTest(variant=name, size=size):
                    self.assertFalse(satisfiable(self.encode(name, 1, size)+empty))

    def test_block_has_exact_period_one(self):
        for name in ['sat-life-grid-cycle', 'sat-life-gridquad-cycle', 'sat-life-grid90-cycle']:
            block = [[f'{x}a{y}'] for x in [1, 2] for y in [1, 2]]
            with self.subTest(variant=name):
                self.assertTrue(satisfiable(self.encode(name, 1, 2)+block))
                self.assertFalse(satisfiable(self.encode(name, 2, 2)+block))

    def test_all_ten_grid_changes_still_compose(self):
        self.assertEqual(len(self.programs), 10)


if __name__ == '__main__':
    unittest.main()
