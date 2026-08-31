# Architecture Decisions

Status: `ACCEPTED / IMPLEMENTED_STATIC-QA-PASS / INDEPENDENT-REVIEW-PASS / RUNTIME-NOT-TESTED`
Decision date: 2026-08-31
Goal: `docs/GOAL.md`
Public evidence: `docs/PUBLIC_ECOSYSTEM_AUDIT.md`
Verified source: `BBJP-CF88150E7B355ECD32D9`

このdocumentはFinal Producer Directive後のarchitecture decision source-of-truthである。`docs/ARCHITECTURE.md`はcurrent namespaced implementationを記録し、旧Rosetta vertical sliceはgenerated parity baseline/historical QA evidenceとして保持する。

## Decision summary

一般公開版は、`mod_battle_brothers_jp.zip` 1個にCoreとoptional support moduleを同梱する。Vanilla userのhard requirementはBattle Brothers本体とModern Hooks `>=0.6.0`だけとし、Legends、Assets、DLC、MSU、legacy mod_hooksはpresence/versionを安価に確認して条件付きでsupportする。

Rosetta/stdlibはJPのexternal dependencyにしない。canonical reviewed ledgerからdeterministic generatorで、JP専用namespaceのminimum exact/pattern runtimeとreview済みdisplay-boundary hooksを生成する。通常runtimeはofflineで、未知文字列・未知MOD・source signature mismatchはoriginal Englishを返す。raw state、ID、identity、matcher、RNG、gameplay、save/persistenceは翻訳しない。

## ADR-001 — Package topology

### Options considered

1. `Core ZIP + Legends Add-on ZIP`
2. `Single ZIP + conditional modules`
3. Legendsまでhard-requiredするsingle monolith

### Actual source and ecosystem evidence

- Modern Hooks actual API has cheap MOD presence checks and queued registration; absent optional targets need not berequirements。
- Official Legends is a split overhaul with its own DLC/MSU/Assets requirements. Those requirements do not apply to a Vanilla installation。
- Actual installed DLC archives contain their registration scripts while player-facing content scripts are distributed in the base data archive and extracted into the canonical Vanilla module. The reviewed dictionary is therefore common/inert data; only DLC-specific display hooks and Legends composition are independently presence-gated。
- Battle Brothers MOD convention is an unexpanded correctly rooted ZIP in`data`。
- Core/Add-on separation reduces one module's churn domain, but creates package version mismatch, install-order confusion, duplicate runtime risk, and support burden。

### Selected design

`Single ZIP + safely conditional modules`。

Runtime layout:

```text
preload / common runtime
        |
        +-- Vanilla/common reviewed data (always)
        +-- base-archive reviewed data + independently gated DLC display hooks
        +-- Legends data/hooks (only when mod_legends is present)
        +-- MSU/Jimmy UI data/hooks (only when target is present)
        +-- JS/CSS/font (registered once)
```

### Rejected alternatives

- Two ZIPs: support isolationよりuser errorとversion mismatchのcostが大きい。common runtime duplicationまたはcross-ZIP dependencyも必要になる。
- Legends-required monolith: Vanilla userへLegends/Assets/MSU/DLCを強制し、fixed outcomeに反する。

### Impact

- Quality: canonical dataはmodule metadataを保持し、conditional loadingでも同一review evidenceを使う。
- Compatibility: absent optional targetへhookしない。unknown MODはCore exact rulesだけを安全に通過できる。
- User install: userは1 ZIPだけ選ぶ。Legends userは既存のLegends dependencyを別途満たす。
- Maintenance: module fingerprintは分離し、Legends churnだけを再検証できる。
- Performance: startup presence checkはbounded。game起動時source scanはしない。
- Migration cost: preload/generator/module manifest変更が必要だが、translation本文のmigrationは不要。

### Test strategy

