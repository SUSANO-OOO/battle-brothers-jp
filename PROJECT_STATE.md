# Project State

Updated: 2026-08-30 03:36 (Asia/Tokyo)

## Current phase

Phase 7 — reviewed dynamic runtime is statically green; independently reviewed Vanilla/Legends bulk translation continues.

## Current commit

Local checkpoint: `2a2da26153bd099c46dbd8d3dded183353e161ed` on `codex/integrated-jp-mod`. GitHub authentication is blocked, so no remote commit is claimed.

## Installed snapshot ID

`BBJP-CF88150E7B355ECD32D9`

Snapshot basis SHA-256: `CF88150E7B355ECD32D92BC0F6D425F1654AD86A448681088B5094E6FCED8697`

## Detected versions

- Battle Brothers executable: `1.5.2.3`
- Runtime Vanilla registration: `1.5.2-3`
- Steam app/build: `365360` / `23856902`
- Official DLC: Lindwurm, Beasts & Exploration, Warriors of the North, Blazing Deserts, Of Flesh and Faith; runtime `1.0.0` each
- Legends: `19.4.20`
- Legends Assets: `19.4.3`
- Modern Hooks: `0.6.0`
- mod_hooks compatibility API: `21.1`
- MSU: `1.9.0`
- Bundled Events/Ambitions Delayed Fix: `0.7`
- Bundled Jimmy's Tooltips: `1.0.5`
- Rosetta candidate: `0.5.0`, commit `dde98e99fd95ed0e7474a4328555144b4e913678` (not installed in current game)
- stdlib QA source: `2.6`, commit `3dfaa3ae85462aeb0f5892d3475102ce5a1bd50e` (not installed in current game)

## Architecture

- Vanilla bootstrap: no game/config replacement; explicit `::Rosetta.activate("ja")`.
- Squirrel: Rosetta `0.5.0` translation maps and boundary hooks.
- JS/UI: Modern Hooks early `registerJS`/`registerCSS`; no whole-file replacement.
- Font: official Noto Sans CJK JP static OTF `2.004`, OFL 1.1, SHA-256 `68A3FC98800B2A27B371F2FB79991DAF3633BD89309D4FFAA6946FD587F375B5`.
- Compatibility: exact pins for current content snapshot; graph-first process for future optional MODs.

## Completed work

- Required GitHub preflight attempted; invalid stored `SUSANO-OOO` token recorded without creating another-owner repository.
- Actual game/DLC/MOD archives, sizes, SHA-256, versions, archive contents, runtime registrations, queue log, and write paths captured read-only.
- Installed snapshot and machine-readable inventory completed.
- Existing Japanese MOD audit completed: no archive or runtime registration; loose fonts hash-match official archive entries.
- Current dependency/incompatibility/queue graph normalized to 22 nodes and 48 single-semantics relations; JP MOD has 7 requirement and 3 queue edges.
- Official installed sources copied/decompiled only below ignored `work/`; 3,104/3,104 Vanilla `.cnut` decompiled.
- Rosetta `0.5.0`, Modern Hooks UI API, and stdlib dependency audited from official sources.
- Candidate extraction completed with parser failure 0 and duplicate stable key 0. Eight source files use evidence-preserving fallback warnings.
- Fixed the JS lexer after detecting comment-apostrophe false positives and visible one-word UI false negatives; regression tests cover both cases.
- Conservative call-site classification and global translation-unit deduplication completed.
- Architecture documented and Vertical Slice implemented across Vanilla Squirrel, dynamic token, Legends, bundled MOD setting, JS UI, and Japanese font layers.
- Independent review found two unreachable pairs, glossary drift, graph/schema gaps, archive QA gaps, fingerprint gaps, optional absence gaps, and a popup path. All implementation/QA findings were corrected before bulk work.
- All 19 Vertical Slice mappings have source-to-boundary evidence and completed independent review.
- Core UI review resolved 94 initial units. Two context collisions (`Play`, `General`) were split into four context units; global UI/settings mappings and two exact translation-only boundaries prevent semantic cross-over.
- First mechanics review completed for 91 Legends and 200 Vanilla units. One incomplete upstream Legends tooltip remains untranslated rather than invented.
- Deterministic generation emits only independently reviewed units. All 127 reviewed dynamic units now have executable Rosetta or exact-boundary contracts; raw extractor hints are never emitted.
- Reviewed-literal call-path audit classified 277 units and remediated all 64 gaps through exact jQuery-constructor, skill death-string, crafting-label, and Adaptive-tooltip boundaries.
- Added class-scoped Legends Adaptive/Barter Greed/Perfect Fit/Small Target wrappers which preserve all computed values and tooltip metadata; the Squirrel boundary harness is green.
- Added an all-rule Rosetta collision harness. It caught two cross-module aliases and 21 overlapping metric samples; independent review unified 26 affected units into six canonical rules plus aliases after auditing 72 actual source occurrences. All 121 representative samples now have exactly one effective Rosetta rule.
- Independently translated and reviewed the first 300 Vanilla item units; 56 draft translations were corrected by the separate reviewer before canonical adoption.
- Independently translated and reviewed the first 300 Legends item units; 46 draft translations were corrected, while five upstream display/implementation differences remain notes rather than gameplay changes.
- Independently reviewed 296 Vanilla skills/effects units; 27 drafts were corrected. Occurrence-level source audit resolved 90 internal machine-key occurrences and retained two player-facing `Barrage` contexts as untranslated.
- Fixed the exclusion pipeline after a canonical application exposed a mixed-context deduplication risk: the ignored ledger was restored before regeneration, exact stable-key coverage is now mandatory, mixed unresolved units are split first, and canonical ledger partition QA prevents exclusions from hiding inside translation units.
- Created the local root checkpoint `2a2da26153bd099c46dbd8d3dded183353e161ed` on `codex/integrated-jp-mod`; no remote claim is made.
- Portable GitHub Actions workflow added for repository-only Python/JS checks. Hosted CI has not run because no authenticated remote exists.
- Graph-first `scan`, `extract`, `diff`, `coverage`, `validate`, `build`, `qa`, and `update` commands are exposed through `tools/bbjp.py`; `update` deliberately stops before extraction when installed fingerprints changed.
- Deterministic development-only ZIPs are built below `work/qa`; none is a release artifact.
- Glossary/style/lore foundation written; category review remains.

