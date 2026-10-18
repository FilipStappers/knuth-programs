"""BUG-102: terminal nodes belong to the estimated search tree profile."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_flip.c').exists(),'GraphBase sources required')
class DanceEstimatorTerminals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.native=GraphNative(Path(cls.temp.name))
        text=(ROOT/'programs/programs/dance.w').read_text()
        change=(ROOT/'programs/programs/dance-random.ch').read_text()
        change=change.replace('#include "gb_flip.h"','''#include "gb_flip.h"
static long test_choice(long n) {
  static unsigned int call;
  return n>1? call++%2: 0;
}''').replace('gb_unif_rand(minlen)','test_choice(minlen)')
        path=cls.native.work/'fixed-choice.ch'
        path.write_text(change)
        cls.program=cls.native.build('estimate',text,path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def estimate(self,data,trials):
        result=subprocess.run([str(self.program),str(trials),'0'],input=data.encode(),
                              capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertNotIn(b'Consistency failure',result.stderr)
        return {int(level):(float(nodes),float(updates)) for level,nodes,updates in re.findall(
            rb'Level (\d+):\s+([\d.]+) nodes,\s+([\d.]+) updates',result.stdout)}

    def test_forced_and_uniform_trees_include_terminal_level(self):
        for depth,branches in [(1,1),(3,2),(150,1)]:
            columns=[f'C{i}' for i in range(depth)]
            data=' '.join(columns)+'\n'+''.join(name+'\n' for name in columns for _ in range(branches))
            for trials in [1,2]:
                with self.subTest(depth=depth,branches=branches,trials=trials):
                    rows=self.estimate(data,trials)
                    self.assertEqual(set(rows),set(range(depth+1)))
                    for level in range(depth+1):
                        self.assertEqual(rows[level],(float(branches**level),
                            float(branches**level) if level<depth else 0.0))

    def test_unequal_success_depths_average_and_clear_later_levels(self):
        # The two controlled root choices alternate depths one and two.
        data='A B\nA B\nA\nB\n'
        for trials in [1,2,3,4]:
            with self.subTest(trials=trials):
                rows=self.estimate(data,trials)
                self.assertEqual(rows[0],(1.0,round(2+2*((trials+1)//2)/trials,1)))
                self.assertEqual(rows[1][0],2.0)
                terminal=2*(trials//2)/trials
                self.assertAlmostEqual(rows.get(2,(0,0))[0],terminal,delta=0.051)
                self.assertAlmostEqual(sum(value[0] for value in rows.values()),3+terminal,delta=0.051)
                self.assertAlmostEqual(sum(value[1] for value in rows.values()),4.0,delta=0.051)

    def test_dead_end_creates_no_success_terminal(self):
        for trials in [1,3]:
            self.assertEqual(self.estimate('A B\nA\n',trials),{0:(1.0,1.0),1:(0.0,0.0)})


if __name__ == '__main__':
    unittest.main()
