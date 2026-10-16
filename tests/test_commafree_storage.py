"""B047: packed undo cells must cover the full unsigned 16-bit domain."""
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def commafree(code):
    return all((a+b)[k:k+4] not in code for a in code for b in code for k in range(1, 4))


class CommafreeStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def build(self, mode):
        text = (ROOT/'programs/programs/back-commafree4.w').read_text()
        if mode == 'first':
            old = '  l++;@+goto enter;'
            self.assertEqual(text.count(old), 1)
            text = text.replace(old, '  l++; sanity(); return 0; /* observe one root choice */')
        source = self.work/'back.w'
        source.write_text(text)
        generated = self.work/'back.c'
        subprocess.run(['ctangle', str(source), '-', str(generated)],
                       check=True, capture_output=True)
        driver = generated
        if mode == 'cells':
            driver = self.work/'driver.c'
            driver.write_text(r'''
#define main published_main
#include "back.c"
#undef main
int main(void) {
  unsigned int address,value;
  for (address=0;address<65536;address++) {
    for (value=0;value<3;value++) {
      unsigned int old=value==0? 0:value==1? 1:65535;
      unsigned int next=65535-old;
      mem[address]=old; uptr=0; curstamp++;
      store(address,next);
      if (uptr!=1 || mem[address]!=next) return 1;
      store(address,old); /* only the first store in an epoch is saved */
      if (uptr!=1) return 2;
      unstore(0);
      if (uptr || mem[address]!=old) return 3;
    }
  }
  return 0;
}
''')
        program = self.work/mode
        subprocess.run(['gcc', '-std=gnu99', '-fgnu89-inline', '-Wno-implicit-int',
                        '-O1', '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                        str(driver), '-o', str(program)], check=True, capture_output=True)
        return program

    def test_every_unsigned_cell_address_and_extreme_value_round_trips(self):
        result = subprocess.run([str(self.build('cells'))], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_seven_letter_root_choice_and_list_consistency(self):
        result = subprocess.run([str(self.build('first')), '7', '546'],
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b'')

    def test_complete_binary_search_matches_independent_normalized_subsets(self):
        program = self.build('full')
        words = [w for w in itertools.product(range(2), repeat=4)
                 if len({w[k:]+w[:k] for k in range(4)}) == 4]
        for goal in [1, 2, 3]:
            expected = set()
            for size in range(goal, 4):
                for subset in itertools.combinations(words, size):
                    code = frozenset(subset)
                    if ((0, 0, 0, 1) in code or (0, 0, 1, 0) in code) and commafree(code):
                        expected.add(code)
            result = subprocess.run([str(program), '2', str(goal)], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            actual = [frozenset(tuple(map(int, word.decode())) for word in line.split(b':')[1].split()
                                if not word.startswith(b'('))
                      for line in result.stdout.splitlines()]
            self.assertEqual(len(actual), len(set(actual)))
            self.assertEqual(set(actual), expected)


if __name__ == '__main__':
    unittest.main()
