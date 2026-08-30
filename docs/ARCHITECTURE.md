# Architecture

Status: `VERTICAL_SLICE_STATIC_REACHABILITY_GREEN / RUNTIME_NOT_TESTED`

Target snapshot: `BBJP-CF88150E7B355ECD32D9`

## Decision

新MODはwhole-file replacementを行わず、以下の5層に分ける。

### A. Vanilla language/bootstrap

Rosetta `0.5.0`には`ja`定義があるが、actual source自身がJapanese autodetectionを「doesn't work」と記している。preloadでtranslation pairを登録した後、`::Rosetta.activate("ja")`を明示実行する。ゲーム設定、language file、本体archiveは変更しない。

### B. Squirrel translation

Rosetta `0.5.0`をexternal dependencyとして使う。Rosettaはitems、skills、actors、backgrounds、origins、events、contracts、tooltips、loading tips、combat results、template substitution、MSU settings等の実境界をhookする。特に`buildTextFromTemplate`の前で翻訳するため、`%name%`等のruntime tokenを翻訳前の形で保持できる。

ただしactual Rosetta sourceはitem `getName()`、background `getNameOnly()`、world entity `getName()`を表示境界より前に翻訳する。独立した全consumer監査では、installed Legends `perk_legend_specialist_poacher`が`"Piercing"` / `"Broad Head"`を検索してdamage/effectを分岐し、Donkey backgroundがliteral equalityでtooltip branchを選び、Beggar originがsettlement nameをflagへ保存して後で`getName()`一致検索することを確認した。Vanilla/Legendsのunique world-name生成もraw候補と`getName()`を比較し、派生party名はgetter結果から保存名を作る。よってglobal name getter翻訳はcurrent snapshotへ無条件適用できない。

日本語化MODはRosettaと同じLate bucketでRosettaより後にwrapperを登録する。itemはPoacherの2 methodに加え、item表示名をspawned tactical dogのidentityへコピーする`unleash_wardog.onUse`、`wardog_item.onActorDied`、`legend_accessory_dog.onActorDied`だけsemantic scopeを開く。backgroundはDonkey判定の1 methodだけをscope化し、その中のgetter呼出しに限ってRosettaのactive languageを`null`へ退避する。これにより通常のinventory/tooltip表示は翻訳を保ちながら、damage/effect、Donkey branch、raw item/dog identityにはsource Englishを渡す。通常終了・例外の両方でlanguageとscopeを復元する。

world `getName()`はsave flag、contract objective、faction/party name、unique-name比較などconsumerが広範で将来も開放的なため、getter全体をsource-languageに固定する。world-map labelは`updateStrength`、deserialize、location/party initializerの完了後に表示文字列だけ翻訳し、settlement `getUIInformation()`はJS DTOの`Title`/`SubTitle`だけを翻訳する。template変数は後述のclone上で翻訳する。tooltip、event log、event/contract list等はRosetta既存の完成後boundaryを使う。`m.Name`、PronounTable、ID、save値、matcher、damage値、item stateは変更しない。

tactical actorの`getName()` / `getNameOnly()` / `getTitle()` / `getKilledName()`も、contract flag、mood history、named item、corpse/resurrection identity、Fallen/obituary、saveへ流れるopen-ended semantic surfaceを持つためglobal source-languageに固定する。日本語は`data_helper`のactor DTO、Legends roster DTO、obituary clone、corpse-stub display getterなどactor provenanceが実証された最終表示で復元する。source contextが`Const.Strings.*Titles`、actor/background/trait title配列・setter等と確認でき、独立review済みのliteralだけをSquirrel/JS共通のfull actor-title registryへ生成する。一般event/template/JS表示ではfull registryを使わず、`ACTOR_TITLE_DISPLAY_FRAGMENT`として個別に境界監査したgeneric-safe subsetだけを使う。itemはactor-derived possessive形（title直後がapostrophe）のみfull registryを許可し、tile tooltipは`id=3`、`type=description`、末尾` was slain here.`のcorpse-name形だけに限定する。broad skill/item tooltip fragment hookは置かない。prefix重複を避けるためEnglish length降順（同長lexicographic）で固定し、full/generic両registryについてSquirrel/JS完全一致・重複・順序・generic⊂full・manifest件数をQAする。`Dame`のような専用`ROSETTA_PATTERN`はbare fragmentへ入れず、Squirrel display boundaryで完全文字列をRosettaへ通してからliteral fragmentを処理する。`The Lone Wolf`と`Weeds`はglobal literalへ出さず、raw identity否定fixtureと`Old Gods` / `Holy Mother`衝突fixtureを通過したgeneric-safe opt-inとして登録する。

