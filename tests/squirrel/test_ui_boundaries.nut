dofile(getenv("STDLIB_DIR") + "load.nut", true);

local groupNames = {
    Agile = "敏捷",
    Tenacious = "不屈",
    Martyr = "殉教者",
    Harbor = "港",
    ["A harbor that allows you to book passage by ship to other parts of the continent"] = "大陸各地へ向かう船便を手配できる港",
    Hohenburg = "ホーエンブルク",
    ["a fortified settlement"] = "堅固な城塞都市",
    ["A brigand stronghold is nearby, attracting all manner of thieves, vagrants and murderers."] = "近隣の盗賊砦に、盗人やならず者、人殺しどもが集まっている。",
    ["A Diplomatic Mission"] = "外交任務",
    [" The arena master"] = " 闘技場の支配人",
    ["Amber Wristguards"] = "琥珀の腕甲",
    ["Ancestral Helm"] = "先祖伝来の兜",
    ["Ancestor's Stone"] = "祖霊の石",
    ["Elder Lute"] = "古老のリュート",
    ["Deserted the company"] = "傭兵団から脱走した",
    ["Got a better paying offer"] = "もっと割のいい仕事を持ちかけられた",
    ["Handed over to authorities"] = "当局へ引き渡された",
    ["Hanged for attempted murder"] = "殺人未遂で絞首刑に処された",
    ["Left to claim their birthright"] = "生まれながらの権利を求めて去った",
    ["Murdered by his fellow brothers"] = "同じ傭兵団の仲間たちに殺された",
    ["Brigands have stolen the %s from his lordship. He wants it back."] = "盗賊が領主の%sを盗んだ。領主は取り戻すことを望んでいる。"
};

