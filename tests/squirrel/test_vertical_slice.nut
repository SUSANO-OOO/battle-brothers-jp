::BattleBrothersJP <- {
    Author = "SUSANO-OOO"
    Mod = {}
}

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/runtime/core.nut", true);
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/translations/reviewed_literals.nut", true);
::buildTextFromTemplate <- function (_text, _vars) {
    local rendered = _text;
    foreach (pair in _vars)
    {
        rendered = ::BattleBrothersJP.Runtime.Str.replace(rendered, "%" + pair[0] + "%", pair[1]);
    }
    return rendered;
};
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/event_variable_boundaries.nut", true);

function assertEqual(_actual, _expected) {
    if (_actual != _expected) {
        throw "Expected '" + _expected + "', got '" + _actual + "'";
    }
}

assertEqual(::BattleBrothersJP.Runtime.translate("Have at least 50,000 crowns."), "50,000クラウン以上を保有する。");
assertEqual(::BattleBrothersJP.Runtime.translate("Welcome to the company, %dragonslayer%."), "%dragonslayer%、傭兵団へようこそ。");
assertEqual(::BattleBrothersJP.Runtime.translate("Crafting"), "製作");
assertEqual(::BattleBrothersJP.Runtime.translate("Ancient Southern Face Mask"), "古代南方の仮面");
assertEqual(::BattleBrothersJP.Runtime.translate("Crafting [color=#135213]+5%[/color]"), "製作 [color=#135213]+5%[/color]");
assertEqual(::BattleBrothersJP.Runtime.translate("Dame Roderick"), "デイム・Roderick");
assertEqual(::BattleBrothersJP.Runtime.translate("Dame"), "Dame");
assertEqual(::BattleBrothersJP.Runtime.translate("Dame "), "Dame ");
assertEqual(::BattleBrothersJP.Runtime.translate("Madame Roderick"), "Madame Roderick");
assertEqual(::BattleBrothersJP.Runtime.translate("Deserted the company"), "傭兵団から脱走した");
assertEqual(::BattleBrothersJP.Runtime.translate("Got a better paying offer"), "もっと割のいい仕事を持ちかけられた");
assertEqual(::BattleBrothersJP.Runtime.translate("Handed over to authorities"), "当局へ引き渡された");
assertEqual(::BattleBrothersJP.Runtime.translate("Hanged for attempted murder"), "殺人未遂で絞首刑に処された");
assertEqual(::BattleBrothersJP.Runtime.translate("Left to claim their birthright"), "生まれながらの権利を求めて去った");
assertEqual(::BattleBrothersJP.Runtime.translate("Reproach of the Old Gods"), "古き神々の譴責");
// The shared HedgeKnightTitles identity must never become a global literal.
// Its split scenario-title occurrence is handled by an exact UI boundary.
assertEqual(::BattleBrothersJP.Runtime.translate("The Lone Wolf"), "The Lone Wolf");
local rawPronounVars = [["their", "his"]];
assertEqual(::buildTextFromTemplate("Is %their% former self again", rawPronounVars), "彼の本来の姿に戻った");
assertEqual(rawPronounVars[0][1], "his");
local rawLegendaryWeaponVars = [["weapon", "Reproach of the Old Gods"]];
assertEqual(::buildTextFromTemplate("You carry %weapon%.", rawLegendaryWeaponVars), "You carry 古き神々の譴責.");
assertEqual(rawLegendaryWeaponVars[0][1], "Reproach of the Old Gods");
assertEqual(::BattleBrothersJP.Runtime.translate("Not in the vertical slice"), "Not in the vertical slice");

print("VERTICAL_SLICE_NAMESPACED_RUNTIME_TEST_OK\n");
