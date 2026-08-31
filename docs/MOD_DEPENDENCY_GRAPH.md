# MOD Dependency Graph

対象snapshotは`BBJP-CF88150E7B355ECD32D9`。machine-readableな22 node・42 relation・source evidenceは`reports/mod-dependency-graph.json`に記録する。

## Semantics

- `requirement`: presence/versionの必須条件。queue順とは別概念。
- `incompatibility`: 同時導入を拒否する条件。
- `queue_before` / `queue_after`: 実行順だけを表す。

Legendsのlegacy無印expressionはactual API上requirementとafter-orderの両方を持つため、graphでは2 edgeへ正規化する。Modern Hooksの`>`/`<`はorderだけであり、dependencyへ昇格しない。

## Installed ecosystem

Current read-only snapshotでは、legacy mod_hooks `21.1`、Modern Hooks `0.6.0`、MSU `1.9.0`、Legends `19.4.20`、Assets `19.4.3`、全5 DLC、Events Fix、Jimmy's Tooltips、Legends load-order/compat modulesが登録される。Rosetta `0.5.0`とstdlib `2.6`は開発時に公式sourceを監査したが、実環境には導入されていない。

Rosetta自身のMSU/stdlib requirementとqueue relationは、public ecosystem/composition referenceとしてgraphに残す。これはJPからRosetta/stdlibへのrequirementを意味しない。

## JP localization chain

`mod_battle_brothers_jp`の唯一のrequirement edgeは`mod_modern_hooks >=0.6.0`である。`>mod_legends`、`>mod_msu`、`>mod_rosetta`はLate bucket内のoptional composition relationであり、対象が無くてもstartup requirementにはならない。

Normal bucketは安価なregistered-MOD version検出、namespaced runtime/data、条件付きJS/CSS登録を行う。Late bucketはverified profileに一致するdisplay-only hooksだけを登録する。Vanilla profileが未知ならhook/JS/CSSを登録せずEnglish pass-throughする。Legends partitionの不一致はCore全体ではなくLegends supportだけをdisableする。

Actual ignored Modern Hooks queue graph（SHA-256 `18459B04E9467EE0198DAD4794DDD91EB1A6543D2CAFD8FF9DF952541373C276`）を実行するlocal composition harnessが、MSU/Rosetta/Legends/JPのorderingを検証した。これはreal game runtime QAではない。
