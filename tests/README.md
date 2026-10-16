# Regression tests for fixes

Run from the repository root on a system with Python 3, CWEB `ctangle` and GCC:

```sh
python3 -m unittest discover -s tests -v
```

Generated C and executables are built in temporary directories. Tests compile
the current literate source rather than retaining generated C as a second source.
Some legacy entry points rely on permissive implicit-int support; individual
test builds specify that compatibility explicitly.

For the converter's additional real SAT0 pipeline check, supply the Stanford
GraphBase source directory (containing `gb_flip.c` and `gb_flip.h`):

```sh
GRAPHBASE=/path/to/sgb python3 -m unittest discover -s tests -v
```

Without GRAPHBASE, that optional integration check is reported as skipped.
The exhaustive converter projection checks have no GraphBase dependency.
The coloring-boundary regressions also use GraphBase to write and restore real
graph fixtures. They use `GRAPHBASE` when set, or a sibling `../../sgb` source
installation when available, and otherwise report a skip. Encoder code is
instrumented; the GraphBase dependency objects are compiled separately.

ACHAIN3 cache tests change only `nmax` to 8 in a temporary literate-source
copy, leaving the committed default unchanged. They compare all output bytes
with independent shortest-chain enumeration through n=7 under both char modes.
The separate known general search defect (for example n=15) is not repaired or
claimed covered by this cache fix.
