@x
@<Glob...@>=
@y
@<Glob...@>=
int board[33][33]; /* prespecified clues */
int n=7; /* size of the prespecified clue board */
@z
@x
  p=strlen(buf);
  if (o,p==0 || buf[--p]!='\n') panic("Input line way too long or empty");
@y
  p=strlen(buf);
  if (o,p==0 || buf[--p]!='\n') panic("Input line way too long or empty");
  for (j=0;j<8;j++) if (buf[j]!="|sudoku!"[j]) break;
  if (j==8) {
    for (n=0;n<=32 && n+8<p && buf[n+8]!='!';n++) ;
    if (n<1 || n>32) panic("Invalid sudoku clue size");
    if (p!=7+n*(n+1) &&
        !(p==8+n*(n+1) && buf[p-1]=='!'))
      panic("Invalid sudoku clue shape");
    for (k=0;k<n;k++)
      if (buf[7+(n+1)*k]!='!') panic("Invalid sudoku clue separator");
    for (k=0;k<n;k++) for (j=0;j<n;j++) {
      i=buf[(n+1)*k+j+8];
      if ((i>='1' && i<='9') || (i>='a' && i<='w')) board[k][j]=i;
      if (i=='#') board[k][j]=' ';
    }
  }      
@z
@x
  if (spacing && (count mod spacing==0)) {
    printf(""O"lld:\n",count);
    for (k=0;k<=level;k++) print_option(choice[k],stdout);
    fflush(stdout);
  }
@y
  if (spacing && (count mod spacing==0)) {
    register cc,r,x,y;
    for (k=0;k<=level;k++) {
      for (r=choice[k]+1;nd[r].itm>0;r++) ;
      r=nd[r].up, cc=nd[r].itm, x=cl[cc].name[1], y=cl[cc].name[2];
      if (x>='0' && x<='9') x=x-'0';
      else if (x>='a' && x<'w') x=x-'a'+10;
      else x=32;
      if (y>='0' && y<='9') y=y-'0';
      else if (y>='a' && y<'w') y=y-'a'+10;
      else y=32;
      if (cl[cc].name[0]!='p' || x==32 || y==32) {
        fprintf(stderr,"Unreadable item `%.8s'!\n",cl[cc].name);
        x=y=32;
      }
      board[x][y]=cl[nd[r+1].itm].name[2];
    }
    printf("%lld:\n",count);
    for (x=0;x<n;x++) {
      printf(" ");
      for (y=0;y<n;y++) printf("%c",board[x][y]? board[x][y]: '?');
      printf("\n");
    }
    fflush(stdout);
  }
@z
