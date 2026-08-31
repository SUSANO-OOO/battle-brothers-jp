// JP-owned finite display boundaries replacing the safe subset of Rosetta's
// hook pack. Every wrapper calls the original exactly once. Post-processing
// touches a copy of returned UI data; a JP-only error returns the saved raw
// result, while an original exception remains visible to the game/hook chain.

if ("RuntimeDisplayBoundariesInstalled" in ::BattleBrothersJP) return;
::BattleBrothersJP.RuntimeDisplayBoundariesInstalled <- true;

local mod = ::BattleBrothersJP.Mod;
local Runtime = ::BattleBrothersJP.Runtime;
if (!("DisplayGetterScopeDepth" in ::BattleBrothersJP))
    ::BattleBrothersJP.DisplayGetterScopeDepth <- 0;

local function translateValue(_value)
{
    return Runtime.translate(_value);
}

local translatedGetter = @(__original) function (...) {
    vargv.insert(0, this);
    local originalResult = __original.acall(vargv);
    try
    {
        return translateValue(originalResult);
    }
    catch (jpError)
    {
        return originalResult;
    }
};

// Item/skill/entity/scenario getters have gameplay and unknown-MOD consumers.
// Keep them raw by default and translate only while a finite original UI
// producer is executing. Nested display producers compose through the counter.
local displayScopedGetter = @(__original) function (...) {
    vargv.insert(0, this);
    local originalResult = __original.acall(vargv);
    if (::BattleBrothersJP.DisplayGetterScopeDepth == 0) return originalResult;
    try { return translateValue(originalResult); }
    catch (jpError) { return originalResult; }
};

local function callOriginalInDisplayScope(_original, _args)
{
    ::BattleBrothersJP.DisplayGetterScopeDepth += 1;
    try
    {
        local result = _original.acall(_args);
        ::BattleBrothersJP.DisplayGetterScopeDepth -= 1;
        return result;
    }
    catch (originalError)
    {
        ::BattleBrothersJP.DisplayGetterScopeDepth -= 1;
        throw originalError;
    }
}

local function cloneTranslatedTooltip(_originalResult)
{
    if (typeof _originalResult != "array") return _originalResult;
    local ret = _originalResult.slice(0);
    foreach (index, entry in _originalResult)
    {
        if (typeof entry != "table" || !("text" in entry)) continue;
        local copied = clone entry;
        copied.text = translateValue(entry.text);
        ret[index] = copied;
    }
    return ret;
}

local tooltipHook = @(__original) function (...) {
    vargv.insert(0, this);
    local originalResult = callOriginalInDisplayScope(__original, vargv);
    try
    {
        return cloneTranslatedTooltip(originalResult);
    }
    catch (jpError)
    {
        return originalResult;
    }
};

local function cloneTranslatedLists(_originalResult)
{
    if (typeof _originalResult != "array") return _originalResult;
    local ret = _originalResult.slice(0);
    foreach (listIndex, list in _originalResult)
    {
        if (typeof list != "table") continue;
        local copiedList = clone list;
        if ("title" in copiedList) copiedList.title = translateValue(copiedList.title);
        if ("items" in list && typeof list.items == "array")
        {
            local copiedItems = list.items.slice(0);
            foreach (itemIndex, item in list.items)
            {
                if (typeof item != "table" || !("text" in item)) continue;
                local copiedItem = clone item;
                copiedItem.text = translateValue(item.text);
                copiedItems[itemIndex] = copiedItem;
            }
            copiedList.items = copiedItems;
        }
        ret[listIndex] = copiedList;
    }
    return ret;
}

local listHook = @(__original) function (...) {
    vargv.insert(0, this);
    local originalResult = __original.acall(vargv);
    try
    {
        return cloneTranslatedLists(originalResult);
    }
    catch (jpError)
    {
        return originalResult;
    }
};

mod.hookTree("scripts/items/item", function (q) {
    q.getDescription = displayScopedGetter;
});

