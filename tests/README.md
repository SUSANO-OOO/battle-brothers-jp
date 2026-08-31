# Tests

Automated tests cover syntax, generated translation validity, duplicate keys, pattern collisions, canonical ledger partitioning, unresolved/stale strings, placeholder/tag integrity, encoding/BOM/mojibake, glyph coverage, archive layout, preload/dependency/queue metadata, optional-target absence, third-party inclusion, gameplay-change absence, and user-environment write boundaries.

Repository-portable checks run with `python -m unittest discover -s tests -p 'test_*.py'` and `node tests/js/test_ui_translation.js`. Local QA additionally supplies the pinned Squirrel compiler, ignored canonical/source evidence, font, installed Modern Hooks queue-graph source, and a development archive to `tools/qa_mod.py`. Rosetta `0.5.0` and stdlib are historical parity/provenance inputs only; neither is a JP runtime dependency.

Generated Squirrel harnesses have separate gates for representative translation output and all-rule collision detection. The current harness invokes the namespaced runtime's compiled match parts and requires exactly one effective rule for every reviewed runtime sample; a successful first-match result is not enough when another rule also matches. A frozen pre-migration parity corpus preserves Rosetta-derived expected behavior without loading Rosetta at game runtime.

Focused Squirrel gates cover exact-corpus parity, 123 patterns/147 samples, anchor/collision behavior, atomic data registration, matcher/translation bounds, rejection of multiple unbounded `str` captures, null/non-string/long/malformed input, repeated initialization, original-once and exception semantics, copy-on-write DTOs, unknown MOD wrappers before/after JP, optional profile/target absence, MSU boundaries, legacy/Rosetta namespace preservation, representative performance, and the actual ignored Modern Hooks queue graph. Python/package gates cover explicit file allowlisting, license hashes, metadata consistency, deterministic ZIP metadata, QA-to-artifact SHA binding, failed-release non-publication, junction/symlink/hardlink escape rejection, and atomic final publication.

These are repository/static/mock/archive tests. Fully isolated Battle Brothers boot, Coherent UI rendering, save/load, and install/uninstall runtime QA remain `NOT_TESTED`.

Resolved-exclusion unit tests ensure internal machine keys cannot be counted as reviewed translations.
