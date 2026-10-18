"""BUG-057: Montgomery operands must be reduced nonzero residues.

Fixed witness words exercise arithmetic; no RNG/sampling assessment is made.
"""
import math
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'programs/programs/prime-sieve-sparse.w'


class SparsePrimalityWitnesses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        work=Path(cls.temp.name)
        text=SOURCE.read_text()
        for macro,value in [('del','1024LL'),('kmax','10000'),('ksmall','100'),
                            ('qsize','4'),('lsize','4096')]:
            text=re.sub(r'(?m)^@d '+macro+r' .*$', '@d '+macro+' '+value,text)
        text=text.replace('main(int argc, char*argv[])','int sieve_main(int argc, char*argv[])')
        text=re.sub(r'(?m)^@d ran_arr_next\(\).*$', '@d ran_arr_next() test_witness()',text)
        text=text.replace('@c','''@c
long test_witness(void) {
  static unsigned int k;
  static const long words[]={1073741823,1073741822,2,3,5,7,11,13,17,19,23,29,31,37};
  return words[k++%14];
}
''',1)
        source=work/'sparse.w'
        source.write_text(text)
        generated=source.with_suffix('.c')
        subprocess.run(['ctangle',str(source),'-',str(generated)],check=True,capture_output=True)
        with generated.open('a') as f:
            f.write('''
int main(void) { unsigned long long z; outfile=tmpfile();
while(scanf("%llu",&z)==1) printf("%llu %d\\n",z,isprime(z));
fclose(outfile); return 0; }
''')
        cls.program=source.with_suffix('')
        subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1','-fsanitize=undefined,bounds',
                        '-fsanitize-undefined-trap-on-error',str(generated),'-o',str(cls.program)],
                       check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_small_candidate_against_trial_division(self):
        values=list(range(55))+list(range(55,20000,4))
        result=subprocess.run([str(self.program)],input='\n'.join(map(str,values)).encode(),
                              capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        actual={int(z):int(p) for z,p in (line.split() for line in result.stdout.splitlines())}
        expected={z:int(z>=2 and all(z%d for d in range(2,math.isqrt(z)+1))) for z in values}
        self.assertEqual(actual,expected)

    def test_unsupported_montgomery_domains_reject(self):
        for z in [61,2**63+3]:
            result=subprocess.run([str(self.program)],input=str(z).encode(),capture_output=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'Unsupported Montgomery primality domain',result.stderr)
            self.assertEqual(result.stdout,b'')

    def test_large_mersenne_primes_and_explicit_composites(self):
        primes=[2**p-1 for p in [31,61]]
        # Exact Lucas-Lehmer certificates for these two prime exponents.
        for p,n in zip([31,61],primes):
            state=4
            for _ in range(p-2):
                state=(state*state-2)%n
            self.assertEqual(state,0)
        composites=[(2**29+3)*(2**29+5),(2**30+3)*(2**30+5),3215031751]
        values=primes+composites
        result=subprocess.run([str(self.program)],input='\n'.join(map(str,values)).encode(),
                              capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertEqual([int(line.split()[1]) for line in result.stdout.splitlines()],[1,1,0,0,0])


if __name__ == '__main__':
    unittest.main()