- Vanilla-only mocksでLegends/MSU symbolsが完全不在でもload。
- Legends present/Assets present、Legends absent、MSU present/absentの各composition。
- optional target absenceでhook registration 0、exception 0。
- ZIP rootに余計なproject directoryがないこと。
- manifest/module/dependency metadataとREADMEの一致。

## ADR-002 — Framework dependencies

### Options considered

1. Modern Hooks + MSU + Rosetta + stdlib
2. Modern Hooks + MSU
3. Modern Hooks only
4. frameworkなしのwhole-file replacement/custom loader

### Actual source and ecosystem evidence

- Modern Hooks provides registration、hookTree/hook、queue、JS/CSS registration、dependency reporting required by JP。
- MSU provides valuable registry/settings utilities but the JP Core runtime does not need them. Legends itself alreadyrequires MSU。
- Rosetta `0.5.0` hard-requires MSU and stdlib; its broad getter hooks are larger than JP's audited safe display surface。
- whole-file replacement collides with Vanilla/overhaul updates and other MODs; installed ecosystem actively uses both Modern and legacy hooks。

### Selected design

- Hard framework dependency: `mod_modern_hooks >= 0.6.0`。
- Optional coexistence/integration: `mod_msu`、`mod_hooks`、Legends/Assets/DLC。
- JP external dependencyから除外: `mod_rosetta`、`stdlib`。

### Rejected alternatives

- MSU hard dependency: Vanilla Coreにactual API needがなく、user burden/failure domainだけ増える。
- no framework: source replacementとload-order fragilityを増やし、public MOD compositionを悪化させる。

### Impact

- Quality: Modern Hooks 0.6.0のwrapper validationをbaselineにできる。
- Compatibility: legacy hooks/MSUを否定せず共存する。requirementとqueueを混同しない。
- User install: Vanilla userの追加frameworkはModern Hooksだけ。
- Maintenance: dependency surfaceを最小化。
- Performance: registration layerの追加は1つ。
- Migration cost: MSU/Rosetta-specific callsをnamespaced runtime/conditional adapterへ置換する。

### Test strategy

- hard dependency manifest exact check。
- Modern Hooks absent/too oldは明確にblock; MSU/Legends absentはblockしない。
- legacy mod_hooks before/after、MSU before/after、unknown MOD same-target before/after composition。
- requirements/incompatibilitiesとqueue relationsをmachine graphで別edgeとして検証。

## ADR-003 — Localization runtime and licensing

### Options considered

1. Rosetta/stdlibをexternal dependencyとして維持
2. Rosetta/stdlib全体をreleaseへvendor
3. Rosetta-compatible minimum runtimeをJP namespaceへlegal adaptation
4. literal-only runtimeを完全新規実装し、既存patternを全てboundary hookへ移す

### Actual source evidence

- Audited Rosetta `0.5.0` commit `dde98e99fd95ed0e7474a4328555144b4e913678` and stdlib `2.6` commit `3dfaa3ae85462aeb0f5892d3475102ce5a1bd50e` are BSD-2-Clause。
- Current generated corpus has 4,631 Vanilla + 1,525 Legends + 25 MSU literal Squirrel pairs, 123 independently reviewed bounded pattern rules, 147 positive samples, 85 JS pairs, and 14 audited boundary-only units. Canonical ledger is the source-of-truth; generated files are disposable。
- The pre-migration project referenced `::Rosetta`/`::std`; current runtime implements only exact lookup, the audited bounded capture subset, translation dispatch, and small namespaced string helpers。
- Rosetta broad getters caused concrete item/background/world/actor identity and save-semantic hazards, already mitigated by downstream display-only guards。

### Selected design

Implement `::BattleBrothersJP.Runtime/v1` with:

