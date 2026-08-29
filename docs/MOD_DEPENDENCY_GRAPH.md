# MOD Dependency Graph

対象snapshotは`BBJP-CF88150E7B355ECD32D9`。machine-readableな22 node・48 relation・source evidenceは`reports/mod-dependency-graph.json`に記録した。

## 読み方

- `requirement`: 必須presence/version条件。
- `incompatibility`: 同時導入禁止条件。
- `queue_before` / `queue_after`: 実行順だけの条件。
- Legendsで使われる旧Hooksの無印expressionは、requirementとafter-orderの両方を表すが、machine-readable graphでは必ず2本の独立edgeへ正規化する。Modern Hooksの`>`/`<`は原則としてorderだけを表す。

dependencyであることだけからload順を推測していない。actual preload sourceと、read-only取得したruntime queue logの両方を根拠にした。

## Current active chain

`mod_hooks 21.1`が旧APIを提供し、`mod_modern_hooks 0.6.0`がModern Hooks APIを提供する。`mod_msu 1.9.0`はVanilla `>=1.5.0-13`を要求する。Legends `19.4.20`はMSU `>=1.9.0`、Legends Assets `>=19.4.3`、Vanilla `>=1.5.2-3,<1.5.3`、全5 DLC、同梱Events Fixを要求し、それらの後で実行される。

同梱Jimmy's Tooltips `1.0.5`はLegends、MSU、Modern Hooksをrequireし、通常bucketとVeryLate bucketの双方でLegendsより後にhookする。Legends内部のload-order-fixとcompat-checkは独立登録されるため、inventoryでも別nodeとして保持する。

## Localization chain

Rosetta `0.5.0`をSquirrel境界として採用した。Rosetta自身はMSU `>=1.6.0`と`stdlib >=2.5`をrequireし、MSU前の早期hookとMSU後のLate hookを別queueとして登録する。現在snapshotにRosettaとstdlibは存在しないためexternal dependencyであり、今回ZIPへは内包しない。

`mod_battle_brothers_jp`からはVanilla、Legends、Legends Assets、MSU、Modern Hooks、Rosetta、stdlibへの7 requirement edgeと、Rosetta/MSU/Legendsへの3 queue-after edgeを個別に記録した。Rosettaの主getter/template hookはLate bucketであるため、JP MODも同じ`QueueBucket.Late`を指定した上で`>mod_rosetta`を適用する。bucketが異なると`>` relationだけではwrapper順が保証されない。requirementとqueueを合成したrelation typeは使用しない。

JS-origin文字列はRosetta `0.5.0`の対象外なので、Modern Hooks `registerJS`/`registerCSS`を使う独立UI層が必要である。
