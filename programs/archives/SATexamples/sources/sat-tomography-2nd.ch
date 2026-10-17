@x
@d mmax 200 /* should be at most 255 unless I use bigger radix than hex */
@y
This version also constrains second-order sums: the number of adjacent
pairs of ones in each row, column, or diagonal. Each input value is
followed by a comma and its pair sum, as in `\.{r3=20,8}'.

@d mmax 200 /* should be at most 255 unless I use bigger radix than hex */
@z
@x
int r[mmax+1],c[mmax+1],a[mmax+nmax],b[mmax+nmax]; /* the given data */
@y
#include <string.h>
#include <ctype.h>
int r[mmax+1],c[mmax+1],a[mmax+nmax],b[mmax+nmax]; /* the given data */
int rr[mmax+1],cc[mmax+1],aa[mmax+nmax],bb[mmax+nmax]; /* adjacent-pair sums */
@z
@x
  register int d,i,j,k,l,m,n,nn,t;
@y
  register int d,i,j,k,l,ll,m,n,nn,t;
@z
@x
  if (*p!='\n') {
@y
  if (*p++!=',') {
    fprintf(stderr,"Missing comma!\nBad line %s",buf);
    exit(-12);
  }
  if (*p<'0' || *p>'9') {
    fprintf(stderr,"Missing adjacent-pair sum!\nBad line %s",buf);
    exit(-12);
  }
  for (ll=0;*p>='0' && *p<='9';p++) {
    if (ll>(INT_MAX-(*p-'0'))/10) {
      fprintf(stderr,"Adjacent-pair sum out of range!\nBad line %s",buf);
      exit(-12);
    }
    ll=10*ll+(*p-'0');
  }
  if (*p!='\n') {
@z
@x
  r[d]=l;
@y
  r[d]=l,rr[d]=ll;
@z
@x
  c[d]=l;
@y
  c[d]=l,cc[d]=ll;
@z
@x
  a[d]=l;
@y
  a[d]=l,aa[d]=ll;
@z
@x
  b[d]=l;
@y
  b[d]=l,bb[d]=ll;
@z
@x
printf("~ sat-tomography (%dx%d, %d)\n",
@y
printf("~ sat-tomography-2nd (%dx%d, %d)\n",
@z
@x
  gen_clauses(n,r[i]);
@y
  gen_clauses(n,r[i]);
  gen_second_order(n,rr[i]);
@z
@x
  gen_clauses(m,c[j]);
@y
  gen_clauses(m,c[j]);
  gen_second_order(m,cc[j]);
@z
@x
      gen_clauses(d,a[d]);
@y
      gen_clauses(d,a[d]);
      gen_second_order(d,aa[d]);
@z
@x
      gen_clauses(m,a[d]);
@y
      gen_clauses(m,a[d]);
      gen_second_order(m,aa[d]);
@z
@x
      gen_clauses(m+n-d,a[d]);
@y
      gen_clauses(m+n-d,a[d]);
      gen_second_order(m+n-d,aa[d]);
@z
@x
      gen_clauses(d,a[d]);
@y
      gen_clauses(d,a[d]);
      gen_second_order(d,aa[d]);
@z
@x
      gen_clauses(n,a[d]);
@y
      gen_clauses(n,a[d]);
      gen_second_order(n,aa[d]);
@z
@x
      gen_clauses(m+n-d,a[d]);
@y
      gen_clauses(m+n-d,a[d]);
      gen_second_order(m+n-d,aa[d]);
@z
@x
      gen_clauses(d,b[d]);
@y
      gen_clauses(d,b[d]);
      gen_second_order(d,bb[d]);
@z
@x
      gen_clauses(m,b[d]);
@y
      gen_clauses(m,b[d]);
      gen_second_order(m,bb[d]);
@z
@x
      gen_clauses(m+n-d,b[d]);
@y
      gen_clauses(m+n-d,b[d]);
      gen_second_order(m+n-d,bb[d]);
@z
@x
      gen_clauses(d,b[d]);
@y
      gen_clauses(d,b[d]);
      gen_second_order(d,bb[d]);
@z
@x
      gen_clauses(n,b[d]);
@y
      gen_clauses(n,b[d]);
      gen_second_order(n,bb[d]);
@z
@x
      gen_clauses(m+n-d,b[d]);
@y
      gen_clauses(m+n-d,b[d]);
      gen_second_order(m+n-d,bb[d]);
@z
@x
@*Index.
@y
@ We introduce an indicator for each adjacent pair. If its endpoints
are $x$ and $y$, three clauses impose $p\iff xy$. The existing equality
counter then enforces the sum of these indicators. This uses the supplied
base's equality interface directly, rather than assuming two separate
at-most calls with complemented cell names.

Pair indicators use a `p' prefix, the original uppercase line identifier,
and two hex digits. Their equality counter uses the lowercase line letter;
thus its auxiliaries cannot collide with the first-order counter or with
pair indicators. Even at the declared dimensions, these names have at most
eight characters. The |name| array is replaced from left to right, after
both original endpoint names have been used.

@<Subroutines@>=
void gen_second_order(int n,int total) {
  int j,last;
  char pairname[9];
  if (total<0 || total>(n? n-1:0)) {
    fprintf(stderr,"Adjacent-pair sum out of range for case %s!\n",buf);
    exit(-99);
  }
  for (j=1;j<n;j++) {
    sprintf(pairname,"p%s%02x",buf,j);
    printf("~%s ~%s %s\n",name[j],name[j+1],pairname);
    printf("%s ~%s\n",name[j],pairname);
    printf("%s ~%s\n",name[j+1],pairname);
    strcpy(name[j],pairname);
  }
  last=strlen(buf)-1;
  buf[last]=tolower((unsigned char)buf[last]);
  gen_clauses(n? n-1:0,total);
}

@*Index.
@z
