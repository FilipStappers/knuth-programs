"""BUG-087: the Fortran seed bootstrap must stay in its integer residue range."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from fortran_native import ROOT, COMPILER, build, run
from graph_native import FLAGS


@unittest.skipUnless(COMPILER,'Native gfortran required')
class FrngSeeds(unittest.TestCase):
    def test_integer_seed_boundaries_match_the_c_port(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            text=(ROOT/'programs/programs/frng.f').read_text().split('       PROGRAM MAIN')[0]
            source=work/'seeds.f'
            source.write_text(text+'''      PROGRAM MAIN
      IMPLICIT INTEGER (A-Z)
      DIMENSION A(2009)
      CHARACTER*32 ARG
      CALL GET_COMMAND_ARGUMENT(1,ARG)
      READ(ARG,*) SEED
      CALL RNSTRT(SEED)
      DO BATCH=1,2
        N=1009
        IF (BATCH.EQ.2) N=2009
        CALL RNARRY(A,N)
        DO I=1,1009
          PRINT '(I12)',A(I)
        END DO
      END DO
      END
''')
            program=work/'fortran'
            build(source,program)
            reference=work/'reference.c'
            reference.write_text('#include <stdlib.h>\n#define main published_main\n#include "'+
                (ROOT/'programs/programs/rng.c').as_posix()+'''"
#undef main
int main(int argc,char **argv){long a[2009];int batch,i;ran_start(strtol(argv[1],0,10));
for(batch=0;batch<2;batch++){ran_array(a,batch?2009:1009);for(i=0;i<1009;i++)printf("%ld\\n",a[i]);}return 0;}
''')
            c_program=work/'reference'
            subprocess.run(['gcc',*FLAGS,str(reference),'-o',str(c_program)],check=True,capture_output=True)
            for seed in [2**30-2,2**30-1,-2,-1,-2147483648,2147483647,0,1,310952]:
                with self.subTest(seed=seed):
                    result=run(program,seed)
                    self.assertEqual(result.returncode,0,result.stderr)
                    expected=subprocess.run([str(c_program),str(seed)],capture_output=True,check=True,timeout=10)
                    actual=list(map(int,result.stdout.split()))
                    self.assertEqual(actual,list(map(int,expected.stdout.split())))
                    self.assertEqual(len(actual),2018)
                    self.assertTrue(all(0<=value<2**30 for value in actual))


if __name__=='__main__': unittest.main()
