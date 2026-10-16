\datethis
@*Intro. This program reads output from an {\mc o} command in  {\mc BDD14}
into internal arrays, by brute force.

With change files I can adapt it to other uses.

The output from an {\mc o} command in {\mc BDD15}
can be read in a similar fashion. Unlike {\mc bddread.w}, this reader
finds the root from child links: Variable names need not remain in rank
order after ZDD reordering.
However, the interpretations are different
and the correct program must be applied to each output.

Note that if a variable is not present in the input to {\mc bddread}
then it is ignored.
If there is a variable that is not present in the BDD 
(because it is allowed to be true or false in all solutions), 
then you need to add this possibility yourself.
For example, you must multiply the BDD solution count by a factor of 2
for every such variable.
This is typically not a problem in ZDDs,
because a variable not present in a ZDD is forced to be false.

@d memsize 40000000 /* this many nodes */
@d varsize 8192 /* this many variables */
@d bdds 1 /* this many BDDs */
@d bufsize 100 /* buffer size; 100 is plenty big */

@c
#include <stdio.h>
#include <stdlib.h>
typedef struct {
  int v;
  int lo;
  int hi;
  int mark;
} node;
int present[varsize];
node* mem[bdds];
int root[bdds];
FILE *infile;
char buf[bufsize];
unsigned int i1,i2,i3,i4;
int memmax;
@<Subroutines@>@;

int
main(int argc,char *argv[]) {
  register int j,k,r,minv;
  for (r=0;r<bdds;r++) {
    int terminal=0;
    mem[r]=(node*)malloc(memsize*sizeof(node));
    if (!mem[r]) {
      printf("Sorry, I can't allocate mem[%d]!\n",r);
      exit(-99);
    }
    for (k=0;k<memsize;k++) mem[r][k].lo=mem[r][k].hi=mem[r][k].mark=0;
    if (!(infile=fopen(argv[r+1],"r"))) {
      printf("Sorry, I can't open `%s' for reading!\n",argv[r+1]);
      exit(-1);
    }
    for (k=0,minv=varsize;;) {
      if (!fgets(buf,bufsize,infile)) break;
      if ((buf[0]=='0' || buf[0]=='1') && (buf[1]=='\n' || buf[1]==0)) {
        if (k || terminal) {
          fprintf(stderr,"A terminal export must be the only record!\n");
          exit(-69);
        }
        root[r]=buf[0]-'0',terminal=1;
        continue;
      }
      if (terminal) {
        fprintf(stderr,"A terminal export must be the only record!\n");
        exit(-69);
      }
      j=sscanf(buf,"%x: (~%u?%x:%x)\n",&i1,&i2,&i3,&i4);
      if (j!=4)
        printf("! I got only %d inputs from the line %s",j,buf);
      else {
        if (i1>memmax) memmax=i1;
        if (i3>memmax) memmax=i3;
        if (i4>memmax) memmax=i4;
        if (i1>=memsize || i2>=varsize || i3>=memsize || i4>=memsize) {
          printf("! address out of range in the line %s",buf);
          exit(-69);
        }@+else if (mem[r][i1].lo || mem[r][i1].hi)
          printf("! clobbered node in the line %s",buf);
        else {
          k++,mem[r][i1].v=i2, mem[r][i1].lo=i3, mem[r][i1].hi=i4;
          mem[r][i1].mark=1; /* this address has a branch record */
          present[i2]=1;
        }
      }
    }
    if (!terminal && k) {
      for (j=2;j<=memmax;j++) if (mem[r][j].mark&1) {
        int low=mem[r][j].lo,high=mem[r][j].hi;
        if ((low>1 && !(mem[r][low].mark&1)) ||
            (high>1 && !(mem[r][high].mark&1))) {
          fprintf(stderr,"A child address has no branch record!\n");
          exit(-69);
        }
        if (low>1) mem[r][low].mark|=2;
        if (high>1) mem[r][high].mark|=2;
      }
      for (j=2,minv=0;j<=memmax;j++)
        if (mem[r][j].mark==1) root[r]=j,minv++;
      if (minv!=1) {
        fprintf(stderr,"Expected exactly one ZDD root!\n");
        exit(-69);
      }
      for (j=0;j<=memmax;j++) mem[r][j].mark=0;
    }
    fprintf(stderr,"%d nodes input into mem%d\n",k,r);
    fprintf(stderr,"(memmax=%d)\n",memmax);
  }
  for (j=k=0;j<varsize;j++) if (present[j]) k++;
  fprintf(stderr,"There are %d variables.\n",k);
  @<Do our thing@>;
}

@ @<Sub...@>=

@ @<Do our thing@>=

@*Index.
 
