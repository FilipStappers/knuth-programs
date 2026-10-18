"""B037: admitted polynomial endpoints need an explicit unsigned representation."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCES=Path(__file__).resolve().parents[1]/'programs/programs'


def width_two(n):
    dp={(mask,mask,bin(mask).count('1')):1 for mask in [1,2,3]}
    rows={}
    for height in range(1,n):
        if height>=2:
            values=[0]*n
            for (last,both,size),count in dp.items():
                if both==3:
                    values[size-1]=(values[size-1]+count)%251
            rows[height]=values
        following={}
        for (last,both,size),count in dp.items():
            for mask in [1,2,3]:
                size2=size+bin(mask).count('1')
                if last&mask and size2<=n:
                    key=(mask,both|mask,size2)
                    following[key]=(following.get(key,0)+count)%251
        dp=following
    return rows


class PolynumEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.work=Path(cls.temp.name)
        cls.programs={}
        for name,mode in [('polynum','signed'),('polynum','unsigned'),('polyslave','signed')]:
            generated=cls.work/(name+'-'+mode+'.c')
            subprocess.run(['ctangle',str(SOURCES/(name+'.w')),'-',str(generated)],check=True,capture_output=True)
            program=generated.with_suffix('')
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1','-include','stdlib.h',
                            '-include','string.h','-f'+mode+'-char','-fsanitize=undefined,bounds',
                            '-fsanitize-undefined-trap-on-error',str(generated),'-o',str(program)],
                           check=True,capture_output=True)
            cls.programs[name+'-'+mode]=program

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_admitted_endpoints_against_row_mask_oracle(self):
        for n in [9,126,127,128,130]:
            expected=width_two(n)
            for mode in ['signed','unsigned']:
                with self.subTest(n=n,mode=mode):
                    prefix=self.work/'poly'
                    producer=subprocess.run([str(self.programs['polynum-'+mode]),str(n),'2',
                                             '10000','100000',str(prefix)],capture_output=True,timeout=20)
                    self.assertEqual(producer.returncode,0,producer.stderr.decode())
                    consumer=subprocess.run([str(self.programs['polyslave-signed']),str(prefix),'251'],
                                            capture_output=True,timeout=20)
                    self.assertEqual(consumer.returncode,0,consumer.stderr.decode())
                    actual={int(h):list(map(int,values.split(','))) for h,values in re.findall(
                        r'p\[(\d+),2,251\]=\{([^}]+)\}',Path(str(prefix)+'-251.m').read_text())}
                    self.assertEqual(actual,expected)


if __name__ == '__main__':
    unittest.main()