Rosettaは`buildTextFromTemplate`へ渡すraw templateを先に翻訳するため、後から挿入する変数値には通常literal ruleが届かない。ここはcallerの`_vars`を変更せず各pairをcloneし、一般のstring値を最終rendering用にRosettaへ通す。これによりworld getterをrawに保ってもsettlement/item/skill/faction名をtemplate内だけ翻訳できる。その上でexact `noble` / `sibling` / `sib`、`justbeggar`、`nemesisS`のkey/valueだけはcontext固有訳を適用する。current snapshotで実きょうだいを指すdisowned-noble templateはraw templateの固有句で分岐する。語呂合わせを含むteamplayer等の全文は別の翻訳unitとしてreviewし、単語global replacementは行わない。

Legendsイベントの`PronounTable`は単純なliteral辞書として扱わない。installed sourceに存在するsubject/object/possessive/reflexive/person/child/to-beのfamilyとvalueをexact allowlistし、表示用にcloneしたtemplate変数だけを日本語へ写像する。既知familyに未知valueが来た場合もRosetta general translationへ流さずrawのままfail closedとする。これによりcaller配列、PronounTable、actor、event state、ID、save dataは不変である。死亡原因`KilledBy`も同様に、review済み6 literalだけを`world_obituary_screen.convertFallenToUIData`の返却DTO cloneで翻訳し、World.Statisticsと保存値は変更しない。

翻訳データはmodule/category別の`.nut`へ生成し、`::Rosetta.add`で登録する。literal、stable ID、patternを区別する。Rosetta parserが扱えないsourceは未解決のまま黙殺せず、fallback抽出とreason付きexclusionへ送る。

### C. JavaScript/UI translation

Rosetta `0.5.0`はJS-origin stringsを処理しない。Modern Hooks `0.6.0`の`::Hooks.registerJS`をqueued function内で使い、vanilla/Legendsのscreenがinstantiateされる前に共通UI controlをwrapする。`$.fn.createTextButton`、`$.fn.createDialog`、`$.fn.createPopupDialog`に加え、exact-stringの`html`、`text`、`append` setterだけを翻訳する。getter、DOM object、未知文字列はそのまま通す。

actual call path監査でRosettaが到達しない境界が判明したため、whole-file replacementではなく限定的Squirrel hookを追加した。`ambition.getUIText()`、obituaryの返却DTO `KilledBy`、contract baseの`getDescription()`、Legends camp crafting `queryLoad()`、settlement `getUIInformation()`の表示field、port buildingの独立travel-roster DTO、named armor/helmetの`getName()`戻り値、および4つのexact Legends perk classで完成後のtextだけを処理する。`skill.getKilledString()`はWorld.Statisticsへ保存されるためsource-languageのまま保持し、obituary画面へ返すcloneだけを翻訳する。contract descriptionはLegendsが選択済みtemplateを保存した`m.Description`へ書き戻さず、getterのstring返却値だけを訳す。installed call site 4件はすべてDTO/tooltip表示であり、original 1回、state・flags・serialization・save不変をharnessで固定した。港はraw settlement nameを先に捕捉し、返却DTOの`Name`とexact一致する`ListName`だけを翻訳する。`ID`、cost、image、route、settlement object、raw identityは変更せず、`BackgroundText`はraw description prefixだけを訳して既にrender済みのsuffixをbyte-for-byte保持する。Adaptiveの列挙は固定prefixとcolor境界内のgroup名だけを再構成し、metric wrapperは計算済みcolor値をbyte-for-byte保持する。`Play`の文脈訳も定数配列やpersisted `m.Name`ではなく戻り値のsuffixだけを変換する。いずれもgameplay state、数値、id/type/icon、save dataを変更しない。

