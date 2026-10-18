@x
@*Intro. Standard input contains a list of pairs of positive integers.
We set \.{/tmp/ez.gb} to the (undirected) graph with those edges.
@y
@*Intro. File \.{foo.dat} contains a list of pairs of positive integers.
We set \.{foo.gb} to the (undirected) graph with those edges.
(The base name `\.{foo}' is given on the command line.)
@z
@x
main() {
@y
#include <string.h>
char *fname;
size_t fname_size;
FILE *infile;
main(int argc,char*argv[]) {
@z
@x
  for (k=0,nn=0;k<maxm;k++) {
    if (scanf("%u %u", &u[k], &v[k])!=2) break;
@y
  if (argc!=2) {
    fprintf(stderr,"Usage: %s foo\n",argv[0]);
    exit(-1);
  }
  fname_size=strlen(argv[1]);
  if (fname_size>(size_t)-1-5 || !(fname=malloc(fname_size+5))) {
    fprintf(stderr,"I can't allocate the filename!\n");
    exit(-3);
  }
  sprintf(fname,"%s.dat",argv[1]);
  infile=fopen(fname,"r");
  if (!infile) {
    fprintf(stderr,"I can't read file `%s'!\n",fname);
    exit(-2);
  }
  for (k=0,nn=0;k<maxm;k++) {
    if (fscanf(infile,"%u %u", &u[k], &v[k])!=2) break;
@z
@x
  save_graph(g,"/tmp/ez.gb");
  printf("Created graph /tmp/ez.gb with %ld vertices and %ld edges.\n",
@y
  fclose(infile);
  snprintf(g->id,sizeof(g->id),"ezgraph %s",argv[1]);
  sprintf(fname,"%s.gb",argv[1]);
  save_graph(g,fname);
  printf("Created graph %s with %ld vertices and %ld edges.\n",fname,
@z
@x
            g->n,g->m/2);
@y
            g->n,g->m/2);
  free(fname);
@z