## Translation counts and coverage

- Extracted occurrences: `48,158`
- Reasoned resolved-exclusion occurrences: `2,690`
- Translatable occurrences: `45,468`
- Unique translation units: `31,971` (ambiguous global units use context-specific partitions)
- Untranslated units: `30,669`
- Translated-needs-review units: `0`
- Reviewed units: `1,302`
- Extraction failures: `0`
- Extraction fallback warnings: `8` source files / `601` candidates
- Release coverage gate: `NOT_MET`

## Last green tests

- Project Python unit tests: `38/38 PASS`.
- Rosetta official Python extractor suite: `102 PASS, 1 XFAIL`.
- Vertical Slice Squirrel syntax: preload and translation files compile with Squirrel `3.0.7`.
- Vertical Slice Rosetta harness: Japanese literals and `%dragonslayer%` token preservation PASS.
- JS syntax and button/dialog/popup wrapper behavior: PASS (`UI_TRANSLATION_TEST_OK`).
- Last fully green Vertical Slice static MOD QA: all 17 checks PASS in `reports/qa-vertical-slice.json`.
- Current development-tranche static QA: `25/25 PASS` in `reports/qa-reviewed-1302.json`, including exact canonical ledger partitioning, runtime accounting, pending patterns 0, all 121 representative patterns, all-rule collision audit, Squirrel/JS boundary harnesses, canonical snapshot/ledger lock, exact archive parity, third-party allowlist, and write-scope.
- Font static QA for the current generated tranche: 1,574 required non-ASCII code points, missing 0.

Rosetta's full upstream Squirrel `test.nut` is **not green** under BBbuilder's standard `sq.exe`: it reports a runtime wrong-parameter error while returning exit code 0. `sq_taro.exe` only compiles it. This is not reported as PASS and needs compatible runtime or isolated game confirmation.

## Blockers

- GitHub: `gh auth status` reports the stored token for `SUSANO-OOO` is invalid; repository existence/ownership/create/push/read-back remain unverified.
- Runtime dependencies: Rosetta `0.5.0` and stdlib `>=2.5` are not installed in the user's current game. The project will not install them automatically.
- Runtime QA: fully isolated game + Documents/config/save/log environment is not yet proven safe. The real environment remains untouched.
- Release coverage: 30,669 unique units remain untranslated.
- Upstream source defect: Legends `Enter a trance and bla bla bla.` plus an undefined `t` remains unapproved.

## Unresolved items

- Independently resolve or explicitly exclude the incomplete upstream Legends trance tooltip with evidence.
- Translate and independently review the two player-facing `Barrage` context units; the achievement identifier is already excluded.
- Complete Vanilla, Legends, MSU/Jimmy UI, and remaining framework player-facing translations.
- Manually audit all conservative exclusions and all 601 fallback candidates.
- Complete high-risk category, terminology, lore, placeholder/pattern, JS call-site, and UI layout passes.
- Run hosted CI only after authenticated GitHub remote creation/push becomes possible.
- Produce a release build only after coverage/review gates reach zero.
- Establish safe runtime-isolation status or finish as `RC_READY / MANUAL_INSTALL_VERIFICATION_REQUIRED`.

## Next exact action

Complete independent review of the current Legends skills draft, then independently review the Vanilla contracts draft; apply only reviewed player-facing entries and occurrence-audit any internal candidates.

## Artifact state

- Release artifact: `NOT_BUILT`.
- Latest development tranche only: `work/qa/mod_battle_brothers_jp_REVIEWED_1302.zip`.
- Development tranche SHA-256: `EB50B1E39D329CBCB3AEB918B9EAEB41BA09B2821A717D8BDBEA7D52BE9E4EA1`; exact 10/10 source/archive parity PASS.
- `dist/mod_battle_brothers_jp.zip` does not exist and no RC claim is made.

## Runtime state

`NOT_TESTED`. Current pre-project log is inventory evidence only. No game boot/load/render/save QA has been performed for this MOD.

## Write audit

- Writes to actual Battle Brothers installation/user-data by this project: `0`.
- Snapshot scan pre/post tree digests matched for both game root and user-data.
- All project writes are confined to this repository workspace.
