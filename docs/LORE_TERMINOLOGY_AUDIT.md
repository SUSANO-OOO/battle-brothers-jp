# Lore and Terminology Audit

Status: `FOUNDATION COMPLETE / CATEGORY PASSES PENDING`

Target snapshot: `BBJP-CF88150E7B355ECD32D9`

## Foundation decisions

- `company`は「傭兵団」、`brother`は通常「団員」。同じ語へ潰さない。
- `resolve`は「精神力」、`morale`は「士気」。mechanics上別物として保持する。
- `armor`はitemとして「防具」、damage layer/valueとして「装甲」。
- `contract`はUI categoryで「依頼」、法的・交渉文脈で「契約」。
- creature/faction proper nounsは安易な一般名詞化を避け、Wiederganger等はlore固有音写を採用する。
- `origin`は「出自」、`background`は「経歴」。campaign ruleとcharacter historyを区別する。

## Required category audit passes

| Category | Primary risk | Gate |
|---|---|---|
| Perks | 数値、stack、exception、skill unlock | 全descriptionをactual mechanicsと照合 |
| Skills | AP/fatigue/range/hit/damage/targeting | active implementationとtooltip一致 |
| Injuries/status | duration、body part、mechanical penalty | effect codeと名称一致 |
| Contracts | payment、objective、failure、choice consequence | state/screen transitionを保持 |
| Events | actor、choice、result、template variable | 全placeholder/variant保持 |
| Origins | roster/economy/rule exceptions | starting_scenario codeと照合 |
| Factions/religion | lore、階級、固有名 | 同一term全出現監査 |
| Named/legendary content | 固有名、来歴、既存一般itemとの区別 | name/description一対でreview |
| Legends class/perk/magic | Vanillaとの用語衝突 | Legends actual tree/mechanicsから命名 |
| Dynamic patterns | overmatch/undermatch/collision | representative samples + negative cases |

## Current audit result

Vertical Slice 7 Squirrel pairと12 JS UI labelについて、独立reviewで`company`の訳語不一致と不自然な「網技」を検出し、「傭兵団」「投網の技術」へ修正した。再reviewは19/19完了し、Squirrel compiler、Rosetta literal/placeholder harness、JS wrapper unit test、19件のstatic reachability、placeholder static QAはgreenである。

第一翻訳trancheでは、core UI 94件、Legends mechanics 91件、Vanilla mechanics 200件を独立reviewした。`Play`と`General`は一律訳で意味が衝突するためcontext unitへ分割した。dynamic pattern 127件は訳文reviewとruntime成立を分離し、raw extractor hintを生成物から遮断した状態で専用監査中である。game runtimeと表示は未実施なので、category audit完了またはRUNTIME_VERIFIEDとはしない。
