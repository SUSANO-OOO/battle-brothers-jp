// Risk-based composition harness: an unknown MOD may wrap the same display
// target before or after JP. The chain must remain intact and original executes
// exactly once in either order.
local hookFactories = {};
local methodShapes = {
    ["scripts/items/item"] = ["getDescription"],
    ["scripts/skills/skill"] = ["getName", "getDescription"],
    ["scripts/entity/tactical/entity"] = ["getDescription"],
    ["scripts/scenarios/world/starting_scenario"] = ["getName", "getDescription"],
    ["scripts/scenarios/scenario_manager"] = ["getScenariosForUI"],
    ["scripts/ui/screens/tactical/modules/topbar/tactical_screen_topbar_event_log"] = ["log", "logEx"],
    ["scripts/ui/screens/dialog_screen"] = ["show"],
    ["scripts/ui/screens/tactical/tactical_combat_result_screen"] = ["onQueryCombatInformation"],
    ["scripts/ui/screens/loading/loading_screen"] = ["onQueryData"],
    ["scripts/ui/screens/tooltip/tooltip_events"] = [
        "onQueryTileTooltipData", "onQueryEntityTooltipData", "onQueryRosterEntityTooltipData",
        "onQuerySkillTooltipData", "onQueryStatusEffectTooltipData",
        "onQuerySettlementStatusEffectTooltipData", "onQueryUIElementTooltipData",
        "onQueryUIItemTooltipData", "onQueryUIPerkTooltipData", "onQueryFollowerTooltipData"
    ],
    ["scripts/events/event"] = ["getUIList", "getUIButtons"],
    ["scripts/contracts/contract"] = ["getUITitle", "getUIList"]
};

local function registerHook(_target, _callback)
{
    local q = {};
    foreach (method in methodShapes[_target]) q[method] <- null;
    _callback(q);
    hookFactories[_target] <- q;
}

local legacySentinel = {Version = "21.1", Calls = 0};
::mod_hooks <- legacySentinel;
::BattleBrothersJP <- {
    Runtime = {
        translate = function (_value) { return _value == "Tooltip" ? "ツールチップ" : _value; }
    },
    Mod = {hook = registerHook, hookTree = registerHook}
};
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut", true);
if (::mod_hooks != legacySentinel) throw "legacy mod_hooks namespace changed";

function assertEqual(_actual, _expected, _label)
{
    if (_actual != _expected) throw _label + " expected '" + _expected + "', got '" + _actual + "'";
}

local function unknownWrapper(_original, _counter)
{
    return function (...)
    {
        _counter.Calls += 1;
        local args = [this];
        args.extend(vargv);
        return _original.acall(args);
    };
}

local jpFactory = hookFactories["scripts/ui/screens/tooltip/tooltip_events"].onQuerySkillTooltipData;

local beforeOriginalCalls = 0;
local beforeSource = [{id = 1, text = "Tooltip"}];
local beforeOriginal = function (...) { beforeOriginalCalls += 1; return beforeSource; };
local unknownBeforeCalls = {Calls = 0};
local jpAfterUnknown = jpFactory(unknownWrapper(beforeOriginal, unknownBeforeCalls));
local beforeResult = jpAfterUnknown("entity", "skill");
assertEqual(beforeOriginalCalls, 1, "unknown-before original once");
assertEqual(unknownBeforeCalls.Calls, 1, "unknown-before wrapper once");
assertEqual(beforeResult[0].text, "ツールチップ", "unknown-before translated result");
assertEqual(beforeSource[0].text, "Tooltip", "unknown-before source immutable");

local afterOriginalCalls = 0;
local afterSource = [{id = 1, text = "Tooltip"}];
local afterOriginal = function (...) { afterOriginalCalls += 1; return afterSource; };
local unknownAfterCalls = {Calls = 0};
local unknownAfterJP = unknownWrapper(jpFactory(afterOriginal), unknownAfterCalls);
local afterResult = unknownAfterJP("entity", "skill");
assertEqual(afterOriginalCalls, 1, "unknown-after original once");
assertEqual(unknownAfterCalls.Calls, 1, "unknown-after wrapper once");
assertEqual(afterResult[0].text, "ツールチップ", "unknown-after translated result");
assertEqual(afterSource[0].text, "Tooltip", "unknown-after source immutable");

local exceptionCalls = 0;
local exceptionOriginal = function (...) { exceptionCalls += 1; throw "UNKNOWN_CHAIN_ORIGINAL_FAILURE"; };
local exceptionChain = unknownWrapper(jpFactory(exceptionOriginal), {Calls = 0});
local caught = false;
try { exceptionChain("entity", "skill"); }
catch (error) { caught = error == "UNKNOWN_CHAIN_ORIGINAL_FAILURE"; }
if (!caught) throw "composition suppressed original exception";
assertEqual(exceptionCalls, 1, "composition failing original once");

print("RUNTIME_COMPOSITION_TEST_OK\n");
