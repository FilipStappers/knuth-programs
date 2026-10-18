"""BUG-011: preserve graph descriptions as literal text through reduction."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'programs/programs/simpath-reduce.w'


class SimpathLiteralNames(unittest.TestCase):
    def test_literal_percent_names_and_unchanged_reduction(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            names=work/'names.txt'
            source=work/'reduce.w'
            source.write_text(SOURCE.read_text().replace('/tmp/simpath-names',names.as_posix())
                              .replace('@d memsize (1<<25)','@d memsize (1<<12)'))
            generated=source.with_suffix('.c')
            program=source.with_suffix('')
            subprocess.run(['ctangle',str(source),'-',str(generated)],check=True,capture_output=True)
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1',
                            '-fsanitize=undefined,bounds','-fsanitize-undefined-trap-on-error',
                            str(generated),'-o',str(program)],check=True,capture_output=True)
            for name in ['plain','name%%text','100%%','two%%percents%%']:
                with self.subTest(name=name):
                    description=f'1({name})\n'.encode()
                    result=subprocess.run([str(program)],input=description+b'#1:\n2:0,1\n',
                                          capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertEqual(names.read_bytes(),description)
                    self.assertEqual(result.stdout,b'2: (~1?0:1)\n')


if __name__ == '__main__':
    unittest.main()
