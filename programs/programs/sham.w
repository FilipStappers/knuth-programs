\datethis
@i gb_types.w

@*Symmetric Hamiltonian cycles. This program finds all Hamiltonian cycles of
an undirected graph in which the mapping $v\mapsto N-1-v$ is an
automorphism, such that the same automorphism also applies to the cycle.

We use a utility field to record the vertex degrees.

@d deg u.I
@d mm 8 /* should be even */
@d nn 9
@d solution_mod 100000

@c
#include "gb_graph.h" /* the GraphBase data structures */
#include "gb_basic.h" /* standard graphs */
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <stdint.h>
@<Subroutines@>@;

main()
{
  Graph *g=board(mm,nn,0,0,5,0,0); /* knight moves on rectangular chessboard */
  Vertex *x, *z, *tmax;
  register Vertex *t,*u,*v;
  register Arc *a,*aa, *yy;
  register int d;
  Arc *b,*bb;
  unsigned long long count=0,dcount=0;
  int dmin;
  if (!g || g->n<4 || (g->n&1) || g->n>INT_MAX) {
    fprintf(stderr,"I need a nonempty even-order graph with at least four vertices!\n");
    return -1;
  }
  @<Find the reflection-symmetric cycles@>;
  @<Reduce |g| to half size@>;
  @<Prepare |g| for backtracking, and find a vertex |x| of minimum degree@>;
  for (v=g->vertices;v<g->vertices+g->n;v++) printf(" %d",v->deg);
  printf("\n"); /* TEMPORARY CHECK */
  if (x->deg<2) {
    printf("The minimum degree is %d (vertex %s)!\n",x->deg,x->name);
    goto finish;
  }
  for (b=x->arcs;b->next;b=b->next) for (bb=b->next;bb;bb=bb->next) {
    a=b;
    z=bb->tip;
    @<Find all simple paths of length |g->n-2| from |a->tip| to |z|,
         avoiding |x|@>;
  }
finish:
  printf("Altogether %llu solutions and %llu wannabees.\n",count,dcount);
  for (v=g->vertices;v<g->vertices+g->n;v++) printf(" %d",v->deg);
  printf("\n"); /* TEMPORARY CHECK, SHOULD AGREE WITH FORMER VALUES */
}

@ We identify each vertex with its symmetric mate, and set the length
of an arc to 1 if the arc crosses to the mate instead of staying in the
same class.

Multiple arcs and self-loops can be introduced in this step.

@d mate(v) (g->vertices+(g->n-1-((v)-g->vertices)))
                       
@<Reduce |g| to half size@>=
for (v=g->vertices;mate(v)>v;v++)
  for (a=v->arcs;a;a=a->next) {
    u=mate(a->tip);
    if (u>a->tip) a->len=0;
    else {
      a->len=1;
      a->tip=u;
    }
  }
g->n/=2;

@ Self-loops caused a subtle bug (my test for |v->deg==1| below
failed), and they are of no interest in Hamiltonian circuits. So
I'm now getting rid of them.

@<Remove self-loops@>=
for (v=g->vertices;v<g->vertices+g->n;v++)
  for (a=v->arcs,aa=NULL;a;a=a->next)
    if (a->tip==v) {
      if (aa) aa->next=a->next;
      else v->arcs=a->next;
    } else aa=a;

@ Vertices that have already appeared in the path are ``taken,'' and
their |taken| field is nonzero. Initially we make all those fields zero.

@d taken v.I

@<Prepare |g| for backtracking, and find a vertex |x| of minimum degree@>=
@<Remove self-loops@>;
dmin=INT_MAX,x=g->vertices;
for (v=g->vertices;v<g->vertices+g->n;v++) {
  v->taken=0;
  d=0;
  for (a=v->arcs;a;a=a->next) d++;
  v->deg=d;
  if (d<dmin) dmin=d,x=v;
}

@*The data structures. I use one simple rule to cut off unproductive
branches of the search tree: If one of the vertices we could move to next
is adjacent to only one other unused vertex, we must move to it now.

The moves will be recorded in the vertex array of |g|. More precisely, the
|k|th arc of the path will be |t->ark| when |t| is the |k|th vertex of
the graph.

This program is a typical backtrack program. I am more comfortable doing
it with labels and goto statements than with while loops, but some day
I may learn my lesson.

@d ark x.A

@<Find all simple paths of length |g->n-2|...@>=
v=a->tip;
t=g->vertices;@+tmax=t+g->n-1;
x->taken=1;
a->len+=4; /* the first move is ``forced'' */
advance: @<Increase |t| and update the data structures to show that
           vertex |v| is now taken; |goto backtrack| if no further
           moves are possible@>;
try: @<Look at edge |a| and its successors, advancing if it is a valid move@>;
restore: @<Downdate the data structures to the state they were in when
           level |t| was entered@>;
backtrack: @<Decrease |t|, if possible, and try the next possibility;
           or |goto done|@>;
done:

@ @<Increase |t| and update the data structures...@>=
t->ark=a;
t++;
v=a->tip;
v->taken=1;
if (v==z) {
  if (t==tmax) @<Record a solution@>;
  goto backtrack;
}
yy=NULL; /* |yy| is a forced arc, if any exist */
for (aa=v->arcs;aa;aa=aa->next) {
  u=aa->tip;
  d=u->deg-1;
  if (d==1 && u->taken==0) {
    if (yy) goto restore; /* restoration will stop at |aa| */
    yy=aa;
  }
  u->deg=d;
}
if (yy) {
  a=yy;
  a->len+=4;
  goto advance;
}
a=v->arcs;