mod.hookTree("scripts/skills/skill", function (q) {
    q.getName = displayScopedGetter;
    q.getDescription = displayScopedGetter;
});

mod.hookTree("scripts/entity/tactical/entity", function (q) {
    q.getDescription = displayScopedGetter;
});

mod.hookTree("scripts/scenarios/world/starting_scenario", function (q) {
    q.getName = displayScopedGetter;
    q.getDescription = displayScopedGetter;
});

mod.hook("scripts/scenarios/scenario_manager", function (q) {
    q.getScenariosForUI = @(__original) function (...) {
        vargv.insert(0, this);
        return callOriginalInDisplayScope(__original, vargv);
    };
});

mod.hook("scripts/ui/screens/tactical/modules/topbar/tactical_screen_topbar_event_log", function (q) {
    q.log = @(__original) function (_text) {
        local displayText = _text;
        try { displayText = translateValue(_text); } catch (jpError) {}
        return __original(displayText);
    };
    q.logEx = @(__original) function (_text) {
        local displayText = _text;
        try { displayText = translateValue(_text); } catch (jpError) {}
        return __original(displayText);
    };
});

mod.hook("scripts/ui/screens/dialog_screen", function (q) {
    q.show = @(__original) function (_title, _text, _doneCallback, _okCallback = null, _cancelCallback = null, _isMonologue = false) {
        local title = _title;
        local text = _text;
        try
        {
            title = translateValue(_title);
            text = translateValue(_text);
        }
        catch (jpError)
        {
            title = _title;
            text = _text;
        }
        return __original(title, text, _doneCallback, _okCallback, _cancelCallback, _isMonologue);
    };
});

mod.hook("scripts/ui/screens/tactical/tactical_combat_result_screen", function (q) {
    q.onQueryCombatInformation = @(__original) function () {
        local originalResult = __original();
        try
        {
            if (typeof originalResult != "table") return originalResult;
            local ret = clone originalResult;
            if ("title" in ret) ret.title = translateValue(ret.title);
            if ("subTitle" in ret) ret.subTitle = translateValue(ret.subTitle);
            return ret;
        }
        catch (jpError)
        {
            return originalResult;
        }
    };
});

mod.hook("scripts/ui/screens/loading/loading_screen", function (q) {
    q.onQueryData = @(__original) function () {
        local originalResult = __original();
        try
        {
            if (typeof originalResult != "table") return originalResult;
            local ret = clone originalResult;
            if ("text" in ret) ret.text = translateValue(ret.text);
            return ret;
        }
        catch (jpError)
        {
            return originalResult;
        }
    };
});

mod.hook("scripts/ui/screens/tooltip/tooltip_events", function (q) {
    q.onQueryTileTooltipData = tooltipHook;
    q.onQueryEntityTooltipData = tooltipHook;
    q.onQueryRosterEntityTooltipData = tooltipHook;
    q.onQuerySkillTooltipData = tooltipHook;
    q.onQueryStatusEffectTooltipData = tooltipHook;
    q.onQuerySettlementStatusEffectTooltipData = tooltipHook;
    q.onQueryUIElementTooltipData = tooltipHook;
    q.onQueryUIItemTooltipData = tooltipHook;
    q.onQueryUIPerkTooltipData = tooltipHook;
    q.onQueryFollowerTooltipData = tooltipHook;
});

mod.hook("scripts/events/event", function (q) {
    q.getUIList = listHook;
    q.getUIButtons = @(__original) function () {
        local originalResult = __original();
        try
        {
            if (typeof originalResult != "array") return originalResult;
            local ret = originalResult.slice(0);
            foreach (index, button in originalResult)
            {
                if (typeof button != "table" || !("tooltip" in button)) continue;
                local copied = clone button;
                copied.tooltip = translateValue(button.tooltip);
                ret[index] = copied;
            }
            return ret;
        }
        catch (jpError)
        {
            return originalResult;
        }
    };
});

mod.hook("scripts/contracts/contract", function (q) {
    q.getUITitle = translatedGetter;
    q.getUIList = listHook;
});
