"""B037: one transient checksum discrepancy must replay every file part."""
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest

SOURCES=Path(__file__).resolve().parents[1]/'programs/programs'


class PolyslaveRetry(unittest.TestCase):
    def test_base_and_restart_replay_from_part_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            source=work/'slave.w'
            text=(SOURCES/'polyslave.w').read_text()
            text=text.replace('@d buf_size (1<<16)','@d buf_size 16')
            text=text.replace('@d filelength_threshold (1<<30)','@d filelength_threshold 32')
            text=text.replace('@c','@c\nstatic int test_injected;')
            source.write_text(text)
            stream=bytes([9,8,0,0,0,16,0x40,0,0,10])+bytes([0x91])*64+bytes(range(0x84,0x89))
            checks=[]
            prefix=work/'stream'
            for part,start in enumerate(range(0,len(stream),32)):
                data=stream[start:start+32]
                Path(str(prefix)+f'.{part}').write_bytes(data)
                checksum=0
                for offset in range(0,len(data),16):
                    value=0
                    for byte in data[offset:offset+16]:
                        value=(2*value+byte)%(2**32)
                    checksum=(checksum+value)%(2**32)
                checks.append(checksum)
            Path(str(prefix)+'.ck').write_bytes(struct.pack('='+len(checks)*'I',*checks))
            # A restart with a valid saved empty subtotal/counter state at row 3.
            dump=[9,3,251,16,3]+[0]*10+[1]+[0]*15
            Path(str(prefix)+'-251.dump').write_bytes(struct.pack('='+len(dump)*'I',*dump))
            expected=''.join(f'p[{row},3,251]={{'+','.join(['0']*9)+'}\n' for row in range(3,8))
            for restart in [False,True]:
                with self.subTest(restart=restart):
                    generated=work/('restart.c' if restart else 'base.c')
                    subprocess.run(['ctangle',str(source),
                                    str(SOURCES/'polyslave-restart.ch') if restart else '-',str(generated)],
                                   check=True,capture_output=True)
                    code=generated.read_text()
                    # Inject after reading a genuine checksum; all fixture bytes stay valid.
                    code,count=re.subn(r'if\s*\(checkbuf!=checksum\)\s*\{',
                        'if(file_extension==1 && !test_injected) { test_injected=1; checkbuf^=1; }\n'
                        'if(checkbuf!=checksum) {',code)
                    self.assertEqual(count,1)
                    generated.write_text(code)
                    program=generated.with_suffix('')
                    subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1',
                                    '-include','stdlib.h','-include','string.h',
                                    '-fsanitize=undefined,bounds','-fsanitize-undefined-trap-on-error',
                                    str(generated),'-o',str(program)],check=True,capture_output=True)
                    output=Path(str(prefix)+'-251.m')
                    output.write_text('')
                    result=subprocess.run([str(program),str(prefix),'251'],capture_output=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertEqual(result.stdout.count(b'Checksum mismatch!'),1)
                    self.assertIn(b'All done!',result.stdout)
                    self.assertEqual(output.read_text(),expected)


if __name__ == '__main__':
    unittest.main()
