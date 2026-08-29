// Rosetta 0.5.0 translates several name getters at their source. The pinned
// game/Legends snapshot also consumes a few of those getters as gameplay,
// identity, uniqueness, or persisted-data inputs. Keep normal display calls
// localized, but expose source-language names inside only the audited semantic
// consumers below. The scope counters are restored on success and exception.

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

// Item display names stay translated. Only the two Poacher methods that match
// the English ammo-name tokens "Piercing" and "Broad Head" receive raw names.
mod.hookTree("scripts/items/item", function (q) {
    q.getName = @(__original) function (...) {
        if (scopes.Item == 0)
        {
            vargv.insert(0, this);
            return __original.acall(vargv);
        }
        return callWithRosettaDisabled(__original, this, vargv);
    }
});

mod.hook("scripts/skills/perks/perk_legend_specialist_poacher", function (q) {
    q.onAnySkillUsed = makeSemanticScopeWrapper("Item");
    q.onTargetHit = makeSemanticScopeWrapper("Item");
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
