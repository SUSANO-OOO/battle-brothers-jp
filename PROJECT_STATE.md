# Project State

Updated: 2026-08-30 07:28 (Asia/Tokyo)

## Current phase

Phase 7 — 4,477 canonical units independently reviewed; Vanilla events 005 is under independent review and 006 is drafted for the next pass.

## Current commit

Checkpoint update is being prepared on `codex/integrated-jp-mod`; the preceding local checkpoint is `597d60bf81060e3a62ed5ad130218809279a2e1d`. GitHub authentication is blocked, so no remote commit is claimed.

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
- Semantic name safety: normal item/background display getters remain localized, while only the audited Poacher/Donkey and three dog-identity consumer methods receive source-language names. World `getName()` remains source-language globally because its open-ended consumers persist identity; map labels, settlement DTOs, templates, tooltips, and other completed display strings are translated downstream.
- Dynamic template values: `buildTextFromTemplate` receives a cloned display-variable list. General string values are translated only in the clone; exact `noble`/`sibling`/`sib`/`justbeggar`/`nemesisS` mappings resolve context collisions. The caller list, PronounTable, keys, IDs, source templates, contract flags, and save data remain unchanged.

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
- Independently reviewed 295 Legends skills/effects units; 47 drafts were corrected. Eight hidden labels/icon/matcher occurrences were excluded only after all-occurrence source audit.
- Independently reviewed 254 Vanilla contract units; 21 initial drafts and one mixed-context term were corrected. Audit of 424 machine candidates excluded 413 occurrences, split four mixed units, and independently reviewed all 11 visible contexts as four deduplicated terms.
- Independently reviewed 233 Vanilla event units; 33 initial drafts and one mixed-context term were corrected. The completed 393-occurrence audit excluded 389 internal occurrences and split four mixed terms; all four player-facing contexts now have explicit post-template runtime boundaries.
- Independently reviewed 295 Vanilla background units; 57 drafts were corrected. All 30 occurrences belonging to five proposed exclusions were independently audited before being resolved as template/label/tooltip parameter keys.
- Completed the 300-unit Legends background tranche: 299 player-facing units are independently reviewed, 60 draft translations were corrected, and the sole `shield` sprite lookup ID was excluded only after exact source review.
- Resolved two installed Legends background source defects without inventing lore: `{ TODO | TODO }` is transparently localized as `{未実装 | 未実装}`, while the ranger commander `%name's face` / `h%name%` typos are normalized only on the post-Rosetta display template. Independent review caught the required Modern Hooks tree-hook ordering; the composition harness now proves Rosetta inner -> JP remediation outer.
- Added and independently audited the Vanilla port travel-roster DTO boundary. Reviewed title/subtitle/destination text is localized after raw settlement identity is captured; IDs, costs, routes, images, roster order, source objects, and the rendered ship-description suffix remain unchanged.
- Independent 15-finding Rosetta name-semantics audit proved that global item/background/world-name translation can break Poacher damage/effects, Donkey tooltip routing, Beggar save lookup, world unique-name generation, and persisted derived names. Post-Rosetta guards now use exact scopes for item/background semantics and a global raw world getter with display-only map/UI/template boundaries; dedicated harnesses cover normal localized display, raw matcher input, Donkey equality, world identity, labels, settlement DTOs, and cloned template variables.
- Independent runtime-boundary review caught a cross-bucket queue-order defect and three persisted-state mutations. The preload now runs in Rosetta's Late bucket after Rosetta; armor-name constants, contract flags, and caller-owned event variables are no longer mutated.
- Independently resolved the installed unfinished Vala tooltip for localization: the faithful `トランス状態に入り、うんぬんかんぬん。` translation is approved without invented mechanics. The unrelated undefined-`t` gameplay path remains unmodified and not runtime verified as a known upstream limitation.
- Completed the 300-unit Legends contract source tranche: 285 source units are independently reviewed and 15 internal units covering 23 control-key occurrences are resolved exclusions. The final 65 source translations and 23 derived return-item templates were adopted only after their actual display boundaries were proven.
- Added and independently approved a return-only `contract.getDescription()` boundary for the 160 installed Legends description templates that Rosetta 0.5.0 does not otherwise intercept. The wrapper calls the original once and leaves `m.Description`, contract state, flags, serialization, and save data raw.
- Added and independently audited display-only boundaries for 19 open-contract DTO titles, the arena description fragment, 23 formatted return-item descriptions, and four faction-relation shapes. Exact prefixes, type/icon guards, item allowlists, placeholder counts, original-once behavior, and fail-closed malformed inputs are covered without changing contract flags, relation history, or saves.
- Hardened literal-source runtime patterns after the generated `Dame` fragment audit: a capture is mandatory and a runtime sample equal to the literal source is rejected. `Dame <first><rest>` is localized, while bare `Dame`, `Dame `, and `Madame Roderick` remain untouched.
- Independently translated and reviewed 300 Vanilla settlement units; 21 draft translations changed during review.
- Completed the first 300-unit Legends event tranche: 294 player-facing units are independently reviewed with 61 total review corrections, while six internal units covering seven occurrences are resolved exclusions.
- Added exact clone-only Legends pronoun/person mappings and a five-cause obituary DTO boundary. Independent re-audit confirmed known-family unknown values and unknown obituary causes fail closed, all 48 remediation literals are generated, and caller variables, PronounTable, actor/event state, Statistics, persistence, and saves remain raw.
- Independently reviewed the second 300-unit Vanilla event tranche: 297 translations were adopted with 46 draft corrections, while two exact screen-routing IDs and one player-facing language-invariant numeric value were resolved as three reasoned exclusions. `Barnabas' Dagger` is localized only through the existing `item.getName()` return boundary; raw `m.Name`, stash, serialization, and save identity remain unchanged.
- Independently reviewed all 300 units in the third Vanilla event tranche with 57 draft corrections and no exclusions or unresolved player-facing text. `Fishes` and `Hoggart's Heirloom` use existing return-only title/item display boundaries, and the installed ambiguous shadow sentence is resolved from its immediate toast/option context without inventing mechanics; eight upstream source-defect notes remain explicit.
- Completed the fourth 300-unit Vanilla event tranche: 299 player-facing translations are independently reviewed with 84 draft corrections, and the internal `Kingmaker` achievement ID is a reasoned exact exclusion. Three initially blocked units were promoted only after independent boundary re-audit passed.
- Added three exact item-name semantic scopes for Legends dog spawning/death paths. Normal accessory/inventory display remains localized while `Warrior the Warhound`, raw item identity, spawned tactical dog identity, and save-facing state stay source-language; success, exception, argument, return, and restoration contracts are covered by the Squirrel harness.
- Extended the obituary returned-DTO allowlist for `Murdered by his fellow brothers`; raw `Statistics.Fallen`, source entries, persistence, and saves remain unchanged, and unknown/malformed values still fail closed.
- Rejected and removed a tentative `getMoodChanges()` return translation after source audit found an installed gameplay comparison against the raw English mood reason. Mood and relation history remain raw in state and are localized only at the existing final tooltip boundaries.
- Fixed the exclusion pipeline after a canonical application exposed a mixed-context deduplication risk: the ignored ledger was restored before regeneration, exact stable-key coverage is now mandatory, mixed unresolved units are split first, and canonical ledger partition QA prevents exclusions from hiding inside translation units.
- The preceding reviewed-4,178 tranche is committed locally at `597d60bf81060e3a62ed5ad130218809279a2e1d`; the reviewed-4,477 checkpoint is being prepared locally and no remote claim is made.
- Portable GitHub Actions workflow added for repository-only Python/JS checks. Hosted CI has not run because no authenticated remote exists.
- Graph-first `scan`, `extract`, `diff`, `coverage`, `validate`, `build`, `qa`, and `update` commands are exposed through `tools/bbjp.py`; `update` deliberately stops before extraction when installed fingerprints changed.
- Deterministic development-only ZIPs are built below `work/qa`; none is a release artifact.
- Glossary/style/lore foundation written; category review remains.

