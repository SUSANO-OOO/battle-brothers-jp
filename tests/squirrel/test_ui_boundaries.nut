dofile(getenv("STDLIB_DIR") + "load.nut", true);

local groupNames = {
    Agile = "敏捷",
    Tenacious = "不屈",
    Martyr = "殉教者"
};

::Rosetta <- {
    _ = function (_text) {
        return _text in groupNames ? groupNames[_text] : _text;
    }
};

::Const <- {
    Strings = {
        LegendArmorLayers = []
    }
};

local hooks = {};
local methodShapes = {
    ["scripts/ambitions/ambition"] = ["getUIText"],
    ["scripts/skills/skill"] = ["getKilledString"],
    ["scripts/ui/screens/world/modules/camp_screen/camp_crafting_dialog_module"] = ["queryLoad"],
    ["scripts/contracts/contracts/find_artifact_contract"] = ["start"],
    ["scripts/skills/perks/perk_legend_adaptive"] = ["getUnactivatedPerkTooltipHints"],
    ["scripts/skills/perks/perk_legend_barter_greed"] = ["getTooltip"],
    ["scripts/skills/perks/perk_legend_perfect_fit"] = ["getTooltip", "getUnactivatedPerkTooltipHints"],
    ["scripts/skills/perks/perk_legend_small_target"] = ["getTooltip"]
};

local function registerHook(_target, _callback)
{
    local q = {};
    foreach (method in methodShapes[_target]) q[method] <- null;
    _callback(q);
    hooks[_target] <- q;
}

::BattleBrothersJP <- {
    Mod = {
        hook = registerHook,
        hookTree = registerHook
    }
};

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/ui_boundaries.nut", true);

function assertEqual(_actual, _expected)
{
    if (_actual != _expected) throw "Expected '" + _expected + "', got '" + _actual + "'";
}

function assertUnchanged(_actual, _expected)
{
    assertEqual(_actual.id, _expected.id);
    assertEqual(_actual.type, _expected.type);
    assertEqual(_actual.icon, _expected.icon);
}

local adaptiveOriginal = function (_actor) {
    return [{
        id = 3,
        type = "hint",
        icon = "ui/tooltips/positive.png",
        text = "Activating this Perk will randomly grant one of the following Perk Groups:\n[color=#0b0084]Agile, Tenacious, or Martyr[/color]"
    }];
};
local adaptiveWrapper = hooks["scripts/skills/perks/perk_legend_adaptive"].getUnactivatedPerkTooltipHints(adaptiveOriginal);
local adaptiveResult = adaptiveWrapper(null);
assertEqual(
    adaptiveResult[0].text,
    "このパークを有効化すると、以下のパークグループからランダムに1つ獲得する：\n[color=#0b0084]敏捷、不屈、または 殉教者[/color]"
);

local singleOriginal = function (_actor) {
    return [{
        id = 3,
        type = "hint",
        icon = "ui/tooltips/positive.png",
        text = "Activating this Perk will grant the following Perk Group:\n[color=#0b0084]Agile[/color]"
    }];
};
local singleWrapper = hooks["scripts/skills/perks/perk_legend_adaptive"].getUnactivatedPerkTooltipHints(singleOriginal);
local singleResult = singleWrapper(null);
assertEqual(
    singleResult[0].text,
    "このパークを有効化すると、以下のパークグループを獲得する：\n[color=#0b0084]敏捷[/color]"
);

local barterEntry = {
    id = 10,
    type = "text",
    icon = "ui/icons/melee_defense.png",
    text = "[color=%positive%]+7[/color] Melee Defense"
};
local barterShape = { id = 10, type = "text", icon = "ui/icons/melee_defense.png" };
local barterOriginal = function () { return [barterEntry]; };
local barterWrapper = hooks["scripts/skills/perks/perk_legend_barter_greed"].getTooltip(barterOriginal);
local barterResult = barterWrapper();
assertEqual(barterResult[0].text, "近接防御 [color=%positive%]+7[/color]");
assertUnchanged(barterResult[0], barterShape);

local perfectOriginal = function () {
    return [{
        id = 6,
        type = "text",
        icon = "ui/icons/initiative.png",
        text = "[color=%positive%]+30%[/color] Initiative"
    }];
};
local perfectWrapper = hooks["scripts/skills/perks/perk_legend_perfect_fit"].getTooltip(perfectOriginal);
assertEqual(perfectWrapper()[0].text, "先制値 [color=%positive%]+30%[/color]");

local smallOriginal = function () {
    return [
        {
            id = 6,
            type = "text",
            icon = "ui/icons/melee_defense.png",
            text = "[color=%positive%]+10[/color] Melee Defense"
        },
        {
            id = 6,
            type = "text",
            icon = "ui/icons/ranged_defense.png",
            text = "[color=%positive%]+10[/color] Ranged Defense"
        }
    ];
};
local smallWrapper = hooks["scripts/skills/perks/perk_legend_small_target"].getTooltip(smallOriginal);
local smallResult = smallWrapper();
assertEqual(smallResult[0].text, "近接防御 [color=%positive%]+10[/color]");
assertEqual(smallResult[1].text, "射撃防御 [color=%positive%]+10[/color]");

print("UI_BOUNDARIES_TEST_OK\n");
