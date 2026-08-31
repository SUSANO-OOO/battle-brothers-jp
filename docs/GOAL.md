# Project Goal

Status: ACTIVE
Authority: Final Producer Directive (2026-08-31)
Codex native goal: configured for the current project task

## Goal

Battle Brothersを日本語で遊びたい一般ユーザーが、自分のBattle Brothers本体・所有DLC・導入MOD構成に応じて、できるだけ簡単に日本語化を導入できる一般公開・継続保守可能な日本語化systemを完成させる。

日本語化MODはgameplay、balance、AI、save、persistence、他MODを極力壊さず、正式対応範囲はactual source、actual mechanics、Battle Brothersの世界観と文脈に忠実な高品質で自然な日本語を提供する。未対応MOD、未検証version、未知文字列は、危険な推測翻訳より安全なoriginal English pass-throughを優先する。

Battle Brothers本体、framework、Legends、その他MODが更新された後も、canonical ledgerにあるreview済みtranslation資産を捨てず、変更範囲だけを差分検出・再検証・再翻訳できるようにする。対応version、必要dependency、導入方法、既知制限を、MOD知識のない一般ユーザーにも理解できる形で提供する。

## Priority

1. game、save、other MODを壊さない。
2. supported player-facing contentを正確かつ自然な日本語にする。
3. 一般ユーザーが自分に必要なpackage/dependencyだけを容易に導入できるようにする。
4. unsupported/unknown contentは危険な推測翻訳よりEnglish pass-throughを優先する。
5. update時にreview済みtranslationを維持し、変更範囲だけを再検証する。
6. version、dependency、compatibility、install方法を非技術ユーザーへ明確にする。

翻訳率を上げるためにPriority 1を犠牲にしてはならない。

## Fixed outcomes

- actual user Battle Brothers環境とuser-dataへのwriteは常に0件とする。
- VanillaユーザーへLegends、Legends Assets、Legends-specific componentを要求しない。
- official DLC未所有をstartup failureにしない。
- Rosettaとbattle-brothers-stdlibを、日本語化のためにユーザーが別途探してinstallするdependencyにしない。
- normal gameplay runtimeはofflineで成立させる。
- reviewed translationはarchitecture移行を理由に再翻訳せず、canonical reviewed dataからdeterministicにruntimeへ生成する。
- unknown/unsupported inputはbounded reviewed contractに一致しない限り破壊せずpass-throughする。
- translation-specificなsave dependencyを極力作らない。
- public latest、current verified source snapshot、next public release targetを混同しない。
- 実施していないtestをPASSと報告しない。

## Completion

Goalはresearchやarchitecture documentの完成ではなく、current verified snapshotを途中放棄せず、public ecosystem evidenceに基づくpackage/runtime、review済みVanilla・Legends・supported MOD翻訳、compatibility metadata、非技術ユーザー向けREADME、QA evidence、実際に導入可能なrelease artifactまで完成したときに達成される。
