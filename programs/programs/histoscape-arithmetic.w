@*Exact counting arithmetic. Each intermediate count is bounded by
the number of input matrices, at most $16^{10\cdot10}=2^{400}$.
Seven base-$10^{18}$ digits suffice, since $10^{18}>2^{59}$.
Adding two digits and a carry fits in an unsigned 64-bit word.

@d count_digits ((4*maxn*maxn)/59+1)
@d count_base 1000000000000000000ULL

@<Type definitions@>=
typedef struct {
  unsigned long long digit[count_digits]; /* least significant first */
} bignum;

@ @<Counting constants@>=
const bignum count_zero={{0}},count_one={{1}};

@ @<Counting subroutines@>=
void add_count(bignum *a,const bignum *b) {
  int k;
  unsigned long long sum,carry=0;
  for (k=0;k<count_digits;k++) {
    sum=a->digit[k]+b->digit[k]+carry;
    carry=(sum>=count_base);
    a->digit[k]=sum-(carry? count_base:0);
  }
  if (carry) {
    fprintf(stderr,"The exact count exceeds its proven capacity!\n");
    exit(-5);
  }
}
@#
void print_count(FILE *stream,const bignum *a) {
  int k=count_digits-1;
  while (k && !a->digit[k]) k--;
  fprintf(stream,"%llu",a->digit[k]);
  while (k) fprintf(stream,"%018llu",a->digit[--k]);
}
