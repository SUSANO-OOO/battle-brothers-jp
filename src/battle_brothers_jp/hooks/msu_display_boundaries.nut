// Optional MSU 1.9.0 final-UI projection. No MSU class is referenced unless
// preload has verified the optional MSU profile.
if ("MSUDisplayBoundariesInstalled" in ::BattleBrothersJP) return;
::BattleBrothersJP.MSUDisplayBoundariesInstalled <- true;

local Runtime = ::BattleBrothersJP.Runtime;
local mod = ::BattleBrothersJP.Mod;

local function cloneTranslatedUIData(_originalResult, _translateLabels)
{
    if (typeof _originalResult != "table") return _originalResult;
    local ret = clone _originalResult;
    if ("name" in ret) ret.name = Runtime.translate(ret.name);
    if (!_translateLabels || !("settings" in ret) || typeof ret.settings != "array") return ret;

    local settings = ret.settings.slice(0);
    foreach (index, setting in ret.settings)
    {
        if (typeof setting != "table" || !("labels" in setting)
            || typeof setting.labels != "array") continue;
        local copiedSetting = clone setting;
        local labels = setting.labels.slice(0);
        foreach (labelIndex, label in setting.labels)
            labels[labelIndex] = Runtime.translate(label);
        copiedSetting.labels = labels;
        settings[index] = copiedSetting;
    }
    ret.settings = settings;
    return ret;
}

local function hookGetUIData(_class, _translateLabels = false)
{
    local original = _class.getUIData;
    _class.getUIData = function (_flags = []) {
        local originalResult = original.call(this, _flags);
        try
        {
            return cloneTranslatedUIData(originalResult, _translateLabels);
        }
        catch (jpError)
        {
            return originalResult;
        }
    };
}

hookGetUIData(::MSU.Class.SettingsElement);
hookGetUIData(::MSU.Class.SettingsTitle);
hookGetUIData(::MSU.Class.SettingsPage, true);
hookGetUIData(::MSU.Class.SettingsPanel);

// MSU 1.9.0 extends the Vanilla tooltip dispatcher with this endpoint. It is
// absent without MSU, so this registration file is loaded only after an exact
// optional profile match. Preserve the original result and clone only text.
local function cloneTranslatedTooltip(_originalResult)
{
    if (typeof _originalResult != "array") return _originalResult;
    local ret = _originalResult.slice(0);
    foreach (index, entry in _originalResult)
    {
        if (typeof entry != "table" || !("text" in entry)) continue;
        local copied = clone entry;
        copied.text = Runtime.translate(entry.text);
        ret[index] = copied;
    }
    return ret;
}

mod.hook("scripts/ui/screens/tooltip/tooltip_events", function (q) {
    if (!q.contains("onQueryMSUTooltipData")) return;
    q.onQueryMSUTooltipData = @(__original) function (...) {
        vargv.insert(0, this);
        local originalResult = __original.acall(vargv);
        try
        {
            return cloneTranslatedTooltip(originalResult);
        }
        catch (jpError)
        {
            return originalResult;
        }
    }
});
