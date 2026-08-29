dofile(getenv("STDLIB_DIR") + "load.nut", true);

local groupNames = {
    Agile = "敏捷",
    Tenacious = "不屈",
    Martyr = "殉教者",
    Harbor = "港",
    ["A harbor that allows you to book passage by ship to other parts of the continent"] = "大陸各地へ向かう船便を手配できる港",
    Hohenburg = "ホーエンブルク",
    ["a fortified settlement"] = "堅固な城塞都市"
};

::Rosetta <- {
    _ = function (_text) {
        return _text in groupNames ? groupNames[_text] : _text;
    }
};

local hooks = {};
local methodShapes = {
    ["scripts/ambitions/ambition"] = ["getUIText"],
    ["scripts/skills/skill"] = ["getKilledString"],
    ["scripts/ui/screens/world/modules/camp_screen/camp_crafting_dialog_module"] = ["queryLoad"],
    ["scripts/entity/world/settlement"] = ["getUIInformation"],
    ["scripts/entity/world/settlements/buildings/port_building"] = ["getUITravelRoster"],
    ["scripts/items/legend_armor/legend_named_armor"] = ["getName"],
    ["scripts/items/legend_armor/legend_named_armor_upgrade"] = ["getName"],
    ["scripts/items/legend_helmets/legend_named_helmet"] = ["getName"],
    ["scripts/items/legend_helmets/legend_named_helmet_upgrade"] = ["getName"],
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

local settlementOriginal = function () {
    return {
        Title = "Hohenburg",
        SubTitle = "a fortified settlement",
        Assets = 17
    };
};
local settlementWrapper = hooks["scripts/entity/world/settlement"].getUIInformation(settlementOriginal);
local settlementResult = settlementWrapper();
assertEqual(settlementResult.Title, "ホーエンブルク");
assertEqual(settlementResult.SubTitle, "堅固な城塞都市");
assertEqual(settlementResult.Assets, 17);

local portOriginalCalls = 0;
local portSourceSettlement = { Name = "Hohenburg" };
local portOriginal = function () {
    portOriginalCalls += 1;
    return {
        Title = "Harbor",
        SubTitle = "A harbor that allows you to book passage by ship to other parts of the continent",
        HeaderImage = "ui/header.png",
        Roster = [
            {
                ID = 91,
                EntryID = 0,
                ListName = "Sail to " + portSourceSettlement.Name,
                Name = portSourceSettlement.Name,
                Cost = 170,
                ImagePath = "ui/settlements/01.png",
                ListImagePath = "ui/settlements/list01.png",
                FactionImagePath = "ui/factions/01.png",
                ExtraField = "preserve me",
                BackgroundText = "a fortified settlement<br><br>既に翻訳済みの船便説明"
            },
            {
                ID = 92,
                ListName = "Charter for Hohenburg",
                Name = "Hohenburg",
                Cost = 200,
                BackgroundText = "Standalone description"
            },
            { ID = 93, ListName = "Sail to Hohenburg", Name = 9 },
            "malformed entry"
        ]
    };
};
local portWrapper = hooks["scripts/entity/world/settlements/buildings/port_building"].getUITravelRoster(portOriginal);
local portResult = portWrapper();
assertEqual(portResult.Title, "港");
assertEqual(portResult.SubTitle, "大陸各地へ向かう船便を手配できる港");
assertEqual(portOriginalCalls, 1);
assertEqual(portSourceSettlement.Name, "Hohenburg");
assertEqual(portResult.HeaderImage, "ui/header.png");
assertEqual(portResult.Roster.len(), 4);
assertEqual(portResult.Roster[0].Name, "ホーエンブルク");
assertEqual(portResult.Roster[0].ListName, "船でホーエンブルクへ向かう");
assertEqual(portResult.Roster[0].BackgroundText, "堅固な城塞都市<br><br>既に翻訳済みの船便説明");
assertEqual(portResult.Roster[0].ID, 91);
assertEqual(portResult.Roster[0].EntryID, 0);
assertEqual(portResult.Roster[0].Cost, 170);
assertEqual(portResult.Roster[0].ImagePath, "ui/settlements/01.png");
assertEqual(portResult.Roster[0].ListImagePath, "ui/settlements/list01.png");
assertEqual(portResult.Roster[0].FactionImagePath, "ui/factions/01.png");
assertEqual(portResult.Roster[0].ExtraField, "preserve me");
assertEqual(portResult.Roster[1].ListName, "Charter for Hohenburg");
assertEqual(portResult.Roster[1].Name, "ホーエンブルク");
assertEqual(portResult.Roster[1].BackgroundText, "Standalone description");
assertEqual(portResult.Roster[2].ListName, "Sail to Hohenburg");
assertEqual(portResult.Roster[2].Name, 9);
assertEqual(portResult.Roster[3], "malformed entry");
local portNullWrapper = hooks["scripts/entity/world/settlements/buildings/port_building"].getUITravelRoster(function () {
    return null;
});
assertEqual(portNullWrapper(), null);
local portMalformedWrapper = hooks["scripts/entity/world/settlements/buildings/port_building"].getUITravelRoster(function () {
    return { Title = 7, SubTitle = false, Roster = null, Sentinel = 23 };
});
local portMalformedResult = portMalformedWrapper();
assertEqual(portMalformedResult.Title, 7);
assertEqual(portMalformedResult.SubTitle, false);
assertEqual(portMalformedResult.Roster, null);
assertEqual(portMalformedResult.Sentinel, 23);
local portNonTableWrapper = hooks["scripts/entity/world/settlements/buildings/port_building"].getUITravelRoster(function () {
    return "unchanged";
});
assertEqual(portNonTableWrapper(), "unchanged");

local generatedNameWrapper = hooks["scripts/items/legend_armor/legend_named_armor"].getName(function () {
    return this.m.Name;
});
local generatedItem = { m = { Name = "Famed Play" } };
assertEqual(generatedNameWrapper.call(generatedItem), "Famed 戯れ");
assertEqual(generatedItem.m.Name, "Famed Play");
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