Legends contractの残余境界は、open contract titleの返却DTO field、arena contractの返却description entry、return-item description、faction relation tooltipへ分離した。return-itemはraw `Flags.Item`のcolorized markerがexactly oneで、review済み`%s` templateとitem訳の両方が存在する場合だけclone上で再構成する。relation tooltipはactual `world-relations-screen.Relations` element ID、entry id/type/polarity icon、4 exact prefix、class別28/11 item allowlistをすべて満たす場合だけentry cloneを訳す。contract name、Flags、relation history、serialized state、saveはrawのまま保持し、malformed/未知入力は原返却値へfail closedする。

installed Legends `legend_ranger_commander_background`には`%name's face`と`h%name%`という2つのplayer-facing source typoがある。canonical翻訳はsource signatureを保持し、同じLate bucketでRosettaより後に登録するexact-class `hookTree`を外側wrapperにして、Rosetta返却templateだけを`%name%の顔` / `%name%`へ正規化する。通常のexact `hook`はModern Hooksのfinalization順でRosetta tree hookの内側になるため採用しない。合成fixtureでsource → Rosetta inner → JP remediation outer、inner 1回、unrelated/non-string不変を検証する。

Vanilla `kraken_cult_enter_event` B1には、variantを閉じる`}`の後に余分な`}`が1個ある。exact event classのinherited `buildText`だけをModern Hooksでwrapし、installed English prefixとsuffixが同時一致した入力に限ってnative/Rosetta後の最終返却値を検査する。raw `}`が末尾に残る場合だけ1文字除き、source screen、reply flag、option result、event state、saveには書き戻さない。malformed composition、正常なbalanced source、無関係option、already-clean、non-stringのfixtureを分離する。

reviewed literalはignored canonical ledgerからdeterministic generatorでSquirrel/JS mapへ出力する。同じ英語が異なる意味を持つ場合はcontext unitへ分割し、global mapで安全な文脈だけを登録する。残りはexact translation-only boundaryを使う。既存Vanilla/Legends JS全体の差替えは行わない。internal ID、CSS class、HTML scaffoldは翻訳対象外である。

resolved exclusionはoccurrence-level source auditを先に行い、unit全stable keyが同じ非表示semanticsである場合だけwhole-unit除外できる。player-facingとmachine keyが同一unitへdeduplicateされた場合は、machine key occurrenceと未翻訳player-facing occurrenceへ先にcontext分割する。canonical QAは全translatable occurrenceがexactly one unitに属し、除外occurrenceがunitに属さないことを検証する。

Rosetta extractorの`mode=pattern`に現れる`<this.m.Name>`等はsource-expression hintであり、有効なruntime captureではない。独立review済みであっても、`<name:str>`等の有効patternと代表sample、または狭いboundary hookが確定するまで生成物へ出さない。現在の127 reviewed pattern unitはすべてこの監査を通過した。さらにRosetta `0.5.0`は最初に一致したruleを採用するため、全代表sampleを全登録ruleの`matchParts()`へ通し「実効matchがexactly 1」であることを生成ハーネスで検査する。

source Englishそのものをpatternの左辺として使う特殊契約（例: bare `Dame`をgenerated nameだけに届かせる契約）は、captureを最低1個要求し、runtime sampleがsource Englishと同一なら生成・適用を拒否する。現契約は`Dame <first:word><rest:str>`だけを`デイム・<first><rest>`へ変換し、bare `Dame`、`Dame `、`Madame Roderick`は不変である。

### D. Font/rendering

