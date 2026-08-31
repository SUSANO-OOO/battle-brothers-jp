# Project State

Updated: 2026-08-31 09:42 (Asia/Tokyo)

## Current phase

Phase 7 — 6,275 canonical units independently reviewed. Vanilla events 010 and its exact malformed-template display boundary are complete and Full static QA is green; the final 357-unit Vanilla-events literal tranche remains in genuine-Japanese draft repair before independent review.

## Current commit

Latest committed checkpoint before this working milestone: `106fb90b4bf1df83fccf670a878fd0c37c0272e0` on `codex/integrated-jp-mod`. The fully checked 6,275-unit changes are prepared for a grouped checkpoint commit; no remote commit is claimed yet.

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
- Tactical actor identity: `getName`/`getNameOnly`/`getTitle`/`getKilledName` remain globally source-language for gameplay and persistence. A 389-entry full actor-title registry is used only at actor-provenance display boundaries; the two independently audited identity-sensitive opt-ins form a separate generic-safe subset for bounded event/template/JS final display.

## Completed work

- GitHub preflight rechecked outside the network sandbox: `gh api user` returned `SUSANO-OOO`, while `gh repo view SUSANO-OOO/battle-brothers-jp` confirmed the repository does not exist. The requested PRIVATE create was rejected by the platform safety reviewer pending explicit destination/export re-approval; no repository or remote was created.
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
- Completed Vanilla event tranches 005–008. The Lone Wolf and Weeds were promoted only after global raw actor identity, actor-provenance display restoration, a two-entry generic-safe subset, registry parity/order checks, and adversarial Old Gods/Holy Mother collision fixtures passed independent re-audit.
- Resolved the installed Kraken cult B1 `}}` source defect at the exact event-class final-display boundary. The wrapper matches the installed prefix and malformed suffix, calls the original once, removes only a surviving final raw brace, and leaves replies, options, event state, gameplay, serialization, and saves unchanged. Independent audit passed; actual game rendering remains `NOT_TESTED`.
- Completed Vanilla events 009: 299 new units were independently reviewed with 76 corrections, while the already-reviewed Kraken unit was not reapplied. All 214 non-Kraken high-risk entries were checked against the reusable source/mechanics evidence.
- Resolved the installed Barbarian story missing outer brace by supplementing only the Rosetta-translated temporary template. Independent audit proved balanced/wrong-structure/non-string inputs fail closed and all three inner variants remain available.
- Resolved two installed duplicated-result prose defects at exact screen IDs: Greenskin Investigation J now reports the selected secret-keeping/arming-sword outcome, and grave-heist F reports the actual no-loot failure. Independent audit matched both override strings byte-for-byte to their review contracts and verified original-once plus state/gameplay/save non-mutation.
- Completed Vanilla events 010: all 300 units were independently reviewed, 71 draft translations were corrected, and all 292 HIGH-RISK mechanics/choice units were checked against installed source consumers. Player-facing unresolved and translation blockers are zero.
- Resolved the installed `enter_unfriendly_town_event` missing outer variant brace at an exact display-only boundary. The canonical English/Japanese signature remains open 3 / close 2 / pipe 7 with `%townname%`; only the Rosetta-translated temporary template receives one closing brace. Balanced, pipe/token drift, invalid translation, and non-string fixtures fail closed without mutating settlement identity, Screen.Text, event state, gameplay, persistence, or save.
- Adopted a risk-based completion pipeline: reuse existing semantic/call-site evidence, deep-audit only HIGH RISK residuals, bulk-review NORMAL/LOW prose from one reusable context pack, group Full QA and git checkpoints at architecture/category/2,000–3,000-unit milestones, and do not re-audit closed architecture without new contradictory evidence.
- Closed the one-time semantic-safety residual audit without repeating prior consumer work: 23 areas are `AUDITED_CLOSED`, no new contradiction or architecture blocker exists, and the sole `RESIDUAL_UNAUDITED` item is fully isolated live runtime/rendering. The supported-snapshot semantic architecture is now frozen unless new concrete destructive evidence appears.
- Prepared one reusable context pack for all 573 remaining Vanilla-event pattern units. None of the extractor expression hints is an executable Rosetta capture: 562 require exact-boundary review, eight require context splitting, and three are internal-exclusion candidates. No pattern was emitted or guessed.
- Completed the independent residual audit for those 573 pattern units and all 659 physical assignments: 564 executable-boundary units, eight context splits, and one internal Kraken screen-routing exclusion are resolved across 11 grouped display families with zero audit blockers. The early-access title and generated shield name were restored to the player-facing set; translation/implementation remain non-canonical DRAFT work.
- Rejected the original final 357-unit literal draft before adoption because all entries retained English-dominant placeholder prose. A separate v2 translation is in progress; any long-form generic placeholder output is likewise rejected and repaired before independent review.
- The reviewed-5,676 development tranche is static-QA green `32/32`, including Squirrel/JS composition, collision, glyph, archive-structure, source/archive parity, third-party allowlist, dependency graph, snapshot lock, and write-scope checks.
- The reviewed-4,477 tranche is committed locally at `3d299879fc04aa8dacb513df08d31f701cb2da6f` on `codex/integrated-jp-mod`; no remote claim is made.
- Portable GitHub Actions workflow added for repository-only Python/JS checks. Hosted CI has not run because no authenticated remote exists.
- Graph-first `scan`, `extract`, `diff`, `coverage`, `validate`, `build`, `qa`, and `update` commands are exposed through `tools/bbjp.py`; `update` deliberately stops before extraction when installed fingerprints changed.
- Deterministic development-only ZIPs are built below `work/qa`; none is a release artifact.
- Glossary/style/lore foundation written; category review remains.

