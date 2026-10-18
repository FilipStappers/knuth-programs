"""B039-antislide3-empty-profile: finite statistics for unvisited levels."""
import math
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'programs/programs/antislide3.w'


class AntislideProfile(unittest.TestCase):
    def check_profile(self, mode):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'anti.w'
            text=SOURCE.read_text()
            for dimension in ['ll','mm','nn']:
                text=text.replace('@d '+dimension+' 4 ','@d '+dimension+' 3 ')
            needle='  if (verbose) @<Print a profile of the search tree@>;'
            text=text.replace(needle,'''  for(j=1;j<=ll*mm*nn;j++)
    fprintf(stderr,"RAW %d %d %d %d %d\\n",j,profile[j],prof_syms[j],prof_cons[j],prof_frcs[j]);
'''+needle)
            if mode=='empty':
                for module in ['Set up data structures for antisliding blocks',
                               'Backtrack through all solutions',
                               'Make redundancy checks to see if the backtracking was consistent']:
                    text=text.replace('  @<'+module+'@>;', '')
                text=text.replace('  for(j=1;j<=ll*mm*nn;j++)',
                                  '  profile[1]=2; prof_syms[1]=5; prof_cons[1]=7; prof_frcs[1]=1;\n'
                                  '  for(j=1;j<=ll*mm*nn;j++)')
            source.write_text(text)
            generated=source.with_suffix('.c')
            program=source.with_suffix('')
            subprocess.run(['ctangle',str(source),'-',str(generated)],check=True,capture_output=True)
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1',
                            '-fsanitize=undefined,bounds,float-divide-by-zero',
                            '-fsanitize-undefined-trap-on-error',str(generated),'-o',str(program)],
                           check=True,capture_output=True)
            result=subprocess.run([str(program),'1'],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertIn(('Altogether '+('2' if mode=='search' else '0')+' solutions.').encode(),result.stdout)
            raw={int(j):(int(p),int(s),int(c),int(f)) for j,p,s,c,f in re.findall(
                rb'RAW (\d+) (\d+) (\d+) (\d+) (\d+)',result.stderr)}
            rows=re.findall(rb'Level (\d+): (\d+) sols, (\S+) syms, (\S+) cons, (\S+) frcs',result.stdout)
            self.assertEqual(len(rows),27)
            if mode=='empty':
                self.assertTrue(any(row[0]==0 for row in raw.values()))
            self.assertTrue(any(row[0]>0 for row in raw.values()))
            for j,p,*means in rows:
                count,*totals=raw[int(j)]
                self.assertEqual(int(p),count)
                for value,total in zip(means,totals):
                    actual=float(value)
                    self.assertTrue(math.isfinite(actual))
                    self.assertAlmostEqual(actual,total/count if count else 0,delta=0.051)

    def test_complete_small_search_profile(self):
        self.check_profile('search')

    def test_unvisited_reporting_levels(self):
        self.check_profile('empty')


if __name__ == '__main__':
    unittest.main()
