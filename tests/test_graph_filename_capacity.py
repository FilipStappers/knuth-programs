"""B057: admitted graph names must fit without corrupting adjacent storage."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import ROOT, FLAGS, GraphNative

SOURCES = ROOT/'programs/archives/SATexamples/sources'


class GraphFilenameCapacity(unittest.TestCase):
    def test_integer_output_formats_preserve_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            for name in ['flower-snark-line','mcgregor-graph']:
                text=(SOURCES/(name+'.w')).read_text()
                size=re.search(r'char buf\[(\d+)\]',text)[1]
                statement=re.search(r'sprintf\(buf,"(?:fsnarkline|mcgregor).*?;',text)[0]
                source=work/(name+'.c')
                source.write_text('''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct { char buf['''+size+''']; unsigned char guard[32]; } storage;
#define buf storage.buf
int main(int argc,char **argv){ int n=atoi(argv[1]); size_t i;
memset(&storage,90,sizeof(storage));
'''+statement+'''
for(i=0;i<sizeof(storage.guard);i++) if(storage.guard[i]!=90)return 79;
puts(buf);return 0;}
''')
                program=source.with_suffix('')
                subprocess.run(['gcc',*FLAGS,str(source),'-o',str(program)],check=True,capture_output=True)
                for n in [1,100000,2147483647,-2147483648]:
                    result=subprocess.run([str(program),str(n)],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,(name,n,result.stderr))
                    prefix='fsnarkline' if name=='flower-snark-line' else 'mcgregor'
                    self.assertEqual(result.stdout,f'{prefix}{n}.gb\n'.encode())

    def test_named_graph_long_basename(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            native=GraphNative(work)
            # empty(n) is just the allocation here; avoid linking unrelated
            # GraphBase graph constructors. Real edge insertion/save still run.
            text=(SOURCES/'ezgraph.w').read_text().replace('g=empty(nn+1);','g=gb_new_graph(nn+1);')
            program=native.build('named',text,SOURCES/'ezgraph-named.ch')
            for length in [1,15,16,180]:
                base=work/('g'*length)
                base.with_suffix('.dat').write_text('1 2\n2 3\n')
                result=subprocess.run([str(program),str(base)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,(length,result.stderr))
                graph=base.with_suffix('.gb').read_text()
                self.assertRegex(graph,r'"ezgraph [^"]*",\s*4,4\n')
                self.assertIn(f'Created graph {base}.gb',result.stdout.decode())


if __name__=='__main__': unittest.main()