- exact English → reviewed Japanese hash map; exact lookup has first priority;
- reviewed pattern registry supporting only capture types actually present in the 123-rule effective corpus (`int`, `word`, `str`, `tag`, `int_tag`, `val_tag`, `str_tag`) and replacement `:t`; bare `val` is not currently emitted and is not migration scope;
- patterns indexed by audited literal anchors/family rather than scanning every rule for every string;
- `translate(value)` returns non-string, null, unknown, malformed, or ambiguous input unchanged;
- small namespaced string helpers only; no global `::std` registration;
- no global `::Rosetta` registration and no Rosetta getter hook pack;
- explicit license/notice file for any copied or adapted BSD code, with source commit recorded;
- deterministic generation from reviewed canonical data; no manual migration of generated files。

### Rejected alternatives

- External dependencies: violates producer outcome and retains unnecessary global hooks/user burden。
- Full vendoring: legal but duplicates broad hooks/utilities and namespace registrations not needed by JP。
- Total rewrite + all patterns to hooks: avoids derived code but duplicates a reviewed/tested matching contract and expands implementation/migration cost without a player benefit。

### Impact

- Quality: reviewed translations and placeholder signatures remain unchanged; generator parity proves migration。
- Compatibility: no duplicate Rosetta/stdlib registration when other MODs install them independently。
- User install: no Rosetta/stdlib download。
- Maintenance: supported capture semantics are small and project-owned; update diff stays deterministic。
- Performance: literal O(1) average lookup; only anchored candidate patterns run; unknown string is bounded and passes through。To prevent future-update backtracking blowups, generator, registration, and matcher reject more than one unbounded `str` capture per rule; the frozen 123-rule corpus already satisfies this contract。
- Migration cost: generator, 4 runtime/hook files, preload, and Squirrel harnesses require systematic API rename/adaptation. Canonical translation rows remain untouched。

### Test strategy

- old Rosetta-based expected-output corpus vs new runtime byte-for-byte parity for all 123 effective reviewed pattern rules and every reviewed exact/pattern sample。
- all-rule collision test: each representative sample has exactly one effective rule。
- adversarial English/Japanese/mixed/empty/long/null/table/array/HTML/BBCode/unknown fields。
- repeated initialization and duplicate data registration are idempotent。
- pathological length/rule-set benchmark with documented baseline and upper bound。
- license notice and third-party allowlist QA。

## ADR-004 — Hook boundaries, queue, fail-safe behavior

### Options considered

1. Rosetta-style broad global getters/root functions
2. narrow audited display DTO/return/template boundaries
3. unrestricted global substring/regex replacement

### Actual source evidence

- Installed source proves item/background/world/actor names can feed damage branches、equality、unique-name generation、contract flags、mood history、derived identity、persistence and save data。
- Existing reviewed hooks already demonstrate clone/return-only display DTO boundaries, original exactly once, caller/state non-mutation, and exact source signatures。
- Modern Hooks docs recommend `Normal` generally; `Late` is appropriate for bounded wrappers around large overhaul behavior. Current JP needs to observe final display results without becoming a library/loader。

### Selected design

- Common translation runtime has no hooks by itself。
- Use exact class/field or final display boundary wherever source evidence exists。
- Shared/root hook inventory is explicit: `buildTextFromTemplate`, selected `::Const` display builders, audited getters, jQuery wrappers, CSS/font registration. Each entry records scope、necessity、composition order、original-once、idempotence、unknown input、optional absence。
- `original` is called exactly once and its result saved. JP processing occurs afterward/on a clone. JP-only failure returns the original result. Original exceptions are not swallowed and original is never rerun for fallback。
- Queue audited final-display wrappers in Modern Hooks `Late`; use optional `>mod_legends`/`>mod_msu` order relations only where actual target composition needs it, never as implicit requirements. Simpler registration remains`Normal` unless implementation evidence requires another bucket. Bucket selection is per registration, not one JP-wide bucket, and every `<`/`>` relation is interpreted only inside that same bucket。
- No whole-file replacement; no broad global substring replacement; no online service; no runtime source scan。

### Rejected alternatives

- Broad getters: concrete gameplay/save hazards。
- Global speculative replacement: unknown MOD collision/overmatch risk and unsafe Japanese guesses。

