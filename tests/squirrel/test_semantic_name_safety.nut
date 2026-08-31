local hooks = {};
local methodShapes = {
    ["scripts/items/item"] = ["getName"],
    ["scripts/entity/world/world_entity"] = ["updateStrength", "onDeserialize"],
    ["scripts/entity/world/location"] = ["onInit"],
    ["scripts/entity/world/party"] = ["onInit"]
};

local function registerHook(_target, _callback)
{
    local q = {};
    foreach (method in methodShapes[_target]) q[method] <- null;
    _callback(q);
    hooks[_target] <- q;
}

::BattleBrothersJP <- {
    DisplayGetterScopeDepth = 0,
    ActorTitleDisplayFragments = [
        {english = "the Holy Avenger", japanese = "聖なる復讐者"},
        {english = "the White Death", japanese = "白き死"},
        {english = "The Lone Wolf", japanese = "一匹狼"},
        {english = "the Lone Wolf", japanese = "一匹狼"},
        {english = "the Old Guard", japanese = "古参兵"},
        {english = "the White", japanese = "白き者"},
        {english = "the Holy", japanese = "聖なる者"},
        {english = "the Old", japanese = "老人"},
        {english = "Weeds", japanese = "雑草"}
    ],
    ActorTitleGenericDisplayFragments = [
        {english = "The Lone Wolf", japanese = "一匹狼"},
        {english = "Weeds", japanese = "雑草"}
    ],
    Mod = {
        hook = registerHook,
        hookTree = registerHook
    }
};

::BattleBrothersJP.Runtime <- {
    translate = function (_text) {
        local translated = {
            ["Broad Head Arrows"] = "幅広鏃の矢",
            ["Donkey"] = "ロバ",
            ["Hohenburg"] = "ホーエンブルク",
            ["The Lone Wolf"] = "一匹狼",
            ["Warrior the Warhound"] = "戦犬のウォリアー",
            ["Weeds"] = "雑草"
        };
        return _text in translated ? translated[_text] : _text;
    }
};

::buildTextFromTemplate <- function (_text, _vars) {
    return {Text = _text, Vars = _vars};
};

local generateNameCalls = 0;
local generateNameReceiver = null;
local throwFromGenerateName = false;
::Const <- {
    Strings = {
        HedgeKnightTitles = ["The Lone Wolf"]
    },
    World = {
        Common = {}
    }
};
::Const.World.Common.generateName <- function (_list) {
    generateNameCalls += 1;
    generateNameReceiver = this;
    if (throwFromGenerateName) throw "generate-name-sentinel";
    return ::buildTextFromTemplate(_list[0], []).Text;
};

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/semantic_name_safety.nut", true);
local firstItemNameFactory = hooks["scripts/items/item"].getName;
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/semantic_name_safety.nut", true);
if (hooks["scripts/items/item"].getName != firstItemNameFactory)
    throw "semantic name safety initialized twice";
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/event_variable_boundaries.nut", true);
local firstTemplateBoundary = ::buildTextFromTemplate;
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/event_variable_boundaries.nut", true);
if (::buildTextFromTemplate != firstTemplateBoundary)
    throw "event variable boundary initialized twice";

function assertEqual(_actual, _expected)
{
    if (_actual != _expected) throw "Expected '" + _expected + "', got '" + _actual + "'";
}

local function getDisplayName(_getter, _item)
{
    ::BattleBrothersJP.DisplayGetterScopeDepth += 1;
    local result = _getter.call(_item);
    ::BattleBrothersJP.DisplayGetterScopeDepth -= 1;
    return result;
}

// Ordinary item identity is raw; only a finite display scope localizes it.
local itemGetter = hooks["scripts/items/item"].getName(function () {
    return this.m.Name;
});
local arrowItem = {m = {Name = "Broad Head Arrows"}};
arrowItem.getName <- itemGetter;
assertEqual(arrowItem.getName(), "Broad Head Arrows");
assertEqual(getDisplayName(itemGetter, arrowItem), "幅広鏃の矢");

