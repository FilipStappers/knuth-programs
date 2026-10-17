@*Intro. Generate clauses for an open shop scheduling problem,
as explained in the paper by Tamura, Taga, Kitagawa, and Banbara
in {\sl Constraints\/ \bf14} (2009), 254--272.

The command line contains three things: the number of machines, $m$; the
number of jobs, $n$; and the desired ``makespan,''~$t$.
Both dimensions must be positive and fit their single-character names.
We require $0\le t\le100000$, so every time threshold has at most five
decimal digits and its variable name fits native SAT's eight-character limit.

Standard input contains an $m\times n$ matrix of work times $w_{ij}$,
representing the time taken on machine $i$ by job~$j$.
There are $m$ lines of $n$ numbers each.
One or more optional title lines, each beginning with `\.{\char`\~}', may also
appear at the beginning of the input; they will be echoed in the output.

The variables are \.{$ij$<$u$}, meaning that the starting time $s_{ij}$
is less than $u$; and \.{!$iji'j'$}, meaning that ``$s_{ij}+w_{ij}\le s_{i'j'}$
if and only if $ij<i'j'$.''
The latter variables appear if and only if $i=i'$ and $j\ne j'$ or
$i\ne i'$ and $j=j'$ and $w_{ij}>0$ and $w_{i'j'}>0$.

@d maxmn '~'-'0' /* jobs/machines are single characters, |'0'<=c<'~'| */
@d bufsize 128 /* for the comment lines at the beginning of |stdin| */
@d maxt 100000 /* largest threshold is |t-1| */

@c
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <ctype.h>
int m,n,t; /* command-line parameters */
int w[maxmn][maxmn]; /* the input matrix */
char buf[bufsize];
@<Subroutines@>;
main (int argc,char*argv[]) {
  register int i,j,ii,jj,k,l;
  @<Process the command line@>;
  @<Input the matrix@>;
  @<Generate the axiom clauses@>;
  @<Generate the nonoverlap clauses@>;
}

@ @<Process the command line@>=
if (argc!=4 ||
      !decimal_integer(argv[1],&m) ||
      !decimal_integer(argv[2],&n) ||
      !decimal_integer(argv[3],&t)) {
  fprintf(stderr,"Usage: %s m n t < w[m][n]\n", argv[0]);
  exit(-1);
}
if (m<=0 || m>maxmn) {
  fprintf(stderr,"Sorry, m (%d) must be between 1 and %d!\n",m,maxmn);
  exit(-2);
}
if (n<=0 || n>maxmn) {
  fprintf(stderr,"Sorry, n (%d) must be between 1 and %d!\n",n,maxmn);
  exit(-3);
}
if (t<0 || t>maxt) {
  fprintf(stderr,"The makespan must be between 0 and %d!\n",maxt);
  exit(-3);
}

@ Decimal input is checked before conversion to int, including complete
weight tokens. The bounds above also keep every row/column sum within int.

@<Subroutines@>=
int decimal_integer(char *text,int *value) {
  char *end;
  long parsed;
  errno=0;
  parsed=strtol(text,&end,10);
  if (errno || end==text || *end || parsed<INT_MIN || parsed>INT_MAX) return 0;
  *value=parsed;
  return 1;
}

int read_weight(int *value) {
  char token[64];
  int ch,len=0;
  do ch=getchar(); while (ch!=EOF && isspace((unsigned char)ch));
  if (ch==EOF) return 0;
  do {
    if (ch==0 || len==63) return 0;
    token[len++]=ch;
    ch=getchar();
  } while (ch!=EOF && !isspace((unsigned char)ch));
  if (ferror(stdin)) return 0;
  token[len]='\0';
  return decimal_integer(token,value);
}

@ I don't do any fancy error checking about breaks between lines.

@<Input the matrix@>=
while (1) {
  i=getc(stdin);@+ungetc(i,stdin);
  if (i!='~') break;
  fgets(buf,bufsize,stdin);
  printf("%s",
                buf);
}    
for (i=0;i<m;i++) {
  for (j=0;j<n;j++) {
    if (!read_weight(&w[i][j])) {
      fprintf(stderr,"Oops, I had trouble reading w%d%d!\n",i,j);
      exit(-4);
    }
    if (w[i][j]<0 || w[i][j]>t) {
      fprintf(stderr,"Oops, w%d%d should be between 0 and %d, not %d!\n",
                           i,j,t,w[i][j]);
      exit(-5);
    }
  }
}
for (i=0;i<m;i++) {
  for (k=0,j=0;j<n;j++) k+=w[i][j];
  if (k>t) {
    fprintf(stderr,"Unsatisfiable (machine %d needs %d)!\n",i,k);
    exit(-10);
  }
}
for (j=0;j<n;j++) {
  for (k=0,i=0;i<m;i++) k+=w[i][j];
  if (k>t) {
    fprintf(stderr,"Unsatisfiable (job %d needs %d)!\n",j,k);
    exit(-11);
  }
}
printf("~ sat-oss %d %d %d\n",m,n,t);
for (i=0;i<m;i++) {
  printf("~ ");
  for (j=0;j<n;j++) printf("%4d",w[i][j]);
  printf("\n");
}

@ The starting time $s_{ij}$ will be at most $t-w_{ij}$.
We don't assign starting times when $w_{ij}=0$;
such times can always be assumed to be 0 without loss of generality.

@<Generate the axiom clauses@>=
for (i=0;i<m;i++) for (j=0;j<n;j++) if (w[i][j])
  for (l=1;l<t-w[i][j];l++)
    printf("~%c%c<%d %c%c<%d\n",'0'+i,'0'+j,l,'0'+i,'0'+j,l+1);

@ @<Generate the nonoverlap clauses@>=
for (i=0;i<m;i++) for (j=0;j<n;j++) if (w[i][j]) {
  for (ii=0;ii<m;ii++) for (jj=0;jj<n;jj++)
    if (((ii==i && jj!=j) || (ii!=i && jj==j)) && w[ii][jj]) {
      for (l=0;l+w[i][j]<=t+1-w[ii][jj];l++) {
        if (i<ii || j<jj) printf("~!%c%c%c%c",'0'+i,'0'+j,'0'+ii,'0'+jj);
        else printf("!%c%c%c%c",'0'+ii,'0'+jj,'0'+i,'0'+j);
        if (l>0) printf(" %c%c<%d",'0'+i,'0'+j,l);
        if (l+w[i][j]<t+1-w[ii][jj]) printf(" ~%c%c<%d",'0'+ii,'0'+jj,l+w[i][j]);
        printf("\n");
    }
  }
}

@*Index.
