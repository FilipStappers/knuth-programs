@*Intro. This is a simple filter that inputs the well-known DIMACS format for
satisfiability problems and outputs the format used by {\mc SAT0}, {\mc SAT1},
etc.

DIMACS format begins with zero or more optional comment lines, indicated by
their first character `\.c'. The next line should say `\.p \.{cnf} $n$ $m$',
where $n$ is the number of variables and $m$ is the number of clauses.
Then comes a string of $m$ ``clauses,'' which are sequences of
nonzero integers of absolute value $\le n$, followed by zero.
A literal for the $k$th variable is represented by $k$; its complement
is represented by $-k$.

SAT format is explained in the programs cited above.
Variable numbers below 100000000 retain their decimal names. Larger
numbers use a leading \.v followed by base-36 digits, so every positive
32-bit index fits the native eight-character limit. These names are
distinct from the decimal names and from the special variable \.0.
An empty DIMACS clause is represented by two contradictory unit clauses on
the SAT variable named \.0. This name cannot clash with an input variable,
because DIMACS literals have nonzero variable numbers. A blank SAT line
would instead be ignored, losing the contradiction.

@d buf_size 1024

@c
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <string.h>
char buf[buf_size];
int m,n,v;
@<Subroutines@>@;
int main(void) {
  register int j,k,l,p;
  @<Read the preamble@>;
  if (m==0 || n==0) {
    fprintf(stderr,"I didn't find m or n!\n");
    exit(-1);
  }
  @<Read and translate the clauses@>;
  if (fflush(stdout)==EOF || ferror(stdin)) {
    fprintf(stderr,"I/O error during conversion!\n");
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
}

@ @<Read the preamble@>=
while (1) {
  if (!fgets(buf,buf_size,stdin)) break;
  if (buf[0]=='c') @<Process a comment line and |continue|@>;
  if (buf[0]!='p' || buf[1]!=' ' ||
          buf[2]!='c' || buf[3]!='n' || buf[4]!='f' ||
          !isspace((unsigned char)buf[5]) || !strchr(buf,'\n')) {
    fprintf(stderr,"Unrecognized input line: %s\n",buf);
    exit(-2);
  }
  {
    char *cursor=buf+5;
    n=header_count(&cursor);
    m=header_count(&cursor);
    while (isspace((unsigned char)*cursor)) cursor++;
    if (*cursor) {
      fprintf(stderr,"Unexpected data after DIMACS header counts!\n");
      exit(-2);
    }
  }
  break;
}

@ @<Process a comment line and |continue|@>=
{
  printf("~ %s",buf+1);
  continue;
}

@ @<Read and translate...@>=
j=k=l=p=0;
while (fscanf(stdin,"%i",&v)==1) {
  if (v==0) {
    if (j==0) {
      fprintf(stderr,"Clause %d is empty; encoding a contradiction.\n",k+1);
      printf(" 0\n ~0");
    }
    printf("\n");
    if (k==m) {
      fprintf(stderr,"Too many clauses (more than %d)!\n",m);
      exit(-3);
    }
    k++,j=0;
  }@+else if (v>0) {
    if (v>n) {
      fprintf(stderr,"Too many variables (%d > %d)!\n",v,n);
      exit(-4);
    }
    printf(" "),print_var(v);
    if (v>p) p=v;
    j++,l++;
  }@+else {
    if (v<-n) {
      fprintf(stderr,"Too many variables (%d < -%d)!\n",v,n);
      exit(-5);
    }
    printf(" ~"),print_var(-v);
    if (-v>p) p=-v;
    j++,l++;
  }
}
if (j) {
  fprintf(stderr,"The last clause didn't end with 0!\n");
  printf("\n");
  k++;
}  
if (k<m) fprintf(stderr,"Too few clauses (%d < %d)!\n",k,m);
fprintf(stderr,"OK, I translated %d input literals in %d input clauses"
               " (largest input variable %d).\n",
           l,k,p);

@ A compact name must still identify each large DIMACS variable uniquely.

@<Subroutines@>=
void print_var(int value) {
  char digits[]="0123456789abcdefghijklmnopqrstuvwxyz";
  char name[sizeof(int)*8];
  int k=0;
  if (value<100000000) printf("%d",value);
  else {
    do {
      name[k++]=digits[value%36];
      value/=36;
    } while (value);
    putchar('v');
    while (k) putchar(name[--k]);
  }
}

@ Header counts must be positive decimal integers representable as |int|.

@<Subroutines@>=
int header_count(char **cursor) {
  char *end;
  long value;
  errno=0;
  value=strtol(*cursor,&end,10);
  if (errno==ERANGE || end==*cursor || value<=0 || value>INT_MAX ||
      (*end && !isspace((unsigned char)*end))) {
    fprintf(stderr,"Invalid DIMACS header count!\n");
    exit(-2);
  }
  *cursor=end;
  return (int)value;
}

@*Index.

