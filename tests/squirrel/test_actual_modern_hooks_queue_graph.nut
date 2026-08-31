// Local-only execution of the exact installed Modern Hooks queue graph. The
// third-party source remains ignored under work/ and is never copied to release.
::Hooks <- {
    errorAndThrow = function (_message) { throw _message; }
};
::Math <- {
    max = function (_a, _b) { return _a > _b ? _a : _b; }
};
dofile(getenv("BBJP_MH_QUEUE_GRAPH"), true);

class QueueFunction
{
    ModID = null;
    FunctionID = null;
    Before = null;
    After = null;

    constructor(_modID, _functionID, _before = null, _after = null)
    {
        ModID = _modID;
        FunctionID = _functionID;
        Before = _before == null ? [] : _before;
        After = _after == null ? [] : _after;
    }

    function getModID() { return ModID; }
    function getFunctionID() { return FunctionID; }
    function getLoadBefore() { return Before; }
    function getLoadAfter() { return After; }
}

local msu = QueueFunction("mod_msu", "late");
local legends = QueueFunction("mod_legends", "late");
local rosetta = QueueFunction("mod_rosetta", "late", [], ["mod_msu"]);
local jpCommon = QueueFunction("mod_battle_brothers_jp", "common", [], ["mod_legends", "mod_rosetta"]);
local jpMSU = QueueFunction("mod_battle_brothers_jp", "msu", [], ["mod_msu", "mod_rosetta"]);
local graph = ::Hooks.ModHooksQueueGraph([jpMSU, jpCommon, rosetta, legends, msu]);
local sorted = graph.getSorted();

local function position(_value)
{
    local at = sorted.find(_value);
    if (at == null) throw "queue function missing from actual graph";
    return at;
}
if (position(msu) >= position(rosetta)) throw "Rosetta did not load after MSU";
if (position(rosetta) >= position(jpCommon)) throw "JP common did not load after Rosetta";
if (position(legends) >= position(jpCommon)) throw "JP common did not load after Legends";
if (position(rosetta) >= position(jpMSU)) throw "JP MSU did not load after Rosetta";
if (position(msu) >= position(jpMSU)) throw "JP MSU did not load after MSU";

print("ACTUAL_MODERN_HOOKS_QUEUE_GRAPH_OK\n");