## Translation counts and coverage

- Extracted occurrences: `48,158`
- Reasoned resolved-exclusion occurrences: `3,570`
- Translatable occurrences: `44,588`
- Unique translation units: `31,822` (ambiguous global units use context-specific partitions)
- Untranslated units: `25,547`
- Translated-needs-review units: `0`
- Reviewed units: `6,275`
- Reviewed unique-unit coverage: `19.7191%` (`6,275 / 31,822`)
- Reviewed occurrence coverage: `24.7802%` (`11,049 / 44,588`)
- REVIEWED increase from the last fully checked 5,676 checkpoint: `+599`
- Unresolved HIGH RISK in canonical REVIEWED content: `0`; pending draft tranches are not canonical.
- Architecture blockers: `0` in canonical content. The events-010 malformed-template gate is implemented and harnessed; semantic architecture remains frozen.
- Runtime blockers: Rosetta/stdlib are absent from the actual game, and fully isolated runtime QA is not yet proven safe.
- Current overall completion estimate: `19.7191%` by unique supported translation units; release quality gates remain binary and unmet until 100%.
- Extraction failures: `0`
- Extraction fallback warnings: `8` source files / `601` candidates
- Release coverage gate: `NOT_MET`

## Last green tests

- Project Python unit tests: `70/70 PASS`.
- Rosetta official Python extractor suite: `102 PASS, 1 XFAIL`.
- Vertical Slice Squirrel syntax: preload and translation files compile with Squirrel `3.0.7`.
- Vertical Slice Rosetta harness: Japanese literals and `%dragonslayer%` token preservation PASS.
- JS syntax and button/dialog/popup wrapper behavior: PASS (`UI_TRANSLATION_TEST_OK`).
- Last fully green Vertical Slice static MOD QA: all 17 checks PASS in `reports/qa-vertical-slice.json`.
- Latest Full archive QA is `32/32 PASS` for reviewed-6,275 in `reports/qa-reviewed-6275-boundary010.json`.
- Post-apply 6,275 validation: Python `70/70 PASS`, focused Squirrel source-defect/boundary harness PASS, deterministic generation PASS, reviewed-only batch validation `300/300`, and `git diff --check` PASS.
- Font static QA for the current generated tranche: 2,544 required non-ASCII code points, missing 0.
- Current generation contains 6,261 emitted units plus 14 exact boundary-accounting units; pending reviewed runtime patterns are 0. The 13-entry development ZIP matches repository-owned source 13/13. Runtime game QA remains `NOT_TESTED`.

Rosetta's full upstream Squirrel `test.nut` is **not green** under BBbuilder's standard `sq.exe`: it reports a runtime wrong-parameter error while returning exit code 0. `sq_taro.exe` only compiles it. This is not reported as PASS and needs compatible runtime or isolated game confirmation.

## Blockers

- GitHub: authenticated API identity is `SUSANO-OOO` and repository absence was verified. The user has now authorized GitHub use; PRIVATE creation/push/read-back to the exact directed repository `SUSANO-OOO/battle-brothers-jp` is the next external action.
- Runtime dependencies: Rosetta `0.5.0` and stdlib `>=2.5` are not installed in the user's current game. The project will not install them automatically.
- Runtime QA: fully isolated game + Documents/config/save/log environment is not yet proven safe. The real environment remains untouched.
- Release coverage: 25,547 unique units remain untranslated.

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

Create/push/read back the authorized PRIVATE GitHub repository after the 6,275-unit checkpoint commit. In parallel, finish and independently review the genuine-Japanese v2 draft for the final 357 Vanilla-event literals; do not promote the rejected English-dominant or generic-placeholder drafts. Then independently review the audited 572 player-facing pattern drafts plus one Kraken exclusion and implement only the 11 grouped final-display families.

## Artifact state

- Release artifact: `NOT_BUILT`.
- Latest fully checked development tranche only: `work/qa/mod_battle_brothers_jp_REVIEWED_6275_BOUNDARY010.zip`.
- Development-tranche SHA-256: `55CCC27A3B9335F65424BA67B83729E789C5EE640DF2818FC993498B60F12FCF`; exact 13/13 source/archive parity PASS. It is not a release artifact.
- `dist/mod_battle_brothers_jp.zip` does not exist and no RC claim is made.

## Runtime state

`NOT_TESTED`. Current pre-project log is inventory evidence only. No game boot/load/render/save QA has been performed for this MOD.

## Write audit

- Writes to actual Battle Brothers installation/user-data by this project: `0`.
- Snapshot scan pre/post tree digests matched for both game root and user-data.
- All project writes are confined to this repository workspace.
