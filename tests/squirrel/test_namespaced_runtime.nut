::Rosetta <- {active = "fr", sentinel = 17, translate = function (_value) { return _value; }};
::std <- {sentinel = 23, Str = {name = "external"}};
local rosettaSentinel = ::Rosetta;
local stdSentinel = ::std;
local rosettaTranslate = ::Rosetta.translate;
local stdStr = ::std.Str;
::BattleBrothersJP <- {};
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/runtime/core.nut", true);
local firstRuntime = ::BattleBrothersJP.Runtime;
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/runtime/core.nut", true);
if (::BattleBrothersJP.Runtime != firstRuntime) throw "runtime initialization is not idempotent";

local Runtime = ::BattleBrothersJP.Runtime;
local pairs = [
    { en = "Exact", ja = "完全一致" },
    { en = "one turn", ja = "1ターン" },
    { en = "<b>HTML</b>", ja = "<b>HTML訳</b>" },
    { mode = "pattern", anchor = "apples", en = "<n:int> apples", ja = "<n>個のリンゴ",
      parts = [{name = "n", sub = "int"}, " apples"],
      replacement = [{name = "n", flags = null}, "個のリンゴ"] },
    { mode = "pattern", anchor = "begin", en = "begin <x:str> Z", ja = "開始<x>終",
      parts = ["begin ", {name = "x", sub = "str"}, " Z"],
      replacement = ["開始", {name = "x", flags = null}, "終"] },
    { mode = "pattern", anchor = "damage", en = "<v:val_tag> Damage", ja = "<v> ダメージ",
      parts = [{name = "v", sub = "val_tag"}, " Damage"],
      replacement = [{name = "v", flags = null}, " ダメージ"] },
    { mode = "pattern", anchor = "dazed", en = "Dazed for <d:str>", ja = "<d:t>の間、朦朧",
      parts = ["Dazed for ", {name = "d", sub = "str"}],
      replacement = [{name = "d", flags = "t"}, "の間、朦朧"] },
    { mode = "pattern", anchor = "end", en = "<x:str> end", ja = "末尾<x>",
      parts = [{name = "x", sub = "str"}, " end"],
      replacement = ["末尾", {name = "x", flags = null}] },
    { mode = "pattern", anchor = "start", en = "start <y:str>", ja = "先頭<y>",
      parts = ["start ", {name = "y", sub = "str"}],
      replacement = ["先頭", {name = "y", flags = null}] }
];
Runtime.add({ module = "test", version = "1" }, pairs);
Runtime.add({ module = "test", version = "1" }, pairs);

function assertEqual(_actual, _expected, _label)
{
    if (_actual != _expected)
        throw _label + " expected '" + _expected + "', got '" + _actual + "'";
}

assertEqual(Runtime.translate("Exact"), "完全一致", "exact");
assertEqual(Runtime.translate("12 apples"), "12個のリンゴ", "int pattern");
assertEqual(Runtime.translate("begin middle Z"), "開始middle終", "str pattern");
assertEqual(Runtime.translate("[color=#fff]12.5%[/color] Damage"),
    "[color=#fff]12.5%[/color] ダメージ", "tag pattern");
assertEqual(Runtime.translate("Dazed for one turn"), "1ターンの間、朦朧", "recursive :t");
assertEqual(Runtime.translate("<b>HTML</b>"), "<b>HTML訳</b>", "HTML exact");
assertEqual(Runtime.translate("Unknown"), "Unknown", "unknown pass-through");
assertEqual(Runtime.translate("start end"), "start end", "ambiguous pass-through");
assertEqual(Runtime.translate("日本語 Exact"), "日本語 Exact", "mixed unknown pass-through");
assertEqual(Runtime.translate(""), "", "empty pass-through");
if (Runtime.translate(null) != null) throw "null pass-through";
local tableValue = { value = "Exact" };
local arrayValue = ["Exact"];
if (Runtime.translate(tableValue) != tableValue) throw "table pass-through";
if (Runtime.translate(arrayValue) != arrayValue) throw "array pass-through";

local longValue = "";
for (local i = 0; i < 70000; i++) longValue += "x";
if (Runtime.translate(longValue) != longValue) throw "long input pass-through";