### Impact

- Quality: translation reaches proven player display with context。
- Compatibility: unknown input and source drift remain original; wrapper chain stays intact。
- User install: no configuration。
- Maintenance: sensitive hooks each carry version/source signature profile。
- Performance: bounded hook set and exact lookup; clone only small display DTO/list where required。
- Migration cost: current Rosetta interception reachability must be mapped to explicit boundaries; closed evidence is reused rather than re-audited。

### Test strategy

- unknown MOD wraps same target before JP and after JP。
- original exception、JP exception、repeated init、null/non-string/unknown shape。
- original call count exactly1; no recursion; no duplicate callback/wrapper。
- raw object/state/save identity hash unchanged before/after display call。
- source signature mismatch disables sensitive boundary and keeps English。

## ADR-005 — Version/fingerprint and graceful degradation

### Options considered

1. exact version mismatchでMOD全体をstartup block
2. versionを無視して全hook/dataを適用
3. version + source fingerprint profileによるgraded support

### Selected design

Use graded support:

- `HARD_DEPENDENCY`: API compatibilityに必要なModern Hooks baselineのみ。
- `VERIFIED`: version、archive/relevant source hash、structural signature、verification dateがprofile一致。
- `UNVERIFIED_COMPATIBLE`: unchanged exact sourceはreview済み訳を再利用; changed/new/unknownはEnglish。
- `UNVERIFIED_MOD`: core exact translation以外は推測しない。
- `UNSUPPORTED`: known API/content gap。可能ならCoreだけsafeに継続。
- `KNOWN_CONFLICT`: concrete crash/corruption/composition evidenceがある組合せ。
- `KNOWN_INCOMPATIBLE`: current artifactがdependency/version validationで意図的に拒否する組合せ。user-facing runtime statusは`UNSUPPORTED`へmapし、concrete coexistence defectを示す`KNOWN_CONFLICT`とは区別する。
- high-risk/source-defect hookはstructural signature mismatch時にそのhookだけdisableし、log/warningを出す。

### Evidence and impact

Current installed Legends `19.4.20`とpublic latest`19.4.21`の差はpatch releaseで、version stringだけではtranslation surface変更を判断できない。exact blockは安全だが変更なし訳まで失い、blind applyは危険である。source fingerprint profileはreview資産を保ちながらchanged範囲だけをEnglishへ戻せる。

### Test strategy

- exact verified profile、newer unchanged source、changed literal、changed boundary signature、unknown version。
- profile mismatchでstartup crash 0、sensitive hook registration 0、original English preserved。
- README/machine manifest/runtime warningのstatus一致。

## ADR-006 — Update pipeline and work preservation

### Selected design

Development pipeline and game runtime are strictly separated:

```text
development: scan -> dependency graph diff -> source fingerprint diff
             -> SAFE_REUSE / REVIEW_REQUIRED / RETRANSLATION_REQUIRED
             -> boundary revalidation -> independent review -> generate -> QA

game runtime: manifest/profile read -> cheap presence/version/signature checks
              -> prebuilt exact maps and bounded hooks -> English fail-safe
```

Canonical reviewed ledger、source evidence、review evidence、context split、placeholder signature、expected output、collision evidenceをarchitecture migrationの入力とする。generated `.nut`/`.js`はdeterministically再生成し、手修正しない。source unchangedなreview済みunitは`SAFE_REUSE`で再翻訳しない。

### Migration sequence

1. `COMPLETE`: Gate A/Bとfinal Vanilla literal classificationをgreenにしてcanonical checkpointを取る。
2. `COMPLETE`: generated expected-output corpusをfreezeし、namespaced runtime parity fixtureにする。
3. `COMPLETE`: preload/runtime/generatorを移行し、Rosetta/stdlib external dependencyを削除する。
4. `RETEST`: composition、adversarial、performance、atomic registration、matcher bounds、copy/fallback、license/package QAを独立reviewする。
5. reviewed Vanilla pattern families、Legends translation、public latest deltaを新runtimeへだけ追加する。

