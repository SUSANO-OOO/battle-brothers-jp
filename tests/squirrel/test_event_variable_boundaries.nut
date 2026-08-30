::BattleBrothersJP <- {
    ActorTitleDisplayFragments = [
        {english = "The Lone Wolf", japanese = "一匹狼"},
        {english = "Weeds", japanese = "雑草"},
        {english = "the Lone Wolf", japanese = "一匹狼"},
        {english = "the Holy", japanese = "聖なる者"},
        {english = "the Old", japanese = "老人"}
    ],
    ActorTitleGenericDisplayFragments = [
        {english = "The Lone Wolf", japanese = "一匹狼"},
        {english = "Weeds", japanese = "雑草"}
    ],
    Mod = {}
};

::Rosetta <- {
    _ = function (_text) {
        local translations = {
            Hohenburg = "ホーエンブルク",
            ["The Lone Wolf"] = "一匹狼",
            ["Weeds"] = "雑草",
            ["Amber Wristguards"] = "琥珀の腕甲",
            ["Dame Roderick"] = "デイム・Roderick"
        };
        return _text in translations ? translations[_text] : _text;
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
    ["home", "Hohenburg"],
    ["dismissedName", "Aldric The Lone Wolf"],
    ["weedsName", "Asta Weeds"],
    ["oldGods", "Honor and fear of the Old Gods"],
    ["holyMother", "Blood Vial of the Holy Mother"]
];
local rendered = ::buildTextFromTemplate("The %sibling_bro% met a %noble_employer%.", callerVars);
assertEqual(findValue(rendered.Vars, "sibling_bro"), "団員");
assertEqual(findValue(rendered.Vars, "sib_bro"), "仲間");
assertEqual(findValue(rendered.Vars, "noble_employer"), "貴族");
assertEqual(findValue(rendered.Vars, "their_bro"), "彼の");
assertEqual(findValue(rendered.Vars, "unrelated"), "brother");
assertEqual(findValue(rendered.Vars, "justbeggar"), "物乞い");
assertEqual(findValue(rendered.Vars, "nemesisS"), "将軍");
assertEqual(findValue(rendered.Vars, "home"), "ホーエンブルク");
assertEqual(findValue(rendered.Vars, "dismissedName"), "Aldric 一匹狼");
assertEqual(findValue(rendered.Vars, "weedsName"), "Asta 雑草");
assertEqual(findValue(rendered.Vars, "oldGods"), "Honor and fear of the Old Gods");
assertEqual(findValue(rendered.Vars, "holyMother"), "Blood Vial of the Holy Mother");
// The wrapper must not mutate the caller-owned variable list.
assertEqual(findValue(callerVars, "sibling_bro"), "brother");
assertEqual(findValue(callerVars, "noble_employer"), "nobleman");
assertEqual(findValue(callerVars, "justbeggar"), "beggar");
assertEqual(findValue(callerVars, "nemesisS"), "General");
assertEqual(findValue(callerVars, "home"), "Hohenburg");
assertEqual(findValue(callerVars, "dismissedName"), "Aldric The Lone Wolf");
assertEqual(findValue(callerVars, "weedsName"), "Asta Weeds");
assertEqual(findValue(callerVars, "their_bro"), "his");

local pronounVars = [
    ["They_dude", "He"],
    ["them_sis", "her"],
    ["their_neuter", "their"],
    ["theirs_dude", "his"],
    ["themselves_sis", "herself"],
    ["person_neuter", "person"],
    ["person_dude", "man"],
    ["person_sis", "woman"],
    ["child_enemy", "girl"],
    ["offspring_dude", "son"],
    ["They're_dude", "he's"],
    ["they were_sis", "she was"],
    ["are they_neuter", "are they"],
    ["they_unknown", "Hohenburg"]
];
local pronounRendered = ::buildTextFromTemplate("Pronoun display", pronounVars);
assertEqual(findValue(pronounRendered.Vars, "They_dude"), "彼");
assertEqual(findValue(pronounRendered.Vars, "them_sis"), "彼女");
assertEqual(findValue(pronounRendered.Vars, "their_neuter"), "その者の");
assertEqual(findValue(pronounRendered.Vars, "theirs_dude"), "彼のもの");
assertEqual(findValue(pronounRendered.Vars, "themselves_sis"), "彼女自身");
assertEqual(findValue(pronounRendered.Vars, "person_neuter"), "者");
assertEqual(findValue(pronounRendered.Vars, "person_dude"), "男");
assertEqual(findValue(pronounRendered.Vars, "person_sis"), "女");
assertEqual(findValue(pronounRendered.Vars, "child_enemy"), "少女");
assertEqual(findValue(pronounRendered.Vars, "offspring_dude"), "息子");
assertEqual(findValue(pronounRendered.Vars, "They're_dude"), "彼は");
assertEqual(findValue(pronounRendered.Vars, "they were_sis"), "彼女は");
assertEqual(findValue(pronounRendered.Vars, "are they_neuter"), "その者は");
assertEqual(findValue(pronounRendered.Vars, "they_unknown"), "Hohenburg");
assertEqual(findValue(pronounVars, "They_dude"), "He");
assertEqual(findValue(pronounVars, "them_sis"), "her");
assertEqual(findValue(pronounVars, "their_neuter"), "their");
assertEqual(findValue(pronounVars, "They're_dude"), "he's");
assertEqual(findValue(pronounVars, "they were_sis"), "she was");
assertEqual(findValue(pronounVars, "they_unknown"), "Hohenburg");

local pronounFamilyCases = [
    { Family = "they", Values = [["they", "その者"], ["he", "彼"], ["she", "彼女"]] },
    { Family = "them", Values = [["them", "その者"], ["him", "彼"], ["her", "彼女"]] },
    { Family = "their", Values = [["their", "その者の"], ["his", "彼の"], ["her", "彼女の"]] },
    { Family = "theirs", Values = [["theirs", "その者のもの"], ["his", "彼のもの"], ["hers", "彼女のもの"]] },
    { Family = "themselves", Values = [["themselves", "その者自身"], ["himself", "彼自身"], ["herself", "彼女自身"]] },
    { Family = "person", Values = [["person", "者"], ["man", "男"], ["woman", "女"]] },
    { Family = "people", Values = [["people", "人々"], ["men", "男たち"], ["women", "女たち"]] },
    { Family = "swordsman", Values = [["swordsman", "剣士"], ["swordswoman", "剣士"]] },
    { Family = "child", Values = [["child", "子供"], ["boy", "少年"], ["girl", "少女"]] },
    { Family = "offspring", Values = [["child", "子"], ["son", "息子"], ["daughter", "娘"]] },
    { Family = "they are", Values = [["they are", "その者は"], ["he is", "彼は"], ["she is", "彼女は"]] },
    { Family = "they were", Values = [["they were", "その者は"], ["he was", "彼は"], ["she was", "彼女は"]] },
    { Family = "they will", Values = [["they will", "その者は"], ["he will", "彼は"], ["she will", "彼女は"]] },
    { Family = "they're", Values = [["they're", "その者は"], ["he's", "彼は"], ["she's", "彼女は"]] },
    { Family = "they'll", Values = [["they'll", "その者は"], ["he'll", "彼は"], ["she'll", "彼女は"]] },
    { Family = "are they", Values = [["are they", "その者は"], ["is he", "彼は"], ["is she", "彼女は"]] },
    { Family = "were they", Values = [["were they", "その者は"], ["was he", "彼は"], ["was she", "彼女は"]] }
];
foreach (familyCase in pronounFamilyCases)
{
    foreach (valueCase in familyCase.Values)
    {
        local auditKey = familyCase.Family + "_audit";
        local rawAuditVars = [[auditKey, valueCase[0]]];
        local renderedAuditVars = ::buildTextFromTemplate("Pronoun family audit", rawAuditVars);
        assertEqual(findValue(renderedAuditVars.Vars, auditKey), valueCase[1]);
        assertEqual(findValue(rawAuditVars, auditKey), valueCase[0]);
    }
}

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

local returnItemVars = [
    ["item", "Amber Wristguards"],
    ["itemLower", "amber wristguards"]
];
local returnItemRendered = ::buildTextFromTemplate("Recover %itemLower%.", returnItemVars);
assertEqual(findValue(returnItemRendered.Vars, "item"), "琥珀の腕甲");
assertEqual(findValue(returnItemRendered.Vars, "itemLower"), "琥珀の腕甲");
assertEqual(findValue(returnItemVars, "item"), "Amber Wristguards");
assertEqual(findValue(returnItemVars, "itemLower"), "amber wristguards");
local mismatchedLowerVars = [["item", "Amber Wristguards"], ["itemLower", "other item"]];
local mismatchedLower = ::buildTextFromTemplate("Recover %itemLower%.", mismatchedLowerVars);
assertEqual(findValue(mismatchedLower.Vars, "itemLower"), "other item");
local ambiguousItemVars = [["item", "Amber Wristguards"], ["item", "Other"], ["itemLower", "amber wristguards"]];
local ambiguousItem = ::buildTextFromTemplate("Recover %itemLower%.", ambiguousItemVars);
assertEqual(findValue(ambiguousItem.Vars, "itemLower"), "amber wristguards");
local unknownItemVars = [["item", "Unknown Relic"], ["itemLower", "unknown relic"]];
local unknownItem = ::buildTextFromTemplate("Recover %itemLower%.", unknownItemVars);
assertEqual(findValue(unknownItem.Vars, "itemLower"), "unknown relic");
assertEqual(findValue(unknownItemVars, "item"), "Unknown Relic");
assertEqual(findValue(unknownItemVars, "itemLower"), "unknown relic");

local commanderVars = [["commander", "Dame Roderick"]];
local commanderRendered = ::buildTextFromTemplate("Defeat %commander%.", commanderVars);
assertEqual(findValue(commanderRendered.Vars, "commander"), "デイム・Roderick");
assertEqual(findValue(commanderVars, "commander"), "Dame Roderick");

print("EVENT_VARIABLE_BOUNDARIES_TEST_OK\n");