## Translation counts and coverage

- Extracted occurrences: `48,158`
- Reasoned resolved-exclusion occurrences: `3,565`
- Translatable occurrences: `44,593`
- Unique translation units: `31,823` (ambiguous global units use context-specific partitions)
- Untranslated units: `27,346`
- Translated-needs-review units: `0`
- Reviewed units: `4,477`
- Reviewed unique-unit coverage: `14.0684%` (`4,477 / 31,823`)
- Reviewed occurrence coverage: `20.5212%` (`9,151 / 44,593`)
- Extraction failures: `0`
- Extraction fallback warnings: `8` source files / `601` candidates
- Release coverage gate: `NOT_MET`

## Last green tests

- Project Python unit tests: `61/61 PASS`.
- Rosetta official Python extractor suite: `102 PASS, 1 XFAIL`.
- Vertical Slice Squirrel syntax: preload and translation files compile with Squirrel `3.0.7`.
- Vertical Slice Rosetta harness: Japanese literals and `%dragonslayer%` token preservation PASS.
- JS syntax and button/dialog/popup wrapper behavior: PASS (`UI_TRANSLATION_TEST_OK`).
- Last fully green Vertical Slice static MOD QA: all 17 checks PASS in `reports/qa-vertical-slice.json`.
- Current development-tranche static QA: `31/31 PASS` for reviewed-4,477 in `reports/qa-reviewed-4477.json`, including canonical ledger/tranche accounting, snapshot lock, syntax, semantic/display boundary harnesses, collision harnesses, glyph coverage, archive parity, third-party allowlist, and write-scope.
- Font static QA for the current generated tranche: 2,182 required non-ASCII code points, missing 0.
- The current 4,477-unit source generation contains 4,463 emitted units plus 14 exact boundary units; pending runtime patterns are 0. The 13-entry development ZIP matches repository-owned source 13/13. Runtime game QA remains `NOT_TESTED`.

