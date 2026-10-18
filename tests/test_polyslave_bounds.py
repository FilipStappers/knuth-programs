"""B037: counter headers and relative addresses must precede memory access."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

SOURCES=Path(__file__).resolve().parents[1]/'programs/programs'


class PolyslaveBounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.work=Path(cls.temp.name)
        text=(SOURCES/'polyslave.w').read_text()
        # Independent stops before any otherwise-invalid counter access.
        text=text.replace('count[0]=1;',
                          'if(slave_size<=n) { fprintf(stderr,"UNGUARDED totals\\n"); exit(71); }\ncount[0]=1;')
        text=text.replace('  p=get_inst();',
                          '  p=get_inst();\nif(cur_src<0 || cur_trg<0) { fprintf(stderr,"UNGUARDED address\\n"); exit(71); }')
        source=cls.work/'slave.w'
        source.write_text(text)
        cls.programs=[]
        for restart in [False,True]:
            generated=cls.work/('restart.c' if restart else 'base.c')
            subprocess.run(['ctangle',str(source),str(SOURCES/'polyslave-restart.ch') if restart else '-',
                            str(generated)],check=True,capture_output=True)
            program=generated.with_suffix('')
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1','-include','stdlib.h',
                            '-include','string.h','-fsanitize=undefined,bounds',
                            '-fsanitize-undefined-trap-on-error',str(generated),'-o',str(program)],
                           check=True,capture_output=True)
            cls.programs.append(program)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_stream(self,program,size,instructions):
        prefix=self.work/'input'
        data=bytes([9,8])+size.to_bytes(4,'big')+instructions
        Path(str(prefix)+'.0').write_bytes(data)
        checksum=0
        for byte in data:
            checksum=(2*checksum+byte)%(2**32)
        Path(str(prefix)+'.ck').write_bytes(struct.pack('=I',checksum))
        dump=[9,3,251,size,3]+[0]*10+[1]+[0]*max(0,size-1)
        Path(str(prefix)+'-251.dump').write_bytes(struct.pack('='+len(dump)*'I',*dump))
        return subprocess.run([str(program),str(prefix),'251'],capture_output=True,timeout=5)

    def test_reserved_totals_and_header_representation(self):
        for program in self.programs:
            for size in [0,1,9,2**31,2**32-1]:
                with self.subTest(program=program.name,size=size):
                    # No enormous fixture/dump allocation for invalid headers.
                    if size>=2**31:
                        prefix=self.work/'input'
                        Path(str(prefix)+'.0').write_bytes(bytes([9,8])+size.to_bytes(4,'big'))
                        Path(str(prefix)+'.ck').write_bytes(b'\0'*4)
                        result=subprocess.run([str(program),str(prefix),'251'],capture_output=True,timeout=5)
                    else:
                        result=self.run_stream(program,size,bytes(range(0x84,0x89)))
                    self.assertNotEqual(result.returncode,0)
                    self.assertNotEqual(result.returncode,71,result.stderr.decode())
                    self.assertIn(b'counter storage size',result.stderr)

    def test_negative_relative_addresses(self):
        for program in self.programs:
            for instructions in [bytes([0xd1,0xa1]),bytes([0xf1,0x91])]:
                with self.subTest(program=program.name,instructions=instructions):
                    result=self.run_stream(program,16,instructions)
                    self.assertNotEqual(result.returncode,0)
                    self.assertNotEqual(result.returncode,71,result.stderr.decode())
                    self.assertIn(b'address out of range',result.stderr)

    def test_exact_reserved_capacity_and_valid_address_updates(self):
        for program in self.programs:
            for size in [10,16]:
                with self.subTest(program=program.name,size=size):
                    # Move source/target to the last slot, copy it to itself,
                    # then return both pointers and publish all five rows.
                    p=size-1
                    instructions=bytes([0xc0,p,0xe0,p,0xa1,0xd0,p,0xf0,p])+bytes(range(0x84,0x89))
                    result=self.run_stream(program,size,instructions)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertIn(b'All done!',result.stdout)

    def test_upper_address_and_range_endpoints_reject(self):
        for program in self.programs:
            for instructions in [bytes([0xc0,17,0xa1]),bytes([0xe0,17,0x91]),
                                 bytes([0,0,0,17,0xa1]),bytes([0x40,0,0,17,0x91]),
                                 bytes([0xc0,15,0xa2]),bytes([0xe0,15,0x92])]:
                with self.subTest(program=program.name,instructions=instructions):
                    result=self.run_stream(program,16,instructions)
                    self.assertNotEqual(result.returncode,0)
                    self.assertNotEqual(result.returncode,71,result.stderr.decode())
                    self.assertIn(b'address out of range',result.stderr)


if __name__ == '__main__':
    unittest.main()