この順序はaccepted translationを守り、同じfeatureを旧/new runtimeへ二重実装する時間を避ける。

## ADR-007 — Source-bound replacement-key classification

### Options considered

1. `onPrepareVariables` context名やpath-looking textによるheuristic exclusion
2. unitの代表occurrenceだけをsource確認して全occurrenceへ適用
3. raw-byte sourceにbindしたstructural roleを全occurrenceへ要求

### Actual source evidence

- VanillaとLegendsは`_vars.push([key,value])`と
  `buildTextFromTemplate(..., vars)`のkey/valueを同じliteral channelへ抽出する。
- global deduplication後は同じEnglish unitがkey、display value、general proseを
  cross-moduleで共有し得るため、context名や代表1件では安全に分類できない。
- 実source probeではVanilla tavern `item`とLegends faction `regionname`は
  binding keyとして一意に証明できる一方、pair index 1のpath-shaped valueは
  display candidateであり、legacy path heuristicへ渡してはいけない。

### Selected design

`bbjp-squirrel-role-v2`のfail-closed lexical/structural analyzerとschema-v2
all-occurrence evidenceを採用する。SHA-256、UTF-8 byte span、callee/arity/argument
position、lexical function/block、unshadowed parameter、unique def/useをbindする。
canonical stable key、unit occurrence、translation-unit membershipの重複/driftも
mutation前に拒否する。詳細contractは`docs/TRANSLATION_PIPELINE.md`を参照。

### Rejected alternatives

- Heuristic-only: internal keyをplayer-facing proseとしてdraftし、逆にdisplay valueを
  internalとして消す両方向のriskがある。
- Representative-only: Vanilla/Legends mixed unitとcontext splitを誤分類する。
- Complete Squirrel CFG/parser: false-negativeを減らせるがcurrent Goalに不要な実装量。
  unsupported flowをreviewへ送る方が安全で早い。

### Impact

- Quality/safety: proven binding keyだけをexcludeし、不確実なtextはEnglish/manual review。
- Compatibility: source drift、unknown MOD syntax、malformed inputはfail-closed。
- Maintenance: analyzer semantics変更時はversion bumpでstale evidenceを失効。
- Performance: sourceは1 operationにつきabsolute pathごとに1回parseし、game runtimeでは実行しない。
- Migration: current canonical 6,417 reviewed unitsは再分類・再翻訳しない。旧batchはreview済み本文を保ったままschema-v2 evidenceを再生成する。

### Test evidence

- Independent implementation review: PASS、open P0/P1/P2 0。
- Focused: 86/86 PASS。Full Python suite: 161 PASS、symlink privilege 1 SKIP。
- CRLF raw-byte hash/span、source/placeholder/membership drift、duplicate identity、
  branch/loop/switch dominance、foreach/catch shadowing、legacy batch拒否を検証。
- Current canonical 48,158 occurrences / 31,607 units integrity PASS、canonical hash不変、actual user environment write 0。

## Implementation result and release claims

Namespaced runtime、external Rosetta/stdlib dependency removal、optional profiles、exact corpus parity、collision、composition、adversarial、performance、package source binding、22-entry development ZIPはlocal static/full QAと独立再reviewをPASSした。Runtime/package両reviewのopen P0/P1/P2は0で、canonical reviewed 6,417 unitsとledger hashは不変である。Review report SHA-256は`FC4933924F7D9CFD0CCF0AC4F5F389E29FC8F19C572BE5CDBA4252693A6C9286`。

次はまだPASSではない:

- fully isolated Vanilla-only/Legends game composition runtime
- fully isolated game boot/render/save testing
- Legends `19.4.21` support
- release ZIP/RC status

Real game runtimeを実施していないため`RUNTIME_VERIFIED`とはしない。coverage gate未達のdevelopment artifactをrelease/RCとも呼ばない。
