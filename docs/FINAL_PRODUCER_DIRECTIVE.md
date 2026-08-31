# Final Producer Directive — Durable Project Rules

Effective: 2026-08-31
Precedence: 同テーマの過去指示と矛盾する場合、この文書と`GOAL.md`を優先する。既存の安全境界は維持する。

## Governing outcome

`GOAL.md`のProject Goalを、品質、安全性、public usability、保守性、完成時間、agent/token costを総合して最も合理的なactual-evidence-based designで達成する。特定のframework、現在のRosetta implementation、Core/Add-onという名称、ZIP数そのものを目的にしない。

## Non-negotiable safety

- actual game/MOD/config/log/profile/save/user-dataは完全READ-ONLY。
- gameplay、balance、AI、RNG、economy、identity、save、persistenceを翻訳都合で変更しない。
- independently reviewed translationだけをcanonicalへ昇格する。
- canonical ledger、source/context、review、signature、runtime contract、collision evidenceを維持する。
- proprietary source/assets、third-party archives、既存日本語MOD素材をreleaseへ含めない。
- original exactly once、display-only clone/return、unknown input pass-through、JP-only failure時のoriginal resultを基本とする。original exceptionを握り潰さない。
- force push/history destructionを行わず、未reviewed DRAFTをcanonical/releaseへ混入させない。
- 未実施testをPASSとしない。

## Required architecture outcomes

- Vanilla利用者へLegendsを強制しない。未所有official DLCを安全に扱う。
- package topology、Modern Hooks/MSU/mod_hooks dependencyはpublic ecosystemとactual sourceの比較後に決定する。
- Rosetta/stdlibを日本語化の外部install要件にしない。legal vendoring、namespaced minimum runtime、自前minimum implementation等を比較する。
- development scan/diff/extractionとgame runtimeを分離し、runtimeはoffline・prebuilt data・bounded hooksで成立させる。
- unsupported MOD/textはunsafe Japanese guessを行わずEnglishを保持する。
- source fingerprintとgraceful version degradationを使い、version番号だけで無条件startup blockしない。
- shared/global hooksは必要性、scope、composition、idempotence、original-once、unknown input、optional absence、performanceを重点監査する。

## Required evidence and deliverables

- current verified snapshot、public latest、next public release targetを分離する。
- public official/source/release/community evidenceを一度まとめ、`PUBLIC_ECOSYSTEM_AUDIT.md`とmachine-readable profileへ保存する。
- 重要architecture決定はoptions、actual/public evidence、selected/rejected design、品質・互換性・install・保守・performance・cost・test strategyをADRへ残す。
- `onPrepareVariables` replacement key等の誤分類をbatch手作業だけで終わらせず、extractor/classifier metadataとregression testへ反映する。不確実なものはREVIEW_REQUIREDとする。
- unknown MOD before/after composition、selected frameworks、Legends、representative MOD、adversarial value types、repeated init、performance、font/mojibake/UIをrisk-based QAする。
- update差分をSAFE_REUSE、REVIEW_REQUIRED、RETRANSLATION_REQUIRED、BOUNDARY_REVALIDATION_REQUIRED、DISABLE_SENSITIVE_BOUNDARY、KNOWN_INCOMPATIBLE等へ分類する。
- 非技術ユーザーが必要package、置き場所、verified versions、dependencies、limitationsをすぐ判断できるREADME/release metadataとinstallable artifactを作る。

## Work preservation and efficiency

既存REVIEWED、DRAFT、ignored evidence、context packs、independent reviews、regression fixtures、checkpointsを機械的に削除・再生成しない。closed evidenceは再利用し、新しい矛盾、code/architecture/dependency/source変更、test failureがある範囲だけ再openする。NORMAL/LOW proseはbulk draft→independent review→automated validation、HIGH RISKだけconsumer/mechanicsまで深く監査する。Full QA/checkpointはarchitecture/category/2,000–3,000 reviewed-unit等の節目に集約する。

## Runtime and release status

current installed snapshotを完成対象から外さない。fully isolated runtime QAを安全に構築できない場合は実ユーザー環境へinstallせず、`RC_READY / MANUAL_INSTALL_VERIFICATION_REQUIRED`とする。runtime未実施項目は`NOT_TESTED`として明示する。
