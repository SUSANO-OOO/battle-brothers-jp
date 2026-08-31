# Public MOD Ecosystem Audit

Audit date: 2026-08-31
Refresh policy: Battle Brothers、framework、Legends、またはpublic release targetが更新されたときだけ再開する。translation trancheごとには再調査しない。
Machine-readable profile: `reports/public-ecosystem-profile.json`

## Scope and evidence policy

一般公開版のpackage/runtimeをproducer PCだけに最適化しないため、author公式情報、actual public source、release metadata、代表MOD、補助的なcommunity/Nexus情報を比較した。actual installed fileは引き続きcurrent verified source-of-truthであり、public latestへ自動的に置き換えていない。

Evidence priority:

1. game/MOD/framework authorのofficial release・documentation
2. actual source code
3. GitHub/Nexus release metadata
4. community evidence（補助のみ）

## Three separate version states

| State | Battle Brothers | Legends code | Legends Assets | Modern Hooks | MSU | Meaning |
|---|---:|---:|---:|---:|---:|---|
| `CURRENT_VERIFIED_SOURCE_SNAPSHOT` | `1.5.2.3` / runtime `1.5.2-3` | `19.4.20` | `19.4.3` | `0.6.0` | `1.9.0` | `BBJP-CF88150E7B355ECD32D9`; canonical translation/review evidenceのsource-of-truth |
| `PUBLIC_LATEST` at audit time | `1.5.2.3` | `19.4.21` | `19.4.3` | `0.6.0` | `1.9.0` | public metadataの観測値。verified対応を意味しない |
| `NEXT_PUBLIC_RELEASE_TARGET` | `1.5.2.3` | current snapshotを完成後、`19.4.21`差分remediationがboundary/translation QAを通った範囲 | `19.4.3` | `>=0.6.0` baseline | optional | public releaseで実際に表明するtarget。classified deltaの未解決範囲は`UNVERIFIED_COMPATIBLE`またはEnglish pass-through |

Battle Brothersのofficial announcementsは`1.5.2.3`をcurrent updateとして掲示しており、installed executable/runtimeも同系列である。Legendsは2026-08-29に`19.4.21`をlatestとして公開し、`19.4.20`の置換、Assets `19.4.3`、ZIPを展開しないこと、`19.4.0+`からのsave compatibilityを明記している。したがってLegendsだけがverified snapshotより1 patch新しい。公式compareと両release ZIPを用いた差分classificationは完了したが、再翻訳・boundary再検証が未完了なので`VERIFIED`とはしない。

