Local repairs, not part of the Stanford GraphBase. SGB-001.
@x
characters long, since the data is supposed to have at most 79
characters per line, followed by newline and null.
@y
characters plus one spare byte long, since the data is supposed to have
at most 79 characters per line, followed by newline and null. The spare
byte lets us safely normalize an overlong 80-character input chunk.
@z
@x
static char buffer[81]; /* the current line of input */
@y
static char buffer[82]; /* current line, including a synthetic newline */
@z
@x
  if (!fgets(buffer,sizeof(buffer),cur_file)) {
@y
  if (!fgets(buffer,sizeof(buffer)-1,cur_file)) {
@z
@x
  if (p--==buffer || *p!='\n') {
    io_errors |= missing_newline; p++;
  }
  while (--p>=buffer && *p==' ') ; /* move back over trailing blanks */
  *++p='\n'; *++p=0; /* newline and null are always present at end of line */
@y
  if (p>buffer && p[-1]=='\n') p--;
  else io_errors |= missing_newline;
  while (p>buffer && p[-1]==' ') p--; /* remove trailing blanks safely */
  *p++='\n'; *p=0; /* synthetic newline and null fit in the spare space */
@z