::Const <- {
    UI = {
        Color = {
            getHighlightLightBackgroundValue = @() "#123456"
        },
        getColorized = @(_text, _color) "[color=" + _color + "]" + _text + "[/color]"
    }
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
    ["scripts/contracts/contract"] = ["getDescription"],
    ["scripts/ui/global/data_helper"] = ["convertContractToUIData"],
    ["scripts/contracts/contracts/arena_contract"] = ["getUIContent"],
    ["scripts/ui/screens/tooltip/tooltip_events"] = ["onQueryUIElementTooltipData"],
    ["scripts/ui/screens/world/world_obituary_screen"] = ["convertFallenToUIData"],
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

local contractCalls = 0;
local contractState = {
    m = {
        Description = "A brigand stronghold is nearby, attracting all manner of thieves, vagrants and murderers.",
        State = "Offer"
    }
};
local contractDescriptionWrapper = hooks["scripts/contracts/contract"].getDescription(function () {
    contractCalls += 1;
    return this.m.Description;
});
assertEqual(
    contractDescriptionWrapper.call(contractState),
    "近隣の盗賊砦に、盗人やならず者、人殺しどもが集まっている。"
);
assertEqual(contractCalls, 1);
assertEqual(contractState.m.Description, "A brigand stronghold is nearby, attracting all manner of thieves, vagrants and murderers.");
assertEqual(contractState.m.State, "Offer");
local contractNullWrapper = hooks["scripts/contracts/contract"].getDescription(function () { return null; });
assertEqual(contractNullWrapper(), null);

local returnItemFlags = {
    Item = "Amber Wristguards",
    has = function (_key) { return _key == "Item"; },
    get = function (_key) { return this.Item; }
};
local returnItemState = {
    m = {
        Type = "contract.return_item",
        Flags = returnItemFlags,
        Description = "Brigands have stolen the [color=#123456]Amber Wristguards[/color] from his lordship. He wants it back.",
        State = "Offer"
    }
};
local returnItemDescriptionWrapper = hooks["scripts/contracts/contract"].getDescription(function () {
    return this.m.Description;
});
assertEqual(
    returnItemDescriptionWrapper.call(returnItemState),
    "盗賊が領主の[color=#123456]琥珀の腕甲[/color]を盗んだ。領主は取り戻すことを望んでいる。"
);
assertEqual(returnItemState.m.Description, "Brigands have stolen the [color=#123456]Amber Wristguards[/color] from his lordship. He wants it back.");
assertEqual(returnItemState.m.Flags.Item, "Amber Wristguards");
assertEqual(returnItemState.m.State, "Offer");
local malformedFlagsState = {
    m = {
        Type = "contract.return_item",
        Flags = {},
        Description = returnItemState.m.Description
    }
};
assertEqual(returnItemDescriptionWrapper.call(malformedFlagsState), malformedFlagsState.m.Description);
local zeroMarkerState = {
    m = {
        Type = "contract.return_item",
        Flags = returnItemFlags,
        Description = "Brigands have stolen the Amber Wristguards from his lordship. He wants it back."
    }
};
assertEqual(returnItemDescriptionWrapper.call(zeroMarkerState), zeroMarkerState.m.Description);
local wrongColorState = {
    m = {
        Type = "contract.return_item",
        Flags = returnItemFlags,
        Description = "Brigands have stolen the [color=#654321]Amber Wristguards[/color] from his lordship. He wants it back."
    }
};
assertEqual(returnItemDescriptionWrapper.call(wrongColorState), wrongColorState.m.Description);
local returnItemTemplate = "Brigands have stolen the %s from his lordship. He wants it back.";
local savedReturnItemTranslation = groupNames[returnItemTemplate];
groupNames[returnItemTemplate] = "盗賊が品を盗んだ。";
assertEqual(returnItemDescriptionWrapper.call(returnItemState), returnItemState.m.Description);
groupNames[returnItemTemplate] = "盗賊が%sと%sを盗んだ。";
assertEqual(returnItemDescriptionWrapper.call(returnItemState), returnItemState.m.Description);
groupNames[returnItemTemplate] = savedReturnItemTranslation;
local duplicateMarkerState = {
    m = {
        Type = "contract.return_item",
        Flags = returnItemFlags,
        Description = "[color=#123456]Amber Wristguards[/color] and [color=#123456]Amber Wristguards[/color]"
    }
};
assertEqual(returnItemDescriptionWrapper.call(duplicateMarkerState), duplicateMarkerState.m.Description);

local rawContract = {
    m = {Name = "A Diplomatic Mission", State = "Offer"}
};
local contractDtoSource = {
    id = 4,
    title = "A Diplomatic Mission",
    headerImagePath = "ui/contracts/test.png",
    content = [{id = 1, type = "description", text = "raw description"}],
    buttons = [{id = 2, text = "Accept"}],
    extra = "sentinel"
};
local contractDtoCalls = 0;
local contractDtoWrapper = hooks["scripts/ui/global/data_helper"].convertContractToUIData(function (_contract) {
    contractDtoCalls += 1;
    if (_contract != rawContract) throw "contract identity changed";
    return contractDtoSource;
});
local contractDtoResult = contractDtoWrapper(rawContract);
assertEqual(contractDtoCalls, 1);
assertEqual(contractDtoResult.title, "外交任務");
assertEqual(contractDtoResult.id, 4);
assertEqual(contractDtoResult.headerImagePath, "ui/contracts/test.png");
assertEqual(contractDtoResult.content[0].text, "raw description");
assertEqual(contractDtoResult.buttons[0].text, "Accept");
assertEqual(contractDtoResult.extra, "sentinel");
assertEqual(rawContract.m.Name, "A Diplomatic Mission");
assertEqual(rawContract.m.State, "Offer");
local contractDtoNullWrapper = hooks["scripts/ui/global/data_helper"].convertContractToUIData(function (_contract) { return null; });
assertEqual(contractDtoNullWrapper(rawContract), null);
local contractDtoNumberWrapper = hooks["scripts/ui/global/data_helper"].convertContractToUIData(function (_contract) { return 7; });
assertEqual(contractDtoNumberWrapper(rawContract), 7);
local contractDtoNonStringWrapper = hooks["scripts/ui/global/data_helper"].convertContractToUIData(function (_contract) { return {title = 9}; });
assertEqual(contractDtoNonStringWrapper(rawContract).title, 9);
local contractDtoAbsentTitleWrapper = hooks["scripts/ui/global/data_helper"].convertContractToUIData(function (_contract) { return {id = 12}; });
assertEqual(contractDtoAbsentTitleWrapper(rawContract).id, 12);
local contractDtoUnknownTitleWrapper = hooks["scripts/ui/global/data_helper"].convertContractToUIData(function (_contract) { return {title = "Unknown Contract"}; });
assertEqual(contractDtoUnknownTitleWrapper(rawContract).title, "Unknown Contract");
local contractDtoExceptionPropagated = false;
local contractDtoThrowingWrapper = hooks["scripts/ui/global/data_helper"].convertContractToUIData(function (_contract) { throw "dto sentinel"; });
try
{
    contractDtoThrowingWrapper(rawContract);
}
catch (error)
{
    contractDtoExceptionPropagated = error == "dto sentinel";
}
if (!contractDtoExceptionPropagated) throw "contract DTO exception did not propagate";

local arenaSource = [
    {id = 1, type = "description", text = "Prefix The arena master / The arena master suffix", icon = "event"},
    {id = 2, type = "list", text = " The arena master", icon = "list"},
    {id = 3, type = "description", text = "Already translated", icon = "other"}
];
local arenaCalls = 0;
local arenaWrapper = hooks["scripts/contracts/contracts/arena_contract"].getUIContent(function () {
    arenaCalls += 1;
    return arenaSource;
});
local arenaResult = arenaWrapper();
assertEqual(arenaCalls, 1);
assertEqual(arenaResult[0].text, "Prefix 闘技場の支配人 / 闘技場の支配人 suffix");
assertEqual(arenaResult[0].id, 1);
assertEqual(arenaResult[0].icon, "event");
assertEqual(arenaResult[1].text, " The arena master");
assertEqual(arenaResult[2].text, "Already translated");
assertEqual(arenaSource[0].text, "Prefix The arena master / The arena master suffix");
if (arenaResult[0] == arenaSource[0]) throw "arena display entry was not cloned";
local arenaNullWrapper = hooks["scripts/contracts/contracts/arena_contract"].getUIContent(function () { return null; });
assertEqual(arenaNullWrapper(), null);
local arenaScalarWrapper = hooks["scripts/contracts/contracts/arena_contract"].getUIContent(function () { return 8; });
assertEqual(arenaScalarWrapper(), 8);
local arenaMalformedSource = [
    5,
    {id = 1, text = " The arena master"},
    {id = 2, type = "description", text = 17},
    {id = 3, type = "description", text = "No matching fragment"}
];
local arenaMalformedWrapper = hooks["scripts/contracts/contracts/arena_contract"].getUIContent(function () { return arenaMalformedSource; });
local arenaMalformedResult = arenaMalformedWrapper();
assertEqual(arenaMalformedResult[0], 5);
assertEqual(arenaMalformedResult[1].text, " The arena master");
assertEqual(arenaMalformedResult[2].text, 17);
assertEqual(arenaMalformedResult[3].text, "No matching fragment");
local savedArenaTranslation = groupNames[" The arena master"];
delete groupNames[" The arena master"];
local arenaUnregisteredSource = [{id = 1, type = "description", text = "Prefix The arena master suffix"}];
local arenaUnregisteredWrapper = hooks["scripts/contracts/contracts/arena_contract"].getUIContent(function () { return arenaUnregisteredSource; });
local arenaUnregisteredResult = arenaUnregisteredWrapper();
assertEqual(arenaUnregisteredResult[0].text, "Prefix The arena master suffix");
if (arenaUnregisteredResult != arenaUnregisteredSource) throw "unregistered arena mapping should return original array";
groupNames[" The arena master"] <- savedArenaTranslation;

local relationSource = [
    {id = 1, type = "title", text = "Relations", icon = "title"},
    {id = 11, type = "hint", icon = "ui/tooltips/positive.png", text = "Returned stolen Amber Wristguards", extra = 7},
    {id = 11, type = "hint", icon = "ui/tooltips/negative.png", text = "Failed to return stolen Ancestral Helm"},
    {id = 11, type = "hint", icon = "ui/tooltips/positive.png", text = "Obtained Ancestor's Stone"},
    {id = 11, type = "hint", icon = "ui/tooltips/negative.png", text = "Failed to obtain Elder Lute"}
];
local relationCalls = 0;
local relationWrapper = hooks["scripts/ui/screens/tooltip/tooltip_events"].onQueryUIElementTooltipData(
    function (_entityId, _elementId, _elementOwner) {
        relationCalls += 1;
        assertEqual(_entityId, 42);
        assertEqual(_elementId, "world-relations-screen.Relations");
        assertEqual(_elementOwner, "world-relations-screen");
        return relationSource;
    }
);
local relationResult = relationWrapper(42, "world-relations-screen.Relations", "world-relations-screen");
assertEqual(relationCalls, 1);
assertEqual(relationResult[0].text, "Relations");
assertEqual(relationResult[1].text, "盗品「琥珀の腕甲」を返却");
assertEqual(relationResult[1].id, 11);
assertEqual(relationResult[1].type, "hint");
assertEqual(relationResult[1].icon, "ui/tooltips/positive.png");
assertEqual(relationResult[1].extra, 7);
assertEqual(relationResult[2].text, "盗品「先祖伝来の兜」の返却に失敗");
assertEqual(relationResult[3].text, "「祖霊の石」を入手");
assertEqual(relationResult[4].text, "「古老のリュート」の入手に失敗");
assertEqual(relationSource[1].text, "Returned stolen Amber Wristguards");
assertEqual(relationSource[2].text, "Failed to return stolen Ancestral Helm");
assertEqual(relationSource[3].text, "Obtained Ancestor's Stone");
assertEqual(relationSource[4].text, "Failed to obtain Elder Lute");
if (relationResult == relationSource || relationResult[1] == relationSource[1]) throw "relation tooltip display was not cloned";

local unrelatedRelationWrapper = hooks["scripts/ui/screens/tooltip/tooltip_events"].onQueryUIElementTooltipData(
    function (_entityId, _elementId, _elementOwner) { return relationSource; }
);
local unrelatedRelation = unrelatedRelationWrapper(42, "world-relations-screen.Other", "world-relations-screen");
if (unrelatedRelation != relationSource) throw "unrelated tooltip owner must retain original array";

local guardedRelationSource = [
    {id = 11, type = "hint", icon = "ui/tooltips/positive.png", text = "Returned stolen Unknown Relic"},
    {id = 11, type = "hint", icon = "ui/tooltips/negative.png", text = "Returned stolen Amber Wristguards"},
    {id = 10, type = "hint", icon = "ui/tooltips/positive.png", text = "Returned stolen Amber Wristguards"},
    {id = 11, type = "text", icon = "ui/tooltips/positive.png", text = "Returned stolen Amber Wristguards"},
    {id = 11, type = "hint", icon = "ui/tooltips/positive.png", text = "Returned stolen Ancestor's Stone"},
    {id = 11, type = "hint", icon = "ui/tooltips/positive.png", text = "Prefix Returned stolen Amber Wristguards"},
    7
];
local guardedRelationWrapper = hooks["scripts/ui/screens/tooltip/tooltip_events"].onQueryUIElementTooltipData(
    function (_entityId, _elementId, _elementOwner) { return guardedRelationSource; }
);
local guardedRelationResult = guardedRelationWrapper(null, "world-relations-screen.Relations", null);
if (guardedRelationResult != guardedRelationSource) throw "unmatched relation shapes must retain original array";
foreach (i, entry in guardedRelationSource)
{
    if (typeof entry == "table") assertEqual(guardedRelationResult[i].text, entry.text);
}
local scalarRelationWrapper = hooks["scripts/ui/screens/tooltip/tooltip_events"].onQueryUIElementTooltipData(
    function (_entityId, _elementId, _elementOwner) { return 9; }
);
assertEqual(scalarRelationWrapper(null, "world-relations-screen.Relations", null), 9);

local obituarySource = {
    Fallen = [
        {Name = "Aldric", KilledBy = "Deserted the company", Kills = 3, Traits = ["raw"]},
        {Name = "Beatrix", KilledBy = "Got a better paying offer", Kills = 2},
        {Name = "Cedric", KilledBy = "Handed over to authorities", Kills = 1},
        {Name = "Dora", KilledBy = "Hanged for attempted murder", Kills = 0},
        {Name = "Edric", KilledBy = "Left to claim their birthright", Kills = 0},
        {Name = "Fara", KilledBy = "Murdered by his fellow brothers", Kills = 0},
        {Name = "Gernot", KilledBy = "Hohenburg", Kills = 0},
        {Name = "Hilde", KilledBy = 7},
        "malformed"
    ],
    Page = 2
};
local obituaryCalls = 0;
local obituaryWrapper = hooks["scripts/ui/screens/world/world_obituary_screen"].convertFallenToUIData(
    function () {
        obituaryCalls += 1;
        return obituarySource;
    }
);
local obituaryResult = obituaryWrapper();
assertEqual(obituaryCalls, 1);
assertEqual(obituaryResult.Fallen[0].KilledBy, "傭兵団から脱走した");
assertEqual(obituaryResult.Fallen[0].Name, "Aldric");
assertEqual(obituaryResult.Fallen[0].Kills, 3);
assertEqual(obituaryResult.Fallen[0].Traits[0], "raw");
assertEqual(obituaryResult.Fallen[1].KilledBy, "もっと割のいい仕事を持ちかけられた");
assertEqual(obituaryResult.Fallen[2].KilledBy, "当局へ引き渡された");
assertEqual(obituaryResult.Fallen[3].KilledBy, "殺人未遂で絞首刑に処された");
assertEqual(obituaryResult.Fallen[4].KilledBy, "生まれながらの権利を求めて去った");
assertEqual(obituaryResult.Fallen[5].KilledBy, "同じ傭兵団の仲間たちに殺された");
assertEqual(obituaryResult.Fallen[6].KilledBy, "Hohenburg");
assertEqual(obituaryResult.Fallen[7].KilledBy, 7);
assertEqual(obituaryResult.Fallen[8], "malformed");
assertEqual(obituaryResult.Page, 2);
assertEqual(obituarySource.Fallen[0].KilledBy, "Deserted the company");
assertEqual(obituarySource.Fallen[1].KilledBy, "Got a better paying offer");
assertEqual(obituarySource.Fallen[2].KilledBy, "Handed over to authorities");
assertEqual(obituarySource.Fallen[3].KilledBy, "Hanged for attempted murder");
assertEqual(obituarySource.Fallen[4].KilledBy, "Left to claim their birthright");
assertEqual(obituarySource.Fallen[5].KilledBy, "Murdered by his fellow brothers");
assertEqual(obituarySource.Fallen[6].KilledBy, "Hohenburg");
if (obituaryResult == obituarySource
    || obituaryResult.Fallen == obituarySource.Fallen
    || obituaryResult.Fallen[0] == obituarySource.Fallen[0]) throw "obituary DTO was not cloned";
local obituaryUnknownSource = {Fallen = [{KilledBy = "Unknown demise"}], Page = 3};
local obituaryUnknownWrapper = hooks["scripts/ui/screens/world/world_obituary_screen"].convertFallenToUIData(
    function () { return obituaryUnknownSource; }
);
if (obituaryUnknownWrapper() != obituaryUnknownSource) throw "unknown obituary cause must retain original DTO";
local obituaryNullWrapper = hooks["scripts/ui/screens/world/world_obituary_screen"].convertFallenToUIData(
    function () { return null; }
);
assertEqual(obituaryNullWrapper(), null);
local obituaryMalformedWrapper = hooks["scripts/ui/screens/world/world_obituary_screen"].convertFallenToUIData(
    function () { return {Fallen = 4, Page = 5}; }
);
assertEqual(obituaryMalformedWrapper().Fallen, 4);

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
