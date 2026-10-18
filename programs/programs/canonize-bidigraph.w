\let\swap=\leftrightarrow
@i gb_types.w

@*Intro. Given a bidirected graph~$B$, this program outputs an equivalent
bidirected graph~$[B]$ with the property that $[B]=[B']$ if and only if
$B'$ is obtained from $B$ by ``complementing'' some subset of the
vertices. Furthermore $[B]$ is directed whenever $B$ is directed.

(A bidirected graph is represented as in other programs such as
{\mc SSBIDIHAM}; please see that program for the basic definitions.
Complementing a vertex means to swap $v^-\!\swap v^+$
in the undirected graph $G(B)$ that corresponds to~$B$.
Complementation is of interest because it preserves the essential path
structure of~$B$.)

\def\0#1#2{\mathrel{\.{#1#2}}}
Every pair of distinct vertices $v$ and $w$ in a bidirected graph
is related in one of 16 different ways, depending on which of the
edges $v\0<<w$, $v\0>>w$, $v\0<>w$, $v\0><w$ are present.
(And there are 8 possible ``loops'' between a vertex and itself,
because $v\0<<v$ is the same as $v\0>>v$.)

Internally we represent a bidirected graph on $n$ vertices by an $n\times n$
adjacency matrix $a$, where $a[v][w]$ is a four-bit code. For example,
$a[v][w]=1000$ means that $v\0<<w$ but we don't have
$v\0>>w$ or $v\0<>w$ or $v\0><w$;
$a[v][w]=0101$ means that the only edges between $v$ and~$w$ are
$v\0>>w$ and $v\0><w$.

Suppose the four bits of $a[v][w]$ are $\it pqrs$. The operation of
complementing $v$ changes those bits to $\it srqp$; the operation of
complementing $w$ changes them to $\it rspq$; and the operation of
complementing both changes them to $\it qpsr$.

Our canonical form complements the variables in such a way that
the lexicographic order of the bitstrings on and above the diagonal
of the adjacency matrix, namely the sequence of $(n+1)n/2$ four-bit codes
$$(a[1][1],\ldots, a[1][n]; a[2][2],\ldots,a[2][n]; \ldots, a[n][n]),$$
is maximized.

@d maxn 100

@c
#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int a[maxn][maxn]; /* adjacency matrix */
int sign[maxn]; /* the sign of |vert(k)|, or zero */
int parent[maxn]; /* representatives of sign components */
int parity[maxn]; /* sign difference from a vertex to its parent */
int indep; /* the number of free sign components */
Graph *g,*gg;
@<Subroutines@>;
int main(int argc,char*argv[]) {
  register int i,j,k,n,cmax,code,edoc,exo;
  register int l,r,rk,rj,rn,pk,pj,pn,mask,c;
  register Arc *aa;
  register Vertex *v, *w;
  @<Process the command line@>;
  @<Set up the adjacency matrix@>;
  @<Determine canonical signs@>;
  @<Output the canonical graph@>;
  fprintf(stderr,"(%d vertices are independent.)\n",
                      indep@q)@>);
  if (!exo) fprintf(stderr,"This graph is actually directed!\n");
}

@ @<Process the command line@>=
if (argc!=2) {
  fprintf(stderr,"Usage: %s foo.gb\n",argv[0]);
  exit(-1);
}
g=restore_graph(argv[1]);
if (!g) {
  fprintf(stderr,"I couldn't reconstruct graph %s!\n",argv[1]);
  exit(-2);
}
n=g->n;
if (n>=maxn) {
  fprintf(stderr,"Sorry, graph %s has too many vertices (%d>=%d)!\n",
                              argv[1],n,maxn);
  exit(-2);
}

@ @d vert(k) (g->vertices+(k))
@d inx(v) ((v)-g->vertices)

@<Set up the adjacency matrix@>=
for (k=0;k<n;k++) {
  v=vert(k);
  for (aa=v->arcs;aa;aa=aa->next) {
    w=aa->tip, j=inx(w);
    switch (aa->len & 0x3) {
case 0: code=edoc=0x2;@+break;      /* $v\0<>w$ and $w\0<>v$ */
case 1: code=0x8,edoc=0x4;@+break;  /* $v\0<<w$ and $w\0>>v$ */
case 2: code=edoc=0x1;@+break;      /* $v\0><w$ and $w\0><v$ */
case 3: code=0x4,edoc=0x8;@+break;  /* $v\0>>w$ and $w\0<<v$ */   
    }
    a[k][j]|=code, a[j][k]|=edoc;
  }
}

