@*Intro. Generate SAT instances for van der Waerden configurations: There
are to be no $k$ equally spaced zeroes and no $l$ equally spaced ones, in a
binary string of length~$n$. (If unsatisfiable, every red-green coloring
of $\{1,2,\ldots,n\}$ contains a red arithmetic progression of length~$k$
or a green arithmetic progression of length~$l$.)

The numbers $k$, $l$, $n$ are given on the command line.
Both progression lengths must be at least two, and $n$ must be nonnegative.

@c
#include <stdio.h>
#include <stdlib.h>
int k,l,n;
main(int argc, char*argv[]) {
  register int i,j,d;
  @<Process the command line@>;
  @<Output the positive clauses@>;
  @<Output the negative clauses@>;
}

@ @<Process the command line@>=
if (argc!=4 || sscanf(argv[1],"%d",&k)!=1 ||
               sscanf(argv[2],"%d",&l)!=1 ||
               sscanf(argv[3],"%d",&n)!=1) {
  fprintf(stderr,"Usage: %s k l n\n",argv[0]);
  exit(-1);
}
if (k<2 || l<2 || n<0) {
  fprintf(stderr,"Progression lengths must be at least two and n nonnegative!\n");
  exit(-2);
}
printf("~ sat-waerden %d %d %d\n",k,l,n);

@ @<Output the positive clauses@>=
for (d=1;d<=(n-1)/(k-1);d++) {
  for (i=1;i<=n-(k-1)*d;i++) {
    for (j=0;j<k;j++) printf(" %d",i+j*d);
    printf("\n");
  }
}

@ @<Output the negative clauses@>=
for (d=1;d<=(n-1)/(l-1);d++) {
  for (i=1;i<=n-(l-1)*d;i++) {
    for (j=0;j<l;j++) printf(" ~%d",i+j*d);
    printf("\n");
  }
}

@*Index.