Rosetta's full upstream Squirrel `test.nut` is **not green** under BBbuilder's standard `sq.exe`: it reports a runtime wrong-parameter error while returning exit code 0. `sq_taro.exe` only compiles it. This is not reported as PASS and needs compatible runtime or isolated game confirmation.

## Blockers

- GitHub: `gh auth status` reports the stored token for `SUSANO-OOO` is invalid; repository existence/ownership/create/push/read-back remain unverified.
- Runtime dependencies: Rosetta `0.5.0` and stdlib `>=2.5` are not installed in the user's current game. The project will not install them automatically.
- Runtime QA: fully isolated game + Documents/config/save/log environment is not yet proven safe. The real environment remains untouched.
- Release coverage: 27,346 unique units remain untranslated.

## Unresolved items

- Preserve the reviewed Vala placeholder disclosure and do not present the unmodified undefined-`t` upstream gameplay defect as runtime verified.
- Translate and independently review the two player-facing `Barrage` context units; the achievement identifier is already excluded.
- Complete Vanilla, Legends, MSU/Jimmy UI, and remaining framework player-facing translations.
- Manually audit all conservative exclusions and all 601 fallback candidates.
- Complete high-risk category, terminology, lore, placeholder/pattern, JS call-site, and UI layout passes.
- Run hosted CI only after authenticated GitHub remote creation/push becomes possible.
- Produce a release build only after coverage/review gates reach zero.
- Establish safe runtime-isolation status or finish as `RC_READY / MANUAL_INSTALL_VERIFICATION_REQUIRED`.

## Next exact action

Complete the independent review of Vanilla events 005. Confirm from actual source that `The Lone Wolf` remains raw when stored as a generated hedge-knight title and is localized only by existing event/actor return boundaries, and review `Reproach of the Old Gods` across item and event-template display paths before canonical adoption; then repeat clean-build QA. Vanilla events 006 is already drafted for the following independent pass.

## Artifact state

- Release artifact: `NOT_BUILT`.
- Latest fully checked development tranche only: `work/qa/mod_battle_brothers_jp_REVIEWED_4477.zip`.
- Development-tranche SHA-256: `D72A6EC715332E1D09A047405FA040B5C9552D260CC76DB8B2F63EF7447AE488`; exact 13/13 source/archive parity PASS. It is not a release artifact.
- `dist/mod_battle_brothers_jp.zip` does not exist and no RC claim is made.

## Runtime state

`NOT_TESTED`. Current pre-project log is inventory evidence only. No game boot/load/render/save QA has been performed for this MOD.

## Write audit

- Writes to actual Battle Brothers installation/user-data by this project: `0`.
- Snapshot scan pre/post tree digests matched for both game root and user-data.
- All project writes are confined to this repository workspace.
