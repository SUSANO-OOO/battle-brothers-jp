dofile(getenv("STDLIB_DIR") + "load.nut", true);
dofile(getenv("ROSETTA_DIR") + "mocks.nut", true);
dofile(getenv("ROSETTA_DIR") + "scripts/!mods_preload/!rosetta.nut", true);

::BattleBrothersJP <- {
    Author = "SUSANO-OOO"
}

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/translations/reviewed_literals.nut", true);
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/translations/context_patterns.nut", true);
::Rosetta.activate("ja");

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
assertEqual(::Rosetta.translate("Not in the vertical slice"), "Not in the vertical slice");

print("VERTICAL_SLICE_ROSETTA_TEST_OK\n");
