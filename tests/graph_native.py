"""Small native GraphBase fixture builder shared by Hamiltonian regressions."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
FLAGS = ['-std=gnu99','-Wno-implicit-int','-O1','-fcommon',
         '-include','stdlib.h','-include','string.h',
         '-I'+str(GRAPHBASE),'-fsanitize=undefined,bounds',
         '-fsanitize-undefined-trap-on-error','-fno-sanitize-recover=all']


class GraphNative:
    def __init__(self, work):
        self.work = work
        self.objects = []
        for name in ['gb_graph','gb_io','gb_save','gb_flip']:
            obj = work/(name+'.o')
            subprocess.run(['gcc','-std=gnu99','-Wno-implicit-int','-O1','-fcommon','-I'+str(GRAPHBASE),
                            '-include','stdlib.h','-include','string.h',
                            '-c',str(GRAPHBASE/(name+'.c')),'-o',str(obj)],
                           check=True,capture_output=True)
            self.objects.append(str(obj))
        fixture = work/'fixture.c'
        fixture.write_text('''#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc,char **argv) {
  int n=atoi(argv[1]),directed=atoi(argv[2]),i,j; char name[32]; Graph *g=gb_new_graph(n);
  if(!g) return 1;
  for(i=0;i<n;i++){sprintf(name,"v%d",i);g->vertices[i].name=gb_save_string(name);}
  while(scanf("%d %d",&i,&j)==2) {
    if(directed) gb_new_arc(g->vertices+i,g->vertices+j,1);
    else gb_new_edge(g->vertices+i,g->vertices+j,1);
  }
  return save_graph(g,argv[3]);
}
''')
        self.writer = work/'fixture'
        subprocess.run(['gcc',*FLAGS,str(fixture),*self.objects,'-o',str(self.writer)],
                       check=True,capture_output=True)

    def build(self, name, text):
        source, generated, program = [self.work/(name+s) for s in ['.w','.c','']]
        source.write_text(text)
        subprocess.run(['ctangle',str(source),'-',str(generated)],cwd=GRAPHBASE,
                       check=True,capture_output=True)
        subprocess.run(['gcc',*FLAGS,str(generated),*self.objects,'-lm','-o',str(program)],
                       check=True,capture_output=True)
        return program

    def graph(self, n, edges, directed=False):
        path = self.work/'graph.gb'
        subprocess.run([str(self.writer),str(n),str(int(directed)),str(path)],
                       input=''.join(f'{i} {j}\n' for i,j in edges).encode(),
                       capture_output=True,check=True,timeout=10)
        return path
