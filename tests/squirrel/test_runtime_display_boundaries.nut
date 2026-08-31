local hooks = {};
local registrations = 0;
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
    registrations += 1;
    local q = {};
    foreach (method in methodShapes[_target]) q[method] <- null;
    _callback(q);
    hooks[_target] <- q;
}

::BattleBrothersJP <- {
    Runtime = {
        ThrowOn = null,
        translate = function (_value) {
            if (_value == this.ThrowOn) throw "JP_FAILURE";
            if (typeof _value != "string") return _value;
            local pairs = {
                Name = "名前", Description = "説明", Title = "題名", Subtitle = "副題",
                Tooltip = "ツールチップ", Item = "項目", Button = "ボタン"
            };
            return _value in pairs ? pairs[_value] : _value;
        }
    },
    Mod = { hook = registerHook, hookTree = registerHook }
};

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut", true);
local registrationCount = registrations;
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut", true);
if (registrations != registrationCount) throw "runtime display boundaries initialized twice";

function assertEqual(_actual, _expected, _label)
{
    if (_actual != _expected) throw _label + " expected '" + _expected + "', got '" + _actual + "'";
}

local skillOriginalCalls = 0;
local skillName = hooks["scripts/skills/skill"].getName(function () {
    skillOriginalCalls += 1;
    return "Name";
});
assertEqual(skillName(), "Name", "skill getter raw outside display scope");
assertEqual(skillOriginalCalls, 1, "skill original once");

local tooltipOriginal = [
    {id = 1, text = "Tooltip", value = 7},
    {id = 2, text = "Unknown"},
    "opaque"
];
local tooltipCalls = 0;
local tooltipScopedName = null;
local tooltip = hooks["scripts/ui/screens/tooltip/tooltip_events"].onQuerySkillTooltipData(
    function (_entity, _skill) {
        tooltipCalls += 1;
        tooltipScopedName = skillName();
        return tooltipOriginal;
    }
);
local tooltipResult = tooltip("entity", "skill");
assertEqual(tooltipScopedName, "名前", "skill getter translated inside tooltip scope");
assertEqual(tooltipResult[0].text, "ツールチップ", "tooltip text");
assertEqual(tooltipOriginal[0].text, "Tooltip", "tooltip source immutable");
if (tooltipResult == tooltipOriginal || tooltipResult[0] == tooltipOriginal[0])
    throw "tooltip result was not cloned";
assertEqual(tooltipCalls, 1, "tooltip original once");

::BattleBrothersJP.Runtime.ThrowOn = "Tooltip";
local failedTooltip = tooltip("entity", "skill");
if (failedTooltip != tooltipOriginal) throw "JP failure did not return original tooltip reference";
assertEqual(tooltipCalls, 2, "tooltip JP failure original once");
::BattleBrothersJP.Runtime.ThrowOn = null;

local scenarioName = hooks["scripts/scenarios/world/starting_scenario"].getName(
    function () { return "Name"; }
);
assertEqual(scenarioName(), "Name", "scenario getter raw outside UI scope");
local scenarioManager = hooks["scripts/scenarios/scenario_manager"].getScenariosForUI(
    function () { return [{Name = scenarioName(), Description = "Description"}]; }
);
local scenarios = scenarioManager();
assertEqual(scenarios[0].Name, "名前", "scenario getter translated in finite UI producer");
assertEqual(::BattleBrothersJP.DisplayGetterScopeDepth, 0, "scenario display scope restored");

local originalExceptionCaught = false;
local failingTooltip = hooks["scripts/ui/screens/tooltip/tooltip_events"].onQueryEntityTooltipData(
    function (...) { throw "ORIGINAL_TOOLTIP_FAILURE"; }
);
try { failingTooltip(); }
catch (error) { originalExceptionCaught = error == "ORIGINAL_TOOLTIP_FAILURE"; }
if (!originalExceptionCaught) throw "original tooltip exception was suppressed";
assertEqual(::BattleBrothersJP.DisplayGetterScopeDepth, 0, "tooltip exception scope restored");

local dialogCalls = 0;
local dialogArgs = null;
local dialog = hooks["scripts/ui/screens/dialog_screen"].show(
    function (_title, _text, _done, _ok, _cancel, _monologue) {
        dialogCalls += 1;
        dialogArgs = [_title, _text, _done, _ok, _cancel, _monologue];
        return 17;
    }
);
assertEqual(dialog("Title", "Description", "done"), 17, "dialog return");
assertEqual(dialogArgs[0], "題名", "dialog title");
assertEqual(dialogArgs[1], "説明", "dialog text");
assertEqual(dialogCalls, 1, "dialog original once");

local combatOriginal = {title = "Title", subTitle = "Subtitle", score = 9};
local combatCalls = 0;
local combat = hooks["scripts/ui/screens/tactical/tactical_combat_result_screen"].onQueryCombatInformation(
    function () { combatCalls += 1; return combatOriginal; }
);
local combatResult = combat();
assertEqual(combatResult.title, "題名", "combat title");
assertEqual(combatResult.subTitle, "副題", "combat subtitle");
assertEqual(combatOriginal.title, "Title", "combat source immutable");
assertEqual(combatCalls, 1, "combat original once");

local listOriginal = [{title = "Title", items = [{text = "Item", code = 4}]}];
local listCalls = 0;
local eventList = hooks["scripts/events/event"].getUIList(function () {
    listCalls += 1;
    return listOriginal;
});
local listResult = eventList();
assertEqual(listResult[0].title, "題名", "list title");
assertEqual(listResult[0].items[0].text, "項目", "list item");
assertEqual(listOriginal[0].title, "Title", "list source title immutable");
assertEqual(listOriginal[0].items[0].text, "Item", "list source item immutable");
assertEqual(listCalls, 1, "list original once");

local buttonsOriginal = [{text = "Unknown", tooltip = "Button"}];
local buttonsCalls = 0;
local buttons = hooks["scripts/events/event"].getUIButtons(function () {
    buttonsCalls += 1;
    return buttonsOriginal;
});
local buttonsResult = buttons();
assertEqual(buttonsResult[0].tooltip, "ボタン", "button tooltip");
assertEqual(buttonsOriginal[0].tooltip, "Button", "button source immutable");
assertEqual(buttonsCalls, 1, "button original once");

local logCalls = 0;
local logValue = null;
local log = hooks["scripts/ui/screens/tactical/modules/topbar/tactical_screen_topbar_event_log"].log(
    function (_text) { logCalls += 1; logValue = _text; return 5; }
);
assertEqual(log("Description"), 5, "log return");
assertEqual(logValue, "説明", "log text");
assertEqual(logCalls, 1, "log original once");

local originalErrorCalls = 0;
local failingLoading = hooks["scripts/ui/screens/loading/loading_screen"].onQueryData(function () {
    originalErrorCalls += 1;
    throw "ORIGINAL_FAILURE";
});
local caught = false;
try { failingLoading(); } catch (error) { caught = error == "ORIGINAL_FAILURE"; }
if (!caught) throw "original exception was suppressed";
assertEqual(originalErrorCalls, 1, "failing original once");

local nullLoading = hooks["scripts/ui/screens/loading/loading_screen"].onQueryData(function () { return null; });
if (nullLoading() != null) throw "null result was not passed through";

print("RUNTIME_DISPLAY_BOUNDARIES_TEST_OK\n");
