\datethis
@*Introduction. This is a quick-and-dirty implementation of the Garsia-Wachs
algorithm, written as I was preparing the 2nd edition of Volume~3, then
patched after Wolfgang Panny discovered a serious bug. (The bug
was corrected in the 17th printing of the 2nd edition, October 2004.)

The input weights are given on the command line. They must be nonnegative
integers whose total is at most |LLONG_MAX|.

The leaf nodes are 0, 1, \dots, $n$; the internal nodes are
$n+1$, $n+2$, \dots,~$2n$.

@d size 64 /* this number should exceed twice the number of input weights */

@c
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>

long long w[size]; /* node weights */
int l[size],r[size]; /* left and right children */
int d[size]; /* depth */
long long q[size]; /* working region */
int v[size]; /* number of node in working region */
int t; /* current size of working region */
int m; /* current node */

@<Subroutines@>@;

main(argc,argv)
  int argc; char *argv[];
{
  register int i,j,k,n;
  long long weight,total=0;
  char *end;
  @<Scan the command line@>;
  @<Do phase 1@>;
  @<Do phase 2@>;
  @<Do phase 3@>;
}

@ @<Scan the command line@>=
n=argc-2;
if (n<0) {
  fprintf(stderr,"Usage: %s wt0 ... wtn\n",argv[0]); exit(0);
}
if (n+n>=size) {
  fprintf(stderr,"Recompile me with a larger tree size!\n"); exit(0);
}
for (j=0;j<=n;j++) {
  errno=0;
  weight=strtoll(argv[j+1],&end,10);
  if (errno==ERANGE || end==argv[j+1] || *end || weight<0 ||
      weight>LLONG_MAX-total) {
    fprintf(stderr,"Invalid weight or excessive total at wt%d!\n",j); exit(1);
  }
  total+=weight;
  w[j]=weight; l[j]=r[j]=-1;
}

@ @<Do phase 1@>=
printf("Phase I:\n");
m=n;
t=1;
q[1]=w[0]; v[1]=0;
for (k=1;k<=n;k++) {
  while (t>1 && q[t-1]<=w[k]) combine(t);
  t++; q[t]=w[k]; v[t]=k;
  for (j=1;j<=t;j++) printf("%lld ",q[j]); printf("\n");
}
while (t>1) combine(t);

@ Working entries occupy positions 1 through |t|. Explicit index tests
replace an infinity sentinel, so no finite weight can overtake it.
Each combined weight is a sum over disjoint input leaves and is therefore
bounded by the total checked on input.

@ The |combine| subroutine combines weights |q[k-1]| and |q[k]| of the working
list, and continues to combine earlier weights if necessary to maintain
the condition $q[j-1]>q[j+1]$.

(The bug in my previous version was, in essence, to use `|if|' instead of
`|while|' in the final statement of this routine.)

@<Sub...@>=
combine(register int k)
{
  register int j,d;
  long long x;
  m++; l[m]=v[k-1]; r[m]=v[k]; w[m]=x=q[k-1]+q[k];
  printf(" node %d(%lld)=%d(%lld)+%d(%lld)\n",m,x,l[m],w[l[m]],r[m],w[r[m]]);
  t--;
  for (j=k;j<=t;j++) q[j]=q[j+1],v[j]=v[j+1];
  for (j=k-2;j>0 && q[j]<x;j--) q[j+1]=q[j],v[j+1]=v[j];
  q[j+1]=x; v[j+1]=m;
  for (d=1;d<=t;d++) printf("%lld ",q[d]);
  printf("\n");
  while (j>1 && q[j-1]<=x) {
    d=t-j; combine(j); j=t-d;
  }
}

@ @<Do phase 2@>=
printf("Phase II:\n");
mark(v[1],0);

@ The |mark| subroutine assigns level numbers to a subtree.

@<Sub...@>=
mark(k,p)
  int k; /* node */
  int p; /* starting depth */
{
  printf(" node %d(%lld) has depth %d\n",k,w[k],p);
  d[k]=p;
  if (l[k]>=0) mark(l[k],p+1);
  if (r[k]>=0) mark(r[k],p+1);
}

@ @<Do phase 3@>=
printf("Phase III:\n");
t=0; m=2*n;
if (n>0) build(1); /* a singleton already is the required tree */

@ The |build| subroutine rebuilds a tree from the depth table,
by doing a depth-first search according a slick idea by Bob Tarjan.
It creates a tree rooted at node~|m| having leftmost leaf~|t|.

@<Sub...@>=
build(b)
  int b; /* depth of node |m|, plus 1 */
{
  register int j=m;
  if (d[t]==b) l[j]=t++;
  else {
    m--; l[j]=m; build(b+1);
  }
  if (d[t]==b) r[j]=t++;
  else {
    m--; r[j]=m; build(b+1);
  }
  printf(" node %d = %d + %d\n", j,l[j],r[j]);
}
  
@* Index.