// HedgeKnightTitles is both player-facing content and a generated actor name
// list. Only that exact list is raw during generation; other lists delegate.
local worldNameReceiver = ::Const.World.Common;
assertEqual(::Const.World.Common.generateName.call(worldNameReceiver, ::Const.Strings.HedgeKnightTitles), "The Lone Wolf");
assertEqual(generateNameCalls, 1);
if (generateNameReceiver != worldNameReceiver) throw "generateName receiver changed";
assertEqual(::Const.World.Common.generateName.call(worldNameReceiver, ["Hohenburg"]), "ホーエンブルク");
assertEqual(generateNameCalls, 2);
throwFromGenerateName = true;
local generateNameErrorCaught = false;
try
{
    ::Const.World.Common.generateName.call(worldNameReceiver, ::Const.Strings.HedgeKnightTitles);
}
catch (error)
{
    generateNameErrorCaught = error == "generate-name-sentinel";
}
throwFromGenerateName = false;
if (!generateNameErrorCaught) throw "generateName did not rethrow the original exception";
assertEqual(generateNameCalls, 3);
assertEqual(::BattleBrothersJP.SemanticNameScopes.RawTemplate, 0);

// The new runtime deliberately does not hook actor identity getters. Their
// complete unbounded semantic/save surface therefore stays raw by construction.
local actorNameGetter = function () {
    local name = this.m.Name;
    local title = this.m.Title;
    return title.len() == 0 ? name : name + " " + title;
};
local actorNameOnlyGetter = function () { return this.m.Name; };
local actorTitleGetter = function () { return this.m.Title; };
local actorKilledNameGetter = function () { return this.m.Name; };
local titledActor = {m = {Name = "Aldric", Title = "The Lone Wolf"}};
titledActor.getName <- actorNameGetter;
titledActor.getNameOnly <- actorNameOnlyGetter;
titledActor.getTitle <- actorTitleGetter;
titledActor.getKilledName <- actorKilledNameGetter;
local generatedActor = {m = {Name = "The Lone Wolf", Title = ""}};
generatedActor.getName <- actorNameGetter;
generatedActor.getNameOnly <- actorNameOnlyGetter;
generatedActor.getTitle <- actorTitleGetter;
generatedActor.getKilledName <- actorKilledNameGetter;
local farmer = {m = {Name = "Asta", Title = "Weeds"}};
farmer.getName <- actorNameGetter;
farmer.getNameOnly <- actorNameOnlyGetter;
farmer.getTitle <- actorTitleGetter;
farmer.getKilledName <- actorKilledNameGetter;

assertEqual(titledActor.getName(), "Aldric The Lone Wolf");
assertEqual(titledActor.getNameOnly(), "Aldric");
assertEqual(titledActor.getTitle(), "The Lone Wolf");
assertEqual(generatedActor.getName(), "The Lone Wolf");
assertEqual(generatedActor.getKilledName(), "The Lone Wolf");
assertEqual(farmer.getName(), "Asta Weeds");
assertEqual(farmer.getTitle(), "Weeds");
assertEqual(titledActor.m.Name, "Aldric");
assertEqual(titledActor.m.Title, "The Lone Wolf");
assertEqual(farmer.m.Title, "Weeds");

// Representative unscoped semantic paths all receive raw identity without a
// per-consumer wrapper: contract flags, mood history, named items, corpse
// state, and a resurrection copy.
local contractFlags = {ChampionBrotherName = titledActor.getName()};
local moodHistory = [{Reason = "Dismissed " + titledActor.getName()}];
local namedItem = {m = {Name = titledActor.getName() + "'s Relic"}};
local corpse = {
    CorpseName = titledActor.getName(),
    Name = "Wiederganger " + titledActor.getName()
};
local resurrected = {m = {Name = corpse.Name}};
assertEqual(contractFlags.ChampionBrotherName, "Aldric The Lone Wolf");
assertEqual(moodHistory[0].Reason, "Dismissed Aldric The Lone Wolf");
assertEqual(namedItem.m.Name, "Aldric The Lone Wolf's Relic");
assertEqual(corpse.CorpseName, "Aldric The Lone Wolf");
assertEqual(corpse.Name, "Wiederganger Aldric The Lone Wolf");
assertEqual(resurrected.m.Name, "Wiederganger Aldric The Lone Wolf");

