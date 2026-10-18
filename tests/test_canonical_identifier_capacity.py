"""BUG-018: include the canonical prefix within GraphBase's fixed id field."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from graph_native import GRAPHBASE, ROOT


@unittest.skipUnless((GRAPHBASE/'gb_graph.h').exists(),'GraphBase headers required')
class CanonicalIdentifierCapacity(unittest.TestCase):
    def test_all_prefix_boundaries_preserve_following_graph_fields(self):
        text=(ROOT/'programs/programs/canonize-bidigraph.w').read_text()
        statement=re.search(r'(?:s|sn)printf\(gg->id,.*?;',text,re.S)[0]
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'id.c'
            source.write_text('''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include "gb_graph.h"
struct guarded { Graph graph; unsigned char tail[32]; } target;
Graph input,*g=&input,*gg=&target.graph;
int main(int argc,char **argv) {
  size_t i,end=offsetof(struct guarded,graph)+offsetof(Graph,id)+sizeof(gg->id);
  memset(&target,90,sizeof(target));
  snprintf(g->id,sizeof(g->id),"%s",argv[1]);
'''+statement+'''
  for(i=end;i<sizeof(target);i++) if(((unsigned char*)&target)[i]!=90) return 79;
  puts(gg->id); return 0;
}
''')
            program=source.with_suffix('')
            subprocess.run(['gcc','-std=gnu99','-O1','-I'+str(GRAPHBASE),str(source),'-o',str(program)],
                           check=True,capture_output=True)
            for length in [0,1,149,150,151,160]:
                with self.subTest(length=length):
                    name='g'*length
                    result=subprocess.run([str(program),name],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
                    self.assertEqual(result.stdout,('canonical '+name[:150]+'\n').encode())


if __name__ == '__main__':
    unittest.main()