@ The |ccode| routine changes a 4-bit |code| for |a[v][w]| by complementing~|v|
if $l=1$, complementing~|w| if $r=1$.

A little bit of bitwise fun.

@<Sub...@>=
int ccode(int code,int l,int r) {
  register int c=code;
  if (l) c=c^(((c^(c>>1))&0x5)*0x3);
  if (l!=r) c=c^(((c^(c>>2))&0x3)*0x5);
  return c;
}

@ We retain all sign choices that maximize the entries examined so far.
A component records equations of the form $s_i\mathbin\oplus s_j=b$;
vertex |n| is an extra anchor whose sign is zero. Thus an unanchored
component retains its two possible orientations until a later entry
can distinguish them.

For a four-bit code, the sign pairs attaining any particular value
form a coset of its stabilizer under the two complementations. Such a set has one, two,
or four elements, and can always be represented by fixed signs and/or
a fixed exclusive-or. Intersecting it with the existing component
equations preserves that representation. Consequently the greedy scan
retains exactly the choices attaining the lexicographic maximum; it
never chooses an orientation merely because the current row is done.

@<Determine canonical signs@>=
for (k=0;k<=n;k++) parent[k]=k,parity[k]=0;
for (k=0;k<n;k++) for (j=k;j<n;j++) {
  rk=representative(k),pk=parity[k];
  rj=representative(j),pj=parity[j];
  rn=representative(n),pn=parity[n];
  cmax=-1,mask=0;
  for (l=0;l<2;l++) for (r=0;r<2;r++) {
    if (rk==rn && l!=(pk^pn)) continue;
    if (rj==rn && r!=(pj^pn)) continue;
    if (rk==rj && (l^r)!=(pk^pj)) continue;
    c=ccode(a[k][j],l,r);
    if (c>cmax) cmax=c,mask=0;
    if (c==cmax) mask|=1<<(2*l+r);
  }
  if (!(mask&0xc)) join(k,n,0);
  if (!(mask&0x3)) join(k,n,1);
  if (!(mask&0xa)) join(j,n,0);
  if (!(mask&0x5)) join(j,n,1);
  if (!(mask&0x6)) join(k,j,0);
  if (!(mask&0x9)) join(k,j,1);
}
rn=representative(n),pn=parity[n];
for (k=0;k<n;k++) {
  rk=representative(k);
  sign[k]=parity[k]^(rk==rn? pn:0);
  if (rk==k && rk!=rn) indep++;
  fprintf(stderr,"%s=%d\n",vert(k)->name,sign[k]);
}

@ The parity is accumulated while compressing the path to a representative.
Joining two components imposes one sign-difference equation. The scan
above has already checked consistency with all previous equations.

@<Sub...@>=
int representative(int k) {
  int p=parent[k];
  if (p!=k) {
    parent[k]=representative(p);
    parity[k]^=parity[p];
  }
  return parent[k];
}
@#
void join(int k,int j,int difference) {
  int rk=representative(k),rj=representative(j);
  if (rk!=rj) {
    parent[rk]=rj;
    parity[rk]=parity[k]^parity[j]^difference;
  }
}

@ @d vvert(k) (gg->vertices+(k))

@<Output the canonical graph@>=
gg=gb_new_graph(n);
for (k=0;k<n;k++)
  vvert(k)->name=gb_save_string(vert(k)->name);
for (exo=j=0;j<n;j++) for (k=0;k<n;k++) if (a[j][k]) {
  cmax=ccode(a[j][k],sign[j],sign[k]);
  if (cmax&0x8) gb_new_arc(vvert(j),vvert(k),1);
  if (cmax&0x4) gb_new_arc(vvert(j),vvert(k),3);
  if (cmax&0x2) exo=1,gb_new_arc(vvert(j),vvert(k),0);
  if (cmax&0x1) exo=1,gb_new_arc(vvert(j),vvert(k),2);
}
snprintf(gg->id,sizeof(gg->id),"canonical %s",g->id);
save_graph(gg,"/tmp/makegraph.gb");
fprintf(stderr,"OK, I've created /tmp/makegraph.gb, with %d vertices",
                                                 n);
fprintf(stderr," and %ld edges\n",
                  gg->m/2);

@*Index.
