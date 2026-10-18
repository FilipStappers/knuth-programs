"""BUG-086: full signed-long seed domain and published stream check."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'programs/programs/rng.c'


class RngSeeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        wrapper = work/'seed.c'
        wrapper.write_text('''#include <stdlib.h>
#include <limits.h>
#define main published_main
#include "'''+SOURCE.as_posix()+'''"
#undef main
int main(int argc,char **argv) {
  long a[2009], seed; int i, batch;
  if(argc==1) return published_main();
  seed=argv[1][0]=='M'? LONG_MAX: argv[1][0]=='m'? LONG_MIN: strtol(argv[1],0,10);
  ran_start(seed);
  for(batch=0;batch<3;batch++) {
    ran_array(a,batch==1?2009:1009);
    for(i=0;i<1009;i++) printf("%ld\\n",a[i]);
  }
  return 0;
}
''')
        cls.program = work/'seed'
        subprocess.run(['gcc','-std=gnu99','-O1','-fsanitize=undefined,bounds',
                        '-fsanitize-undefined-trap-on-error',
                        '-fno-sanitize-recover=all',str(wrapper),'-o',str(cls.program)],
                       check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def stream(self, seed):
        result = subprocess.run([str(self.program),str(seed)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertEqual(result.stderr,b'')
        values = list(map(int,result.stdout.split()))
        self.assertEqual(len(values),3027)
        self.assertTrue(all(0 <= x < 2**30 for x in values))
        return values

    def test_signed_seed_endpoints_and_modular_equivalence(self):
        # C long is at least 32 bits; each endpoint has these low thirty bits.
        for seed, reduced in [('M',2**30-1),('m',0),(-1,2**30-1),
                              (-2,2**30-2),(2**30,0),(2**30+1,1),
                              (2**30-2,-2),(0,0),(1,1),(310952,310952)]:
            with self.subTest(seed=seed):
                self.assertEqual(self.stream(seed),self.stream(reduced))

    def test_published_bulk_stream(self):
        result = subprocess.run([str(self.program)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertEqual(result.stdout,b'995235265\n995235265\n')
        self.assertEqual(result.stderr,b'')


if __name__ == '__main__':
    unittest.main()