Ignored detailed delta evidence `work/review_batches/legends_19_4_20_to_19_4_21_delta_audit.json` (`SHA-256 2EF23DD00A522C419ACB52651DC0FEF45F3474785B6B4A111327482F326B8CF1`) records eight commits and 11 semantic files. A public clone can independently identify the same inputs from the [official 19.4.20...19.4.21 compare](https://github.com/Battle-Brothers-Legends/Legends-public/compare/19.4.20...19.4.21), base `d0e0dc3c34ff87cd5a737038b1648ce135e66985`, head `3238e8a0dc326683e17f11777627ae971e6f2b29`, and the release ZIP digests recorded in the tracked machine profile. The 37 distinct byte-different archive files include 26 BOM/newline-only changes. Classifications are intentionally nonexclusive: 31 `SAFE_REUSE`, one `REVIEW_REQUIRED`, three `RETRANSLATION_REQUIRED`, five `BOUNDARY_REVALIDATION_REQUIRED`, zero `DISABLE_SENSITIVE_BOUNDARY`, and one current exact-pin `KNOWN_INCOMPATIBLE`. The last state maps to runtime status `UNSUPPORTED` for the current artifact and is not the same as a proven `KNOWN_CONFLICT`. Runtime QA for `19.4.21` is not performed.

## Frameworks

### Modern Hooks

- Official latest: `0.6.0` (2025-05-30)。current installedも同じ。
- `require`/`conflictWith`はpresence/version compatibilityであり、`queue`はbefore/after実行順である。official docsも両者を明確に分離している。
- `Normal`がdefaultかつstrongly recommended。`Late`はLegends/Reforged等のlarge MODや限定wrapper、`VeryLate`はlibrary向けで、`First`/`Last`はModern Hooks予約である。
- Actual sourceにはMOD presenceを安価に確認する`::Hooks.hasMod`があり、queue relationのoptional targetが不在でもそのtargetをrequireにはしない。JS/CSS registrationもpreload queue内から提供される。
- `0.6.0`はhook wrapper parameter validationを修正しており、JPのoriginal-once wrapperにも直接関係する。

結論: whole-file replacementを避け、optional class/moduleを条件付き登録し、JS/CSSを正規登録するための唯一のpublic hard framework dependencyとして採用する根拠がある。

Official evidence:

- [Modern Hooks 0.6.0 release](https://github.com/MSUTeam/Modern-Hooks/releases/tag/0.6.0)
- [Modern Hooks Mod Object](https://bbmodding.enduriel.com/docs/modern-hooks/mod-object/)
- [Modern Hooks Queuing](https://bbmodding.enduriel.com/docs/modern-hooks/queuing/)
- [Modern Hooks Nexus page](https://www.nexusmods.com/battlebrothers/mods/685)

### MSU

- Official latest: `1.9.0` (2026-06-23)。current installedも同じ。
- MSUはsettings、registry、serialization helpers、mod UI等を提供し、多数のpublic MODが利用する。LegendsはMSUを必要とする。
- JP Coreのexact lookup、bounded pattern、Modern Hooks registration、JS/CSS overlayにはMSU固有APIは必要ない。JPがMSUをhard-requireすると、Vanilla-only userへ不要な2.3 MB frameworkとそのfailure domainを追加する。
- MSUが他MODのため存在する環境とは共存し、MSU/Jimmy UI由来のreview済み表示textはoptional moduleとして扱う。

結論: JP Coreのhard dependencyにはしない。Legends利用者はLegends自身のdependencyとしてMSUを導入する。

Official evidence:

- [MSU 1.9.0 release](https://github.com/MSUTeam/MSU/releases/tag/1.9.0)
- [MSU Nexus page](https://www.nexusmods.com/battlebrothers/mods/479)

### Legacy mod_hooks

- Public latest/mirror target: `21.1`; current environmentにもcompatibility APIとして存在する。
- Modern Hooksはlegacy mod_hooksを完全には置換せず、Nexusも両方が必要になり得ると明記する。actual Modern Hooks sourceにはlegacy registration/interoperability handlingがある。
- JP自身がlegacy APIを呼ぶ理由はない。一方、legacy/Modern Hooks併存環境をunsupportedとしてはならない。

結論: hard dependencyにはしないが、composition QAで`mod_hooks before/after JP`を扱う。

Evidence:

- [modding script hooks v21.1](https://github.com/jcsato/modding_script_hooks/releases/tag/v21.1)
- [Nexus top MOD listing and coexistence notice](https://www.nexusmods.com/battlebrothers/mods/top)

## Legends and official DLC

Legends official installation guideは、Legends userに全regular DLC、Legends code/assets、MSU、Modern Hooksを要求し、MOD ZIPを展開せず`data`へ配置する。LegendsはVanillaのほぼ全域を変える大規模overhaulなので、MOD listをLegends中心に組むよう案内している。一方、これらはLegends自身の要件であり、Vanilla JP userの要件ではない。

Architecture consequence:

- JP packageはLegends/Assets/DLCをhard-requireしない。
- Legendsが存在する場合だけLegends support hook/dataを登録する。
- DLC別sourceはpresenceに応じて安全に到達し、未所有DLCをstartup blockerにしない。
- Legends `19.4.20`はcurrent verified、`19.4.21`はdelta-audit対象。version番号だけでstartupを止めず、source signatureが合うexact mappingsは再利用し、changed/new textはreviewまでEnglishを維持する。source-defect等のsensitive boundaryはsignature mismatch時に無効化する。

Official evidence:

- [Legends 19.4.21 release](https://github.com/Battle-Brothers-Legends/Legends-public/releases/tag/19.4.21)
- [Legends Assets 19.4.3 release](https://github.com/Battle-Brothers-Legends/Legends-public/releases/tag/19.4.3)
- [Legends installation guide](https://github.com/Battle-Brothers-Legends/Legends-public/wiki/Installation-Guide)

## Representative MOD ecosystem

| Representative | Type | Observed framework/package pattern | JP consequence |
|---|---|---|---|
| Autopilot New | QoL + gameplay/AI | ZIPを`data`へ置く。stdlib、Modern Hooks、MSUをrequireし、hook-onlyと説明。Legends/Reforged等とのtested listあり | Public MODごとにdependency stackが違う。JPは未知MODのdependencyを肩代わりせず、同じtargetのbefore/after compositionを検査する |
| MSU-dependent settings MODs | UI/QoL | MSU Mod Optionsを利用 | MSU present時だけ設定UI文字列を翻訳し、absenceをstartup failureにしない |
| Reforged `0.9.3` | overhaul | active public overhaul、Modern Hooks ecosystem | Legends以外のoverhaulでもJP Coreはload可能、未対応contentはEnglish pass-through、shared broad hooksはfail-safeにする |
| Legends `19.4.x` | overhaul | split code/assets、Modern Hooks+MSU、integrated legacy hooks、all regular DLC | conditional supportとversion/source-signature separationが必要 |

Evidence:

- [Autopilot New README](https://github.com/Suor/battle-brothers-mods/blob/master/autopilot/README.md)
- [Reforged 0.9.3 release](https://github.com/Battle-Modders/mod-reforged/releases/tag/0.9.3)

## Rosetta and battle-brothers-stdlib

Actual audited Rosetta `0.5.0` is tag/commit `dde98e99fd95ed0e7474a4328555144b4e913678`, BSD-2-Clause. It provides useful literal/pattern semantics and many broad hooks, but it hard-requires MSU `>=1.6.0` and stdlib `>=2.5` and registers global `::Rosetta` behavior. Actual audited stdlib `2.6` is commit `3dfaa3ae85462aeb0f5892d3475102ce5a1bd50e`, also BSD-2-Clause.

Current JP code uses only a bounded subset of Rosetta matching plus a small subset of string helpers. The effective migration inventory is 123 reviewed pattern rules: 122 deterministic generated rules plus one manually reviewed context rule. Retaining the two external dependencies would:

- require Vanilla-only users to find/install three frameworks instead of Modern Hooks only;
- keep broad global getter hooks whose semantic risks already required JP compatibility guards;
- create duplicate namespace/registration risk when another MOD independently installs Rosetta/stdlib;
- make version failure domains larger than the required localization functionality.

Conclusion: users will not be required to install Rosetta/stdlib for JP, and JP will not bundle/register them under their global namespaces. This is not a conflict declaration: separately installed Rosetta/stdlib needed by another MOD are allowed to coexist. The selected migration is a JP-namespaced minimum runtime, preserving canonical reviewed data and compatible pattern semantics through deterministic generation. Any Rosetta-derived code retained verbatim or adapted will carry the BSD-2-Clause copyright/license notice.

Evidence:

- [Rosetta source](https://github.com/Suor/battle-brothers-rosetta/tree/dde98e99fd95ed0e7474a4328555144b4e913678)
- [battle-brothers-stdlib](https://github.com/Suor/battle-brothers-stdlib)

## Common installation convention and user burden

Across official Legends guidance and representative MOD READMEs, the common convention is a correctly rooted MOD ZIP placed unexpanded in`Battle Brothers/data`. Multiple separate JP ZIPs would isolate churn, but create Core/Add-on version mismatch and wrong-file support burden. A single conditional ZIP gives both user groups the same operation:

1. Modern Hooksを確認する。
2. 競合する旧日本語化MODがあればユーザー自身で外す。
3. `mod_battle_brothers_jp.zip`を展開せず`Battle Brothers/data`へ置く。
4. 起動する。

Legends userはLegends自身のrequirementsを別途満たす。Vanilla userはLegends、Assets、MSU、Rosetta、stdlibをJPのために導入しない。

## Game/framework update breakage policy

Public evidence shows framework/overhaul releases follow game updates on different schedules. A blanket exact-version startup block is safe but needlessly disables unchanged exact translation; blanket “latest compatible” is unsupported. Public release therefore uses:

- `HARD_DEPENDENCY`: Modern Hooks `>=0.6.0` only;
- `VERIFIED_VERSION`: exact snapshot + relevant source fingerprints;
- `UNVERIFIED_COMPATIBLE`: exact literal reuse where source is unchanged; new/changed strings remain English;
- sensitive display/source-defect hooks: version + structural signature mismatchでdisable;
- unknown MOD: no global substring guessing; exact reviewed rule不一致はEnglish pass-through;
- development update command: scan → dependency diff → source fingerprint diff → review queue → generate → QA.

## Audit conclusion

Public ecosystem evidence supports one installable ZIP with cheap conditional modules, Modern Hooks as the only JP hard framework dependency, optional MSU/Legends/DLC integration, and a self-contained namespaced localization runtime. This minimizes user error and dependency burden while preserving compatibility and current reviewed translation assets. The detailed option comparison and test obligations are fixed in `docs/ARCHITECTURE_DECISIONS.md`.
