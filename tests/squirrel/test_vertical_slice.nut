dofile(getenv("STDLIB_DIR") + "load.nut", true);
dofile(getenv("ROSETTA_DIR") + "mocks.nut", true);
dofile(getenv("ROSETTA_DIR") + "scripts/!mods_preload/!rosetta.nut", true);

::BattleBrothersJP <- {
    Author = "SUSANO-OOO"
    Mod = {}
}

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/translations/reviewed_literals.nut", true);
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/translations/context_patterns.nut", true);
::Rosetta.activate("ja");
::buildTextFromTemplate <- function (_text, _vars) {
    local rendered = ::Rosetta.translate(_text);
    foreach (pair in _vars)
    {
        rendered = ::std.Str.replace(rendered, "%" + pair[0] + "%", pair[1]);
    }
    return rendered;
};
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/event_variable_boundaries.nut", true);

function assertEqual(_actual, _expected) {
    if (_actual != _expected) {
        throw "Expected '" + _expected + "', got '" + _actual + "'";
    }
}

assertEqual(::Rosetta.translate("Have at least 50,000 crowns."), "50,000クラウン以上を保有する。");
assertEqual(::Rosetta.translate("Welcome to the company, %dragonslayer%."), "%dragonslayer%、傭兵団へようこそ。");
assertEqual(::Rosetta.translate("Crafting"), "製作");
assertEqual(::Rosetta.translate("Ancient Southern Face Mask"), "古代南方の仮面");
assertEqual(::Rosetta.translate("Crafting [color=#135213]+5%[/color]"), "製作 [color=#135213]+5%[/color]");
assertEqual(::Rosetta.translate("Dame Roderick"), "デイム・Roderick");
assertEqual(::Rosetta.translate("Dame"), "Dame");
assertEqual(::Rosetta.translate("Dame "), "Dame ");
assertEqual(::Rosetta.translate("Madame Roderick"), "Madame Roderick");
assertEqual(::Rosetta.translate("Deserted the company"), "傭兵団から脱走した");
assertEqual(::Rosetta.translate("Got a better paying offer"), "もっと割のいい仕事を持ちかけられた");
assertEqual(::Rosetta.translate("Handed over to authorities"), "当局へ引き渡された");
assertEqual(::Rosetta.translate("Hanged for attempted murder"), "殺人未遂で絞首刑に処された");
assertEqual(::Rosetta.translate("Left to claim their birthright"), "生まれながらの権利を求めて去った");
assertEqual(::Rosetta.translate("Reproach of the Old Gods"), "古き神々の譴責");
// The shared HedgeKnightTitles identity must never become a global literal.
// Its split scenario-title occurrence is handled by an exact UI boundary.
assertEqual(::Rosetta.translate("The Lone Wolf"), "The Lone Wolf");
local rawPronounVars = [["their", "his"]];
assertEqual(::buildTextFromTemplate("Is %their% former self again", rawPronounVars), "彼の本来の姿に戻った");
assertEqual(rawPronounVars[0][1], "his");
local rawLegendaryWeaponVars = [["weapon", "Reproach of the Old Gods"]];
assertEqual(::buildTextFromTemplate("You carry %weapon%.", rawLegendaryWeaponVars), "You carry 古き神々の譴責.");
assertEqual(rawLegendaryWeaponVars[0][1], "Reproach of the Old Gods");
assertEqual(::Rosetta.translate("Not in the vertical slice"), "Not in the vertical slice");

print("VERTICAL_SLICE_ROSETTA_TEST_OK\n");
