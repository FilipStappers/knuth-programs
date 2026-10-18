"""Native Fortran builder; optional portable package stays in ignored build/."""
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'build/fortran-runtime/usr'
COMPILER=os.environ.get('GFORTRAN') or shutil.which('gfortran')
if not COMPILER and (RUNTIME/'bin/gfortran.exe').exists(): COMPILER=str(RUNTIME/'bin/gfortran.exe')
ENV=os.environ.copy()
ENV['PATH']=str(RUNTIME/'bin')+os.pathsep+ENV.get('PATH','')
ENV['GFORTRAN_ERROR_BACKTRACE']='0'


def build(source,program):
    flags=['-std=legacy','-O1','-fcheck=all','-ftrapv','-fno-use-linker-plugin']
    if str(COMPILER).startswith(str(RUNTIME)):
        libraries=RUNTIME/'lib/gcc/x86_64-pc-cygwin/14'
        flags+=['-B',str(libraries)+'/', '-B','/usr/lib/gcc/x86_64-pc-cygwin/14/', '-L',str(libraries)]
    result=subprocess.run([COMPILER,*flags,str(source),'-o',str(program)],env=ENV,capture_output=True)
    if result.returncode: raise AssertionError(result.stderr.decode(errors='replace'))


def run(program,*args):
    return subprocess.run([str(program),*map(str,args)],env=ENV,capture_output=True,timeout=10)
