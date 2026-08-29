// Narrow UI-boundary hooks for the pinned supported snapshot.
// These wrappers only translate returned display strings. They do not mutate
// gameplay state, balance values, save data, or source objects.

local mod = ::BattleBrothersJP.Mod;

// Translate only a metric suffix on one known tooltip entry.  The calculated
// and colorized value is copied byte-for-byte; the wrapper never recomputes a
// gameplay value or changes any tooltip metadata.
local function translateMetricSuffix(_entries, _icon, _englishSuffix, _japaneseLabel)
{
    if (typeof _entries != "array") return _entries;

    foreach (entry in _entries)
    {
        if (typeof entry != "table" || !("text" in entry) || !("icon" in entry)) continue;
        if (entry.icon != _icon || typeof entry.text != "string") continue;
        if (!::std.Str.endswith(entry.text, _englishSuffix)) continue;

        local leadingValue = ::std.Str.cutsuffix(entry.text, _englishSuffix);
        entry.text = _japaneseLabel + " " + leadingValue;
    }

    return _entries;
}

// Legends Adaptive constructs a colored list after a prefix, so neither the
// prefix nor the enumeration fragment reaches Rosetta as an independent final
// string.  Translate the two fixed prefixes and each isolated group name, then
// rebuild only the text field while preserving the original color wrapper.
local function translateAdaptiveHintText(_text)
{
    if (typeof _text != "string") return _text;

    local englishSingle = "Activating this Perk will grant the following Perk Group:\n";
    local englishRandom = "Activating this Perk will randomly grant one of the following Perk Groups:\n";
    local englishPrefix = null;
    local japanesePrefix = null;

    if (::std.Str.startswith(_text, englishSingle))
    {
        englishPrefix = englishSingle;
        japanesePrefix = "このパークを有効化すると、以下のパークグループを獲得する：\n";
    }
    else if (::std.Str.startswith(_text, englishRandom))
    {
        englishPrefix = englishRandom;
        japanesePrefix = "このパークを有効化すると、以下のパークグループからランダムに1つ獲得する：\n";
    }
    else
    {
        return _text;
    }

    local colorOpen = "[color=#0b0084]";
    local colorClose = "[/color]";
    local colorStart = _text.find(colorOpen);
    if (colorStart == null || colorStart != englishPrefix.len()) return _text;
    if (!::std.Str.endswith(_text, colorClose)) return _text;

    local innerStart = colorStart + colorOpen.len();
    local inner = _text.slice(innerStart, -colorClose.len());
    local names = [];
    local lastPair = ::std.Str.split(", or ", inner);

    if (lastPair.len() == 1)
    {
        names.push(lastPair[0]);
    }
    else if (lastPair.len() == 2)
    {
        names.extend(::std.Str.split(", ", lastPair[0]));
        names.push(lastPair[1]);
    }
    else
    {
        return _text;
    }

    local translatedNames = [];
    foreach (name in names) translatedNames.push(::Rosetta._(name));

    local translatedList;
    if (translatedNames.len() == 1)
    {
        translatedList = translatedNames[0];
    }
    else
    {
        translatedList = ::std.Str.join("、", translatedNames.slice(0, -1));
        translatedList += "、または " + translatedNames.top();
    }

    return japanesePrefix + colorOpen + translatedList + colorClose;
}

// Ambition progress text is sent directly to the world topbar. Rosetta 0.5.0
// has no ambition hook, so translate the final text returned by every ambition
// implementation, including subclasses that override getUIText().
mod.hookTree("scripts/ambitions/ambition", function (q) {
    q.getUIText = @(__original) function () {
        return ::Rosetta._(__original());
    }
});

// Rosetta 0.5.0 translates skill names/descriptions and completed tooltips but
// not the death-reason getter. Translate only its returned display string.
mod.hookTree("scripts/skills/skill", function (q) {
    q.getKilledString = @(__original) function () {
        return ::Rosetta._(__original());
    }
});

// Legends camp crafting sends Title/SubTitle directly to its JS module through
// queryLoad(). Translate only those two UI fields at the Squirrel/JS boundary.
mod.hook("scripts/ui/screens/world/modules/camp_screen/camp_crafting_dialog_module", function (q) {
    q.queryLoad = @(__original) function () {
        local ret = __original();
        if (ret == null) return ret;
        if ("Title" in ret && ret.Title != null) ret.Title = ::Rosetta._(ret.Title);
        if ("SubTitle" in ret && ret.SubTitle != null) ret.SubTitle = ::Rosetta._(ret.SubTitle);
        return ret;
    }
});

// Context-split localization: "Play" is also a scenario button.  Only the
// Legends generated armor-name component receives the noun "戯れ" here.
if ("LegendArmorLayers" in ::Const.Strings) {
    foreach (index, value in ::Const.Strings.LegendArmorLayers) {
        if (value == "Play") ::Const.Strings.LegendArmorLayers[index] = "戯れ";
    }
}

// Context-split localization: MSU uses "General" for its settings page while
// this contract uses it as a generated enemy title.  Change only the display
// flag after the original start logic has selected the title.
mod.hook("scripts/contracts/contracts/find_artifact_contract", function (q) {
    q.start = @(__original) function () {
        __original();
        if (this.m.Flags.get("NemesisNameS") == "General") {
            this.m.Flags.set("NemesisNameS", "将軍");
        }
    }
});

// Legends Adaptive returns a completed dynamic sentence that cannot be
// represented safely as one global literal/pattern rule.
mod.hook("scripts/skills/perks/perk_legend_adaptive", function (q) {
    q.getUnactivatedPerkTooltipHints = @(__original) function (_actor = null) {
        local ret = __original(_actor);
        if (typeof ret != "array") return ret;
        foreach (entry in ret) {
            if (typeof entry == "table" && "text" in entry) {
                entry.text = translateAdaptiveHintText(entry.text);
            }
        }
        return ret;
    }
});

// These class-scoped wrappers disambiguate identical generated suffix shapes
// without installing competing global Rosetta patterns.
mod.hook("scripts/skills/perks/perk_legend_barter_greed", function (q) {
    q.getTooltip = @(__original) function () {
        local ret = __original();
        translateMetricSuffix(ret, "ui/icons/melee_defense.png", " Melee Defense", "近接防御");
        translateMetricSuffix(ret, "ui/icons/ranged_defense.png", " Ranged Defense", "射撃防御");
        return ret;
    }
});

mod.hook("scripts/skills/perks/perk_legend_perfect_fit", function (q) {
    q.getTooltip = @(__original) function () {
        return translateMetricSuffix(__original(), "ui/icons/initiative.png", " Initiative", "先制値");
    }

    q.getUnactivatedPerkTooltipHints = @(__original) function (_actor = null) {
        return translateMetricSuffix(__original(_actor), "ui/icons/initiative.png", " Initiative", "先制値");
    }
});

mod.hook("scripts/skills/perks/perk_legend_small_target", function (q) {
    q.getTooltip = @(__original) function () {
        local ret = __original();
        translateMetricSuffix(ret, "ui/icons/melee_defense.png", " Melee Defense", "近接防御");
        translateMetricSuffix(ret, "ui/icons/ranged_defense.png", " Ranged Defense", "射撃防御");
        return ret;
    }
});
