"""B058: observe admission only, before any RNG initialization or sampling."""
from pathlib import Path
import subprocess
import re
import tempfile
import unittest
from graph_native import ROOT, FLAGS, GraphNative

SOURCES=ROOT/'programs/archives/SATexamples/sources'


class RandomDataParameters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        native=GraphNative(Path(cls.temp.name))
        cls.programs={}
        for name in ['oss-data','sat-closest-string-dat','sat-rand-rep','sat-synth-data']:
            text=(SOURCES/(name+'.w')).read_text()
            # All command-line checks precede the first gb_init_rand except
            # SYNTH, whose initialization starts in the next CWEB module.
            if name=='sat-synth-data':
                text=text.replace('@<Set up the first data point@>;','puts("ACCEPTED"); return 0;',1)
            else:
                seed='s' if name=='sat-closest-string-dat' else 'seed'
                text=text.replace('gb_init_rand('+seed+');','puts("ACCEPTED"); return 0;',1)
            cls.programs[name]=native.build(name,text)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_invalid_domains_and_complete_numeric_tokens(self):
        cases={
            'oss-data':['0 10 .5 0 0','1 10 .5 1 0','79 10 .5 0 0',
                        '2 -1 .5 0 0','2 10 .5 -1 0','2 10 nan 0 0',
                        '2 10 inf 0 0','2 10 .5junk 0 0','2 10 1 0 0'],
            'sat-closest-string-dat':['-1 1 1 1 0','10001 1 1 1 0','3 -1 1 2 0',
                                      '3 2147483647 1 2 0','3 1 0 1 0','3 1 2 1 0','3 1 1 3 0'],
            'sat-rand-rep':['0 1 2 0','1 0 2 0','3 1 2 0','1 1 100000000 0'],
            'sat-synth-data':['0 0','-1 0']}
        for name,invalid in cases.items():
            for data in invalid:
                with self.subTest(name=name,data=data):
                    result=subprocess.run([str(self.programs[name]),*data.split()],capture_output=True,timeout=5)
                    self.assertNotEqual(result.returncode,0)
                    self.assertTrue(result.stderr)
                    self.assertNotIn(b'ACCEPTED',result.stdout)
        for name,valid in [('oss-data','2 10 .5 0 0'),('sat-closest-string-dat','3 1 1 2 0'),
                           ('sat-rand-rep','1 1 2 0'),('sat-synth-data','1 0')]:
            args=valid.split()
            for index in range(len(args)):
                if name=='oss-data' and index==2:continue
                for bad in ['2147483648','-2147483649','1junk']:
                    changed=args.copy();changed[index]=bad
                    with self.subTest(name=name,index=index,bad=bad):
                        result=subprocess.run([str(self.programs[name]),*changed],capture_output=True,timeout=5)
                        self.assertNotEqual(result.returncode,0)
                        self.assertNotIn(b'ACCEPTED',result.stdout)

    def test_admitted_boundary_values_before_random_work(self):
        cases={'oss-data':['1 0 0 0 -2147483648','78 2147483647 .999999 2147483647 2147483647'],
               'sat-closest-string-dat':['2 0 1 1 -2147483648','10000 1 1 9999 2147483647'],
               'sat-rand-rep':['1 1 1 -2147483648','99999999 2147483647 99999999 2147483647'],
               'sat-synth-data':['1 -2147483648','2147483647 2147483647']}
        for name,values in cases.items():
            for data in values:
                result=subprocess.run([str(self.programs[name]),*data.split()],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,(name,data,result.stderr))
                self.assertTrue(result.stdout.endswith(b'ACCEPTED\n'))

    def test_transfer_limit_stays_in_int_range_without_random_draws(self):
        text=(SOURCES/'oss-data.w').read_text()
        declaration=re.search(r'(?:float|double) p;',text)[0]
        statement=re.search(r'max_take=.*?;',text)[0]
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'transfer.c'
            source.write_text('#include <stdio.h>\n#include <limits.h>\n'+declaration+
                '\nint main(void){int del=INT_MAX,max_take; p=0;'+statement+
                'printf("%d\\n",max_take);p=0.5;'+statement+'printf("%d\\n",max_take);return 0;}')
            program=source.with_suffix('')
            subprocess.run(['gcc',*FLAGS,'-fsanitize=float-cast-overflow',str(source),'-o',str(program)],
                           check=True,capture_output=True)
            result=subprocess.run([str(program)],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,b'2147483647\n1073741823\n')


if __name__=='__main__': unittest.main()
