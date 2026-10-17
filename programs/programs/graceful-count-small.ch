@x
have $m$ edges and $n$ nonisolated vertices, for $0\le n\le m+1$,
given~$m>1$. I subdivide into connected and nonconnected graphs.
@y
have $m$ edges and at most $n$ nonisolated vertices, for $0\le n\le m+1$,
given~$m$ and~$n$. I subdivide into connected and nonconnected graphs.

The fixed edges $m$ and $m-1$ require the three distinct vertices
0, 1, and $m$. Thus the counts are zero whenever $n<3$.
@z
@x
@d maxm 20 /* this is plenty big, because $20!$ is a 61-bit number */
@y
@d maxm 100
@z
@x
int mm; /* command-line parameter */
@y
int mm,nn; /* command-line parameters */
@z
@x
  register j,k,l,m;
@y
  register j,k,l,m,n;
@z
@x
  @<Process the command line@>;
  @<Initialize to $(m-1,\ldots,2,1,0)$@>;
@y
  @<Process the command line@>;
  if (n<3) goto done;
  @<Initialize to $(m-1,\ldots,2,1,0)$@>;
@z
@x
@ @<Process the command line@>=
if (argc!=2 || sscanf(argv[1],"%d",
                &mm)!=1) {
  fprintf(stderr,"Usage: %s m\n",
                    argv[0]);
  exit(-1);
}
m=mm;
if (m<2 || m>maxm) {
  fprintf(stderr,"Sorry, m must be between 2 and %d!\n",
                        maxm);
  exit(-2);
}
@y
@ @<Process the command line@>=
if (argc!=3 || sscanf(argv[1],"%d",
                &mm)!=1 || sscanf(argv[2],"%d",
                &nn)!=1) {
  fprintf(stderr,"Usage: %s m n\n",
                    argv[0]);
  exit(-1);
}
m=mm,n=nn;
if (m<2 || m>maxm) {
  fprintf(stderr,"Sorry, m must be between 2 and %d!\n",
                        maxm);
  exit(-2);
}
if (n<0 || n>m+1) {
  fprintf(stderr,"Sorry, n must be between 0 and m+1\n");
  exit(-3);
}   
@z
@x
@ @<Move to the next $m$-tuple, or |goto done|@>=
for (j=1;x[j]==0;j++) {
  @<Delete the edge from $x[j]$ to $x[j]+j$@>;
}
if (j==m-1) goto done;
@<Delete the edge from $x[j]$ to $x[j]+j$@>;
x[j]--;
@<Insert an edge from $x[j]$ to $x[j]+j$@>;
for (j--;j;j--) {
  x[j]=m-j;
  @<Insert an edge from $x[j]$ to $x[j]+j$@>;
}
@y
@ @<Move to the next $m$-tuple, or |goto done|@>=
for (j=1;x[j]==0;j++) {
tryagain_inloop:@+@<Delete the edge from $x[j]$ to $x[j]+j$@>;
}
if (j==m-1) goto done;
tryagain:@+@<Delete the edge from $x[j]$ to $x[j]+j$@>;
x[j]--;
@<Insert an edge from $x[j]$ to $x[j]+j$@>;
if (active>n) {
  if (x[j]==0) goto tryagain_inloop;
  else goto tryagain;
}
for (j--;j;j--) {
  x[j]=m-j;
  @<Insert an edge from $x[j]$ to $x[j]+j$@>;
  if (active>n) goto tryagain;
}
@z
@x
  @<Insert an edge from $x[j]$ to $x[j]+j$@>;
@y
  @<Insert an edge from $x[j]$ to $x[j]+j$@>;
  if (active>n) goto tryagain;
@z
@x
printf("Counts for %d edges:\n",
                 m);
@y
printf("Counts for %d edges and at most %d vertices:\n",
                 m,n);
@z
