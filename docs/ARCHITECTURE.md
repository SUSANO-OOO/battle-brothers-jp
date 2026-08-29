# Architecture

Status: `VERTICAL_SLICE_STATIC_REACHABILITY_GREEN / RUNTIME_NOT_TESTED`

Target snapshot: `BBJP-CF88150E7B355ECD32D9`

## Decision

新MODはwhole-file replacementを行わず、以下の5層に分ける。

### A. Vanilla language/bootstrap

Rosetta `0.5.0`には`ja`定義があるが、actual source自身がJapanese autodetectionを「doesn't work」と記している。preloadでtranslation pairを登録した後、`::Rosetta.activate("ja")`を明示実行する。ゲーム設定、language file、本体archiveは変更しない。

### B. Squirrel translation

Rosetta `0.5.0`をexternal dependencyとして使う。Rosettaはitems、skills、actors、backgrounds、origins、events、contracts、tooltips、loading tips、combat results、template substitution、MSU settings等の実境界をhookする。特に`buildTextFromTemplate`の前で翻訳するため、`%name%`等のruntime tokenを翻訳前の形で保持できる。

翻訳データはmodule/category別の`.nut`へ生成し、`::Rosetta.add`で登録する。literal、stable ID、patternを区別する。Rosetta parserが扱えないsourceは未解決のまま黙殺せず、fallback抽出とreason付きexclusionへ送る。

### C. JavaScript/UI translation

Rosetta `0.5.0`はJS-origin stringsを処理しない。Modern Hooks `0.6.0`の`::Hooks.registerJS`をqueued function内で使い、vanilla/Legendsのscreenがinstantiateされる前に共通UI controlをwrapする。`$.fn.createTextButton`、`$.fn.createDialog`、`$.fn.createPopupDialog`に加え、exact-stringの`html`、`text`、`append` setterだけを翻訳する。getter、DOM object、未知文字列はそのまま通す。

actual call path監査でRosettaが到達しない境界が判明したため、whole-file replacementではなく限定的Squirrel hookを追加した。`ambition.getUIText()`、skillの`getKilledString()`、Legends camp crafting `queryLoad()`の`Title`/`SubTitle`、および4つのexact Legends perk classで完成後のtooltip textだけを処理する。Adaptiveの列挙は固定prefixとcolor境界内のgroup名だけを再構成し、metric wrapperは計算済みcolor値をbyte-for-byte保持する。いずれもgameplay state、数値、id/type/icon、save dataを変更しない。

reviewed literalはignored canonical ledgerからdeterministic generatorでSquirrel/JS mapへ出力する。同じ英語が異なる意味を持つ場合はcontext unitへ分割し、global mapで安全な文脈だけを登録する。残りはexact translation-only boundaryを使う。既存Vanilla/Legends JS全体の差替えは行わない。internal ID、CSS class、HTML scaffoldは翻訳対象外である。

Rosetta extractorの`mode=pattern`に現れる`<this.m.Name>`等はsource-expression hintであり、有効なruntime captureではない。独立review済みであっても、`<name:str>`等の有効patternと代表sample、または狭いboundary hookが確定するまで生成物へ出さない。現在の127 reviewed pattern unitはすべてこの監査を通過した。さらにRosetta `0.5.0`は最初に一致したruleを採用するため、全代表sampleを全登録ruleの`matchParts()`へ通し「実効matchがexactly 1」であることを生成ハーネスで検査する。

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

preloadは`mod_battle_brothers_jp`としてregisterする。translation/UI registrationは`mod_rosetta`、`mod_msu`、`mod_legends`より後にqueueする。一方、Rosetta自身はMSU前のearly hooksとMSU後のLate hooksを別々に登録済みである。このMODはRosettaの一般hookを再実装せず、actual sourceで未到達またはglobal pattern collisionが避けられないと確認したdisplay-string境界だけを補完する。

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

Squirrel 3 filesは`Squirrel 3.0.7` compilerでsyntax green、JSはbundled Nodeの`--check`とwrapper unit testでgreen。runtime未実施のため、end-to-end成立や表示品質をPASSとはしない。
