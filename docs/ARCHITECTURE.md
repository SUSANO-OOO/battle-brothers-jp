# Architecture

Status: `NAMESPACED_RUNTIME_IMPLEMENTED / STATIC_AND_ARCHIVE_QA_PASS / GAME_RUNTIME_NOT_TESTED`

Target: `BBJP-CF88150E7B355ECD32D9`

The public shape is one installable ZIP with a common runtime and presence/version-gated optional modules. The only JP hard framework dependency is Modern Hooks `>=0.6.0`. Vanilla users do not need Legends, Assets, MSU, Rosetta, or battle-brothers-stdlib for JP.

## A. Bootstrap and package profile

`scripts/!mods_preload/mod_battle_brothers_jp.nut` registers `mod_battle_brothers_jp` and requires Modern Hooks only. Its Normal queue reads already registered MOD metadata; it performs no network access and no runtime archive/source scan.

The verified profile is Vanilla `1.5.2-3`, five independently optional DLC registrations `1.0.0`, Legends `19.4.20`, Assets `19.4.3`, MSU `1.9.0`, and installed Legends companion registrations. An unknown base/framework version registers no JP hooks/JS/CSS. A Legends mismatch disables only the Legends partition. Original English remains available and startup is not blocked merely by a content-version mismatch.

Official DLC content scripts are distributed in the installed base data archive and the canonical extractor records them under the Vanilla source module; therefore the exact/pattern dictionary is common. DLC-specific class hooks and features are independently profile-gated. Unowned DLCs do not create missing-target startup failures. This distribution fact replaces the earlier ADR wording that implied five separate generated dictionaries.

## B. Squirrel translation runtime

`::BattleBrothersJP.Runtime/v1` is a JP-owned, offline minimum runtime:

- O(1)-average exact English-to-reviewed-Japanese table;
- 123 independently reviewed bounded patterns, with 147 positive samples;
- precompiled match parts and 80 audited literal-anchor buckets;
- maximum input, translation recursion, matcher recursion, and pattern-part limits, plus a generator/registration/matcher contract allowing at most one unbounded `str` capture per rule;
- atomic profile registration: a malformed/conflicting batch commits nothing;
- non-string, null, long, unknown, malformed, ambiguous, and JP-processing failures pass through;
- repeated core/data initialization is idempotent;
- no `::Rosetta`, `::std`, online API, or dynamic source scan.

Canonical reviewed data remains the source-of-truth. `tools/generate_runtime_translations.py` deterministically emits the runtime dictionary, exact-corpus test, positive samples, and collision harness. Current accounting is 6,403 emitted reviewed units plus 14 reviewed display-boundary units; canonical reviewed total remains 6,417 with zero needs-review.

Rosetta `0.5.0` was used as licensed pre-migration matcher/reference evidence. Only the required bounded behavior was adapted under `::BattleBrothersJP`; the BSD-2-Clause notice and exact upstream commit remain in the package. Rosetta/stdlib are not runtime dependencies and their global namespaces are not modified if another MOD supplies them.

## C. Display boundaries and safety

Runtime data alone does not intercept game state. Modern Hooks registers audited display producers in Late:

- final tooltip, dialog, combat log, event list/button, scenario/UI DTO boundaries;
- cloned template-variable and returned UI DTO translation;
- actor/item/world name fragments only at finite display boundaries;
- exact Legends source-defect repairs after the original returned display string;
- optional MSU/Jimmy display boundaries only on the verified MSU profile.

The contract is:

```text
original exactly once
  -> save original result
  -> clone/copy final display data
  -> JP processing
  -> success: localized copy
  -> JP-only failure: saved original result
```

Original exceptions remain original exceptions and are never swallowed or retried. Raw IDs, lookup keys, actor/item/world identity, contract flags, gameplay values, RNG, AI, inventory objects, serialized state, and save semantics are not translated or written back.

Shared/global surfaces are limited to the audited `buildTextFromTemplate` display path, selected display builders, scoped item getter display access, JS/jQuery UI wrappers, and font CSS. Repeated initialization, null/scalar/malformed data, unknown wrapper-before/after composition, original exception, JP exception, and optional target absence have dedicated harnesses.

## D. JS/UI

The package contains separate generated JS dictionaries for Vanilla UI, Legends, MSU, and Modern Hooks. Only the exact verified profile's dictionary is registered. `main.js` performs exact reviewed lookup at known UI display paths; unknown strings remain unchanged. It does not scan other MOD files or call the network.

## E. Font/rendering

Noto Sans CJK JP Regular `2.004` is packaged under OFL 1.1 at `gfx/fonts/battle_brothers_jp/`. Modern Hooks registers one project CSS file. It does not overwrite official/icon fonts, delete glyphs, or use broad `!important` rules.

Static glyph QA currently covers 2,575 required codepoints with zero missing. UTF-8/BOM/mojibake markers are green. Coherent UI rendering, line wrapping, clipping, icons, and representative resolutions remain `NOT_TESTED` because a fully isolated game/profile runtime has not been proven safe.

## F. Queue and composition

- Normal: profile detection, runtime/data registration, conditional JS/CSS.
- Late `>mod_legends >mod_rosetta`: common and Legends-aware display boundaries. `>mod_rosetta` is optional coexistence order, never a requirement or provider.
- Late `>mod_msu >mod_rosetta`: optional MSU display boundary.

Requirement and ordering remain separate graph edges. The actual installed Modern Hooks `0.6.0` queue-graph source is executed by local QA. Synthetic wrappers prove unknown MOD before/after composition, original once, source immutability, original exception semantics, legacy mod_hooks namespace preservation, and separately installed Rosetta/stdlib namespace preservation.

## G. Version/update policy

Current verified source and public latest are distinct. The runtime uses cheap registered-version profiles and bounded structural/text guards, while development tooling keeps archive/source hashes, snapshot ID, and review evidence. It does not scan hashes during gameplay.

On update, unchanged reviewed units are `SAFE_REUSE`; changed strings, contexts, or hook structures become `REVIEW_REQUIRED`, `RETRANSLATION_REQUIRED`, or `BOUNDARY_REVALIDATION_REQUIRED`. A sensitive mismatch can disable only that boundary. Legends `19.4.21` has a tracked delta audit but remains unsupported until its open deltas close.

## H. Evidence and current boundary

- Runtime generation: `reports/runtime-translation-manifest.json`
- Runtime reachability: `reports/runtime-reachability-map.json`
- Vertical slice: `reports/vertical-slice-reachability.json`
- External composition: `reports/external-composition-contract.json`
- Package source binding: `reports/package-source-manifest.json`
- Dependency graph: `reports/mod-dependency-graph.json`
- Local full QA: `reports/local/namespaced-runtime-corrected-qa.json`

Static Squirrel/JS, exact/pattern parity, collision, adversarial, atomic registration, recursion bounds, performance, optional composition, license/glyph/encoding, deterministic archive, and source/archive parity are tested. Real game boot/load/render/save is not tested. The current ZIP is a development artifact, not RC_READY or RUNTIME_VERIFIED.
