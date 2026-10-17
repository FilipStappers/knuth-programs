@x
  for (v=g->vertices;v<g->vertices+n;v++) if (!v->arcs)
    @<Output the options for vertex |v|@>;
@y
  for (v=g->vertices;v<g->vertices+n;v++)
    @<Output the options for vertex |v|@>;
@z
@x
An isolated vertex has no edge option to supply its label, so it also
gets a primary item \.{\#$v$} and an option for each possible label.
@y
This version gives every vertex a primary item \.{\#$v$} and an option
for each possible label, including vertices incident with edges.
@z
@x
for (v=g->vertices;v<g->vertices+n;v++) if (!v->arcs) printf("#%s ",
@y
for (v=g->vertices;v<g->vertices+n;v++) printf("#%s ",
@z
