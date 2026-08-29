# 日本語用語集

Status: `FOUNDATION / CATEGORY AUDIT REQUIRED`

actual installed source `BBJP-CF88150E7B355ECD32D9`を基準にした初期canonical glossary。長文・固有名詞・Legends独自語はcategory reviewで追記する。

## Campaign and company

| English | Canonical Japanese | Notes |
|---|---|---|
| company / mercenary company | 傭兵団 | 固有のcompany nameは翻訳しない。短い戦闘文脈で「戦団」としない。 |
| mercenary | 傭兵 | `brother`を常に「傭兵」とはしない。 |
| brother / sibling | 団員 | 傭兵団の構成員を指す通常形。実際の血縁なら「兄」「姉」「きょうだい」等をsource contextで選ぶ。 |
| bro / sib | 仲間 | 砕けた人物指示。呼びかけや語呂合わせでは「兄弟」「お前」「あんた」等を全文単位で再構成し、global置換しない。 |
| beggar | 物乞い | background名・人物描写・動的変数を区別し、internal key/IDは変更しない。 |
| campaign | 戦役 | save/load/menuのcanonical UI語。 |
| origin | 出自 | `starting scenario`と混同しない。 |
| scenario | シナリオ | 固有scenario titleは別途監査。 |
| ambition | 野望 | campaign objective system。 |
| retinue | 随員 | individual followerは「随員」。 |
| roster | 団員一覧 | 人数枠は「団員枠」。 |
| stash | 保管庫 | inventoryと区別。 |
| inventory | 所持品 | 文脈により「装備欄」。 |
| crowns | クラウン | 通貨。文章で説明が必要な初出のみ「クラウン金貨」を許容。 |
| renown | 名声 | |
| provisions | 食糧 | item名は個別語を優先。 |
| tools and supplies | 工具と補修材 | armor/weapon repair resource。 |
| ammunition | 矢弾 | arrows/bolts/powderを包括。 |
| medicine | 医薬品 | |

## Character mechanics

| English | Canonical Japanese | Notes |
|---|---|---|
| hitpoints / health | 体力 | 数値labelは「体力」。`damage to hitpoints`は「体力へのダメージ」。 |
| action points | 行動力 | 初出以外の`AP`は数値UIで許容。 |
| fatigue | 疲労 | `maximum fatigue`は「最大疲労値」。 |
| initiative | 先制値 | turn order stat。 |
| resolve | 精神力 | moraleそのものと区別する。 |
| melee skill | 近接技能 | |
| ranged skill | 射撃技能 | |
| melee defense | 近接防御 | |
| ranged defense | 射撃防御 | |
| chance to hit / hitchance | 命中率 | |
| armor | 防具 / 装甲 | itemは「防具」、damage layer/valueは「装甲」。 |
| armor durability | 装甲耐久値 | |
| perk | パーク | proper perk nameはcategory tableで固定。 |
| skill | スキル | weapon actionは固有動作名を優先。 |
| trait | 特性 | |
| background | 経歴 | |
| injury | 負傷 | |
| permanent injury | 後遺症 | |
| status effect | 状態効果 | |
| morale | 士気 | `resolve`と混同しない。 |
| Zone of Control | 支配領域 | 初出tooltipで必要なら`（ZOC）`を併記。 |

## Combat and equipment

| English | Canonical Japanese |
|---|---|
| melee / ranged | 近接 / 遠隔 |
| damage | ダメージ |
| armor damage | 装甲ダメージ |
| damage ignores armor | 装甲を無視するダメージ |
| head hit | 頭部命中 |
| shieldwall | 盾壁 |
| spearwall | 槍衾 |
| stun | 気絶 |
| knock back | ノックバック |
| disarm | 武装解除 |
| bleeding | 出血 |
| poisoned | 毒 |
| weapon | 武器 |
| body armor | 胴防具 |
| helmet | 兜 |
| shield | 盾 |
| mail / mail armor | 鎖帷子 | 一般名・本文。既成の装備型名は`Mail Shirt`＝「メイルシャツ」、`Mail Coif`＝「メイルコイフ」、`Mail Hauberk`＝「メイルホーバーク」。 |
| lamellar | ラメラー | 複合装備型は「ラメラーアーマー」「ラメラーハーネス」。 |
| scale armor | スケイルアーマー | 生物の鱗そのものは「鱗」、金属scaleの構造説明は「鱗札」も使う。 |
| attachment | 付属品 |
| two-handed | 両手持ち |
| offhand | 逆手枠 |

## World, society, and economy

| English | Canonical Japanese | Notes |
|---|---|---|
| contract | 依頼 / 契約 | UI categoryは「依頼」。法的・交渉文脈は「契約」。 |
| employer | 依頼主 | noble固有titleを落とさない。 |
| settlement | 集落 | town/city/village/fortはactual typeに応じ訳し分ける。 |
| noble house | 貴族家 | 固有家名は音写監査。 |
| noble / nobleman / noblewoman | 貴族 | 日本語では通常、性別を表示語へ持ち込まない。固有titleがある場合はtitleを優先。 |
| official | 役人 | titleが判明する場合は「代官」「執政官」等を使う。 |
| commoner | 庶民 | |
| militia | 民兵 | |
| caravan | 隊商 | |
| brigand | 盗賊 | tier nameは別途固定。 |
| raider | 略奪者 | `Barbarian Raider`等はfaction categoryで監査。 |
| cult / cultist | 教団 / 教団員 | Davkul固有文脈では「ダヴクル教団」。 |

## Creatures and lore anchors

| English | Canonical Japanese | Notes |
|---|---|---|
| undead | 不死者 | tone上必要な場合のみ「アンデッド」。 |
| necromancer | 死霊術師 | |
| Wiederganger | ヴィーダーゲンガー | lore固有種。一般描写では「蘇った死者」。 |
| Ancient Dead | 古代の死者 | faction/system名。 |
| Orc / Goblin | オーク / ゴブリン | |
| Hexe / Hexen | ヘクセ / ヘクセン | singular/pluralをsourceどおり区別。 |
| Alp / Alps | アルプ / アルプ | 日本語本文では数で区別。 |
| Unhold | ウンホルト | |
| Schrat | シュラート | |
| Nachzehrer | ナハツェーラー | |
| Lindwurm | リントヴルム | |
| Gilder | ギルダー | 南方宗教の固有神名。職業名として訳さない。所有格は「ギルダーの～」。 |
| Ifrit | イフリート | |
| Serpent | サーペント | system固有enemy名。一般名詞なら「大蛇」。 |
| southern / northern | 南方 / 北方 | `South`固有政治圏は出現contextを監査。 |

## Provisional terms

### Legends Vala / occult skills

| English | 日本語 | 適用範囲・注記 |
|---|---|---|
| Vala | ヴァラ | 旅する予見者・巫女・女魔術師というLegends固有class。固有呼称として音写する。 |
| trance | トランス状態 | Vala関連skill/effect。文中では「トランス状態に入る」とする。 |
| Entrancer | 魅了術師 | background/class表示名。 |
| Choked (status) | 首絞め | effect/status表示。死亡原因を返す`KilledString`だけは「絞殺」とする。 |

Legends固有class、perk tree、magic、camp building、rune、enemy、named itemは未監査のままこの表へ固定しない。`Webknecht`等の造語はsource全出現とmechanicsを確認してから音写または意訳を決める。
