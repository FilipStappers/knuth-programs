"""Direct-source integration controls for the repaired SGB library.

The shipped seeded sample is an existing compatibility fixture, not new RNG
or distribution validation.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from sgb_native import SgbNative,SGB


class SgbIntegration(unittest.TestCase):
    def test_all_modules_shipped_sample_and_data_checksums(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            modules=sorted(p.stem for p in SGB.glob('gb_*.w') if p.stem!='gb_types')
            self.assertEqual(len(modules),18)
            native=SgbNative(work,modules)
            for path in SGB.glob('*.dat'):shutil.copyfile(path,work/path.name)
            result=subprocess.run(['ctangle',str(SGB/'test_sample.w'),'-',str(work/'sample.c')],
                                  cwd=work,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout)
            program=native.executable('sample',(work/'sample.c').read_text())
            result=subprocess.run([str(program)],cwd=work,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,(SGB/'sample.correct').read_bytes())
            self.assertEqual((work/'test.gb').read_bytes(),(SGB/'test.correct').read_bytes())
            program=native.executable('checksums','''#include "gb_io.h"
int main(int argc,char**argv){int i;long code;for(i=1;i<argc;i++){
code=gb_open(argv[i]);if(code)return 2;
while(!gb_eof())gb_newline();code=gb_close();if(code)return 3;
printf("%s OK\\n",argv[i]);}return 0;}
''')
            names=sorted(p.name for p in SGB.glob('*.dat'))
            self.assertEqual(len(names),12)
            result=subprocess.run([str(program),*names],cwd=work,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.decode(),''.join(name+' OK\n' for name in names))


if __name__=='__main__':unittest.main()
