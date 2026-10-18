"""Enigmatic puzzle: native SAT depth, constraint masks and plug sentinels."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'programs/programs/enigmatic-puzzle.w'


class EnigmaNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.work=Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def build(self,name,entry,visit=None):
        text=SOURCE.read_text()
        original='''  @<Process the command line@>;
  @<Initialize the main data structures@>;
  @<Run through the million possible wheel configurations@>;
  @<Print statistics and say adieu@>;'''
        assert text.count(original)==1
        text=text.replace(original,entry+'\nreturn 0;')
        if visit:
            text=text.replace('@<Visit the {\\mc SAT} solution found@>;',visit)
        source=self.work/(name+'.w')
        source.write_text(text)
        generated=source.with_suffix('.c')
        program=source.with_suffix('')
        subprocess.run(['ctangle',str(source),'-',str(generated)],check=True,capture_output=True)
        subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1',
                        '-fsanitize=undefined,bounds','-fsanitize-undefined-trap-on-error',
                        str(generated),'-o',str(program)],check=True,capture_output=True)
        return program

    def run_program(self,program,*args):
        result=subprocess.run([str(program),*map(str,args)],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertEqual(result.stderr,b'')
        return result.stdout

