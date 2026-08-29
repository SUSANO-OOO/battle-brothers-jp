# Battle Brothers 統合日本語化MOD

Battle Brothers本体、公式DLC、Legends、および対応対象として確定した導入済みMODを一体として日本語化する、独立した日本語化MODです。

> 現在は開発中です。`dist/mod_battle_brothers_jp.zip` はまだリリース候補ではありません。進捗と検証境界は `PROJECT_STATE.md` を参照してください。

## 安全境界

制作中、ユーザーの実ゲーム環境・設定・セーブ・ログ・プロファイルは読み取り専用です。生成物を実環境へ自動導入しません。

## 想定インストール形態

完成後は、必要なframework/dependencyを用意し、競合する旧日本語化MODをユーザー自身で外したうえで、`mod_battle_brothers_jp.zip` を展開せず `Battle Brothers/data/` に配置する構成を目標とします。

現在の設計では、導入済みのModern Hooks `>=0.6.0`、MSU `1.9.0`、Legends `19.4.20`、Legends Assets `19.4.3`に加え、Rosetta `0.5.0`とbattle-brothers-stdlib `>=2.5`をexternal dependencyとして要求します。Rosetta/stdlibは現在の実ゲーム環境には未導入であり、本projectが自動installすることはありません。

RC完成後の導入手順は、(1) 上記dependencyを確認、(2) 既存日本語化MODがあればユーザー自身で外す、(3) `mod_battle_brothers_jp.zip`を展開せず`Battle Brothers/data/`へ置く、(4) ゲームを起動、の4段階です。アンインストールは今回のZIPだけを削除します。Codexは実環境でこれらの操作を行いません。

## 開発操作

主要な再現操作:

```powershell
# read-only installed snapshot scan（実パスは各環境で明示）
python tools/bbjp.py scan --game-root <GAME_ROOT> --user-data <USER_DATA> --steam-manifest <APPMANIFEST> --output reports/local/fresh-source-snapshot.json

# source extraction/classification後のcoverage再計算
python tools/classify_ledger.py

# translation batchのplaceholder検証とledger適用
python tools/apply_translation_batch.py --batch work/review_batches/<BATCH>.json --reviewed-only

# independently reviewed runtime pattern/boundary contractの検証・適用
python tools/apply_runtime_pattern_batch.py --batch work/review_batches/<PATTERN_BATCH>.json --dry-run
python tools/apply_runtime_pattern_batch.py --batch work/review_batches/<PATTERN_BATCH>.json

# reviewed ledgerからruntime mapと代表/collision harnessを再生成
python tools/generate_runtime_translations.py

# development-only build（releaseではない）
python tools/build_mod.py --allow-incomplete --output work/qa/mod_battle_brothers_jp_VERTICAL_SLICE.zip

# static/local QA
python tools/qa_mod.py --archive work/qa/mod_battle_brothers_jp_VERTICAL_SLICE.zip --sq <SQ_EXE> --node <NODE_EXE> --report reports/qa-vertical-slice.json

# release buildはcoverage=METに加え、24時間以内のfresh scanと全source/ledger fingerprint一致が必須
python tools/build_mod.py --snapshot-report reports/local/fresh-source-snapshot.json --output dist/mod_battle_brothers_jp.zip

# future MOD/update: fresh scan後、fingerprint差分とdependency graphを先に確認
python tools/bbjp.py update --before reports/source-snapshot.json --after reports/local/fresh-source-snapshot.json --output reports/local/update-plan.json
```

`update`はfingerprint変更を検出した場合、dependency graph更新前に翻訳抽出へ進まず停止します。現在の実装済み/未実装境界は `PROJECT_STATE.md` を参照してください。

## 権利関係

このリポジトリへBattle Brothers本体、DLC、Legendsや第三者MODのアーカイブ全体、既存日本語化MOD、無許諾の翻訳・コード・font・assetを含めません。
