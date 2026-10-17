@x
The restrictions are intended for minimal-chain searches: Every computed
@y
This variant additionally orders operand pairs lexicographically and orders
the first use of inputs $x_1$, $x_2$, $x_3$, $x_4$. Its symmetry reduction
requires those four input roles to be interchangeable in the target problem;
it is not an equivalent encoding for arbitrary fixed truth tables.
For example, the one-gate target $x_3\mathbin{\&}x_4$ (table \.{1111})
is admitted by the base but excluded by this variant.

The restrictions are intended for minimal-chain searches: Every computed
@z
@x
if (n<2 || n>maxn) {
  fprintf(stderr,"n should be between 2 and %d, not %d!\n",maxn,n);
@y
if (n<4 || n>maxn) {
  fprintf(stderr,"n should be between 4 and %d, not %d!\n",maxn,n);
@z
@x
printf("~ sat-chains %d %d",n,r);
@y
printf("~ sat-chains-lex-1234 %d %d",n,r);
@z
@x
  @<Generate clauses to say that step |k| is used at least once@>;
@y
  @<Generate clauses to say that step |k| is used at least once@>;
  @<Generate clauses to say that the operands are lexicographically ordered@>;
@z
@x
  for (h=1;h<(1<<n);h++) {
@y
  breaksym(k,j,i,2,1);
  breaksym(k,j,i,3,2);
  breaksym(k,j,i,4,3);
  for (h=1;h<(1<<n);h++) {
@z
@x
@*Index.
@y
@ The |breaksym| subroutine says that if step |k| uses step |a| but not
step |b|, then some previous step must have used step~|b|.

@<Subroutines@>=
void breaksym(int k,int j,int i,int a,int b) {
  register int ii,jj,kk;
  if ((i==a && j!=b) || (j==a && i!=b)) {
    printf("~K%c%c%c",e(k),e(j),e(i));
    for (kk=n+1;kk<k;kk++) for (jj=kk-1;jj;jj--) for (ii=jj-1;ii;ii--)
      if (ii==b || jj==b) printf(" K%c%c%c",e(kk),e(jj),e(ii));
    printf("\n");
  }
}

@ @<Generate clauses to say that the operands are lexicographically ordered@>=
if (k<n+r) {
  for (i=1;i<k;i++) for (j=i+1;j<k;j++) {
    for (h=1;h<i;h++)
      printf("~K%c%c%c ~K%c%c%c\n",e(k),e(j),e(i),e(k+1),e(j),e(h));
    for (h=1;h<j;h++) for (b=1;b<h;b++)
      printf("~K%c%c%c ~K%c%c%c\n",e(k),e(j),e(i),e(k+1),e(h),e(b));
  }
}

@*Index.
@z
