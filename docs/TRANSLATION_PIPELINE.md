# Translation pipeline

The canonical reviewed ledger is the translation source of truth. Generated
runtime files and review batches are disposable outputs; architecture changes
must never trigger retranslation of already reviewed Japanese.

## Development flow

```text
copied read-only source
  -> raw-byte extraction and source fingerprint
  -> lexical/structural role evidence
  -> all-occurrence unit gate
  -> draft or exclusion review batch
  -> independent review
  -> final source reproof
  -> canonical apply
  -> deterministic runtime generation
  -> QA
```

This flow runs only in the repository. The game runtime reads prebuilt data and
does not scan source archives or use the network.

## Squirrel literal roles

`bbjp-squirrel-role-v2` recognizes only reviewed structural contracts:

- `_vars.push([key, value])` when `_vars` is the unshadowed current-function
  parameter;
- `::Const.LegendMod.extendVarsWithPronouns(_vars, actor, key)` at its exact
  arity and argument positions;
- `::buildTextFromTemplate` or `this.buildTextFromTemplate` with a unique,
  dominating, same-brace-block pair-array definition or an inline pair array.

UTF-8 byte spans and the SHA-256 of the actual copied source bytes bind each
positive proof. Malformed input, unsupported syntax, aliases, reassignment,
shadowing, non-unique literals, unbraced conditional definitions, and
cross-`case` control flow fail closed to review; they never become automatic
exclusions.

## Unit gates

- All occurrences are current parser-proven binding keys:
  `AUTO_EXCLUDE_INTERNAL`.
- Any key mixed with a display value, general literal, missing/unknown proof,
  or incompatible source: `REVIEW_REQUIRED`.
- Proven substitution values and ordinary display literals:
  `MANUAL_TRANSLATION_REVIEW_REQUIRED`.
- Unknown or source-changed content remains English until reviewed.

One representative occurrence can never classify a cross-module unit. Stable
keys, translation-unit IDs, occurrence lists, and membership must be unique and
mutually consistent.

## Schema-v2 mutation contract

New translation, exclusion, and context-split batches require:

- `schema_version: 2` and `role_evidence_required: true`;
- evidence for every canonical occurrence;
- stable key, module, source, context, channel, mode, English,
  placeholder signature, byte span, source hash, role, callee, and argument
  position bound by an evidence fingerprint;
- a fresh source parse immediately before mutation.

Legacy evidence-free batches are rejected by default. They may be regenerated
from their reviewed Japanese and source context, but the Japanese is not
redrafted. `classify_ledger.py` also refuses a stateful canonical ledger, so a
fresh classifier run cannot silently reinterpret existing reviewed/excluded
state.

## Update behavior

For a changed source snapshot, unchanged fingerprints are `SAFE_REUSE`.
Changed text or structural contracts enter `REVIEW_REQUIRED`,
`RETRANSLATION_REQUIRED`, or `BOUNDARY_REVALIDATION_REQUIRED`. Sensitive hooks
are disabled on mismatch until revalidated. Unsupported/unknown text passes
through in original English.

## Verified classifier checkpoint

The 2026-08-31 implementation review passed with no open P0/P1/P2 findings.
The full Python suite reported 161 passes and one Windows privilege-dependent
symlink skip. The canonical ledger, units, and coverage hashes remained
unchanged, and actual user/game-environment writes remained zero. This verifies
the pipeline implementation only; it does not promote any draft or claim
release readiness.
