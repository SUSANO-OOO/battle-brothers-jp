local def = ::BattleBrothersJP <- {
    ID = "mod_battle_brothers_jp"
    Name = "Battle Brothers Integrated Japanese Localization"
    Version = "0.1.0-dev"
    Snapshot = "BBJP-CF88150E7B355ECD32D9"
    Author = "SUSANO-OOO"
};

local mod = def.Mod <- ::Hooks.register(def.ID, def.Version, def.Name);

// The JP runtime needs only Modern Hooks. Legends, Assets, MSU, legacy
// mod_hooks, Rosetta, stdlib, and DLC are optional composition partners.
mod.require("mod_modern_hooks >= 0.6.0");

local function detectProfile(_id, _verifiedVersion)
{
    local present = ::Hooks.hasMod(_id);
    local actual = present ? ::Hooks.getMod(_id).getVersionString() : null;
    return {
        Present = present
        ActualVersion = actual
        VerifiedVersion = _verifiedVersion
        Verified = present && actual == _verifiedVersion
        Enabled = present && actual == _verifiedVersion
    };
}

// Normal: no source scan or network access; only registered MOD metadata.
mod.queue(function () {
    def.ModuleStatus <- {
        vanilla = detectProfile("vanilla", "1.5.2-3")
        dlc_lindwurm = detectProfile("dlc_lindwurm", "1.0.0")
        dlc_unhold = detectProfile("dlc_unhold", "1.0.0")
        dlc_wildmen = detectProfile("dlc_wildmen", "1.0.0")
        dlc_desert = detectProfile("dlc_desert", "1.0.0")
        dlc_paladins = detectProfile("dlc_paladins", "1.0.0")
        legends = detectProfile("mod_legends", "19.4.20")
        legends_assets = detectProfile("mod_legends_assets", "19.4.3")
        msu = detectProfile("mod_msu", "1.9.0")
        modern_hooks = detectProfile("mod_modern_hooks", "0.6.0")
        legacy_hooks = detectProfile("mod_hooks", "21.1")
        legends_events_fix = detectProfile("mod_events_delayed_fix_legends", "0.7")
        legends_jimmys_tooltips = detectProfile("mod_Jimmys_Tooltips_legends", "1.0.5")
        legends_load_order_fix = detectProfile("mod_legends_load_order_fix", "19.4.20")
        legends_compat_check = detectProfile("mod_legends_compat_check", "19.4.20")
    };

    // Unknown base/framework versions fail closed to original English without
    // blocking startup. Each DLC remains independently optional for Core.
    local supportedBase = def.ModuleStatus.vanilla.Verified
        && def.ModuleStatus.modern_hooks.Verified;
    def.ModuleStatus.vanilla.Enabled = supportedBase;
    def.ModuleStatus.dlc_lindwurm.Enabled = supportedBase
        && def.ModuleStatus.dlc_lindwurm.Verified;
    def.ModuleStatus.dlc_unhold.Enabled = supportedBase
        && def.ModuleStatus.dlc_unhold.Verified;
    def.ModuleStatus.dlc_wildmen.Enabled = supportedBase
        && def.ModuleStatus.dlc_wildmen.Verified;
    def.ModuleStatus.dlc_desert.Enabled = supportedBase
        && def.ModuleStatus.dlc_desert.Verified;
    def.ModuleStatus.dlc_paladins.Enabled = supportedBase
        && def.ModuleStatus.dlc_paladins.Verified;
    def.ModuleStatus.msu.Enabled = supportedBase && def.ModuleStatus.msu.Verified;

    // Legends 19.4.20's actual registration requires this full composition.
    // A mismatch disables only the Legends partition and leaves source English.
    def.ModuleStatus.legends.Enabled = supportedBase
        && def.ModuleStatus.legends.Verified
        && def.ModuleStatus.legends_assets.Verified
        && def.ModuleStatus.msu.Enabled
        && def.ModuleStatus.legacy_hooks.Verified
        && def.ModuleStatus.dlc_lindwurm.Enabled
        && def.ModuleStatus.dlc_unhold.Enabled
        && def.ModuleStatus.dlc_wildmen.Enabled
        && def.ModuleStatus.dlc_desert.Enabled
        && def.ModuleStatus.dlc_paladins.Enabled
        && def.ModuleStatus.legends_events_fix.Verified
        && def.ModuleStatus.legends_load_order_fix.Verified
        && def.ModuleStatus.legends_compat_check.Verified;

    ::include("battle_brothers_jp/runtime/core");
    ::include("battle_brothers_jp/translations/reviewed_literals");

    // Each optional JS dictionary is activated only for its exact verified
    // profile. Unknown MODs and changed versions therefore keep English even
    // when they happen to reuse one of the reviewed labels.
    if (def.ModuleStatus.vanilla.Enabled)
    {
        ::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/generated_strings.js");
        if (def.ModuleStatus.legends.Enabled)
            ::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/generated_strings_legends.js");
        if (def.ModuleStatus.msu.Enabled)
            ::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/generated_strings_msu.js");
        if (def.ModuleStatus.modern_hooks.Enabled)
            ::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/generated_strings_modern_hooks.js");
        ::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/main.js");
        ::Hooks.registerCSS("ui/mods/mod_battle_brothers_jp/main.css");
    }
}, ::Hooks.QueueBucket.Normal);

// Optional relations affect only ordering, never dependency status. Each
// Legends-only target in these files is internally guarded by ModuleStatus.
mod.queue(">mod_legends", ">mod_rosetta", function () {
    if (!def.ModuleStatus.vanilla.Enabled) return;
    ::include("battle_brothers_jp/hooks/runtime_display_boundaries");
    ::include("battle_brothers_jp/hooks/semantic_name_safety");
    ::include("battle_brothers_jp/hooks/event_variable_boundaries");
    ::include("battle_brothers_jp/hooks/source_defect_boundaries");
    ::include("battle_brothers_jp/hooks/ui_boundaries");
}, ::Hooks.QueueBucket.Late);

// MSU UI is referenced only after an exact optional profile match.
mod.queue(">mod_msu", ">mod_rosetta", function () {
    if (def.ModuleStatus.msu.Enabled)
        ::include("battle_brothers_jp/hooks/msu_display_boundaries");
}, ::Hooks.QueueBucket.Late);