UI CSSからactual font pathが`coui://gfx/fonts/...`で参照されることを確認した。Modern Hooks `::Hooks.registerCSS`でOFL 1.1の静的`NotoSansCJKjp-Regular.otf`を登録し、既存text/title/description classのfont-familyだけをoverrideする。

- Upstream: `notofonts/noto-cjk`
- Version: `2.004`
- SHA-256: `68A3FC98800B2A27B371F2FB79991DAF3633BD89309D4FFAA6946FD587F375B5`
- Unicode cmap: 44,810 code points
- CJK Unified Ideographs: 20,976 / 20,992 code points

existing Japanese MODのfont/assetは使用していない。現時点のglyph検査はstaticであり、Coherent UIでのrender、line-wrap、clippingはruntime未確認である。

### E. Current/optional MOD compatibility

current release targetはVanilla `1.5.2-3`、Legends `19.4.20`、Legends Assets `19.4.3`、MSU `1.9.0`へexact pinする。sourceが変わった状態で古い翻訳を黙ってloadさせないためである。Modern Hooksは`>=0.6.0`、Rosettaは`=0.5.0`、stdlibは`>=2.5`を要求する。

future MODはdependency graphへrequirement/incompatibility/queue/hook targetを追加してから、独立translation moduleを追加する。optional targetが無い状態でclass hookを直接要求しない。

## Queue design

preloadは`mod_battle_brothers_jp`としてregisterする。Rosettaの主getter/template hookは`QueueBucket.Late`で登録されるため、このMODも必ず同じLate bucketを指定し、そのbucket内で`>mod_rosetta`、`>mod_msu`、`>mod_legends`とする。requirementとqueue relationは別に記述する。このMODはRosettaの一般hookを再実装せず、actual sourceで未到達またはglobal pattern collisionが避けられないと確認したdisplay-string境界だけを補完する。

semantic-name safetyはRosettaのitem/background/world hookより後に登録するcompatibility guardである。専用Squirrel harnessは、通常item/background表示の日本語化、semantic scope内の`Broad Head` matcher/Donkey equality、3つのdog consumerへのraw item名コピー、source item/dog identity不変、global world raw identity、map labelのみの表示翻訳、成功・例外時のactive language/scope復元を検証する。event-variable harnessはcaller-owned array不変、一般変数値の表示翻訳、ordinary sibling、disowned-noble kinship、sib/noble、exact beggar/nemesis branches、portの`destname` clone-only翻訳を検証する。UI harnessはcontract descriptionのoriginal 1回とraw state不変、6件のobituary returned-DTO clone、および港DTOのraw source identity、non-display field、malformed inputを検証し、source-defect harnessはRosettaとのtree-hook合成順を検証する。`getMoodChanges()`等のraw semantic getterは翻訳しない。installed event codeがEnglish mood reasonをgameplay discriminatorとして比較するため、履歴文は保存値ではなく既存の最終tooltip境界でのみ翻訳する。runtime game QAは未実施である。

## Vertical Slice evidence

実装済み境界:

- Vanilla Squirrel literal
- `%dragonslayer%` dynamic placeholder
- Legends Squirrel UI/item text
- bundled Jimmy's Tooltips setting text
- JS-origin main-menu/button/dialog/popup text
- Japanese OTF font CSS registration
- optional MOD objectを定義しないtranslation-registration harness
- 19登録語すべてのsource call pathとtranslation boundaryを記録した`reports/vertical-slice-reachability.json`
- exact allowlistされたtranslation-only UI boundary hookと、値・metadata不変を検証する専用Squirrel harness
- Rosetta item/background/world name hookを隔離し、名称依存gameplay・identity・persistence consumerを元入力のまま保つsemantic-name safety harness
- post-template Legends表示変数をclone上だけで翻訳し、caller dataとinternal keyを不変に保つevent-variable boundary harness

Squirrel 3 filesは`Squirrel 3.0.7` compilerでsyntax green、JSはbundled Nodeの`--check`とwrapper unit testでgreen。runtime未実施のため、end-to-end成立や表示品質をPASSとはしない。
