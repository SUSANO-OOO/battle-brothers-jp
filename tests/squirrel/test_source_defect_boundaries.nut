dofile(getenv("STDLIB_DIR") + "load.nut", true);

local hooks = {};
::BattleBrothersJP <- {
    Mod = {
        hookTree = function (_target, _callback) {
            local q = { onBuildDescription = null };
            _callback(q);
            hooks[_target] <- q;
        }
    }
};

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/source_defect_boundaries.nut", true);

function assertEqual(_actual, _expected)
{
    if (_actual != _expected) throw "Expected '" + _expected + "', got '" + _actual + "'";
}

local sourceCalls = 0;
local englishSource = function () {
    sourceCalls += 1;
    return "English source with %name's face and h%name%.";
};
// Modern Hooks tree-hook composition for this snapshot: Rosetta registered
// first and therefore becomes the inner wrapper; this MOD registered later and
// becomes the outer wrapper. The Rosetta fixture deliberately returns the
// reviewed Japanese string with the two installed source defects preserved.
local rosettaWrapper = @(__original) function () {
    __original();
    return "鷲に%name's faceを引き裂かれた。h%name%は剣の刃を握った。%randomtown%はそのまま。";
};
local rosettaInner = rosettaWrapper(englishSource);
local wrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(rosettaInner);
assertEqual(wrapper(), "鷲に%name%の顔を引き裂かれた。%name%は剣の刃を握った。%randomtown%はそのまま。");
assertEqual(sourceCalls, 1);

local calls = 0;
local directWrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(function () {
    calls += 1;
    return "鷲に%name's faceを引き裂かれた。h%name%は剣の刃を握った。%randomtown%はそのまま。";
});
assertEqual(directWrapper(), "鷲に%name%の顔を引き裂かれた。%name%は剣の刃を握った。%randomtown%はそのまま。");
assertEqual(calls, 1);

local unrelatedWrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(function () {
    return "unrelated %name% template";
});
assertEqual(unrelatedWrapper(), "unrelated %name% template");

local nullWrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(function () {
    return null;
});
assertEqual(nullWrapper(), null);

print("SOURCE_DEFECT_BOUNDARIES_TEST_OK\n");