@ @<Downdate the data structures to the state they were in when
           level |t| was entered@>=
for (a=(t-1)->ark->tip->arcs;a!=aa;a=a->next) a->tip->deg++;

@ @<Look at edge |a| and its successors, advancing if it is a valid move@>=
while (a) {
  if (a->tip->taken==0) {
    a->len+=2; /* oops, this is unnecessary residue of {\sc SHAMR} */
    goto advance;
  }
  a=a->next;
}
restore_all: aa=NULL; /* all moves tried; we fall through to |restore| */

@ Here we come to a subtle point. When a forced move is a duplicated arc,
we want to continue with the duplicate arc; we don't want to backtrack!

But that isn't the most subtle part. It turns out that we want to
consider the duplicate arc {\it previous\/} to the one that worked.
(That one should really have been considered forced; if on the other
hand the first of two duplicate arcs is selected, the second one will
decrease the degree to zero and cannot lead to a complete tour, so
we don't want to reconsider it.) Get it? The present logic works
only when there are at most two duplicate arcs.

@<Decrease |t|, if possible...@>=
t--;
a=t->ark;
a->tip->taken=0;
d=a->len;
a->len &=1;
if (d<4) {
  a=a->next;
  goto try;
}
if (t==g->vertices) goto done;
for (aa=(t-1)->ark->tip->arcs;aa!=a;aa=aa->next) if (aa->tip==a->tip) {
  aa->len+=4;
  a=aa;
  goto advance;
}
goto restore_all; /* the move was forced */

@ @<Record a solution@>=
{ int s=bb->len&1; /* include the closing edge */
  for (u=g->vertices;u<tmax;u++) s^=u->ark->len&1;
  if (s) {
    increment_count(&count);
    if (count%solution_mod==0) {
      printf("%llu: %s",count,x->name);
      for (u=g->vertices;u<tmax;u++)
        printf("%s%s",u->ark->len&1? "*":" ",u->ark->tip->name);
      printf("\n");
    }
  } else {
    increment_count(&dcount);
    if (dcount%solution_mod==0) {
      printf(">%llu: %s",dcount,x->name);
      for (u=g->vertices;u<tmax;u++)
        printf("%s%s",u->ark->len&1? "*":" ",u->ark->tip->name);
      printf("\n");
    }
  }
}

@* Reflections. A fixed-point-free involution of a cycle is either a
half-rotation or a reflection through two opposite edges. The quotient-cycle
search above handles half-rotations. A reflection instead has two fixed
edges, each joining a vertex to its mate. Between them is a path containing
exactly one vertex from each mate pair; its reflected reverse supplies the
other half of the cycle.

We orient such a path from the smaller endpoint pair and start at that
pair's lower-numbered vertex. These choices remove endpoint reversal and
the global exchange of mates, respectively. Original graphs are assumed
simple, as are the knight boards for which this program was written.

@<Subroutines@>=
void increment_count(unsigned long long *count) {
  if (*count==ULLONG_MAX) {
    fprintf(stderr,"The solution counter is exhausted!\n");
    exit(-2);
  }
  (*count)++;
}

void reflection_paths(Graph *g,int *path,unsigned char *used,
                      unsigned char *fixed,int depth,int start,
                      unsigned long long *count) {
  int n=(int)g->n,q=n/2,v=path[depth-1],w,pair,i;
  Arc *a;
  if (depth==q) {
    pair=(v<q?v:n-1-v);
    if (pair<=start || !fixed[pair]) return;
    increment_count(count);
    if (*count%solution_mod==0) {
      printf("%llu: reflection:",*count);
      for (i=0;i<q;i++) printf(" %s",g->vertices[path[i]].name);
      for (i=q;i>0;i--) printf(" %s",g->vertices[n-1-path[i-1]].name);
      printf("\n"); /* reflection witness */
    }
    return;
  }
  for (a=g->vertices[v].arcs;a;a=a->next) {
    w=(int)(a->tip-g->vertices);
    pair=(w<q?w:n-1-w);
    if (!used[pair]) {
      used[pair]=1,path[depth]=w;
      reflection_paths(g,path,used,fixed,depth+1,start,count);
      used[pair]=0;
    }
  }
}

@ @<Find the reflection-symmetric cycles@>=
{
  size_t q=(size_t)g->n/2;
  int *path;
  unsigned char *used,*fixed;
  int i;
  if (q>SIZE_MAX/sizeof(int) || !(path=malloc(q*sizeof(int))) ||
      !(used=calloc(q,1)) || !(fixed=calloc(q,1))) {
    fprintf(stderr,"I can't allocate the reflection search!\n");
    exit(-3);
  }
  for (i=0;i<q;i++)
    for (a=g->vertices[i].arcs;a;a=a->next)
      if (a->tip==g->vertices+g->n-1-i) fixed[i]=1;
  for (i=0;i<q;i++) if (fixed[i]) {
    path[0]=i,used[i]=1;
    reflection_paths(g,path,used,fixed,1,i,&count);
    used[i]=0;
  }
  free(path); free(used); free(fixed);
}

@*Index.
