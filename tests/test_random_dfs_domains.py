"""BUG-016: admission checks only; no generated-random-graph assessment."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from graph_native import GraphNative, GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_flip.c').exists(),'GraphBase sources required')
class RandomDfsDomains(unittest.TestCase):
    def test_both_command_line_domains(self):
        with tempfile.TemporaryDirectory() as temp:
            native=GraphNative(Path(temp))
            cases={
                'a':([
                    ['1','0','1','0'],['-1','3','1','0'],['0','-1','1','0'],
                    ['1','3','-1','0'],['129','3','1','0'],['1','129','1','0'],
                    ['1x','3','1','0'],['4294967297','3','1','0']],
                    [['0','1','0','0'],['128','128','1','-1']]),
                'b':([
                    ['1','0','3','1','0'],['-1','2','3','1','0'],['2','2','3','1','0'],
                    ['3','2','3','1','0'],['0','2','0','1','0'],['0','2','3','-1','0'],
                    ['0','-2','3','1','0'],['0','2','129','1','0'],
                    ['0','2x','3','1','0'],['0','4294967297','3','1','0']],
                    [['0','1','1','0','0'],['127','128','128','1','-1']])}
            for name,(invalid,valid) in cases.items():
                text=(ROOT/f'programs/programs/random-dfs-{name}.w').read_text()
                text=text.replace('@d maxm 100000000','@d maxm 128').replace(
                                  '@d maxm 10000000','@d maxm 128')
                text=text.replace('  @<Process the command line@>;',
                                  '  @<Process the command line@>;\n  puts("ACCEPTED"); return 0;')
                program=native.build(name,text)
                for args in invalid:
                    with self.subTest(name=name,args=args):
                        result=subprocess.run([str(program),*args],capture_output=True,timeout=5)
                        self.assertNotEqual(result.returncode,0)
                        self.assertNotIn(b'ACCEPTED',result.stdout)
                        self.assertTrue(result.stderr)
                for args in valid:
                    with self.subTest(name=name,args=args):
                        result=subprocess.run([str(program),*args],capture_output=True,timeout=5)
                        self.assertEqual(result.returncode,0,result.stderr.decode())
                        self.assertIn(b'ACCEPTED',result.stdout)


if __name__ == '__main__':
    unittest.main()
