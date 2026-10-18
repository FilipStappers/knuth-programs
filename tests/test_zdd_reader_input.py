"""BUG-035: complete ZDD families and reject malformed ordered diagrams."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import ROOT, FLAGS

SOURCES=ROOT/'programs/archives/simpath-example'


class ZddReaderInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        work=Path(cls.temp.name)
        cls.input=work/'input.zdd'
        change=work/'reader.ch'
        change.write_text((SOURCES/'zddread-sols-all.ch').read_text().replace('40000000','1024'))
        cls.program=work/'reader'
        generated=work/'reader.c'
        subprocess.run(['ctangle',str(SOURCES/'bddread.w'),str(change),str(generated)],check=True,capture_output=True)
        subprocess.run(['gcc',*FLAGS,str(generated),'-o',str(cls.program)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def run_diagram(self,data):
        self.input.write_text(data)
        return subprocess.run([str(self.program),str(self.input)],capture_output=True,timeout=5)

    def test_all_three_variable_families_and_terminal_roots(self):
        for bits in range(256):
            family=frozenset(s for s in range(8) if bits>>s&1)
            nodes={}
            def build(family,v=0):
                if not family:return 0
                if v==3:return 1
                lo=build(frozenset(s for s in family if not s>>v&1),v+1)
                hi=build(frozenset(s&~(1<<v) for s in family if s>>v&1),v+1)
                if hi==0:return lo
                key=(v,lo,hi)
                if key not in nodes:nodes[key]=len(nodes)+2
                return nodes[key]
            root=build(family)
            records=''.join(f'{p:x}: (~{v}?{lo:x}:{hi:x})\n' for (v,lo,hi),p in nodes.items())
            for explicit in ([False,True] if root>1 else [True]):
                data=(f'root: {root:x}\n' if explicit else '')+records
                result=self.run_diagram(data)
                self.assertEqual(result.returncode,0,(bits,explicit,result.stderr))
                solutions=[sum(1<<int(v) for v in line.split(':')[1].split())
                           for line in result.stdout.decode().splitlines() if re.match(r'^\d+:',line)]
                self.assertEqual(set(solutions),family,(bits,explicit))
                self.assertEqual(len(solutions),len(family))
        self.assertEqual(self.run_diagram('').returncode,0)
        # Maximum strictly ordered path fills, but never exceeds, the stack.
        data=''.join(f'{v+2:x}: (~{v}?0:{v+3 if v<511 else 1:x})\n' for v in range(512))
        result=self.run_diagram(data)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(('0: '+' '.join(map(str,range(512)))+'\n').encode(),result.stdout)

    def test_malformed_addresses_variables_and_structure_reject(self):
        for data in ['2: (~-1?0:1)\n','80000000: (~0?0:1)\n',
                     '2: (~512?0:1)\n','2: (~0?0:3)\n','2: (~0?0:2)\n',
                     '2: (~0?0:3)\n3: (~0?0:1)\n',
                     '2: (~0?0:1)\n3: (~0?0:1)\n',
                     '2: (~0?0:0)\n2: (~0?0:1)\n',
                     '0: (~0?0:1)\n','root: 3\n2: (~0?0:1)\n',
                     'root: 0\nroot: 1\n','root: -1\n',
                     '2: (~0?0:1) junk\n','nonsense\n','f'*200+'\n']:
            with self.subTest(data=data[:70]):
                result=self.run_diagram(data)
                self.assertNotEqual(result.returncode,0)
                self.assertTrue(result.stderr,result.stdout)
                self.assertNotRegex(result.stdout,rb'(?m)^\d+:')
        result=subprocess.run([str(self.program)],capture_output=True,timeout=5)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'Usage:',result.stderr)


if __name__=='__main__': unittest.main()
