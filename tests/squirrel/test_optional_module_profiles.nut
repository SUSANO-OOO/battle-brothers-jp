local queues = [];
local required = [];
local includedHooks = [];
local jsFiles = [];
local cssFiles = [];

local mod = {
    require = function (...) {
        foreach (value in vargv) required.push(value);
    },
    queue = function (...) {
        local args = vargv.slice(0);
        local bucket = typeof args.top() == "integer" ? args.pop() : 0;
        local callback = args.pop();
        queues.push({Bucket = bucket, Relations = args, Callback = callback});
    }
};

::Hooks <- {
    Mods = {},
    QueueBucket = {Normal = 3, Late = 4},
    register = function (_id, _version, _name) { return mod; },
    hasMod = function (_id) { return _id in this.Mods; },
    getMod = function (_id) { return this.Mods[_id]; },
    registerJS = function (_path) { jsFiles.push(_path); },
    registerCSS = function (_path) { cssFiles.push(_path); }
};

::include <- function (_path) {
    if (_path == "battle_brothers_jp/runtime/core"
        || _path == "battle_brothers_jp/translations/reviewed_literals")
    {
        return dofile(getenv("BBJP_ROOT") + "src/" + _path + ".nut", true);
    }
    includedHooks.push(_path);
};

local function version(_value)
{
    return {Value = _value, getVersionString = function () { return this.Value; }};
}

function assertEqual(_actual, _expected, _label)
{
    if (_actual != _expected) throw _label + " expected '" + _expected + "', got '" + _actual + "'";
}

local function resetHarness(_mods)
{
    queues.clear();
    required.clear();
    includedHooks.clear();
    jsFiles.clear();
    cssFiles.clear();
    ::Hooks.Mods = _mods;
    if ("BattleBrothersJP" in getroottable()) delete getroottable().BattleBrothersJP;
    dofile(getenv("BBJP_ROOT") + "src/scripts/!mods_preload/mod_battle_brothers_jp.nut", true);
    assertEqual(queues.len(), 3, "queue count");
    assertEqual(queues[0].Bucket, ::Hooks.QueueBucket.Normal, "profile queue bucket");
    assertEqual(queues[0].Relations.len(), 0, "profile queue relations");
    assertEqual(queues[1].Bucket, ::Hooks.QueueBucket.Late, "common hook queue bucket");
    assertEqual(queues[1].Relations[0], ">mod_legends", "common queue after Legends");
    assertEqual(queues[1].Relations[1], ">mod_rosetta", "common queue after optional Rosetta");
    assertEqual(queues[2].Bucket, ::Hooks.QueueBucket.Late, "MSU hook queue bucket");
    assertEqual(queues[2].Relations[0], ">mod_msu", "MSU queue after MSU");
    assertEqual(queues[2].Relations[1], ">mod_rosetta", "MSU queue after optional Rosetta");
    queues[0].Callback();
}

