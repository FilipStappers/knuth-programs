"""SGB-010: propagate construction failures and free auxiliary distributions."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from sgb_native import SgbNative


class SgbBigraphFailure(unittest.TestCase):
    def test_invalid_distributions_and_allocation_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            native=SgbNative(Path(temp),['gb_graph','gb_flip','gb_rand'])
            program=native.executable('bigraph_failure','''#include "gb_graph.h"
#include "gb_rand.h"
static void *pointers[100];static int count,calls,fail;
void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_calloc(size_t n,size_t s){void*p;if(++calls==fail)return NULL;p=__real_calloc(n,s);if(p)pointers[count++]=p;return p;}
void __wrap_free(void*p){int i;for(i=0;i<count;i++)if(pointers[i]==p){pointers[i]=pointers[--count];break;}__real_free(p);}
int main(int argc,char**argv){Graph*g;long negative[1]={-1},zero[1]={0};int mode=atoi(argv[1]);long expected=0;
fail=atoi(argv[2]);
if(mode==1)expected=invalid_operand;
if(mode==2)expected=invalid_operand+5;
if(mode==3)expected=invalid_operand+2;
g=random_bigraph(1UL,1UL,0UL,0L,mode==1?negative:mode==3?zero:NULL,mode==2?negative:NULL,1L,1L,0L);
if(expected && (g || panic_code!=expected))return 70;
if(g){if(g->n!=2 || g->m!=0 || g->uu.I!=1)return 71;gb_recycle(g);}
printf("%d %d %d %ld %d\\n",g!=NULL,count,gb_trouble_code,panic_code,calls);return count?72:0;}
''',extra=['-Wl,--wrap=calloc','-Wl,--wrap=free'])
            baseline_calls=None
            for mode,fail in [(1,0),(2,0),(3,0)]+[(0,i) for i in range(0,16)]:
                result=subprocess.run([str(program),str(mode),str(fail)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,(mode,fail,result.stdout,result.stderr))
                good,live,trouble,panic,calls=map(int,result.stdout.split())
                self.assertEqual((live,trouble),(0,0))
                if mode==0 and fail==0:baseline_calls=calls
                if mode or (fail and fail<=baseline_calls):self.assertEqual(good,0,(mode,fail,panic))
                else:self.assertEqual(good,1)


if __name__=='__main__':unittest.main()
