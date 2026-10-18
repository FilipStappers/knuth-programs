@*Intro. This program tries to generate a ``hard'' open shop scheduling
problem with $n$ jobs and $n$ machines, using the method suggested by
Gu\'eret and Prins in {\sl Annals of Operations Research\/ \bf92} (1999),
165--183: We start with work times $w_{ij}$ that are as near
equal as possible, having constant row and column sums~$s$. Then
we choose random rows $i\ne i'$ and random columns $j\ne j'$,
and transfer $\delta$ units of weight by setting
$$w_{ij}\gets w_{ij}-\delta,\quad
  w_{i'j}\gets w_{i'j}+\delta,\quad
  w_{ij'}\gets w_{ij'}+\delta,\quad
  w_{i'j'}\gets w_{i'j'}-\delta,$$
where $0\le\delta\le w_{ij}$ and $\delta\le w_{i'j'}$; this operation clearly
preserves the row and column sums. The value of $\delta$ is randomly
distributed between $p\min\{w_{ij},w_{i'j'}\}$ and $\min\{w_{ij},w_{i'j'}\}$,
where $p$ is a parameter.
The final weights are obtained after making $r$ such transfers.

Parameters $n$, $s$, $p$, and $r$ are given on the command line, together
with a random seed value to specify the source of random numbers.
(Gu\'eret and Prins suggested taking $p=.95$ when $n\ge6$, and $r=n^3$.)

The output consists of $n$ lines of $n$ numbers each, suitable for
input to {\ms SAT-OSS}.

@d maxn '~'-'0' /* jobs/machines are single characters, |'0'<=c<'~'| */

@c
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <errno.h>
#include <math.h>
#include "gb_flip.h" /* the random number generator */
int n,s,r,seed; /* integer command-line parameters */
double p; /* the floating point command-line parameter */
int w[maxn][maxn]; /* the work times */
int scan_int(char *arg,int *destination) {
  char *end;
  long value;
  errno=0; value=strtol(arg,&end,10);
  if (end==arg || *end || errno || value<INT_MIN || value>INT_MAX) return 0;
  *destination=(int)value;
  return 1;
}
int scan_probability(char *arg,double *destination) {
  char *end;
  errno=0; *destination=strtod(arg,&end);
  return end!=arg && !*end && !errno && isfinite(*destination);
}
main(int argc,char*argv[]) {
  register int i,j,ii,jj,del,max_take,rep;
  @<Process the command line@>;
  @<Create the initial weights@>;
  for (rep=0;rep<r;rep++) @<Make a random weight transfer@>;
  @<Output the final weights@>;
}

@ @<Process the command line@>=
if (argc!=6 ||
      !scan_int(argv[1],&n) ||
      !scan_int(argv[2],&s) ||
      !scan_probability(argv[3],&p) ||
      !scan_int(argv[4],&r) ||
      !scan_int(argv[5],&seed) ) {
  fprintf(stderr,"Usage: %s n scale prob reps seed\n",
                                 argv[0]);
  exit(-1);
}
if (n<1 || n>maxn || s<0 || r<0 || (n==1 && r>0)) {
  fprintf(stderr,"Require 1<=n<=%d, scale/reps>=0, and n>=2 for transfers!\n",maxn);
  exit(-2);
}
if (p<0 || p>=1.0) {
  fprintf(stderr,"The probability must be between 0.0 and 1.0, not %.2g!\n",
                                                p);
  exit(-2);
}
gb_init_rand(seed);
printf("~ oss-data %d %d %g %d %d\n",
                          n,s,p,r,seed);

@ @<Create the initial weights@>=
del=s/n;
for (i=0;i<n;i++) for (j=0;j<n;j++) w[i][j]=del;
del=s-n*del;
for (i=0;i<n;i++) for (j=0;j<del;j++)
  w[i][(i+j)%n]++;

@ @<Make a random weight transfer@>=
{
  while (1) {
    i=gb_unif_rand(n);
    ii=gb_unif_rand(n);
    if (i!=ii) break;
  }
  while (1) {
    j=gb_unif_rand(n);
    jj=gb_unif_rand(n);
    if (j!=jj) break;
  }
  del=(w[i][j]<=w[ii][jj]? w[i][j]: w[ii][jj]);
  max_take=(1-p)*(double)del;
  if (max_take) del-=gb_unif_rand(max_take);
  w[i][j]-=del;
  w[ii][j]+=del;
  w[i][jj]+=del;
  w[ii][jj]-=del;
}  

@ @<Output the final weights@>=
for (i=0;i<n;i++) {
  for (j=0;j<n;j++) printf(" %d",
                                   w[i][j]);
  printf("\n");
}

@*Index.
