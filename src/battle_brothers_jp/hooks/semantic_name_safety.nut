// Rosetta 0.5.0 translates several name getters at their source. The pinned
// game/Legends snapshot consumes those getters through a broad, open-ended set
// of gameplay, identity, uniqueness, and persisted-data paths. Actor identity
// getters therefore stay source-language globally, like world-entity names.
// Localization is restored only at finite display boundaries in
// ui_boundaries.nut, event_variable_boundaries.nut, and the final JS renderer.

local mod = ::BattleBrothersJP.Mod;
local scopes = ::BattleBrothersJP.SemanticNameScopes <- {
    Item = 0
    Background = 0
};

local function callWithRosettaDisabled(_original, _self, _arguments)
{
    local activeLanguage = ::Rosetta.active;
    ::Rosetta.active = null;

    try
    {
        _arguments.insert(0, _self);
        local result = _original.acall(_arguments);
        ::Rosetta.active = activeLanguage;
        return result;
    }
    catch (error)
    {
        ::Rosetta.active = activeLanguage;
        throw error;
    }
}

local function makeSemanticScopeWrapper(_scopeName)
{
    return @(__original) function (...) {
        scopes[_scopeName] += 1;
        try
        {
            vargv.insert(0, this);
            local result = __original.acall(vargv);
            scopes[_scopeName] -= 1;
            return result;
        }
        catch (error)
        {
            scopes[_scopeName] -= 1;
            throw error;
        }
    }
}

local function translateReviewedActorNameDisplay(_text)
{
    if (typeof _text != "string") return _text;

    // Apply reviewed anchored full-value rules first (for example Dame plus a
    // generated name), then handle literal title fragments embedded in a raw
    // identity. Bare sources that require captures remain unchanged.
    local translatedText = ::Rosetta._(_text);
    foreach (pair in ::BattleBrothersJP.ActorTitleDisplayFragments)
    {
        local english = pair.english;
        local japanese = pair.japanese;

        local at = translatedText.find(english);
        if (at == null) continue;
        local after = at + english.len();
        local beforeChar = at == 0 ? "" : translatedText.slice(at - 1, at);
        local afterChar = after == translatedText.len() ? "" : translatedText.slice(after, after + 1);
        local beforeOK = at == 0 || [" ", "\n", ">", "]", "(", ":", "\"", "'"].find(beforeChar) != null;
        // Actor-derived named equipment uses the exact raw possessive shape
        // "<actor getName()>'s ...". Do not apply the full actor-title registry
        // to arbitrary item prose such as "Blood Vial of the Holy Mother".
        if (!beforeOK || afterChar != "'" || translatedText.find(english, after) != null) continue;
        translatedText = translatedText.slice(0, at) + japanese + translatedText.slice(after);
    }
    foreach (pair in ::BattleBrothersJP.ActorTitleGenericDisplayFragments)
    {
        local english = pair.english;
        local japanese = pair.japanese;
        local at = translatedText.find(english);
        if (at == null) continue;
        local after = at + english.len();
        local beforeChar = at == 0 ? "" : translatedText.slice(at - 1, at);
        local afterChar = after == translatedText.len() ? "" : translatedText.slice(after, after + 1);
        local beforeOK = at == 0 || [" ", "\n", ">", "]", "(", ":", "\"", "'"].find(beforeChar) != null;
        local afterOK = after == translatedText.len()
            || [" ", "\n", "'", "<", "[", ")", ".", ",", ":", "!", "?", "\""].find(afterChar) != null;
        if (!beforeOK || !afterOK || translatedText.find(english, after) != null) continue;
        translatedText = translatedText.slice(0, at) + japanese + translatedText.slice(after);
    }
    return translatedText;
}

// Item display names stay translated. Only audited consumers that use an item
// display name as an English matcher or copy it into a persistent/runtime
// identity receive the raw source name.
mod.hookTree("scripts/items/item", function (q) {
    q.getName = @(__original) function (...) {
        if (scopes.Item == 0)
        {
            vargv.insert(0, this);
            return translateReviewedActorNameDisplay(__original.acall(vargv));
        }
        return callWithRosettaDisabled(__original, this, vargv);
    }
});

mod.hook("scripts/skills/perks/perk_legend_specialist_poacher", function (q) {
    q.onAnySkillUsed = makeSemanticScopeWrapper("Item");
    q.onTargetHit = makeSemanticScopeWrapper("Item");
});

