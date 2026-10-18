"""B037: native filename formats must fit both base and restart buffers."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCES=Path(__file__).resolve().parents[1]/'programs/programs'


class PolyslaveFilenames(unittest.TestCase):
    def test_every_filename_suffix_with_maximum_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            base=(SOURCES/'polyslave.w').read_text()
            restart=(SOURCES/'polyslave-restart.ch').read_text()
            formats=[('filename',int(re.search(r'filename\[(\d+)\]',base)[1]),line)
                     for line in base.splitlines() if line.strip().startswith('sprintf(filename,')]
            formats += [('dfilename',int(re.search(r'dfilename\[(\d+)\]',restart)[1]),line)
                        for line in restart.splitlines() if line.strip().startswith('sprintf(dfilename,')]
            for index,(name,size,line) in enumerate(formats):
                with self.subTest(format=line):
                    source=work/f'name{index}.c'
                    source.write_text('''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
'''+f'''struct {{ char buf[{size}]; char guard[32]; }} storage;
#define {name} storage.buf
int main(int argc,char **argv) {{
char *base_name=argv[1]; unsigned int modulus=2147483648U,m=modulus;
int file_extension=2147483647;
memset(storage.guard,90,sizeof(storage.guard));
'''+line+'''
for(int i=0;i<32;i++) if(storage.guard[i]!=90) return 79;
puts(storage.buf); return 0;
}
''')
                    program=source.with_suffix('')
                    subprocess.run(['gcc','-std=gnu99','-O1','-fsanitize=undefined,bounds',
                                    '-fsanitize-undefined-trap-on-error',str(source),'-o',str(program)],
                                   check=True,capture_output=True)
                    fmt=re.search(r'"([^"]+)"',line)[1]
                    for length in [1,90,91]:
                        prefix='p'*length
                        result=subprocess.run([str(program),prefix],capture_output=True,timeout=5)
                        self.assertEqual(result.returncode,0,result.stderr.decode())
                        suffix=(f'.2147483647' if '%d' in fmt else
                                '-2147483648.dump' if '.dump' in fmt else
                                '-2147483648.m' if '.m' in fmt else '.ck')
                        self.assertEqual(result.stdout,(prefix[:90]+suffix+'\n').encode())


if __name__ == '__main__':
    unittest.main()
