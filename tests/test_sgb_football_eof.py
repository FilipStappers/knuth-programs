"""SGB-014: EOF must not reuse a previous team or scan uninitialized bytes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from sgb_native import SgbNative,SGB,FLAGS


class SgbFootballEof(unittest.TestCase):
    def test_eof_blank_and_unterminated_team_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            native=SgbNative(work,['gb_graph','gb_io','gb_flip','gb_sort','gb_games'])
            result=subprocess.run(['ctangle',str(SGB/'football.w'),'-',str(work/'football.c')],
                                  cwd=work,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout)
            obj=work/'football.o'
            result=subprocess.run(['gcc',*FLAGS,'-I'+str(work),'-Dmain=football_main','-c',
                                   str(work/'football.c'),'-o',str(obj)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            program=native.executable('football_eof','''#include "gb_graph.h"
extern Graph*g;extern Vertex*prompt_for_team();
int main(void){int i;Vertex*v;g=gb_new_graph(3L);
g->vertices[0].name=gb_save_string("Alpha");g->vertices[1].name=gb_save_string("Beta");
g->vertices[2].name=gb_save_string("AAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
for(i=0;i<4;i++){v=prompt_for_team("Team");fprintf(stderr,"%s\\n",v?v->name:"NULL");}
gb_recycle(g);return 0;}
''',objects=native.objects+[str(obj)])
            for data,expected in [(b'Alpha\n',['Alpha']),
                                  (b'Alpha\nBeta\n',['Alpha','Beta']),
                                  (b'Alpha',['Alpha']),
                                  (b'',['NULL']),
                                  (b'\nAlpha\n',['NULL','Alpha']),
                                  (b'A'*29,['A'*29])]:
                result=subprocess.run([str(program)],input=data,capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,(data,result.stdout,result.stderr))
                self.assertEqual(result.stderr.decode().splitlines(),expected+['NULL']*(4-len(expected)))


if __name__=='__main__':unittest.main()
