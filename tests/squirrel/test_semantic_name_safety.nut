local hooks = {};
local methodShapes = {
    ["scripts/items/item"] = ["getName"],
    ["scripts/items/accessory/legend_accessory_dog"] = ["onActorDied"],
    ["scripts/items/accessory/wardog_item"] = ["onActorDied"],
    ["scripts/skills/actives/unleash_wardog"] = ["onUse"],
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
            ["Warrior the Warhound"] = "戦犬のウォリアー"
        };
        return _text in translated ? translated[_text] : _text;
    }
};
::Rosetta._ <- ::Rosetta.translate;

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/semantic_name_safety.nut", true);

function assertEqual(_actual, _expected)
{
    if (_actual != _expected) throw "Expected '" + _expected + "', got '" + _actual + "'";
}

local rosettaItemGetter = function () {
    return ::Rosetta.translate("Broad Head Arrows");
};
local itemGetter = hooks["scripts/items/item"].getName(rosettaItemGetter);
// Ordinary inventory/UI calls stay localized.
assertEqual(itemGetter(), "幅広鏃の矢");

local poacherOriginal = function () {
    local raw = itemGetter();
    if (regexp("Broad Head").search(raw) == null) throw "Poacher semantic matcher no longer matches";
    return raw;
};
local poacherWrapper = hooks["scripts/skills/perks/perk_legend_specialist_poacher"].onAnySkillUsed(poacherOriginal);
assertEqual(poacherWrapper(), "Broad Head Arrows");
assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 0);

// The second audited Poacher consumer must receive the same raw item value,
// while nested semantic scopes remain balanced.
local poacherTargetHit = hooks["scripts/skills/perks/perk_legend_specialist_poacher"].onTargetHit(function () {
    assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 2);
    return itemGetter();
});
local nestedPoacher = hooks["scripts/skills/perks/perk_legend_specialist_poacher"].onAnySkillUsed(function () {
    assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 1);
    local ret = poacherTargetHit();
    assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 1);
    return ret;
});
assertEqual(nestedPoacher(), "Broad Head Arrows");
assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 0);

// The dog accessory is localized for inventory/UI display, but Legends must
// copy the raw identity into the spawned tactical entity in all three audited
// methods. The source item is never mutated.
local warriorItem = {m = {Name = "Warrior the Warhound"}};
local warriorGetter = hooks["scripts/items/item"].getName(function () {
    return ::Rosetta.translate(this.m.Name);
});
warriorItem.getName <- warriorGetter;
assertEqual(warriorItem.getName(), "戦犬のウォリアー");

local unleashedDog = {Name = null};
local unleashCalls = 0;
local unleashWrapper = hooks["scripts/skills/actives/unleash_wardog"].onUse(function (_user, _tile) {
    unleashCalls += 1;
    assertEqual(_user, "user");
    assertEqual(_tile, "tile");
    unleashedDog.Name = warriorItem.getName();
    return 31;
});
assertEqual(unleashWrapper("user", "tile"), 31);
assertEqual(unleashCalls, 1);
assertEqual(unleashedDog.Name, "Warrior the Warhound");

local fallenWardog = {Name = null};
local wardogDeathWrapper = hooks["scripts/items/accessory/wardog_item"].onActorDied(function (_killer) {
    assertEqual(_killer, "killer");
    fallenWardog.Name = warriorItem.getName();
    return 37;
});
assertEqual(wardogDeathWrapper("killer"), 37);
assertEqual(fallenWardog.Name, "Warrior the Warhound");

local fallenLegendDog = {Name = null};
local legendDogDeathWrapper = hooks["scripts/items/accessory/legend_accessory_dog"].onActorDied(function (_killer) {
    assertEqual(_killer, "legend-killer");
    fallenLegendDog.Name = warriorItem.getName();
    return 41;
});
assertEqual(legendDogDeathWrapper("legend-killer"), 41);
assertEqual(fallenLegendDog.Name, "Warrior the Warhound");
assertEqual(warriorItem.m.Name, "Warrior the Warhound");
assertEqual(warriorItem.getName(), "戦犬のウォリアー");

// An exception must restore the counter and active language before escaping.
local failingDogWrapper = hooks["scripts/skills/actives/unleash_wardog"].onUse(function (_user, _tile) {
    assertEqual(warriorItem.getName(), "Warrior the Warhound");
    throw "dog-sentinel";
});
local dogErrorCaught = false;
try
{
    failingDogWrapper("user", "tile");
}
catch (error)
{
    dogErrorCaught = error == "dog-sentinel";
}
if (!dogErrorCaught) throw "dog semantic scope did not rethrow the original exception";
assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 0);
assertEqual(::Rosetta.active, "ja");
assertEqual(warriorItem.getName(), "戦犬のウォリアー");

local rosettaBackgroundGetter = function () {
    return ::Rosetta.translate("Donkey");
};
local backgroundGetter = hooks["scripts/skills/backgrounds/character_background"].getNameOnly(rosettaBackgroundGetter);
assertEqual(backgroundGetter(), "ロバ");
local trainingOriginal = function () {
    return backgroundGetter() == "Donkey" ? "donkey-branch" : "wrong-branch";
};
local trainingWrapper = hooks["scripts/skills/traits/legend_intensive_training_trait"].getTooltip(trainingOriginal);
assertEqual(trainingWrapper(), "donkey-branch");
assertEqual(::BattleBrothersJP.SemanticNameScopes.Background, 0);

local rosettaWorldGetter = function () {
    return ::Rosetta.translate(this.m.Name);
};
local worldGetter = hooks["scripts/entity/world/world_entity"].getName(rosettaWorldGetter);
local settlement = {
    m = { Name = "Hohenburg" },
    label = { Text = null },
    hasLabel = function (_name) { return _name == "name"; },
    getLabel = function (_name) { return this.label; }
};
settlement.getName <- worldGetter;
assertEqual(settlement.getName(), "Hohenburg");

local originalUpdateStrength = function () {
    this.label.Text = this.getName() + " (4)";
    return 17;
};
local safeUpdateStrength = hooks["scripts/entity/world/world_entity"].updateStrength(originalUpdateStrength);
assertEqual(safeUpdateStrength.call(settlement), 17);
assertEqual(settlement.label.Text, "ホーエンブルク (4)");
assertEqual(settlement.m.Name, "Hohenburg");

local originalOnInit = function () {
    this.label.Text = this.getName();
    return 23;
};
local safePartyOnInit = hooks["scripts/entity/world/party"].onInit(originalOnInit);
settlement.label.Text = null;
assertEqual(safePartyOnInit.call(settlement), 23);
assertEqual(settlement.label.Text, "ホーエンブルク");

// Successful scoped calls restore both scope and language exactly.
assertEqual(::BattleBrothersJP.SemanticNameScopes.Item, 0);
assertEqual(::Rosetta.active, "ja");

print("SEMANTIC_NAME_SAFETY_TEST_OK\n");
