"""SGB-009: gate operand names are literal text."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from sgb_native import SgbNative


class SgbGateNames(unittest.TestCase):
    def test_print_literal_percent_names(self):
        with tempfile.TemporaryDirectory() as temp:
            native=SgbNative(Path(temp),['gb_graph','gb_flip','gb_gates'])
            program=native.executable('gate_names','''#include "gb_graph.h"
#include "gb_gates.h"
int main(void){Graph*g=gb_new_graph(3L);Vertex*v=g->vertices;
v[0].name=gb_save_string("input%%");v[0].typ='I';
v[1].name=gb_save_string("ordinary");v[1].typ='I';
v[2].name=gb_save_string("and%%");v[2].typ='&';
gb_new_arc(v+2,v,1L);gb_new_arc(v+2,v+1,1L);
print_gates(g);gb_recycle(g);return 0;}
''')
            result=subprocess.run([str(program)],capture_output=True,timeout=5,check=True)
            self.assertEqual(result.stdout.decode(),
                             'input%% = input\nordinary = input\nand%% = ordinary & input%%\n')


if __name__=='__main__':unittest.main()
