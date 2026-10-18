"""Native fixture for exact small GraphBase union/intersection oracles."""
from pathlib import Path
import subprocess
from sgb_native import SgbNative


class MultigraphNative(SgbNative):
    def __init__(self,work):
        super().__init__(work,['gb_graph','gb_basic'])
        self.program=self.executable('multigraph','''#include "gb_graph.h"
#include "gb_basic.h"
int main(int argc,char**argv){long directed=atol(argv[2]),multi=atol(argv[3]),i,u,v,l;int which;Arc*a;
Graph*g=gb_new_graph(4L),*h=gb_new_graph(4L),*r,*target;
while(scanf("%d %ld %ld %ld",&which,&u,&v,&l)==4){target=which?h:g;
if(directed)gb_new_arc(target->vertices+u,target->vertices+v,l);
else gb_new_edge(target->vertices+u,target->vertices+v,l);}
r=argv[1][0]=='u'?gunion(g,h,multi,directed):intersection(g,h,multi,directed);if(!r)return 2;
for(i=0;i<r->n;i++)for(a=r->vertices[i].arcs;a;a=a->next)printf("%ld %ld %ld\\n",i,(long)(a->tip-r->vertices),a->len);
gb_recycle(r);gb_recycle(h);gb_recycle(g);return 0;}
''')

    def graph(self,kind,g,h,directed,multi=0):
        data=''.join(f'{which} {u} {v} {length}\n' for which,arcs in enumerate([g,h])
                     for u,v,length in arcs)
        result=subprocess.run([str(self.program),kind,str(directed),str(multi)],
                              input=data.encode(),capture_output=True,timeout=5)
        if result.returncode:raise AssertionError((result.returncode,result.stderr))
        return sorted(tuple(map(int,line.split())) for line in result.stdout.splitlines())


def expected(kind,g,h,directed,multi=0):
    def grouped(arcs):
        result={}
        for u,v,length in arcs:
            key=(u,v) if directed else tuple(sorted((u,v)))
            result.setdefault(key,[]).append(length)
        return result
    gg,hh=grouped(g),grouped(h)
    result=[]
    for key in gg.keys()|hh.keys():
        a,b=gg.get(key,[]),hh.get(key,[])
        if kind=='union':lengths=a+b if multi else [min(a+b)]
        elif not a or not b:continue
        elif multi:lengths=sorted(max(min(a),length) for length in b)[:min(len(a),len(b))]
        else:lengths=[max(min(a),min(b))]
        for length in lengths:
            result.append((*key,length))
            if not directed:result.append((key[1],key[0],length))
    return sorted(result)
