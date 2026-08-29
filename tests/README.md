# Tests

Automated tests will cover syntax, generated translation validity, duplicate keys, pattern collisions, unresolved/stale strings, placeholder/tag integrity, encoding/BOM/mojibake, glyph coverage, archive layout, preload/dependency/queue metadata, optional-target absence, third-party inclusion, gameplay-change absence, and user-environment write boundaries.

Repository-portable checks run with `python -m unittest discover -s tests -p 'test_*.py'` and `node tests/js/test_ui_translation.js`. Local QA additionally supplies the pinned Squirrel compiler, Rosetta `0.5.0`, stdlib, ignored canonical ledger, font, and optional development archive to `tools/qa_mod.py`.

Generated Squirrel harnesses have separate gates for representative translation output and all-rule collision detection. The collision harness invokes Rosetta's actual `matchParts()` implementation and requires exactly one effective rule for every reviewed runtime sample; a successful first-match result is not enough when another rule also matches.
