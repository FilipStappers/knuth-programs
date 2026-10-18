"""B037-polyenum-missing-argument: stop at invalid command-line arity."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'programs/programs/polyenum.w'


class PolyenumArguments(unittest.TestCase):
    def test_exactly_one_output_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'polyenum.w'
            text=SOURCE.read_text()
            # Observe acceptance immediately after the real command-line scan,
            # before the separately tracked startup arithmetic and large search.
            text=text.replace('  @<Initialize@>;','  printf("ACCEPTED %s\\n",base_name); return 0;')
            source.write_text(text)
            generated=source.with_suffix('.c')
            program=source.with_suffix('')
            subprocess.run(['ctangle',str(source),'-',str(generated)],check=True,capture_output=True)
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-include','stdlib.h',
                            '-include','string.h','-O1','-fsanitize=undefined,bounds',
                            '-fsanitize-undefined-trap-on-error',str(generated),'-o',str(program)],
                           check=True,capture_output=True)
            for args in [[],['one','two']]:
                result=subprocess.run([str(program),*args],capture_output=True,timeout=5)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(result.stdout,b'')
                self.assertIn(b'Usage:',result.stderr)
            for prefix in ['output','prefix with spaces']:
                result=subprocess.run([str(program),prefix],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                self.assertEqual(result.stderr,b'')
                self.assertEqual(result.stdout,f'ACCEPTED {prefix}\n'.encode())


if __name__ == '__main__':
    unittest.main()
