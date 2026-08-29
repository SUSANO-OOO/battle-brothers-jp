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

// world_entity.getName() intentionally stays source-language because the
// installed game and Legends also use it for identity, unique-name selection,
// and persisted values. Settlement information is a direct JS DTO, so
// localize its display fields here instead of localizing the semantic getter.
mod.hook("scripts/entity/world/settlement", function (q) {
    q.getUIInformation = @(__original) function () {
        local ret = __original();
        if (ret == null) return ret;
        if ("Title" in ret && ret.Title != null) ret.Title = ::Rosetta._(ret.Title);
        if ("SubTitle" in ret && ret.SubTitle != null) ret.SubTitle = ::Rosetta._(ret.SubTitle);
        return ret;
    }
});

// The port building does not use settlement.getUIInformation(). It assembles a
// separate travel-dialog DTO from semantic settlement names, so translate only
// that returned DTO. The raw settlement objects and their getName() values stay
// unchanged for identity, routing, costs, ownership, and persistence.
mod.hook("scripts/entity/world/settlements/buildings/port_building", function (q) {
    q.getUITravelRoster = @(__original) function () {
        local ret = __original();
        if (typeof ret != "table") return ret;

        if ("Title" in ret && typeof ret.Title == "string") ret.Title = ::Rosetta._(ret.Title);
        if ("SubTitle" in ret && typeof ret.SubTitle == "string") ret.SubTitle = ::Rosetta._(ret.SubTitle);
        if (!("Roster" in ret) || typeof ret.Roster != "array") return ret;

        foreach (entry in ret.Roster)
        {
            if (typeof entry != "table") continue;

            local rawName = "Name" in entry && typeof entry.Name == "string" ? entry.Name : null;
            if (rawName != null)
            {
                local translatedName = ::Rosetta._(rawName);
                entry.Name = translatedName;

                if ("ListName" in entry && typeof entry.ListName == "string")
                {
                    local exactEnglishListName = "Sail to " + rawName;
                    entry.ListName = entry.ListName == exactEnglishListName
                        ? "船で" + translatedName + "へ向かう"
                        : ::Rosetta._(entry.ListName);
                }
            }

            if ("BackgroundText" in entry && typeof entry.BackgroundText == "string")
            {
                // getRandomDescription() has already passed through the global
                // template boundary. Only the settlement-description prefix is
                // a raw direct getter; preserve the rendered suffix byte-for-byte.
                local separator = "<br><br>";
                local separatorAt = entry.BackgroundText.find(separator);
                entry.BackgroundText = separatorAt == null
                    ? ::Rosetta._(entry.BackgroundText)
                    : ::Rosetta._(entry.BackgroundText.slice(0, separatorAt))
                        + separator + entry.BackgroundText.slice(separatorAt + separator.len());
            }
        }

        return ret;
    }
});

// Context-split localization: "Play" is also a scenario button. Named armor
// persists m.Name, so never translate Const.Strings.NameList or m.Name itself.
// Replace the exact generated suffix only in the value returned for display.
local function translateGeneratedArmorName(_name)
{
    if (typeof _name != "string") return _name;
    if (_name == "Play") return "戯れ";
    if (::std.Str.endswith(_name, " Play"))
    {
        return ::std.Str.cutsuffix(_name, " Play") + " 戯れ";
    }
    return _name;
}

local generatedArmorNameHook = @(__original) function (...) {
    vargv.insert(0, this);
    return translateGeneratedArmorName(__original.acall(vargv));
};

mod.hook("scripts/items/legend_armor/legend_named_armor", function (q) {
    q.getName = generatedArmorNameHook;
});
mod.hook("scripts/items/legend_armor/legend_named_armor_upgrade", function (q) {
    q.getName = generatedArmorNameHook;
});
mod.hook("scripts/items/legend_helmets/legend_named_helmet", function (q) {
    q.getName = generatedArmorNameHook;
});
mod.hook("scripts/items/legend_helmets/legend_named_helmet_upgrade", function (q) {
    q.getName = generatedArmorNameHook;
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
