@*Intro. Given $m$, $n$, and $t$, I calculate the number of
matrices with $0\le a_{i,j}<t$ for $0\le i<m$ and $0\le j<n$
whose histoscape is a three-valent polyhedron.

(More generally, this program evaluates all matrices such that
the $(m-1)(n-1)$ submatrices
$$\pmatrix{a_{i-1,j-1}&a_{i-1,j}\cr
a_{i,j-1}&a_{i,j}\cr}$$
for $1\le i<m$ and $1\le j<n$
are not ``bad,'' where badness is an arbitrary relation.)

{\it Note, September 2025:}\enspace I have corrected a serious error
in the original version of this program (May 2020), which mistakenly
said that $\bigl({a\atop c}{b\atop d}\bigr)$ is bad when $a>b>c>d$.
I thank Heiko Thei{\ss}en for pointing out my unfortunate mistake.

The enumeration is by dynamic programming, using an auxiliary
matrix of $t^{n+1}$ exact integer counts. Seven base-$10^{18}$ digits
per count suffice for the entire stated matrix-size and height domain.

It's better to have $m\ge n$. But I'll try some cases with $m<n$ too,
for purposes of testing.

@d maxn 10
@d maxt 16
@d o mems++
@d oo mems+=2
@d ooo mems+=3

@c
#include <stdio.h>
#include <stdlib.h>
@<Type definitions@>;
@<Counting constants@>;
int m,n,t; /* command-line parameters */
char bad[maxt][maxt][maxt][maxt]; /* is a submatrix bad? */
bignum *count; /* the big array of exact counts */
bignum newcount[maxt]; /* counts that will replace old ones */
unsigned long long mems; /* scalar references and whole-count operations */
int inx[maxn+1]; /* indices being looped over */
int tpow[maxn+2]; /* powers of |t| */
@<Counting subroutines@>;
int main(int argc,char*argv[]) {
  register int a,b,c,d,i,j,k,p,q,r,pp;
  @<Process the command line@>;
  @<Compute the |bad| table@>;
  for (i=1;i<m;i++) for (j=1;j<n;j++) @<Handle constraint $(i,j)$@>;
  @<Print the grand total@>;
}

@ @<Process the command line@>=
if (argc!=4 || sscanf(argv[1],"%d",
                            &m)!=1 || sscanf(argv[2],"%d",
                            &n)!=1 || sscanf(argv[3],"%d",
                            &t)!=1) {
  fprintf(stderr,"Usage: %s m n t\n",
                           argv[0]);
  exit(-1);
}
if (m<2 || m>maxn || n<2 || n>maxn) {
  fprintf(stderr,"Sorry, m and n should be between 2 and %d!\n",
                   maxn);
  exit(-2);
}
if (t<2 || t>maxt) {
  fprintf(stderr,"Sorry, t should be between 2 and %d!\n",
                   maxt);
  exit(-3);
}
for (j=1,k=0;k<=n+1;k++) tpow[k]=j,j*=t;
count=(bignum*)malloc(tpow[n+1]*sizeof(bignum));
if (!count) {
  fprintf(stderr,"I couldn't allocate t^%d=%d entries for the counts!\n",
                             n+1,tpow[n+1]);
  exit(-4);
}
                           
@ @<Compute the |bad| table@>=
for (a=0;a<t;a++) for (b=0;b<=a;b++) for (c=0;c<=b;c++) for (d=0;d<=a;d++) {
  if (d>b) goto nogood;
  if (a>b && b==c && c>d) goto nogood; /* `|b==c|' added, September 2025 */
  if (a>b && b==d && d>c) goto nogood;
  continue;
nogood: bad[a][b][c][d]=1;
  bad[a][c][b][d]=1;
  bad[b][d][a][c]=1;
  bad[b][a][d][c]=1;
  bad[d][c][b][a]=1;
  bad[d][b][c][a]=1;
  bad[c][a][d][b]=1;
  bad[c][d][a][b]=1;
}

@ Throughout the main computation, I'll keep the value of |p| equal
to $(|inx[n]|\ldots|inx[1]inx[0]|)_t$.

@<Increase the |inx| table, keeping |inx[q]=0|@>=
for (r=0;r<=n;r++) if (r!=q) {
  ooo,inx[r]++, p+=tpow[r];
  if (inx[r]<t) break;
  oo,inx[r]=0, p-=tpow[r+1];
}

@ Here's the heart of the computation (the inner loop).

@<Handle constraint $(i,j)$@>=
{
  if (j==1) @<Get set to handle constraint $(i,1)$@>@;
  else q=(q==n? 0: q+1);
  while (1) {
    o,b=(q==n? inx[0]: inx[q+1]);
    o,c=(q==0? inx[n]: inx[q-1]);
    for (d=0;d<t;d++) o,newcount[d]=count_zero;
    for (o,a=0,pp=p;a<t;a++,pp+=tpow[q]) {
      for (d=0;d<t;d++) if (o,!bad[a][b][c][d])
        ooo,add_count(&newcount[d],&count[pp]);
    }
    for (o,d=0,pp=p;d<t;d++,pp+=tpow[q]) oo,count[pp]=newcount[d];
    @<Increase the |inx| table, keeping |inx[q]=0|@>;
    if (p==0) break;
  }
  fprintf(stderr," done with %d,%d ..",i,j);
  print_count(stderr,&count[0]);
  fprintf(stderr,", %llu mems\n",mems);
}

@ And here's the tricky part that keeps the inner loop easy.
I don't know a good way to explain it, except to say that
a hand simulation will reveal all.

@<Get set to handle constraint $(i,1)$@>=
{
  if (i==1) {
    for (o,p=tpow[n+1];p>0;p--) o,count[p-1]=count_one;
    q=0;
  }@+else {
    q=(q==n? 0: q+1);
    while (1) {
      for (o,a=0,pp=p,newcount[0]=count_zero;a<t;a++,pp+=tpow[q])
        o,add_count(&newcount[0],&count[pp]);
      for (a=0,pp=p;a<t;a++,pp+=tpow[q]) o,count[pp]=newcount[0];
      @<Increase the |inx| table, keeping |inx[q]=0|@>;
      if (p==0) break;
    }
    q=(q==n? 0: q+1);
  }
}

@ @<Print the grand total@>=
for (newcount[0]=count_zero,p=tpow[n+1]-1;p>=0;p--)
  o,add_count(&newcount[0],&count[p]);
printf("Altogether ");
print_count(stdout,&newcount[0]);
printf(" 3VPs (%llu mems).\n",mems);

@i histoscape-arithmetic.w
@*Index.
