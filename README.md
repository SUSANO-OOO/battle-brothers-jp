# Battle Brothers 統合日本語化MOD

Battle Brothers本体、所有している公式DLC、Legends、および正式対応したMODを、1つのZIPで条件付きに日本語化する公開開発プロジェクトです。

> 現在は開発中です。リリース版はまだありません。`work/qa/namespaced-runtime-corrected.zip`（SHA-256 `6086D3DB440F0089C04634959B702BA50F8CBC31A24104E568132894EE5BA921`）は検証用のdevelopment artifactであり、一般配布用ではありません。正確な進捗は`PROJECT_STATE.md`を参照してください。

## 完成版で必要なもの

- Battle Brothers
- Modern Hooks `0.6.0`以上
- 完成後の`mod_battle_brothers_jp.zip` 1個

Vanillaだけで遊ぶ人は、Legends、Legends Assets、MSU、Rosetta、battle-brothers-stdlibを日本語化のために導入する必要はありません。Legendsを使う人は、Legends自身が指定するDLC・Assets・MSU等を別途揃えてください。

現時点で静的検証済みの対象は、Battle Brothers `1.5.2-3`、各公式DLC `1.0.0`、Legends `19.4.20`、Legends Assets `19.4.3`、MSU `1.9.0`です。異なるversionは起動を機械的に壊さず、検証済み条件に一致しないpartitionを原文Englishのまま通す設計です。Legends `19.4.21`は差分監査済みですが、まだ正式対応ではありません。

## 完成版の導入・削除

1. Modern Hooksを導入する。
2. 競合する既存日本語化MODがあれば、ユーザー自身で外す。
3. `mod_battle_brothers_jp.zip`を展開せず`Battle Brothers\data\`へ置く。
4. ゲームを起動する。

削除は今回のZIPだけを`data`から取り除きます。本projectは実ゲーム環境、設定、セーブ、ログ、プロファイルへ自動install・変更を行いません。

## 設計上の安全境界

- 翻訳runtimeは`::BattleBrothersJP.Runtime`内でoffline動作し、Rosetta/stdlibのglobal namespaceを登録しません。
- exact lookupとreview済みbounded patternだけを使い、未知文字列・未知MOD・未検証versionは原文を維持します。
- raw ID、internal key、actor/item/world identity、gameplay値、RNG、AI、save/persistenceは翻訳しません。
- original処理は1回だけ実行し、JP処理だけが失敗した場合は保存済みoriginal resultへ戻します。
- canonical ledgerのreview済み翻訳からruntimeを決定論的に生成し、architecture変更を理由に再翻訳しません。

## 開発操作

```powershell
# 実環境はread-onlyでscanする。実パスは明示する
python tools/bbjp.py scan --game-root <GAME_ROOT> --user-data <USER_DATA> --steam-manifest <APPMANIFEST> --output reports/local/fresh-source-snapshot.json

# 分類・review済みtranslationから生成
python tools/classify_ledger.py
python tools/generate_runtime_translations.py
python tools/generate_runtime_reachability.py
python tools/generate_package_manifest.py

# development buildとlocal full QA
python tools/build_mod.py --allow-incomplete --output work/qa/mod_battle_brothers_jp_DEV.zip
python tools/qa_mod.py --archive work/qa/mod_battle_brothers_jp_DEV.zip --sq <SQ_EXE> --node <NODE_EXE> --report reports/local/qa-dev.json

# release build: coverage gate、fresh read-only snapshot、Squirrel/Node、archive QAが必須
python tools/build_mod.py --snapshot-report reports/local/fresh-source-snapshot.json --sq <SQ_EXE> --node <NODE_EXE> --output dist/mod_battle_brothers_jp.zip

# future MOD/update: dependency/fingerprint差分を翻訳抽出より先に確認
python tools/bbjp.py update --before reports/source-snapshot.json --after reports/local/fresh-source-snapshot.json --output reports/local/update-plan.json
```

## 権利関係

Battle Brothers本体・DLC・Legends・第三者MODのarchive/source/assets、既存日本語化MOD、無許諾font/assetsは含めません。同梱Noto Sans CJK JPはOFL 1.1、namespaced runtimeでadaptしたRosetta由来部分はBSD-2-Clauseのnoticeを同梱します。
