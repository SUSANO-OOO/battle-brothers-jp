# Tooling

`bbjp.py` provides graph-first `scan`, `extract`, `diff`, `coverage`, `validate`, `build`, `qa`, and `update` operations.

- `scan`: capture an evidence-backed installed snapshot and pre/post read-only tree audit.
- `extract`: copy selected archive code/text only into ignored `work/` paths with ZIP-slip protection.

Raw installed inputs and derived proprietary source remain under ignored `work/` paths.

`apply_exclusion_batch.py` validates independently reviewed internal/non-player-facing units and resolves them without counting them as translations.
`split_unresolved_unit.py` partitions mixed deduplicated units before an internal occurrence is excluded.
`create_exclusion_batch.py` converts occurrence-level source audits into exact whole-unit exclusion batches and skips mixed units.