// Legends copies the item name into the spawned tactical dog in these exact
// methods. Keep that identity raw while the accessory/inventory label remains
// localized everywhere else.
mod.hook("scripts/skills/actives/unleash_wardog", function (q) {
    q.onUse = makeSemanticScopeWrapper("Item");
});

mod.hook("scripts/items/accessory/wardog_item", function (q) {
    q.onActorDied = makeSemanticScopeWrapper("Item");
});

mod.hook("scripts/items/accessory/legend_accessory_dog", function (q) {
    q.onActorDied = makeSemanticScopeWrapper("Item");
});

// HedgeKnightTitles doubles as player-facing actor titles and as a complete
// generated troop name list. Rosetta's buildTextFromTemplate wrapper would
// otherwise localize the selected name before Legends stores/serializes it.
// Disable Rosetta only for this exact list reference and preserve the final
// installed generator, receiver, RNG, arguments, and return value.
local generateWorldName = ::Const.World.Common.generateName;
::Const.World.Common.generateName = function (_list) {
    if (_list != ::Const.Strings.HedgeKnightTitles)
    {
        return generateWorldName.call(this, _list);
    }
    return callWithRosettaDisabled(generateWorldName, this, [_list]);
};

// Actor name getters have an unbounded semantic surface in the installed
// snapshot. Contracts persist getName() in flags, mood history coalesces and
// serializes strings containing it, named equipment copies it into m.Name,
// corpses copy it into resurrection identity, and mods may add more consumers.
// Keep the complete family raw globally; display-only boundaries translate
// reviewed title fragments without mutating actor, item, corpse, or save state.
mod.hookTree("scripts/entity/tactical/actor", function (q) {
    q.getName = @(__original) function (...) {
        return callWithRosettaDisabled(__original, this, vargv);
    }

    q.getNameOnly = @(__original) function (...) {
        return callWithRosettaDisabled(__original, this, vargv);
    }

    q.getTitle = @(__original) function (...) {
        return callWithRosettaDisabled(__original, this, vargv);
    }

    q.getKilledName = @(__original) function (...) {
        return callWithRosettaDisabled(__original, this, vargv);
    }
});

// Background display names stay translated. This exact tooltip method is the
// sole installed consumer that compares getNameOnly() with raw "Donkey".
mod.hook("scripts/skills/backgrounds/character_background", function (q) {
    q.getNameOnly = @(__original) function (...) {
        if (scopes.Background == 0)
        {
            vargv.insert(0, this);
            return __original.acall(vargv);
        }
        return callWithRosettaDisabled(__original, this, vargv);
    }
});

mod.hook("scripts/skills/traits/legend_intensive_training_trait", function (q) {
    q.getTooltip = makeSemanticScopeWrapper("Background");
});

// World getName() has a broad and open-ended semantic surface: Vanilla and
// Legends feed it into save flags, faction names, contract objectives, unique
// name checks, and derived party names. Keep it raw globally so a missed or
// future consumer cannot persist localized identity. Restore localization at
// the finite display boundaries below and in event_variable_boundaries.nut.
local function translateWorldNameLabel(_entity)
{
    if (!_entity.hasLabel("name")) return;
    local label = _entity.getLabel("name");
    if (typeof label.Text != "string") return;

    local rawName = _entity.getName();
    if (typeof rawName == "string" && label.Text.len() >= rawName.len() && label.Text.slice(0, rawName.len()) == rawName)
    {
        // Preserve updateStrength()'s exact computed suffix, e.g. " (4)".
        label.Text = ::Rosetta._(rawName) + label.Text.slice(rawName.len());
    }
    else
    {
        label.Text = ::Rosetta._(label.Text);
    }
}

mod.hook("scripts/entity/world/world_entity", function (q) {
    q.getName = @(__original) function (...) {
        return callWithRosettaDisabled(__original, this, vargv);
    }

    q.updateStrength = @(__original) function (...) {
        vargv.insert(0, this);
        local result = __original.acall(vargv);
        translateWorldNameLabel(this);
        return result;
    }

    q.onDeserialize = @(__original) function (...) {
        vargv.insert(0, this);
        local result = __original.acall(vargv);
        translateWorldNameLabel(this);
        return result;
    }
});

local initializeTranslatedWorldLabel = @(__original) function (...) {
    vargv.insert(0, this);
    local result = __original.acall(vargv);
    translateWorldNameLabel(this);
    return result;
};

mod.hook("scripts/entity/world/location", function (q) {
    q.onInit = initializeTranslatedWorldLabel;
});

mod.hook("scripts/entity/world/party", function (q) {
    q.onInit = initializeTranslatedWorldLabel;
});
