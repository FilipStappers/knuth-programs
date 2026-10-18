@x THIS IS A CHANGE FILE FOR "bddread.w"
With change files I can adapt it to other uses.
@y
Here I compute all the solutions, using ZDD conventions.
An optional line \.{root: h} explicitly gives the hexadecimal root address,
including terminals 0 (the empty family) and 1 (the family of the empty set).
Without it, a nonempty ordered diagram must have a unique root; an empty
file retains the old empty-family convention. All records must belong to
that root and variables must strictly increase along every edge.
@z
@x
@d memsize 200000 /* this many nodes */
@d varsize 128 /* this many variables */
@d bdds 2 /* this many BDDs */
@y
@d memsize 40000000 /* this many nodes */
@d varsize 512 /* this many variables */
@d bdds 1 /* this many BDDs */
@z
@x
#include <stdlib.h>
@y
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
@z
@x
node* mem[bdds];
@y
node* mem[bdds];
int present[varsize];
int stack[varsize];
int stackptr;
int serial;
@z
@x
main(int argc,char *argv[]) {
  register int j,k,r,minv;
  for (r=0;r<bdds;r++) {
    mem[r]=(node*)malloc(memsize*sizeof(node));
    if (!mem[r]) {
      printf("Sorry, I can't allocate mem[%d]!\n",r);
      exit(-99);
    }
    for (k=0;k<memsize;k++) mem[r][k].lo=mem[r][k].hi=0;
    if (!(infile=fopen(argv[r+1],"r"))) {
      printf("Sorry, I can't open `%s' for reading!\n",argv[r+1]);
      exit(-1);
    }
    for (k=0,minv=varsize;;) {
      if (!fgets(buf,bufsize,infile)) break;
      j=sscanf(buf,"%x: (~%d?%x:%x)\n",&i1,&i2,&i3,&i4);
      if (j!=4)
        printf("! I got only %d inputs from the line %s",j,buf);
      else {
        if (i1>memmax) memmax=i1;
        if (i3>memmax) memmax=i3;
        if (i4>memmax) memmax=i4;
        if (i1>=memsize || i2>=varsize || i3>=memsize || i4>=memsize) {
          printf("! address out of range in the line %s",buf);
          exit(-69);
        }@+else if (mem[r][i1].lo+mem[r][i1].hi)
          printf("! clobbered node in the line %s",buf);
        else {
          if (i2<minv) minv=i2,root[r]=i1;
          k++,mem[r][i1].v=i2, mem[r][i1].lo=i3, mem[r][i1].hi=i4;
        }
      }
    }
    printf("%d nodes input into mem%d\n",k,r);
    printf("(memmax=%d)\n",memmax);
  }
  @<Do our thing@>;
}
@y
main(int argc,char *argv[]) {
  int j,k,r,top,roots,explicit_root;
  if (argc!=bdds+1) {
    fprintf(stderr,"Usage: %s diagram.zdd\n",argv[0]);
    exit(-1);
  }
  for (r=0;r<bdds;r++) {
    mem[r]=(node*)calloc(memsize,sizeof(node));
    if (!mem[r]) bad_input("Cannot allocate diagram");
    if (!(infile=fopen(argv[r+1],"r"))) bad_input("Cannot open diagram");
    mem[r][0].v=mem[r][1].v=varsize;
    k=0; explicit_root=0;
    while (fgets(buf,bufsize,infile)) {
      char *cursor=buf;
      if (strlen(buf)==bufsize-1 && buf[bufsize-2]!='\n')
        bad_input("Overlong diagram record");
      while (isspace((unsigned char)*cursor)) cursor++;
      if (!*cursor) continue;
      if (strncmp(cursor,"root:",5)==0) {
        if (explicit_root) bad_input("Repeated root record");
        cursor+=5;
        root[r]=input_number(&cursor,16,memsize-1);
        explicit_root=1;
      }@+else {
        i1=input_number(&cursor,16,memsize-1);
        input_char(&cursor,':'); input_char(&cursor,'('); input_char(&cursor,'~');
        i2=input_number(&cursor,10,varsize-1);
        input_char(&cursor,'?'); i3=input_number(&cursor,16,memsize-1);
        input_char(&cursor,':'); i4=input_number(&cursor,16,memsize-1);
        input_char(&cursor,')');
        if (i1<2 || mem[r][i1].mark) bad_input("Reserved or duplicate node");
        mem[r][i1].v=i2; mem[r][i1].lo=i3; mem[r][i1].hi=i4;
        mem[r][i1].mark=1; present[i2]=1; k++;
        if (i1>memmax) memmax=i1;
      }
      while (isspace((unsigned char)*cursor)) cursor++;
      if (*cursor) bad_input("Trailing text in diagram record");
    }
    if (ferror(infile)) bad_input("Cannot read diagram");
    fclose(infile);
    for (j=2;j<=memmax;j++) if (mem[r][j].mark) {
      int a;
      for (a=0;a<2;a++) {
        int child=(a?mem[r][j].hi:mem[r][j].lo);
        if (child>1 && !mem[r][child].mark) bad_input("Undefined child");
        if (mem[r][child].v<=mem[r][j].v) bad_input("Variables must increase on each edge");
        if (child>1) mem[r][child].mark|=2;
      }
    }
    top=0; roots=0;
    for (j=2;j<=memmax;j++) if (mem[r][j].mark==1) top=j,roots++;
    if (k && roots!=1) bad_input("Diagram must have one root");
    if (!explicit_root) root[r]=top;
    else if ((k && root[r]!=top) || (!k && root[r]>1))
      bad_input("Root does not cover the diagram");
    printf("%d nodes input into mem%d\n",k,r);
    printf("(memmax=%d)\n",memmax);
  }
  @<Do our thing@>;
  free(mem[0]);
}
@z

@x
@ @<Sub...@>=

@ @<Do our thing@>=
@y
@ First, bounded input routines and a recursive traversal.

@<Sub...@>=
void bad_input(char *message) {
  fprintf(stderr,"Invalid ZDD: %s.\n",message);
  exit(-69);
}
int input_number(char **cursor,int base,unsigned int limit) {
  char *end;
  unsigned long value;
  while (isspace((unsigned char)**cursor)) (*cursor)++;
  if (**cursor=='-') bad_input("Negative index");
  errno=0; value=strtoul(*cursor,&end,base);
  if (end==*cursor || errno || value>limit) bad_input("Invalid or out-of-range index");
  *cursor=end;
  return (int)value;
}
void input_char(char **cursor,int ch) {
  while (isspace((unsigned char)**cursor)) (*cursor)++;
  if (**cursor!=ch) bad_input("Malformed record");
  (*cursor)++;
}
void printpaths(int p) {
  register int k,q;
  if (p==0) return;
  if (p==1) {
    printf("%d:",serial);
    for (q=0;q<stackptr;q++) printf(" %d",stack[q]);
    printf("\n");
    serial++;
    return;
  }
  q=mem[0][p].lo;
  if (q) printpaths(q);
  q=mem[0][p].hi;
  if (q) {
    stack[stackptr++]=mem[0][p].v;
    printpaths(q);
    stackptr--;
  }
}

@ @<Do our thing@>=
for (j=k=0;j<varsize;j++) if (present[j]) k++;
fprintf(stderr,"There are %d variables.\n",k);
printpaths(root[0]);
@z
