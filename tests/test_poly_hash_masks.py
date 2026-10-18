"""B037: defined modular hash startup and unsigned instruction high bits."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCES=Path(__file__).resolve().parents[1]/'programs/programs'


class PolyHashMasks(unittest.TestCase):
    def native(self,text):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'probe.c'
            source.write_text('#include <stdio.h>\n#include <stdlib.h>\n#include <stdint.h>\n'+text)
            program=source.with_suffix('')
            subprocess.run(['gcc','-std=gnu99','-O1','-fsanitize=undefined,bounds',
                            '-fsanitize-undefined-trap-on-error',str(source),'-o',str(program)],
                           check=True,capture_output=True)
            result=subprocess.run([str(program)],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertEqual(result.stderr,b'')
            return list(map(int,result.stdout.split()))

    def test_all_startup_hash_words(self):
        for name,array,rows,cols in [('polyenum','hash',range(1,8),range(256)),
                                     ('polynum','hash_bits',range(8),range(1,256))]:
            with self.subTest(name=name):
                text=(SOURCES/(name+'.w')).read_text()
                start=text.index('@<Init...@>=',text.index('The random number generator'))
                body=text[start:].split('@<Init...@>=',1)[1].split('\n\n@',1)[0]
                native='''#define hash_width 20
unsigned int hash[8][256],hash_bits[8][256];
int main(void) { int j,k,m,row_end;
'''+body+f'\nfor(j={rows.start};j<{rows.stop};j++) for(k={cols.start};k<{cols.stop};k++) printf("%u\\n",{array}[j][k]);\nreturn 0;}}'
                state=314159265
                expected=[]
                for _ in rows:
                    for _ in cols:
                        state=(69069*state+1)%(2**32)
                        expected.append(state//2**12)
                self.assertEqual(self.native(native),expected)

    def test_high_masks(self):
        enum=(SOURCES/'polyenum.w').read_text()
        slave=(SOURCES/'polyslave.w').read_text()
        code=re.search(r'(?m)^@d new_level_code (\S+)',enum)[1]
        modulus=re.search(r'(?m)^@d maxm (\S+)',slave)[1]
        body=enum.split('@<Record the arrival of a new |m|@>=',1)[1].split('\n\n@',1)[0]
        native=f'''#define new_level_code {code}
#define maxm {modulus}
unsigned int buf;
int out_it(void) {{ return 1; }}
void panic(char *s) {{ exit(1); }}
int main(void) {{ int m=30;
'''+body+'\nprintf("%u %u\\n",buf,maxm); return 0;}'
        self.assertEqual(self.native(native),[(31<<27)+30,2**31])

    def test_transition_multiplicity_high_bits(self):
        text=(SOURCES/'polyenum.w').read_text()
        expression=re.search(r'(?m)^    buf=(.*patt_code\(s->pat\));$',text)[1]
        native='''#define patt_code(p) 7
struct successor { char degree; } value,*s=&value;
int main(void) { unsigned int buf; int d;
for(d=1;d<=30;d++) { s->degree=d;
buf='''+expression+'''; printf("%u\\n",buf); }
return 0; }
'''
        self.assertEqual(self.native(native),[(d<<27)+(1<<26)+7 for d in range(1,31)])

    def test_bases_and_restart_changes_compose(self):
        with tempfile.TemporaryDirectory() as temp:
            for name,change in [('polyenum',None),('polynum',None),
                                ('polynum','polynum-restart'),('polyslave',None),
                                ('polyslave','polyslave-restart')]:
                with self.subTest(name=name,change=change):
                    generated=Path(temp)/((change or name)+'.c')
                    subprocess.run(['ctangle',str(SOURCES/(name+'.w')),
                                    str(SOURCES/(change+'.ch')) if change else '-',str(generated)],
                                   check=True,capture_output=True)
                    subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int',
                                    '-Wno-implicit-function-declaration','-include','stdlib.h',
                                    '-include','string.h','-c',str(generated),
                                    '-o',str(generated.with_suffix('.o'))],check=True,capture_output=True)


if __name__ == '__main__':
    unittest.main()
