# Knuth programs: fixes and regression tests

Individual corrections to the programs published on
[Donald E. Knuth's Programs to Read](https://www-cs-faculty.stanford.edu/~knuth/programs.html),
including the Stanford GraphBase. This is an independent collection, not an
official Knuth distribution.

The history starts with the original downloaded programs and retains the
individual source corrections and their regression tests. The GraphBase snapshot
is imported separately before its corrections. Original attribution and per-file
notices are retained; no repository-wide license is asserted over upstream material.

- `programs/`: upstream literate sources, supporting assets, and their corrections.
- `tests/`: regression checks and the small fixtures needed to run them.

## Running tests

Use Python 3, CWEB `ctangle`, and GCC. Some checks also require MetaPost, Emacs,
or a built GraphBase source tree selected with `GRAPHBASE`. See
[the test instructions](tests/README.md) for details.

```sh
python3 -m unittest discover -s tests -v
```

Generated files belong in temporary/build directories. Each regression check
covers its stated cases; these corrections do not certify every program for all
inputs, historical runtimes, or mathematical claims.
