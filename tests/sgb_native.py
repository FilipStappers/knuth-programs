"""Build the directly repaired GraphBase sources without CWEB change files."""
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SGB=ROOT/'programs/sgb'
FLAGS=['-std=gnu99','-Wno-implicit-int','-Wno-implicit-function-declaration',
       '-O1','-fcommon','-DSYSV','-include','stdlib.h','-include','string.h',
       '-fsanitize=undefined,bounds','-fsanitize-undefined-trap-on-error']


class SgbNative:
    def __init__(self,work,modules):
        self.work=work
        work.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(SGB/'gb_types.w',work/'gb_types.w')
        shutil.copyfile(SGB/'boilerplate.w',work/'boilerplate.w')
        self.objects=[]
        for name in modules:
            source=SGB/(name+'.w')
            result=subprocess.run(['ctangle',str(source),'-',
                                   str(work/(name+'.c'))],cwd=work,capture_output=True)
            if result.returncode:raise AssertionError(result.stdout.decode(errors='replace'))
        for name in modules:
            obj=work/(name+'.o')
            result=subprocess.run(['gcc',*FLAGS,'-I'+str(work),'-c',str(work/(name+'.c')),'-o',str(obj)],
                                  cwd=work,capture_output=True)
            if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))
            self.objects.append(str(obj))

    def executable(self,name,text,objects=None,extra=()):
        source=self.work/(name+'.c');source.write_text(text)
        program=source.with_suffix('')
        result=subprocess.run(['gcc',*FLAGS,'-I'+str(self.work),*extra,str(source),
                               *(self.objects if objects is None else objects),'-lm','-o',str(program)],
                              cwd=self.work,capture_output=True)
        if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))
        return program
