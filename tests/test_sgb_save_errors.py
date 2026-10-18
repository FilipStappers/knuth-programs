"""SGB-004: save failures are observable and release temporary storage."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from sgb_native import SgbNative


class SgbSaveErrors(unittest.TestCase):
    def test_write_close_and_open_failures_clean_up(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            native=SgbNative(work,['gb_graph','gb_io','gb_save'])
            program=native.executable('save_errors','''#include "gb_graph.h"
#include "gb_save.h"
static void *pointers[100];static int count,handles,unbuffered,fail_close;
void *__real_calloc(size_t,size_t);void __real_free(void*);
FILE *__real_fopen(const char*,const char*);int __real_fclose(FILE*);
void *__wrap_calloc(size_t n,size_t s){void*p=__real_calloc(n,s);if(p)pointers[count++]=p;return p;}
void __wrap_free(void*p){int i;for(i=0;i<count;i++)if(pointers[i]==p){pointers[i]=pointers[--count];break;}__real_free(p);}
FILE *__wrap_fopen(const char*p,const char*m){FILE*f=__real_fopen(p,m);if(f){handles++;if(unbuffered)setvbuf(f,NULL,_IONBF,0);}return f;}
int __wrap_fclose(FILE*f){int result=__real_fclose(f);handles--;return fail_close?EOF:result;}
int main(int argc,char **argv){Graph*g=gb_new_graph(1L);int baseline=count;long result;
unbuffered=!strcmp(argv[1],"unbuffered");fail_close=!strcmp(argv[1],"close");
result=save_graph(g,argv[2]);printf("%ld %d %d\\n",result,count-baseline,handles);gb_recycle(g);return count?79:0;}
''',extra=['-Wl,--wrap=calloc','-Wl,--wrap=free','-Wl,--wrap=fopen','-Wl,--wrap=fclose'])
            for mode,path,expected in [('normal',work/'ok.gb',0),('close',work/'close.gb',-4),
                                       ('buffered','/dev/full',-4),('unbuffered','/dev/full',-4),
                                       ('open',work/'absent'/'output.gb',-2)]:
                with self.subTest(mode=mode):
                    result=subprocess.run([str(program),mode,str(path)],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,(mode,result.stdout,result.stderr))
                    self.assertEqual(result.stdout,f'{expected} 0 0\n'.encode())


if __name__=='__main__':unittest.main()
