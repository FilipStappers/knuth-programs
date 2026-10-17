@*Intro. After a {\mc SAT} solver has solved a problem set up with the
{\mc SAT-TOMOGRAPHY} programs, we want to see the answer in a convenient form.
This program accepts the result (one line per solution) and converts
the literals of the form \.{$d$x$d$} into the rectangular ``\.{dots}''
format of periods and asterisks.
It accepts the encoder's full range of 1 through 200 rows and 1 through
100 columns, ignoring auxiliary literals even when their numeric prefixes
are larger than a pixel coordinate.

Input and output go from |stdin| to |stdout|.
End of file terminates the input; a final line need not end with a newline.

@d mmax 200
@d nmax 100

@c
#include <stdio.h>
#include <stdlib.h>
char pix[mmax+1][nmax+1];
@<Subroutine@>;
int main(void) {
  register int c,i,j,bit,maxi=0,maxj=0;
  while (1) {
    c=fgetc(stdin);
    if (c==EOF) break;
    @<Process the next line of input@>;
  }
  return ferror(stdin)?1:0;
}

@ @<Subroutine@>=
int nextchar(void) {
  register int c=fgetc(stdin);
  return c==EOF?'\n':c;
}
  
@ @<Process the next line of input@>=
for (;c==' ';) {
  @<Process a literal@>;
}
@<Output the pixels found@>;

@ @<Process a literal@>=
c=nextchar();
if (c!='~') bit=1;
else {
  bit=0;
  c=nextchar();
}
for (i=0;c>='0' && c<='9';c=nextchar()) {
  if (i<=mmax) {
    i=10*i+c-'0';
    if (i>mmax) i=mmax+1;
  }
}
if (c!='x') goto litdone;
c=nextchar();
for (j=0;c>='0' && c<='9';c=nextchar()) {
  if (j<=nmax) {
    j=10*j+c-'0';
    if (j>nmax) j=nmax+1;
  }
}
if (c!=' ' && c!='\n') goto litdone;
if (i<1 || i>mmax || j<1 || j>nmax) {
  fprintf(stderr,"Pixel coordinates out of range (rows 1..%d, columns 1..%d)!\n",
                         mmax,nmax);
  exit(-2);
}
@<Record the pixel value $(i,j)$@>;
litdone:@+while (c!=' ' && c!='\n') c=nextchar();

@ @<Record the pixel value $(i,j)$@>=
if (i>maxi) maxi=i;
if (j>maxj) maxj=j;
pix[i][j]=bit;

@ @<Output the pixels found@>=
for (i=1;i<=maxi;i++) {
  for (j=1;j<=maxj;j++) putchar(pix[i][j]?'*':'.');
  putchar('\n');
}
putchar('\n');

@*Index.