assertEqual(Runtime.Str.replace("a-b-a", "a", "x"), "x-b-x", "replace helper");
assertEqual(Runtime.Str.join("、", Runtime.Str.split(", ", "a, b, c")), "a、b、c", "split/join helper");
if (!Runtime.Str.startsWith("prefix", "pre") || !Runtime.Str.endsWith("suffix", "fix"))
    throw "prefix/suffix helper";
assertEqual(Runtime.Str.cutSuffix("name Play", " Play"), "name", "cut suffix helper");

Runtime.add({ module = "test", version = "2" }, [{ en = "Exact", ja = "衝突" }]);
assertEqual(Runtime.translate("Exact"), "完全一致", "mismatched profile fail-closed");
assertEqual(Runtime.Profiles.test, "1", "accepted profile preserved");
assertEqual(Runtime.Diagnostics.len(), 1, "profile mismatch diagnostic count");
assertEqual(Runtime.Diagnostics[0].code, "PROFILE_VERSION_MISMATCH", "profile mismatch diagnostic");

// Profile registration is atomic: an invalid/conflicting later row leaves no
// accepted profile, exact entry, pattern output, rule key, or rule-id advance.
local beforeRuleID = Runtime.NextRuleID;
local invalidAtomicCaught = false;
try
{
    Runtime.add({ module = "invalid_atomic", version = "1" }, [
        { en = "Should Not Commit", ja = "登録禁止" },
        { en = "Broken", ja = "" }
    ]);
}
catch (error) { invalidAtomicCaught = true; }
if (!invalidAtomicCaught) throw "invalid atomic profile was accepted";
if ("invalid_atomic" in Runtime.Profiles || "Should Not Commit" in Runtime.Exact)
    throw "invalid profile was partially committed";
assertEqual(Runtime.NextRuleID, beforeRuleID, "invalid profile rule id unchanged");

local conflictAtomicCaught = false;
try
{
    Runtime.add({ module = "conflict_atomic", version = "1" }, [
        { en = "Another Should Not Commit", ja = "登録禁止2" },
        { en = "Exact", ja = "競合" }
    ]);
}
catch (error) { conflictAtomicCaught = true; }
if (!conflictAtomicCaught) throw "conflicting atomic profile was accepted";
if ("conflict_atomic" in Runtime.Profiles || "Another Should Not Commit" in Runtime.Exact)
    throw "conflicting profile was partially committed";

local deepParts = [];
for (local i = 0; i < Runtime.MaxPatternParts + 1; i++) deepParts.push("x");
if (Runtime.matchParts("x", deepParts) != null) throw "oversized pattern was not rejected";
if (Runtime.matchParts("x", [{name = "x", sub = "unknown"}]) != null)
    throw "unknown capture type was not rejected";
local pathologicalParts = [
    "begin ", {name = "first", sub = "str"}, " X ",
    {name = "second", sub = "str"}, " end"
];
if (Runtime.matchParts("begin a X b end", pathologicalParts) != null)
    throw "multiple unbounded string captures were not rejected by matcher";
local pathologicalAtomicCaught = false;
try
{
    Runtime.add({ module = "pathological_atomic", version = "1" }, [{
        mode = "pattern", anchor = "begin", en = "begin <first:str> X <second:str> end",
        ja = "<first><second>", parts = pathologicalParts,
        replacement = [{name = "first", flags = null}, {name = "second", flags = null}]
    }]);
}
catch (error) { pathologicalAtomicCaught = true; }
if (!pathologicalAtomicCaught || "pathological_atomic" in Runtime.Profiles)
    throw "multiple unbounded string capture profile was accepted";
assertEqual(Runtime.NextRuleID, beforeRuleID, "pathological profile rule id unchanged");

if (::Rosetta != rosettaSentinel || ::Rosetta.active != "fr"
    || ::Rosetta.sentinel != 17 || ::Rosetta.translate != rosettaTranslate)
    throw "external Rosetta namespace was mutated";
if (::std != stdSentinel || ::std.sentinel != 23 || ::std.Str != stdStr
    || ::std.Str.name != "external")
    throw "external std namespace was mutated";

print("NAMESPACED_RUNTIME_TEST_OK\n");
