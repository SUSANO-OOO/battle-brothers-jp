# Tooling

`bbjp.py` provides graph-first `scan`, `extract`, `diff`, `coverage`, `validate`, `build`, `qa`, and `update` operations.

- `scan`: capture an evidence-backed installed snapshot and pre/post read-only tree audit.
- `extract`: copy selected archive code/text only into ignored `work/` paths with ZIP-slip protection.

Raw installed inputs and derived proprietary source remain under ignored `work/` paths.

`apply_exclusion_batch.py` validates independently reviewed internal/non-player-facing units and resolves them without counting them as translations.
`split_unresolved_unit.py` partitions mixed deduplicated units before an internal occurrence is excluded.
`apply_context_split_batch.py` performs a fail-closed, audited exact-stable-key split that atomically applies reviewed display translations and their internal exclusions; validate first with explicit `--dry-run`, and commit only with explicit `--apply` plus a green implementation-review artifact.
`create_exclusion_batch.py` converts occurrence-level source audits into exact whole-unit exclusion batches and skips mixed units.
`create_occurrence_audit_batch.py` expands candidate units to every cross-module call site before exclusion review.
`create_context_split_plan.py` converts completed mixed occurrence audits into exact unresolved/exclusion partition plans.
