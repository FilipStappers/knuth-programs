"""Deterministic constructor fixture for the directly repaired GraphBase."""
import subprocess
from sgb_native import SgbNative


class BasicNative(SgbNative):
    def __init__(self,work):
        super().__init__(work,['gb_graph','gb_io','gb_flip','gb_sort','gb_basic'])
        self.program=self.executable('basic_fixture','''#include "gb_graph.h"
#include "gb_basic.h"
int main(int argc,char **argv){Graph*g,*bait;long i;Arc*a;long n=strtol(argv[2],0,10),h=strtol(argv[3],0,10),d=strtol(argv[4],0,10);
bait=board(12L,12L,0L,0L,1L,0L,0L);if(!bait)return 3;gb_recycle(bait);
if(!strcmp(argv[1],"perms"))g=perms(1L-n,0L,0L,0L,0L,0UL,d);
else if(!strcmp(argv[1],"binary"))g=binary((unsigned long)n,(unsigned long)h,d);
else if(!strcmp(argv[1],"simplex"))g=simplex((unsigned long)n,n,h,0L,0L,0L,d);
else if(!strcmp(argv[1],"subsets"))g=subsets((unsigned long)n,n,h,0L,0L,0L,1UL,d);
else g=parts((unsigned long)n,(unsigned long)h,(unsigned long)strtol(argv[5],0,10),d);
if(!g){fprintf(stderr,"REJECTED %ld\\n",panic_code);return 2;}
printf("G %ld %ld\\n",g->n,g->m);for(i=0;i<g->n;i++){printf("V %ld %s\\n",i,g->vertices[i].name);
for(a=g->vertices[i].arcs;a;a=a->next)printf("A %ld %ld %ld\\n",i,(long)(a->tip-g->vertices),a->len);}
gb_recycle(g);return 0;}
''')

    def graph(self,kind,n,parameter=0,directed=0,max_size=0):
        result=subprocess.run([str(self.program),kind,str(n),str(parameter),str(directed),str(max_size)],
                              capture_output=True,timeout=10)
        if result.returncode:raise AssertionError((kind,n,parameter,result.returncode,result.stderr))
        lines=result.stdout.decode().splitlines()
        count,arcs=map(int,lines[0].split()[1:])
        names={int(line.split(' ',2)[1]):line.split(' ',2)[2] for line in lines if line.startswith('V ')}
        edges=[(names[int(a)],names[int(b)],int(length)) for _,a,b,length in
               (line.split() for line in lines if line.startswith('A '))]
        assert len(names)==count and len(edges)==arcs
        return set(names.values()),edges
