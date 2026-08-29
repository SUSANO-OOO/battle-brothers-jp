# Battle Brothers 統合日本語化MOD制作 — FINAL MASTER DIRECTIVE

あなたは本プロジェクトの実装責任者です。

対象は **Battle Brothersの新しい統合日本語化MOD制作** のみです。他ゲーム、他リポジトリ、過去の別プロジェクトの情報・設計・コード・履歴・QAルールを持ち込まないでください。

この指示の目的は、特定の技術方式を押し付けることではありません。

**最終的に、現在のBattle Brothers環境で実際に使える高品質な日本語化MODを完成させること**が目的です。

実装方式、内部構造、tooling、hook方式等については、後述する絶対条件を守ったうえで、実際のゲーム・MOD・依存関係を調査して最適な方法を選択してください。

計画や調査報告だけで停止せず、実装・翻訳・検証・成果物作成まで進めてください。

---

# 1. 最終成果物

現在このPCに実際に導入されているBattle Brothers環境を調査し、

- Battle Brothers本体 / Vanilla
- DLC
- Legends
- Legends Assets
- 現在導入されているその他MOD
- それらが必要とするframework / dependency

に対して機能する、新しい独立した日本語化MODを制作してください。

これはLegendsだけの翻訳パッチではありません。

**Battle Brothers本体 + Legends + 現在対応対象となるMOD**

を一体として日本語化するMODです。

最終的なユーザー向け成果物は、技術的に妥当である限り、`mod_battle_brothers_jp.zip`のような**1つのinstallable MOD ZIP**としてください。

