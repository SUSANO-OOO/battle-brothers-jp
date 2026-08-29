::BattleBrothersJP <- {
    Mod = {}
};

::Rosetta <- {
    _ = function (_text) {
        return _text == "Hohenburg" ? "ホーエンブルク" : _text;
    }
};

::buildTextFromTemplate <- function (_text, _vars) {
    return { Text = _text, Vars = _vars };
};

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/event_variable_boundaries.nut", true);

function assertEqual(_actual, _expected)
{
    if (_actual != _expected) throw "Expected '" + _expected + "', got '" + _actual + "'";
}

function findValue(_vars, _key)
{
    foreach (pair in _vars) if (pair[0] == _key) return pair[1];
    throw "Missing variable " + _key;
}

local callerVars = [
    ["sibling_bro", "brother"],
    ["sib_bro", "bro"],
    ["noble_employer", "nobleman"],
    ["their_bro", "his"],
    ["unrelated", "brother"],
    ["justbeggar", "beggar"],
    ["nemesisS", "General"],
    ["home", "Hohenburg"]
];
local rendered = ::buildTextFromTemplate("The %sibling_bro% met a %noble_employer%.", callerVars);
assertEqual(findValue(rendered.Vars, "sibling_bro"), "団員");
assertEqual(findValue(rendered.Vars, "sib_bro"), "仲間");
assertEqual(findValue(rendered.Vars, "noble_employer"), "貴族");
assertEqual(findValue(rendered.Vars, "their_bro"), "his");
assertEqual(findValue(rendered.Vars, "unrelated"), "brother");
assertEqual(findValue(rendered.Vars, "justbeggar"), "物乞い");
assertEqual(findValue(rendered.Vars, "nemesisS"), "将軍");
assertEqual(findValue(rendered.Vars, "home"), "ホーエンブルク");
// The wrapper must not mutate the caller-owned variable list.
assertEqual(findValue(callerVars, "sibling_bro"), "brother");
assertEqual(findValue(callerVars, "noble_employer"), "nobleman");
assertEqual(findValue(callerVars, "justbeggar"), "beggar");
assertEqual(findValue(callerVars, "nemesisS"), "General");
assertEqual(findValue(callerVars, "home"), "Hohenburg");

// port_building.getRandomDescription() supplies the destination through this
// exact key.  The rendered suffix must receive the display name while the raw
// caller-owned value remains suitable for settlement identity and routing.
local portDescriptionVars = [["destname", "Hohenburg"]];
local portDescription = ::buildTextFromTemplate("A ship sails to %destname%.", portDescriptionVars);
assertEqual(findValue(portDescription.Vars, "destname"), "ホーエンブルク");
assertEqual(findValue(portDescriptionVars, "destname"), "Hohenburg");

local kinshipVars = [["sibling", "sister"]];
local kinship = ::buildTextFromTemplate("After a coup to dispose %their% older %sibling% failed", kinshipVars);
assertEqual(findValue(kinship.Vars, "sibling"), "きょうだい");
assertEqual(findValue(kinshipVars, "sibling"), "sister");

print("EVENT_VARIABLE_BOUNDARIES_TEST_OK\n");