// Item state derived from an actor remains raw, but the generic item display
// getter translates only the reviewed title fragment on its return value.
local namedItemDisplay = hooks["scripts/items/item"].getName(function () {
    return this.m.Name;
});
assertEqual(namedItemDisplay.call(namedItem), "Aldric The Lone Wolf's Relic");
assertEqual(getDisplayName(namedItemDisplay, namedItem), "Aldric 一匹狼's Relic");
assertEqual(namedItem.m.Name, "Aldric The Lone Wolf's Relic");
local weedsItem = {m = {Name = "Asta Weeds' Sickle"}};
assertEqual(getDisplayName(namedItemDisplay, weedsItem), "Asta 雑草' Sickle");
assertEqual(weedsItem.m.Name, "Asta Weeds' Sickle");
local collisionItem = {m = {Name = "WolfgangThe Lone Wolfish Relic"}};
assertEqual(namedItemDisplay.call(collisionItem), "WolfgangThe Lone Wolfish Relic");
local proseCollisionItems = [
    {m = {Name = "Blood Vial of the Holy Mother"}},
    {m = {Name = "Honor and fear of the Old Gods"}}
];
assertEqual(namedItemDisplay.call(proseCollisionItems[0]), "Blood Vial of the Holy Mother");
assertEqual(namedItemDisplay.call(proseCollisionItems[1]), "Honor and fear of the Old Gods");
local prefixTitleItems = [
    [{m = {Name = "Aldric the Holy Avenger's Relic"}}, "Aldric 聖なる復讐者's Relic"],
    [{m = {Name = "Aldric the Old Guard's Relic"}}, "Aldric 古参兵's Relic"],
    [{m = {Name = "Aldric the White Death's Relic"}}, "Aldric 白き死's Relic"]
];
foreach (fixture in prefixTitleItems)
{
    assertEqual(getDisplayName(namedItemDisplay, fixture[0]), fixture[1]);
}

// Dog item identity is also raw without wrapping gameplay callbacks.
local dogItem = {m = {Name = "Warrior the Warhound"}};
dogItem.getName <- itemGetter;
assertEqual(dogItem.getName(), "Warrior the Warhound");
assertEqual(getDisplayName(itemGetter, dogItem), "戦犬のウォリアー");
assertEqual(dogItem.m.Name, "Warrior the Warhound");
assertEqual(dogItem.getName(), "Warrior the Warhound");
assertEqual(getDisplayName(itemGetter, dogItem), "戦犬のウォリアー");

// No background identity getter is installed. The original matcher therefore
// receives the raw source value; final skill/UI wrappers localize its display.
local backgroundGetter = function () { return "Donkey"; };
assertEqual(backgroundGetter(), "Donkey");
assertEqual(backgroundGetter() == "Donkey" ? "donkey-branch" : "wrong-branch", "donkey-branch");

// World identity remains raw globally, with labels localized after the exact
// display-producing lifecycle methods complete.
local worldGetter = function () { return this.m.Name; };
local settlement = {
    m = {Name = "Hohenburg"},
    label = {Text = null},
    hasLabel = function (_name) { return _name == "name"; },
    getLabel = function (_name) { return this.label; }
};
settlement.getName <- worldGetter;
assertEqual(settlement.getName(), "Hohenburg");
local updateStrength = hooks["scripts/entity/world/world_entity"].updateStrength(function () {
    this.label.Text = this.getName() + " (4)";
    return 17;
});
assertEqual(updateStrength.call(settlement), 17);
assertEqual(settlement.label.Text, "ホーエンブルク (4)");
assertEqual(settlement.m.Name, "Hohenburg");
local partyInit = hooks["scripts/entity/world/party"].onInit(function () {
    this.label.Text = this.getName();
    return 23;
});
settlement.label.Text = null;
assertEqual(partyInit.call(settlement), 23);
assertEqual(settlement.label.Text, "ホーエンブルク");

// Unknown MOD label shapes and JP-only post-processing failures pass through
// after the original lifecycle method has run exactly once.
local malformedOriginalCalls = 0;
local malformedUpdate = hooks["scripts/entity/world/world_entity"].updateStrength(function () {
    malformedOriginalCalls += 1;
    return 31;
});
local nullLabelEntity = {
    hasLabel = function (_name) { return true; },
    getLabel = function (_name) { return null; },
    getName = function () { return "Hohenburg"; }
};
assertEqual(malformedUpdate.call(nullLabelEntity), 31);
assertEqual(malformedOriginalCalls, 1);
local missingTextEntity = {
    hasLabel = function (_name) { return true; },
    getLabel = function (_name) { return {}; },
    getName = function () { return "Hohenburg"; }
};
assertEqual(malformedUpdate.call(missingTextEntity), 31);
assertEqual(malformedOriginalCalls, 2);
local throwingPostprocessEntity = {
    label = {Text = "Hohenburg"},
    hasLabel = function (_name) { return true; },
    getLabel = function (_name) { return this.label; },
    getName = function () { throw "UNKNOWN_MOD_GET_NAME_FAILURE"; }
};
assertEqual(malformedUpdate.call(throwingPostprocessEntity), 31);
assertEqual(malformedOriginalCalls, 3);

assertEqual(::BattleBrothersJP.SemanticNameScopes.RawTemplate, 0);
print("SEMANTIC_NAME_SAFETY_TEST_OK\n");