ユーザーが最終的にそのZIPを、`Battle Brothers\data\`へ**展開せずそのまま配置**し、必要なframework/dependencyが揃っていれば利用できる状態を基本完成形としてください。

Modern Hooks、MSU、Rosetta等の既存frameworkがdependencyとして必要である場合、それらまで無理に今回ZIPへ内包する必要はありません。正しいdependencyとして扱い、READMEへ記載してください。

---

# 2. このプロジェクトで絶対に守る条件

以下は実装裁量ではなく固定条件です。

1. ユーザーの現在のBattle Brothers環境は完全READ-ONLY
2. ゲーム本体を翻訳都合で改造しない
3. gameplay/balance/AI等を変更しない
4. 既存日本語化MODへ依存しない新MODを基本とする
5. 既存日本語化MODの翻訳本文・code・font・assetを無断流用しない
6. Battle Brothersの世界観に忠実な日本語にする
7. 文字化け・missing glyph・placeholder破損を既知のままreleaseしない
8. Legendsと現在の他MODの依存関係・queue・hook構造を理解してから互換性を設計する
9. 現在のSUPPORTED SNAPSHOTに対する翻訳対象を可能な限り全件解決する
10. 将来MODが追加・更新された際に更新できる構造にする
11. 最終的にユーザーが導入可能なZIPを生成する
12. 実施していないtestをPASSと報告しない

---

# 3. Codex側に任せる実装判断

以下はこの指示で先決めしません。実ファイルを調査して最適な方法を選択してください。

- Rosettaを使うか
- Rosettaをどこまで使うか
- Modern Hooksでどのclass/functionをhookするか
- exact queue position
- hookを何段に分けるか
- JS/UI layerの実装方式
- Vanilla translation layerの実装方式
- toolingの実装言語
- CLIの内部設計
- translation data format
- repository内部構造の細部
- branch戦略の細部
- CIの具体的構成
- fontの選定
- artifact内部module構成
- exact ZIP filename

ただし、選択した方式は実source・仕様・テストから根拠を示してください。「この指示にそう書いてあるから」という理由だけで不適切な方式を使わないでください。

---

# 4. ユーザーのBattle Brothers環境は完全READ-ONLY

現在ユーザーが利用しているBattle Brothers installation directory、`data`、game files、DLC、existing MOD files、existing Japanese MOD、config/settings、saves、Battle Brothers関連user-dataは**調査のために読むだけ**です。一切編集してはいけません。

禁止：`data`へのfile追加、MOD file変更、archive変更、MOD削除、rename、move、disable、load-order変更、game file変更、config変更、save変更/作成/削除、今回作った日本語化MODの実環境への自動install、QA目的の一時変更、「あとで戻す」ことを前提としたwrite。

実ユーザー環境へのwrite操作は **0件** でなければなりません。解析が必要なsourceはREAD-ONLYで取得し、project repository、`work/`、staging、isolated copy、sandbox等へコピーして作業してください。`work/`等の解析sourceはgitignoreしてください。

---

# 5. Runtime QAでも実環境を汚さない

isolated runtime QAを行う場合は、game folderだけでなくDocuments、config、save、log、user profile等へのwriteも実ユーザー環境から隔離できることを確認してください。

完全に安全な隔離を保証できない場合は、ユーザーの実環境へ勝手にinstallして確認してはいけません。その場合は、`RC_READY / MANUAL_INSTALL_VERIFICATION_REQUIRED`としてください。

---

# 6. GitHub repository

今回の正式repositoryは、`SUSANO-OOO/battle-brothers-jp`です。

最初に`gh auth status`、`gh api user -q .login`、`gh repo view SUSANO-OOO/battle-brothers-jp`を確認してください。

存在しなければPRIVATE repositoryとして新規作成してください。description候補：`Comprehensive Japanese localization for Battle Brothers, Legends, and supported mods`

既に存在する場合は今回project用であることを確認してください。別用途なら上書き・reset・流用しないでください。認証accountが違う場合も勝手に別ownerへ作らないでください。force pushや履歴破壊操作は禁止です。

GitHub認証/権限が存在しない場合のみexternal blockerとして扱い、それ以外の作業は進めてください。

---

# 7. Repository内に状態を残す

最低限：`README.md`、`AGENTS.md`、`PROJECT_STATE.md`、`CHANGELOG.md`、`VERSION`、`.gitignore`、`docs/`、`src/`、`tools/`、`tests/`、`reports/`、`dist/`、`work/`を用意してください。

この指示も、`docs/MASTER_DIRECTIVE.md`として保存してください。

`PROJECT_STATE.md`にはcurrent phase、current commit、installed snapshot ID、detected versions、architecture、completed work、translation counts、coverage、last green test、blockers、unresolved items、next exact action、artifact state、runtime stateを記録し、長期作業でcontextが切れても再開できるようにしてください。

---

# 8. 実際の環境を先に完全把握する

versionやMOD構成を過去情報やWebだけから決めないでください。**実際にユーザーが導入しているfilesがtranslation targetのsource-of-truthです。**

READ-ONLYで最低限、Battle Brothers exact version、DLC、Vanilla user-facing strings、Legends exact installed version、Legends Assets exact installed version、MSU、Modern Hooks、その他framework、existing Japanese MOD、その他全MOD、filename、size、SHA-256、mod ID、friendly name、version、`.nut`、`.cnut`、`.js`、`.css`、UI/resource、user-facing text、internal-only textを調査してください。

現在の構成を再現可能な`installed snapshot ID`として固定してください。

---

# 9. 他MODは依存関係まで理解する

他MODは「翻訳対象の英文があるか」だけを調べてはいけません。現在のMOD ecosystem全体を理解してください。

各MODについて最低限、Mod ID、version、required dependencies、optional dependencies、framework dependencies、incompatibilities、Legendsとの関係、MSUとの関係、Modern Hooksとの関係、他MODへのdependency、queue/load-before、queue/load-after、hook target、JS/CSS registration、user-facing text scopeを可能な範囲で解析してください。

特にModern Hooksでは、**requirement / incompatibility と queue/load order は別概念**として扱ってください。dependencyだから必ず後にloadすると決めつけてはいけません。実registration/preload/sourceから判断してください。

`docs/MOD_DEPENDENCY_GRAPH.md`、`reports/mod-dependency-graph.json`を作成し、依存グラフを日本語化MODのhook/queue設計の根拠にしてください。

---

# 10. 「存在するMOD」と「有効なMOD」を混同しない

`data`にあるというだけでACTIVEと断定してはいけません。必要に応じ、KNOWN_ACTIVE、LOAD_CANDIDATE、OPTIONAL_PRESENT、FRAMEWORK、KNOWN_INACTIVE、NO_USER_FACING_TEXT、INCOMPATIBLE、LOAD_STATE_UNKNOWN等へ分類してください。判断できないものを推測でACTIVE扱いしないでください。

`docs/INSTALLED_MOD_INVENTORY.md`、`docs/COMPATIBILITY_MATRIX.md`、machine-readable inventory `reports/source-snapshot.json`を作成してください。

---

# 11. Existing Japanese MOD

現在導入されている日本語化MODについて、translation方式、hooks、file replacement、Squirrel、JS/UI、font、glyph、encoding、line wrapping、placeholder、dynamic strings、load priority、Legends非対応原因、他MODとの競合を技術的に解析してください。

ただしその既存MODのJapanese translation text、code、font、assetsを作者の明示許可なしに今回projectへコピー・流用・改変利用してはいけません。

今回の翻訳本文は原則として、**English original + source context + actual game mechanics + lore**から新規に作成してください。

---

# 12. 新日本語化MODは旧日本語化MODから独立させる

今回の新MODをexisting Japanese MODの必須dependencyにしないでください。isolated runtime QAが可能なら、**existing Japanese MODなし + new Japanese MOD**で成立することを確認してください。

旧日本語化MODとnew MODが競合する場合は、「new MOD導入前にユーザー自身で旧日本語化MODを外す」ことをREADMEへ明記してください。実ユーザー環境の旧MODをCodexがdisable/removeしてはいけません。

---

# 13. Architecture

最初から特定方式を決め打ちしないでください。最低限、A. Vanilla language/bootstrap、B. Squirrel translation、C. JS/UI translation、D. font/rendering、E. optional-MOD compatibilityを分けて考えてください。

結果を`docs/ARCHITECTURE.md`へ記録してください。

---

# 14. Modern Hooksは有力候補だが盲目的に固定しない

Modern Hooksが適切な箇所では、whole-file replacementよりhook方式を優先してください。

Mod ID候補：`mod_battle_brothers_jp`。ZIP候補：`mod_battle_brothers_jp.zip`。preload候補：`scripts/!mods_preload/mod_battle_brothers_jp.nut`。

これらは安全なdefault候補です。実際のarchitecture上変更する合理的理由がある場合は変更可能ですが、理由を記録してください。

Modern Hooks採用時はregistration、SemVer、require、incompatibility、queue、before/after relation、optional targets、JS/CSS registrationをactual sourceとdocumentationに基づいて設定してください。

---

# 15. Rosettaも有力候補だが必須ではない

Rosettaを使う場合は、採用するactual versionのREADME、source、translation guide、testsを確認してください。

RosettaでSquirrel translationを効率化できる場合は活用してください。ただしVanilla language bootstrap、JS-origin strings、custom UI、Rosetta interceptionを通らないstringsまで全部Rosettaで解決できると仮定してはいけません。日本語`ja` activation/detectionもactual environmentで確認してください。

Rosettaを採用しない方が今回architectureに適していると実証できた場合は、別方式を選択して構いません。

---

# 16. File replacementは必要最小限

hook/overlayで安全に対応できる場合、whole-file replacementを避けてください。replacementが必要ならexact target、loader priority、archive order、`.nut/.cnut`、collision riskを確認してください。偶然のtimestampや環境依存挙動へ頼らないでください。

---

# 17. 大量翻訳前に技術成立を証明する

いきなり何万件も翻訳してはいけません。まず少数のVertical SliceでVanilla Japanese text、dynamic string、Legends text、placeholder、Japanese font、JS/UI（必要な場合）、dependencyを持つMOD、optional MOD absence等について、end-to-endで日本語化が成立することを確認してください。

architectureに問題があれば、この段階で直してください。Vertical Slice成立後にbulk translationへ進んでください。

---

# 18. 翻訳対象

player-facing textを対象としてください。例：menus、options、tutorials、campaign setup、origins/scenarios、backgrounds、traits、perks、skills、status effects、injuries、items、weapons、armor、shields、crafting、camping、retinue、contracts、events、ambitions、factions、enemies、locations、settlements、world UI、character UI、perk tree、combat log、tooltips、dynamic messages、Legends-specific systems、MOD settings、current MOD-specific content。

原則翻訳しない：internal ID、mod ID、class/function/variable、script paths、dependency IDs、filenames、parser tokens、save semantics、machine-readable data。

user-facingかinternalか不明ならcall site/contextまで確認してください。

---

# 19. 世界観に忠実なプロ翻訳

翻訳品質は最重要release gateです。

Battle Brothersのgrounded low fantasy、中世～近世欧州風の社会、傭兵稼業、軍事文化、武器、防具、戦術、社会階級、貧困、負傷、死、暴力、宗教、迷信、怪異、fatalism、gallows humor、dark humor、傭兵の粗野さ、貴族/役人の距離感、庶民の話し方、Legends独自世界観を維持してください。

禁止：原文にないネットスラング、安易なアニメ口調、corporate日本語、無差別なJRPG調、不自然な直訳、原文以上の脚色、勝手な美化、勝手な検閲、lore捏造、sourceにないcharacterization。

一方、過剰な擬古文も避けてください。

基準：**日本語として自然で読みやすく、Battle Brothersの正式日本語版として読んでも世界観から浮かないこと。**

---

# 20. Translation Source Priority

翻訳判断が曖昧な場合：

1. actual installed source context
2. actual game mechanics/code
3. 同一termの全出現箇所
4. installed MOD documentation
5. Battle Brothers / Legends一次資料
6. official modding docs
7. 補助資料

の順で判断してください。Web最新版とinstalled versionを混同しないでください。

---

# 21. Glossary / Style Guide

`docs/GLOSSARY_JA.md`、`docs/LOCALIZATION_STYLE_GUIDE_JA.md`、`docs/LORE_TERMINOLOGY_AUDIT.md`を作成してください。

最低限、narration、mercenary、noble、official、commoner、religion、cult、occult、undead、military、weapons、armor、injuries、tactics、contracts/economy、settlements、proper nouns、katakana/transliteration、punctuation、numbers、profanity、UI、tooltips、event prose、Legends、MOD-specific exceptionsを定義してください。

同じperk/skill/item/faction等の用語を画面ごとにばらつかせないでください。

---

# 22. AI translation

AIによるdraft生成は可能です。ただしAI outputはDRAFTです。

release前に必ず別passでcontext、semantics、mechanics、lore/tone、terminology、Japanese naturalness、placeholder/patternをレビューしてください。可能であれば独立sub-agent/reviewerも利用してください。生成してそのまま自己承認は禁止です。

---

# 23. High-Risk Translation

特にperks、skills、injuries、status、numerical conditions、contracts、event choices、origin rules、factions/lore、named/legendary content、dynamic patternsは重点監査してください。プレイヤーのgameplay判断へ影響する誤訳を残さないでください。

---

# 24. Translation Ledger / Coverage

全対象をmachine-readableに追跡してください。最低限、module、source、context、English、Japanese、stable key、status、review status、placeholder signature、notesを保持してください。

current SUPPORTED SNAPSHOTについて、`UNTRANSLATED = 0`、`TRANSLATED_NEEDS_REVIEW = 0`、unresolved = 0をrelease gateとしてください。

ただしinternal stringや技術的翻訳対象外を無理に訳す必要はありません。その場合は理由付きresolved exclusionとして記録してください。

---

# 25. Placeholder / Dynamic Text

必ず保持・検証してください：placeholders、format tokens、variables、captures、color tags、markup、image tags、escape、newline、names、numbers、money、item/faction substitutions、event/template variables。

日本語として不要に見えるという理由だけでruntime-required tokenを削除しないでください。pattern overmatch / undermatch / collisionをtestしてください。

---

# 26. Legends Dynamic Content

Legendsのdynamic events/templatesではactors、pronouns、item/faction names、generated values、choices、result strings等を含む可能性があります。単純literal replacementだけで扱えると仮定しないでください。代表sampleで動的置換を検証してください。

---

# 27. 文字化けゼロを必須基準にする

「日本語にはなったが文字化けする」は完成ではありません。

actual encoding、BOM requirement、invalid byte sequences、mojibake、`???`、`�`、`□`、missing glyph、raw escape、raw markup、broken color tags、punctuation/symbolsを検査してください。

「UTF-8なら大丈夫」と決めつけず、actual loader/runtime requirementsを確認してください。known mojibake = 0、required missing glyph = 0をrelease conditionにしてください。

---

# 28. Font / Rendering

正式QA対象です。hiragana、katakana、required kanji、punctuation、symbols、glyph coverage、line wrapping、tooltip width、event長文、buttons、UI clipping、representative resolutionsを確認してください。

既存日本語MODのfontを無断利用しないでください。font同梱が必要ならredistribution可能licenseを確認してください。

---

# 29. Future MOD Update

現在の環境専用の使い捨てMODにしないでください。将来MODを追加した際、1. scan、2. dependency analysis、3. new/changed source detection、4. translation extraction、5. review queue、6. translation、7. QA、8. rebuildができるようにしてください。

最低限、scan、extract、diff、coverage、validate、build、qa、update相当の操作を提供してください。ただし、将来更新基盤を過剰に汎用framework化し、現在の翻訳MOD完成を遅らせないでください。

---

# 30. Future MODでもdependencyを先に理解する

新MODを追加した場合、文字列抽出だけを先にしないでください。まずMod ID、dependencies、optional dependencies、incompatibilities、framework、queue before/after、hook target、Legends/MSU/Modern Hooksとの関係をdependency graphへ追加してください。その後translation moduleを追加してください。

---

# 31. Automated QA

必要十分なautomated QAを作ってください。

最低限：syntax、generated translation validity、duplicate keys、pattern collision、unresolved translation、stale/source-changed translation、placeholder/tag integrity、encoding、BOM、mojibake heuristic、glyph coverage、archive structure、Mod ID、preload registration、dependency data、queue relations、optional target absence、accidental third-party inclusion、gameplay-changing code absence、actual game pathへのwrite absenceを検査してください。

---

# 32. CI

repositoryだけで実行できるtestは可能な範囲でGitHub Actions等にしてください。ただしCI構築そのものをprojectの主目的にしないでください。

Battle Brothers本体やthird-party MODをGitHubへuploadしてはいけません。local sourceが必要な検査はLOCAL QAとして分離してください。

---

# 33. Runtime QA

安全なfully-isolated environmentが構築可能な場合のみ行ってください。

理想構成：**new Japanese MOD + old Japanese MODなし + current Legends + current supported MOD set**

代表確認：main menu、campaign setup、origins、backgrounds、perks/skills、items/tooltips、settlement、contracts、events、crafting、camping、Legends UI、current MOD UI、combat、combat log、battle finish、isolated save/load。

確認：crashなし、translation-related script errorなし、dependency/queue errorなし、mojibakeなし、missing glyphなし、raw tagsなし、placeholder破損なし、critical clippingなし、mechanics誤訳なし、old Japanese MOD hidden dependencyなし。

完全隔離できない場合はユーザー実環境へ勝手に入れないでください。

---

# 34. Gameplay変更禁止

翻訳MODによってbalance、AI、damage、skills、perks、stats、economy、event probability、world generation、save behaviorを変更してはいけません。翻訳hookがgame behaviorを変えていないことも確認してください。

---

# 35. Copyright / License

PRIVATE repositoryから開始してください。

無断commit禁止：Battle Brothers本体、game assets、full decompiled source、Legends archive全体、third-party MOD archive全体、existing Japanese MOD、third-party fonts/assets/audio。

解析sourceはgitignoreされた領域へ置いてください。OSS frameworkを同梱する場合はlicenseを遵守してください。勝手にPUBLIC化しないでください。

---

# 36. Installable ZIP

ユーザー向け最終成果物は原則、`dist/mod_battle_brothers_jp.zip`としてください。ただしactual loader仕様上、別名・別構造が明確に適切ならCodex側で変更して構いません。

重要なのは、**ユーザーが完成したZIPをBattle Brothersの`data`へZIPのまま配置して利用できること**です。

ZIP内部に余計なproject root folderを入れないでください。必要なpreload/scripts/ui等をloaderが期待するcorrect root pathへ置いてください。clean buildからZIPを生成しSHA-256を記録してください。

---

# 37. Install / Uninstall

可能な限り導入手順は、1. required dependency確認、2. 競合するold Japanese MODがあればユーザー自身で外す、3. new Japanese MOD ZIPを`Battle Brothers\data`へ置く、4. game起動にしてください。

uninstallも可能な限り、**今回ZIPを削除するだけ**にしてください。

---

# 38. Failure Loop

failureが発生した場合：1. evidence保存、2. root cause特定、3. fix、4. affected test、5. regression test、6. global check、7. PROJECT_STATE更新、8. continue。

同じfailureが再発する場合はmicro-patchを繰り返さず、dependency graph、architecture、language bootstrap、hooks、queue、patterns、source mapping、encoding、font/renderingまで戻って再監査してください。

---

# 39. Translation Quality Loop

各大category完了時にterminology、context、mechanics、lore/tone、Japanese naturalness、placeholder、encoding/rendering riskを別passで監査してください。問題があれば修正し再監査してください。

---

# 40. Final Loop Audit

完成報告前に必ず独立した最終監査を実施してください。

最低限：current snapshot再確認、source fingerprints、MOD inventory、dependency graph、require/optional/incompatibility、queue relations、git clean、clean build、automated QA、coverage recalculation、unresolved = 0、unreviewed draft = 0、stale/source-changed unresolved = 0、placeholder violations = 0、known mojibake = 0、required missing glyph = 0、dependency/queue conflict = 0、accidental third-party content = 0、actual user environment write = 0、old Japanese MOD hidden dependency = 0、terminology/lore consistency、high-risk translation review、ZIP internal structure、README/version/manifest consistency、artifact SHA-256、final commit SHA、GitHub remote read-backを確認してください。

問題があれば完成報告せず修正loopへ戻ってください。

---

# 41. RC_READY Definition of Done

以下を満たして初めてRC_READYです。

- GitHub repository作成/push済み
- current environment inventory完成
- installed snapshot ID確定
- dependency graph完成
- architecture確定
- Vertical Slice成立
- Vanilla translation完成
- Legends translation完成
- current supported MOD translation/assessment完成
- glossary/style/lore review完成
- unresolved user-facing strings = 0
- unreviewed AI drafts = 0
- stale/source-changed unresolved = 0
- known mojibake = 0
- required missing glyph = 0
- automated QA green
- clean installable ZIP完成
- artifact checksum完成
- actual user environment write = 0
- unauthorized third-party reuse = 0
- README完成
- Final Loop Audit green
- final commit push/read-back済み

---

# 42. RUNTIME_VERIFIED

RC_READYに加え、安全なfully-isolated runtime QAでgame boot、new Japanese MOD load、old Japanese MODなし、supported MOD composition、dependencies/queue正常、translation-related crash = 0、critical mojibake = 0、missing required glyph = 0、critical placeholder defect = 0、critical UI defect = 0、critical mechanics mistranslation = 0を確認できた場合のみRUNTIME_VERIFIEDとしてください。

fully-isolated runtime QAが安全にできない場合は、`RC_READY / MANUAL_INSTALL_VERIFICATION_REQUIRED`が正しい最終状態です。

---

# 43. Final Report

完成時には最低限、GitHub repository URL、final commit SHA、Japanese MOD version、release state、installed snapshot ID、Battle Brothers version、Legends version、supported MOD/version/fingerprint、dependency summary、artifact filename、artifact SHA-256、Vanilla coverage、Legends coverage、per-MOD coverage、excluded items、automated QA、runtime QA、mojibake/font QA、known limitations、future MOD update command、install steps、uninstall stepsを報告してください。

実施していないtestをPASSと書いてはいけません。

---

# 44. Execution Priority

実際の作業優先順位は以下です。

1. GitHub/bootstrap
2. current Battle Brothers environment inventory
3. MOD dependency graph
4. existing Japanese MOD technical analysis
5. architecture
6. small Vertical Slice
7. terminology foundation
8. Vanilla translation
9. Legends translation
10. current MOD translations
11. translation review
12. encoding/font/mojibake QA
13. compatibility QA
14. clean ZIP build
15. future-update toolingの仕上げ
16. Final Loop Audit
17. push/final report

**toolingやCI作りに偏って、肝心の翻訳が進まない状態を作ってはいけません。**

---

このプロジェクトの本質は、**「Battle Brothers + Legends + 現在のMOD環境を、世界観に忠実な高品質日本語でプレイできる日本語化MODを作ること」**です。

他MODについては、単に英文を翻訳するだけではなく、**dependency・framework・load/queue order・hook relationまで理解した上で互換性を確保してください。**

ユーザーの既存Battle Brothers環境は最後まで完全READ-ONLYです。

最終成果物は、ユーザーが自分で`Battle Brothers\data`へZIPのまま配置して利用できる日本語化MODです。

この固定条件を満たす範囲では、具体的な技術方式は実際のsourceとテスト結果に応じて柔軟に選択してください。

責任を持って、到達可能な最高品質のrelease candidateまで作業してください。
