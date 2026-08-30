local hooks = {};
local methodShapes = {
    ["scripts/items/item"] = ["getName"],
    ["scripts/items/accessory/legend_accessory_dog"] = ["onActorDied"],
    ["scripts/items/accessory/wardog_item"] = ["onActorDied"],
    ["scripts/skills/actives/unleash_wardog"] = ["onUse"],
    ["scripts/entity/tactical/actor"] = ["getName", "getNameOnly", "getTitle", "getKilledName"],
    ["scripts/skills/perks/perk_legend_specialist_poacher"] = ["onAnySkillUsed", "onTargetHit"],
    ["scripts/skills/backgrounds/character_background"] = ["getNameOnly"],
    ["scripts/skills/traits/legend_intensive_training_trait"] = ["getTooltip"],
    ["scripts/entity/world/world_entity"] = ["getName", "updateStrength", "onDeserialize"],
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

::Rosetta <- {
    active = "ja",
    translate = function (_text) {
        if (this.active == null) return _text;
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
::Rosetta._ <- ::Rosetta.translate;

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
    return ::Rosetta.translate(_list[0]);
};

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/semantic_name_safety.nut", true);

function assertEqual(_actual, _expected)
{
    if (_actual != _expected) throw "Expected '" + _expected + "', got '" + _actual + "'";
}

// Ordinary item display remains localized, while the two audited semantic
// consumers see raw values and restore their nested scope on return.
local itemGetter = hooks["scripts/items/item"].getName(function () {
    return ::Rosetta.translate(this.m.Name);
});
local arrowItem = {m = {Name = "Broad Head Arrows"}};
arrowItem.getName <- itemGetter;
assertEqual(arrowItem.getName(), "幅広鏃の矢");

local poacherHit = hooks["scripts/skills/perks/perk_legend_specialist_poacher"].onTargetHit(function () {
    assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 2);
    return arrowItem.getName();
});
local poacherUse = hooks["scripts/skills/perks/perk_legend_specialist_poacher"].onAnySkillUsed(function () {
    assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 1);
    local ret = poacherHit();
    assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 1);
    return ret;
});
assertEqual(poacherUse(), "Broad Head Arrows");
assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 0);

// HedgeKnightTitles is both player-facing content and a generated actor name
// list. Only that exact list is raw during generation; other lists delegate.
local worldNameReceiver = ::Const.World.Common;
assertEqual(::Const.World.Common.generateName.call(worldNameReceiver, ::Const.Strings.HedgeKnightTitles), "The Lone Wolf");
assertEqual(generateNameCalls, 1);
if (generateNameReceiver != worldNameReceiver) throw "generateName receiver changed";
assertEqual(::Rosetta.active, "ja");
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
assertEqual(::Rosetta.active, "ja");

// Rosetta's installed actor hooks would translate at the getter. The safety
// wrapper must make every actor identity getter raw for every caller, because
// the installed snapshot has unbounded persistent/semantic consumers.
local actorNameGetter = hooks["scripts/entity/tactical/actor"].getName(function () {
    local name = ::Rosetta.translate(this.m.Name);
    local title = ::Rosetta.translate(this.m.Title);
    return title.len() == 0 ? name : name + " " + title;
});
local actorNameOnlyGetter = hooks["scripts/entity/tactical/actor"].getNameOnly(function () {
    return ::Rosetta.translate(this.m.Name);
});
local actorTitleGetter = hooks["scripts/entity/tactical/actor"].getTitle(function () {
    return ::Rosetta.translate(this.m.Title);
});
local actorKilledNameGetter = hooks["scripts/entity/tactical/actor"].getKilledName(function () {
    return ::Rosetta.translate(this.m.Name);
});
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
assertEqual(::Rosetta.active, "ja");

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
    return ::Rosetta.translate(this.m.Name);
});
assertEqual(namedItemDisplay.call(namedItem), "Aldric 一匹狼's Relic");
assertEqual(namedItem.m.Name, "Aldric The Lone Wolf's Relic");
local weedsItem = {m = {Name = "Asta Weeds' Sickle"}};
assertEqual(namedItemDisplay.call(weedsItem), "Asta 雑草' Sickle");
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
    assertEqual(namedItemDisplay.call(fixture[0]), fixture[1]);
}

