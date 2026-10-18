# Local GraphBase repairs

These local CWEB change files are **not part of the Stanford GraphBase**.
The reviewed 124-file distribution remains unchanged at commit `aede543`.
Use these changes when tangling repaired programs; retain the original source
and its attribution as requested by `boilerplate.w` and `README`.

For a base module, run from the GraphBase directory, for example:

```
ctangle gb_io.w repairs/gb_io.ch
```

Combine a platform change and a local repair in that order with CWEB `ctie`:

```
ctie -c /tmp/gb_graph-combined.ch gb_graph.w PROTOTYPES/gb_graph.ch repairs/gb_graph.ch
ctangle gb_graph.w /tmp/gb_graph-combined.ch
```

Only include a platform change when that file actually exists. Native regression
tests build these local changes against the added tree, rather than an external
GraphBase installation. Review evidence stays in `findings/sgb-review`; repair
status is recorded separately in `findings/sgb-fixes/FIX_STATUS.md`.
