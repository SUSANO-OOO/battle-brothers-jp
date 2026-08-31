// Keep identity-bearing values raw and localize only reviewed display returns.
// Unlike the former Rosetta integration, the JP runtime never wraps actor or
// world getName() families. Their unbounded gameplay/save consumers therefore
// receive the original source value without a global-language toggle.

if ("SemanticNameSafetyInstalled" in ::BattleBrothersJP) return;
::BattleBrothersJP.SemanticNameSafetyInstalled <- true;

local mod = ::BattleBrothersJP.Mod;
local scopes = ::BattleBrothersJP.SemanticNameScopes <- {
    RawTemplate = 0
};

local function safeTranslate(_value)
{
    try { return ::BattleBrothersJP.Runtime.translate(_value); }
    catch (jpError) { return _value; }
}

local function translateReviewedActorNameDisplay(_text)
{
    if (typeof _text != "string") return _text;

    // Apply reviewed anchored full-value rules first (for example Dame plus a
    // generated name), then handle literal title fragments embedded in a raw
    // identity. Bare sources that require captures remain unchanged.
    local translatedText = safeTranslate(_text);
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

// Item identity is raw by default. Translate only while a finite UI producer
// has raised DisplayGetterScopeDepth; gameplay consumers need no compensation
// wrappers because they never observe the localized value.
mod.hookTree("scripts/items/item", function (q) {
    q.getName = @(__original) function (...) {
        vargv.insert(0, this);
        local rawName = __original.acall(vargv);
        local displayScope = "DisplayGetterScopeDepth" in ::BattleBrothersJP
            && ::BattleBrothersJP.DisplayGetterScopeDepth > 0;
        return displayScope ? translateReviewedActorNameDisplay(rawName) : rawName;
    }
});

// HedgeKnightTitles doubles as player-facing actor titles and a generated
// troop-name list. The JP buildTextFromTemplate display hook would otherwise
// localize the selected value before Legends persists it. Bypass JP template
// processing only for this exact list, without changing any global language.
local generateWorldName = ::Const.World.Common.generateName;
::Const.World.Common.generateName = function (_list) {
    if (_list != ::Const.Strings.HedgeKnightTitles)
    {
        return generateWorldName.call(this, _list);
    }
    scopes.RawTemplate += 1;
    try
    {
        local result = generateWorldName.call(this, _list);
        scopes.RawTemplate -= 1;
        return result;
    }
    catch (error)
    {
        scopes.RawTemplate -= 1;
        throw error;
    }
};

// World getName() has a broad and open-ended semantic surface: Vanilla and
// Legends feed it into save flags, faction names, contract objectives, unique
// name checks, and derived party names. Keep it raw globally so a missed or
// future consumer cannot persist localized identity. Restore localization at
// the finite display boundaries below and in event_variable_boundaries.nut.
local function translateWorldNameLabel(_entity)
{
    if (!_entity.hasLabel("name")) return;
    local label = _entity.getLabel("name");
    if (typeof label != "table" || !("Text" in label) || typeof label.Text != "string") return;

    local rawName = _entity.getName();
    if (typeof rawName == "string" && label.Text.len() >= rawName.len() && label.Text.slice(0, rawName.len()) == rawName)
    {
        // Preserve updateStrength()'s exact computed suffix, e.g. " (4)".
        label.Text = safeTranslate(rawName) + label.Text.slice(rawName.len());
    }
    else
    {
        label.Text = safeTranslate(label.Text);
    }
}

// This is JP-only post-processing after the original lifecycle method has
// already completed. Unknown MODs may provide an unusual label/getName shape;
// such a mismatch must preserve the original result instead of breaking the
// hook chain. Exceptions from the original lifecycle method remain untouched.
local function safelyTranslateWorldNameLabel(_entity)
{
    try { translateWorldNameLabel(_entity); }
    catch (jpError) {}
}

mod.hook("scripts/entity/world/world_entity", function (q) {
    q.updateStrength = @(__original) function (...) {
        vargv.insert(0, this);
        local result = __original.acall(vargv);
        safelyTranslateWorldNameLabel(this);
        return result;
    }

    q.onDeserialize = @(__original) function (...) {
        vargv.insert(0, this);
        local result = __original.acall(vargv);
        safelyTranslateWorldNameLabel(this);
        return result;
    }
});

local initializeTranslatedWorldLabel = @(__original) function (...) {
    vargv.insert(0, this);
    local result = __original.acall(vargv);
    safelyTranslateWorldNameLabel(this);
    return result;
};

mod.hook("scripts/entity/world/location", function (q) {
    q.onInit = initializeTranslatedWorldLabel;
});

mod.hook("scripts/entity/world/party", function (q) {
    q.onInit = initializeTranslatedWorldLabel;
});