// Any failing original must leave Rosetta active exactly as it was.
local failingActorGetter = hooks["scripts/entity/tactical/actor"].getName(function () {
    assertEqual(::Rosetta.active, null);
    throw "actor-getter-sentinel";
});
local actorErrorCaught = false;
try
{
    failingActorGetter.call(titledActor);
}
catch (error)
{
    actorErrorCaught = error == "actor-getter-sentinel";
}
if (!actorErrorCaught) throw "actor getter did not rethrow the original exception";
assertEqual(::Rosetta.active, "ja");

// Dog names remain localized in inventory but raw when copied into a tactical
// entity by each installed dog consumer.
local dogItem = {m = {Name = "Warrior the Warhound"}};
dogItem.getName <- itemGetter;
assertEqual(dogItem.getName(), "戦犬のウォリアー");
local unleashed = {Name = null};
local unleash = hooks["scripts/skills/actives/unleash_wardog"].onUse(function (_user, _tile) {
    unleashed.Name = dogItem.getName();
    return _user + _tile;
});
assertEqual(unleash("user", "tile"), "usertile");
assertEqual(unleashed.Name, "Warrior the Warhound");
local wardogCorpse = {Name = null};
local wardogDeath = hooks["scripts/items/accessory/wardog_item"].onActorDied(function (_killer) {
    wardogCorpse.Name = dogItem.getName();
    return _killer;
});
assertEqual(wardogDeath("killer"), "killer");
assertEqual(wardogCorpse.Name, "Warrior the Warhound");
local legendDogCorpse = {Name = null};
local legendDogDeath = hooks["scripts/items/accessory/legend_accessory_dog"].onActorDied(function (_killer) {
    legendDogCorpse.Name = dogItem.getName();
    return _killer;
});
assertEqual(legendDogDeath("legend-killer"), "legend-killer");
assertEqual(legendDogCorpse.Name, "Warrior the Warhound");
assertEqual(dogItem.m.Name, "Warrior the Warhound");
assertEqual(dogItem.getName(), "戦犬のウォリアー");
assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 0);

local failingDog = hooks["scripts/skills/actives/unleash_wardog"].onUse(function (...) {
    assertEqual(dogItem.getName(), "Warrior the Warhound");
    throw "dog-sentinel";
});
local dogErrorCaught = false;
try
{
    failingDog();
}
catch (error)
{
    dogErrorCaught = error == "dog-sentinel";
}
if (!dogErrorCaught) throw "dog scope did not rethrow the original exception";
assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 0);
assertEqual(::Rosetta.active, "ja");

// Background display remains localized except for the exact installed matcher.
local backgroundGetter = hooks["scripts/skills/backgrounds/character_background"].getNameOnly(function () {
    return ::Rosetta.translate("Donkey");
});
assertEqual(backgroundGetter(), "ロバ");
local training = hooks["scripts/skills/traits/legend_intensive_training_trait"].getTooltip(function () {
    return backgroundGetter() == "Donkey" ? "donkey-branch" : "wrong-branch";
});
assertEqual(training(), "donkey-branch");
assertEqual(::BattleBrothersJP.SemanticNameScopes.Background, 0);

// World identity remains raw globally, with labels localized after the exact
// display-producing lifecycle methods complete.
local worldGetter = hooks["scripts/entity/world/world_entity"].getName(function () {
    return ::Rosetta.translate(this.m.Name);
});
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

assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 0);
assertEqual(::BattleBrothersJP.SemanticNameScopes.Background, 0);
assertEqual(::Rosetta.active, "ja");
print("SEMANTIC_NAME_SAFETY_TEST_OK\n");
