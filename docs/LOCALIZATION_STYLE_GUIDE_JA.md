# 日本語ローカライゼーション・スタイルガイド

Status: `FOUNDATION / CATEGORY EXCEPTIONS PENDING`

## Core voice

自然で読みやすい現代日本語を基調とし、grounded low fantasy、傭兵稼業、階級、貧困、負傷、死、宗教、迷信、怪異、fatalism、gallows humorを保つ。原文にないネットスラング、アニメ口調、corporate日本語、無差別なJRPG調、過剰な擬古文、脚色、美化、検閲、lore捏造を禁止する。

## Narration

- event narrationは三人称の常体を基本とする。
- 視覚・臭い・痛み・貧困・暴力の具体性を弱めない。原文以上に残虐さを足さない。
- 地の文を古文調にせず、語彙で中世欧州風の距離を作る。
- gallows humorは説明せず、乾いた可笑しみと不穏さを残す。
- brace variant `{A | B}`は各variantの意味とtoneを揃え、delimiterを保存する。

## Speaker register

- Mercenary: 簡潔で荒っぽい。軍務語彙を使うが、現代軍隊の過剰な官僚語にしない。
- Noble: 丁寧さより身分差と当然視を示す。無差別に「〜であるぞ」としない。
- Official: 事務的で距離がある。現代企業の「ご対応」「ソリューション」等は禁止。
- Commoner: 平易で生活感を優先。全員を同じ訛りにしない。
- Religion/cult: 正統宗教は厳粛、cult/occultは信奉者の確信と不気味さを保つ。勝手に悪魔崇拝語彙を足さない。
- Undead/monstrous speech: sourceに人格が無ければ台詞を創作しない。

## UI and mechanics

- ボタンは短い動作語。「終了」「撤退」「戦役を保存」。
- stat/tooltipsはmechanicsを先に、flavorを後にする。数値条件、対象、duration、stack、上限、例外を省略しない。
- `can not`等の原文上の否定は日本語で曖昧にしない。
- color/image/BBCode/HTML tag、placeholder、newlineはruntime contractとして保存する。
- 原文の単位`tiles`, `turns`, `%`, crownsを落とさない。tileは「マス」、turnは「ターン」。
- tooltip幅のため意味を削らず、重複表現と不要な主語を整理して短くする。

## Punctuation and typography

- 通常本文は全角の「、」「。」。UI label/titleは原則として句点なし。
- ASCII `%`, `+`, `-`, `/`, `:`は数値・token・system表記で保持する。
- 数値と単位の間に原文にない空白を足さない。
- 連続感嘆符、三点リーダ、dashはspeaker toneを見て必要最小限。三点リーダは原則「……」。
- 英字固有名詞と日本語の間へ機械的に空白を入れない。

## Proper nouns and transliteration

- lore固有語は既存日本語MODを参照せず、actual spelling、語源、同一語の全call siteから決める。
- ドイツ語風名詞は英語読みに機械変換しない。長音・促音は日本語として読める一表記へ固定する。
- 人名・地名のgenerated listは同一source spellingを常に同じカタカナへする。
- player-entered company/name、runtime-generated variableの内容は勝手に変換しない。

## Profanity and censorship

罵倒、性、排泄、死体、疾病は原文の強さを保つ。強さを上げ下げせず、放送禁止用語のような伏字を加えない。階級・性別・出自への侮蔑はspeaker characterizationとして扱い、翻訳者の説明を足さない。

## Legends and MOD-specific text

Legends固有systemはVanilla用語を再利用できる箇所だけ揃える。新class/perk/magic/camp/runeを既存JRPG用語へ寄せず、actual mechanicsとlore説明を読んでcategory単位で命名する。MSU/Modern Hooksのdeveloper diagnosticsとplayer-facing settingsをcall siteで分離する。

## Review sequence

AI draftは`TRANSLATED_NEEDS_REVIEW`。別passでcontext、semantics、mechanics、lore/tone、terminology、naturalness、placeholder、encoding/rendering riskを確認して初めて`REVIEWED`へ進める。生成者自身の即時承認は禁止する。
