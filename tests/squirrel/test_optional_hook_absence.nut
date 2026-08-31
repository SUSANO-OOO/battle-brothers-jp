// Optional modules and DLC must contribute zero class hooks when absent.
// This harness deliberately records registrations without invoking callbacks;
// an absent target therefore cannot be hidden by a permissive class mock.

local targets = [];
local mod = {
    hook = function (_target, _callback) { targets.push(_target); },
    hookTree = function (_target, _callback) { targets.push(_target); }
};

::BattleBrothersJP <- {
    Mod = mod
    ModuleStatus = {
        legends = {Enabled = false}
        dlc_unhold = {Enabled = false}
        dlc_wildmen = {Enabled = false}
        dlc_desert = {Enabled = false}
        dlc_paladins = {Enabled = false}
    }
    Runtime = {
        translate = function (_value) { return _value; }
        Str = {}
    }
    ActorTitleDisplayFragments = []
    ActorTitleGenericDisplayFragments = []
};

::Const <- {
    Strings = {HedgeKnightTitles = ["the Hedge Knight"]}
    World = {
        Common = {
            generateName = function (_list) { return _list[0]; }
        }
    }
};

function assertFalse(_value, _label)
{
    if (_value) throw _label;
}

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/semantic_name_safety.nut", true);
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/source_defect_boundaries.nut", true);
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/ui_boundaries.nut", true);

local optionalExact = {
    ["scripts/states/world/asset_manager"] = true,
    ["scripts/ui/screens/world/modules/camp_screen/camp_crafting_dialog_module"] = true,
    ["scripts/contracts/contracts/arena_contract"] = true,
    ["scripts/skills/perks/perk_legend_specialist_poacher"] = true,
    ["scripts/items/accessory/legend_accessory_dog"] = true
};

foreach (target in targets)
{
    assertFalse(target in optionalExact, "absent optional target registered: " + target);
    assertFalse(target.find("/dlc2/") != null, "absent Unhold DLC target registered: " + target);
    assertFalse(target.find("/dlc4/") != null, "absent Wildmen DLC target registered: " + target);
    assertFalse(target.find("/dlc6/") != null, "absent Desert DLC target registered: " + target);
    assertFalse(target.find("/dlc8/") != null, "absent Paladins DLC target registered: " + target);
    assertFalse(target.find("legend_") != null, "absent Legends target registered: " + target);
}

print("OPTIONAL_HOOK_ABSENCE_TEST_OK\n");
