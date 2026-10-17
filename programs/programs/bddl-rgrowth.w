\datethis
@*Intro. Given $n$, generate BDDL to compute a representation of all
restricted growth sequences $a_1\ldots a_n$ (and thus of all set
partitions of $\{1,\ldots,n\}$). The output targets stock BDD14, whose
variable capacity is 1024; thus $1\le n\le44$. Larger consumers require
raising |maxvars| as well as keeping |n<maxn| so that scratch roots remain
distinct from state roots.

@d maxn 500
@d maxvars 1024

@c
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
int n;
int subscr[maxn+1][maxn]; /* allocation of variable subscripts */

main(int argc, char*argv[]) {
  register int i,j,k;
  long requested;
  char *end;
  if (argc!=2) goto usage;
  errno=0;
  requested=strtol(argv[1],&end,10);
  if (errno || end==argv[1] || *end || requested<=0 || requested>=maxn ||
      requested*(requested+1)/2>maxvars) {
usage:
    fprintf(stderr,"Usage: %s n\n",argv[0]);
    fprintf(stderr,"Require 0<n<%d and n(n+1)/2<=%d (BDD14 variables).\n",maxn,maxvars);
    exit(-1);
  }
  n=requested;
  printf("# beginning the output of BDDL-RGROWTH %d\n",n);
  for (i=0,k=n;k;k--)
    for (j=0;j<k;j++) subscr[k][j]=i++;
  for (j=1;j<=n;j++) printf("f%d=c1\n",j);
  for (k=n;k;k--) for (j=1;j<k;j++) {
    printf("f0=x%d?f%d:c0\n",subscr[k][0],j);
    printf("f%d=x%d?c0:f%d\n",maxn,subscr[k][0],j+1);
    printf("f%d=x%d?c0:f%d\n",maxn+1,subscr[k][0],j);
    for (i=1;i<j;i++) {
      printf("f0=x%d?f%d:f0\n",subscr[k][i],maxn+1);
      printf("f%d=x%d?c0:f%d\n",maxn,subscr[k][i],maxn);
      printf("f%d=x%d?c0:f%d\n",maxn+1,subscr[k][i],maxn+1);
    }
    printf("f0=x%d?f%d:f0\n",subscr[k][j],maxn);
    for (i++;i<k;i++) printf("f0=x%d?c0:f0\n",subscr[k][i]);
    printf("f%d=f0\n",j);
  }
  printf("f1=x%d?f1:c0\n",subscr[1][0]);
  printf("! f1 represents restricted growth sequences of length %d\n",n);
}

@*Index.

   

