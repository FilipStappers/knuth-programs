"""SGB-003: documented leading comments preserve saved graph semantics."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from sgb_native import SgbNative


class SgbRestoreComments(unittest.TestCase):
    def test_comments_advance_and_missing_headers_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            native=SgbNative(work,['gb_graph','gb_io','gb_save'])
            program=native.executable('restore_comments','''#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv){Graph*g;int i;Arc*a;
if(argc==3){g=gb_new_graph(3L);for(i=0;i<3;i++)g->vertices[i].name=gb_save_string(i==0?"a":i==1?"b":"c");
gb_new_edge(g->vertices,g->vertices+1,7L);gb_new_edge(g->vertices+1,g->vertices+2,9L);return save_graph(g,argv[1]);}
g=restore_graph(argv[1]);if(!g){fprintf(stderr,"Rejected graph %ld\\n",panic_code);return 2;}
printf("%ld %ld\\n",g->n,g->m);for(i=0;i<g->n;i++){printf("%s",g->vertices[i].name);
for(a=g->vertices[i].arcs;a;a=a->next)printf(" %ld:%ld",(long)(a->tip-g->vertices),a->len);puts("");}gb_recycle(g);return 0;}
''')
            path=work/'original.gb'
            subprocess.run([str(program),str(path),'create'],check=True,capture_output=True,timeout=5)
            expected=b'3 4\na 1:7\nb 2:9 0:7\nc 1:9\n'
            original=path.read_bytes()
            for comments in [b'',b'* comment\n',b'*\n* another comment\n',b'* '+'x'.encode()*76+b'\n']:
                fixture=work/'input.gb';fixture.write_bytes(comments+original)
                result=subprocess.run([str(program),str(fixture)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,(comments,result.stderr))
                self.assertEqual(result.stdout,expected)
            for invalid in [b'',b'* only a comment\n',b'not a header\n',b'* comment\nnot a header\n']:
                fixture.write_bytes(invalid)
                result=subprocess.run([str(program),str(fixture)],capture_output=True,timeout=5)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(b'Rejected graph',result.stderr)
                self.assertEqual(result.stdout,b'')


if __name__=='__main__':unittest.main()
