"""SGB-002: large allocation byte counts remain exact before any allocation."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from sgb_native import SgbNative


class SgbAllocationSizes(unittest.TestCase):
    def test_supported_sizes_and_rounding_limits_without_large_allocations(self):
        with tempfile.TemporaryDirectory() as temp:
            native=SgbNative(Path(temp),['gb_graph'])
            program=native.executable('allocation_sizes','''#include <limits.h>
#include "gb_graph.h"
void *__wrap_calloc(size_t n,size_t s){printf("ALLOC %llu %llu\\n",(unsigned long long)n,(unsigned long long)s);return NULL;}
int main(int argc,char **argv){Area a;long n=strtol(argv[1],NULL,10);init_area(a);
printf("WIDTH %u %u\\n",(unsigned)sizeof(long),(unsigned)sizeof(char*));
gb_alloc(n,a);printf("RESULT %ld\\n",gb_trouble_code);return 0;}
''',extra=['-Wl,--wrap=calloc'])
            for requested in [1,255,256,257,1<<40,0,-1,(1<<63)-1,(1<<63)-21,(1<<63)-301]:
                with self.subTest(requested=requested):
                    result=subprocess.run([str(program),str(requested)],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr)
                    lines=result.stdout.decode().splitlines()
                    width,pointer=map(int,lines[0].split()[1:])
                    self.assertEqual(width,8,'This large-size fixture requires a 64-bit long ABI')
                    if requested<=0 or requested>(1<<63)-1-3*pointer-255:
                        self.assertEqual(lines[1:],['RESULT 2'])
                    else:
                        aligned=(requested+pointer-1)//pointer*pointer
                        units=(aligned+2*pointer+255)//256
                        self.assertEqual(lines[1:],[f'ALLOC {units} 256','RESULT 1'])


if __name__=='__main__':unittest.main()