local baseProfile = {
    vanilla = version("1.5.2-3"),
    mod_modern_hooks = version("0.6.0")
};
resetHarness(baseProfile);
assertEqual(required.len(), 1, "hard dependency count");
assertEqual(required[0], "mod_modern_hooks >= 0.6.0", "hard dependency");
assertEqual(::BattleBrothersJP.ModuleStatus.vanilla.Enabled, true, "vanilla enabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_lindwurm.Enabled, false, "absent Lindwurm DLC disabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_unhold.Enabled, false, "absent Unhold DLC disabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_wildmen.Enabled, false, "absent Wildmen DLC disabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_desert.Enabled, false, "absent Desert DLC disabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_paladins.Enabled, false, "absent Paladins DLC disabled");
assertEqual(::BattleBrothersJP.ModuleStatus.legends.Enabled, false, "absent Legends disabled");
assertEqual(::BattleBrothersJP.ModuleStatus.msu.Enabled, false, "absent MSU disabled");
assertEqual(::BattleBrothersJP.Runtime.translate("%archerfull%, try to knock it down with an arrow?"),
    "%archerfull%、矢で撃ち落とせるか？", "Vanilla profile exact");
assertEqual(::BattleBrothersJP.Runtime.translate("\n\nBut for now, you keep running."),
    "\n\nBut for now, you keep running.", "absent Legends English pass-through");
assertEqual(jsFiles.len(), 3, "Vanilla JS registration count");
assertEqual(jsFiles[0], "ui/mods/mod_battle_brothers_jp/generated_strings.js", "Vanilla JS dictionary");
assertEqual(jsFiles[1], "ui/mods/mod_battle_brothers_jp/generated_strings_modern_hooks.js", "Modern Hooks JS dictionary");
assertEqual(jsFiles[2], "ui/mods/mod_battle_brothers_jp/main.js", "JS boundary registration");
assertEqual(cssFiles.len(), 1, "CSS registration count");
queues[1].Callback();
assertEqual(includedHooks.len(), 5, "common late hook includes");
queues[2].Callback();
assertEqual(includedHooks.len(), 5, "absent MSU hook include");

local supported = {
    vanilla = version("1.5.2-3"),
    dlc_lindwurm = version("1.0.0"),
    dlc_unhold = version("1.0.0"),
    dlc_wildmen = version("1.0.0"),
    dlc_desert = version("1.0.0"),
    dlc_paladins = version("1.0.0"),
    mod_modern_hooks = version("0.6.0"),
    mod_legends = version("19.4.20"),
    mod_legends_assets = version("19.4.3"),
    mod_msu = version("1.9.0"),
    mod_hooks = version("21.1"),
    mod_events_delayed_fix_legends = version("0.7"),
    mod_Jimmys_Tooltips_legends = version("1.0.5"),
    mod_legends_load_order_fix = version("19.4.20"),
    mod_legends_compat_check = version("19.4.20")
};
resetHarness(supported);
assertEqual(::BattleBrothersJP.ModuleStatus.legends.Enabled, true, "supported Legends enabled");
assertEqual(::BattleBrothersJP.ModuleStatus.legacy_hooks.Verified, true, "legacy mod_hooks coexistence profile");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_lindwurm.Enabled, true, "supported Lindwurm DLC enabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_unhold.Enabled, true, "supported Unhold DLC enabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_wildmen.Enabled, true, "supported Wildmen DLC enabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_desert.Enabled, true, "supported Desert DLC enabled");
assertEqual(::BattleBrothersJP.ModuleStatus.dlc_paladins.Enabled, true, "supported Paladins DLC enabled");
assertEqual(::BattleBrothersJP.Runtime.translate("\n\nBut for now, you keep running."),
    "\n\nだが今は、ただ走り続ける。", "supported Legends exact");
assertEqual(::BattleBrothersJP.Runtime.translate("Add"), "追加", "supported MSU exact");
assertEqual(jsFiles.len(), 5, "supported optional JS registration count");
assertEqual(jsFiles[1], "ui/mods/mod_battle_brothers_jp/generated_strings_legends.js", "Legends JS dictionary");
assertEqual(jsFiles[2], "ui/mods/mod_battle_brothers_jp/generated_strings_msu.js", "MSU JS dictionary");
queues[2].Callback();
assertEqual(includedHooks[0], "battle_brothers_jp/hooks/msu_display_boundaries", "MSU hook include");

local mismatched = {
    vanilla = version("1.5.2-3"),
    mod_modern_hooks = version("0.6.0"),
    mod_legends = version("19.4.21"),
    mod_legends_assets = version("19.4.3")
};
resetHarness(mismatched);
assertEqual(::BattleBrothersJP.ModuleStatus.legends.Present, true, "mismatched Legends present");
assertEqual(::BattleBrothersJP.ModuleStatus.legends.Enabled, false, "mismatched Legends disabled");
assertEqual(::BattleBrothersJP.Runtime.translate("\n\nBut for now, you keep running."),
    "\n\nBut for now, you keep running.", "mismatched Legends English pass-through");

local unknownVanilla = {
    vanilla = version("1.5.2-4"),
    mod_modern_hooks = version("0.6.0")
};
resetHarness(unknownVanilla);
assertEqual(::BattleBrothersJP.ModuleStatus.vanilla.Enabled, false, "unknown Vanilla disabled");
assertEqual(::BattleBrothersJP.Runtime.translate("%archerfull%, try to knock it down with an arrow?"),
    "%archerfull%, try to knock it down with an arrow?", "unknown Vanilla English pass-through");
assertEqual(jsFiles.len(), 0, "unknown Vanilla has no JS registrations");
assertEqual(cssFiles.len(), 0, "unknown Vanilla has no CSS registrations");
queues[1].Callback();
assertEqual(includedHooks.len(), 0, "unknown Vanilla common hooks disabled");

local mixedUnknownBase = {
    vanilla = version("1.5.2-4"),
    dlc_lindwurm = version("1.0.0"),
    dlc_unhold = version("1.0.0"),
    dlc_wildmen = version("1.0.0"),
    dlc_desert = version("1.0.0"),
    dlc_paladins = version("1.0.0"),
    mod_modern_hooks = version("0.6.0"),
    mod_legends = version("19.4.20"),
    mod_legends_assets = version("19.4.3"),
    mod_msu = version("1.9.0"),
    mod_hooks = version("21.1"),
    mod_events_delayed_fix_legends = version("0.7"),
    mod_Jimmys_Tooltips_legends = version("1.0.5"),
    mod_legends_load_order_fix = version("19.4.20"),
    mod_legends_compat_check = version("19.4.20")
};
resetHarness(mixedUnknownBase);
assertEqual(::BattleBrothersJP.ModuleStatus.legends.Enabled, false, "Legends disabled on unknown base");
assertEqual(::BattleBrothersJP.ModuleStatus.msu.Enabled, false, "MSU disabled on unknown base");
assertEqual(::BattleBrothersJP.Runtime.translate("\n\nBut for now, you keep running."),
    "\n\nBut for now, you keep running.", "unknown base keeps Legends English");
assertEqual(jsFiles.len(), 0, "unknown base disables all JS boundaries");
assertEqual(cssFiles.len(), 0, "unknown base disables all CSS boundaries");
queues[1].Callback();
assertEqual(includedHooks.len(), 0, "unknown base disables common hooks");

print("OPTIONAL_MODULE_PROFILES_TEST_OK\n");
