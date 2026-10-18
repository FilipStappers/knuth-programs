"""B057: reserve the prime/active suffix within SAT's eight-byte names."""
from pathlib import Path
import itertools
import subprocess
import tempfile
import unittest
from graph_native import ROOT, GraphNative

SOURCES=ROOT/'programs/archives/SATexamples/sources'


class StuckNameLengths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        native=GraphNative(Path(cls.temp.name))
        text=(SOURCES/'sat-gates-stuck.w').read_text()
        text=text.replace('g=restore_graph(argv[1]);','''g=gb_new_graph(1);
g->vertices[0].name=gb_save_string(argv[1]);
g->vertices[0].typ='I';
g->outs=gb_virgin_arc();
g->outs->tip=g->vertices; g->outs->next=NULL;''')
        cls.programs=[native.build('base',text),native.build('kludge',text,
                    SOURCES/'sat-gates-stuck-namekludge.ch')]

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_overlong_wire_names_reject_before_clauses(self):
        for program in self.programs:
            for name in ['Aabcdefg','Aabcdefgh']:
                result=subprocess.run([str(program),name,'0'+name],capture_output=True,timeout=5)
                self.assertNotEqual(result.returncode,0,(program.name,name,result.stdout))
                self.assertIn(b'too long',result.stderr)
                self.assertEqual(result.stdout,b'')

    def test_boundary_names_retain_fault_detection_formula(self):
        for program in self.programs:
            cases=[('A','A'),('Aabcdef','Aabcdef')]
            if program.name=='kludge': cases.append(('A12:34#56','A123456'))
            for given,wire in cases:
                for stuck in [0,1]:
                    result=subprocess.run([str(program),given,str(stuck)+wire],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr)
                    clauses=[line.split() for line in result.stdout.decode().splitlines()
                             if line and not line.startswith('~ ')]
                    names={literal.lstrip('~') for clause in clauses for literal in clause}
                    self.assertTrue(all(0<len(name)<=8 for name in names),names)
                    names=sorted(names)
                    models=[]
                    for bits in itertools.product([False,True],repeat=len(names)):
                        assignment=dict(zip(names,bits))
                        if all(any(assignment[literal.lstrip('~')]!=(literal[0]=='~')
                                   for literal in clause) for clause in clauses):
                            models.append(assignment[wire])
                    self.assertEqual(set(models),{bool(1-stuck)})


if __name__=='__main__': unittest.main()
