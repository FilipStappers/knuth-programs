"""SGB-001: restore newline/terminator within the private line buffer."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from sgb_native import SgbNative


class SgbIoLines(unittest.TestCase):
    def test_line_boundaries_preserve_guard_and_framing(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            native=SgbNative(work,['gb_io'])
            code=(work/'gb_io.c').read_text()
            code,count=re.subn(r'static char buffer\[(\d+)\];',
                r'static struct { char bytes[\1]; unsigned char guard[16]; } storage;\n#define buffer storage.bytes',code)
            self.assertEqual(count,1)
            code+='''
int main(int argc,char **argv){int i;memset(storage.guard,123,sizeof(storage.guard));
gb_raw_open(argv[1]);
for(i=0;i<sizeof(storage.guard);i++)if(storage.guard[i]!=123)return 79;
printf("%lu %d\\n",(unsigned long)strlen(buffer),(io_errors&missing_newline)!=0);
gb_raw_close();return 0;}
'''
            program=native.executable('line_probe',code,objects=[])
            for length,newline in [(0,True),(1,True),(79,True),(80,True),(80,False),(81,True),(0,False)]:
                with self.subTest(length=length,newline=newline):
                    data=work/'input.dat';data.write_bytes(b'x'*length+(b'\n' if newline else b''))
                    result=subprocess.run([str(program),str(data)],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr)
                    expected_length=min(length,80)+1
                    self.assertEqual(result.stdout,f'{expected_length} {int(not newline or length>79)}\n'.encode())


if __name__=='__main__':unittest.main()
