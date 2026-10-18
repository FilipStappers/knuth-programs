"""B037: validate numeric capacity arguments before allocation/output."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCES=Path(__file__).resolve().parents[1]/'programs/programs'


class PolynumCapacityArguments(unittest.TestCase):
    def test_capacity_domains_and_integer_parsing(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            source=work/'poly.w'
            source.write_text((SOURCES/'polynum.w').read_text().replace('  @<Initialize@>;',
                '  printf("ACCEPTED %d %d\\n",conf_size,slave_size); return 0;'))
            for restart in [False,True]:
                with self.subTest(restart=restart):
                    generated=work/('restart.c' if restart else 'base.c')
                    subprocess.run(['ctangle',str(source),str(SOURCES/'polynum-restart.ch') if restart else '-',
                                    str(generated)],check=True,capture_output=True)
                    program=generated.with_suffix('')
                    subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1',
                                    '-include','stdlib.h','-include','string.h','-fsanitize=undefined,bounds',
                                    '-fsanitize-undefined-trap-on-error',str(generated),'-o',str(program)],
                                   check=True,capture_output=True)
                    for conf,slave in [('0','100'),('-1','100'),('1','100'),('2','0'),('2','-1'),
                                       ('2','9'),('2','10'),('2x','100'),('2','100x'),
                                       ('2147483648','100'),('2','4294967297'),('9'*100,'100')]:
                        result=subprocess.run([str(program),'9','2',conf,slave,'unused'],
                                              capture_output=True,timeout=5)
                        self.assertNotEqual(result.returncode,0,(conf,slave,result.stdout))
                        self.assertEqual(result.stdout,b'')
                        self.assertTrue(result.stderr)
                    for conf,slave in [('2','11'),('10000','100000')]:
                        result=subprocess.run([str(program),'9','2',conf,slave,'unused'],
                                              capture_output=True,timeout=5)
                        self.assertEqual(result.returncode,0,result.stderr.decode())
                        self.assertEqual(result.stdout,f'ACCEPTED {conf} {slave}\n'.encode())


if __name__ == '__main__':
    unittest.main()
