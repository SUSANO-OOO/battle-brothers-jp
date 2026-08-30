local def = ::BattleBrothersJP <- {
    ID = "mod_battle_brothers_jp"
    Name = "Battle Brothers Integrated Japanese Localization"
    Version = "0.1.0-dev"
    Snapshot = "BBJP-CF88150E7B355ECD32D9"
    Author = "SUSANO-OOO"
}

local mod = def.Mod <- ::Hooks.register(def.ID, def.Version, def.Name);

// Exact content versions prevent a source update from silently using stale copy.
mod.require(
    "vanilla = 1.5.2-3",
    "mod_legends = 19.4.20",
    "mod_legends_assets = 19.4.3",
    "mod_msu = 1.9.0",
    "mod_modern_hooks >= 0.6.0",
    "mod_rosetta = 0.5.0",
    "stdlib >= 2.5"
);

// Rosetta installs its getter/template hooks in QueueBucket.Late. Queue order
// relations are only meaningful inside the same bucket, so this callback must
// also be Late for >mod_rosetta to make our boundary wrappers outermost.
mod.queue(">mod_rosetta", ">mod_msu", ">mod_legends", function () {
    ::include("battle_brothers_jp/translations/reviewed_literals");
    ::include("battle_brothers_jp/translations/context_patterns");

    // Rosetta 0.5.0's Japanese autodetection is explicitly marked non-working.
    ::Rosetta.activate("ja");

    // Preserve source-language item/background/world names for code that uses
    // getters as gameplay, identity, uniqueness, or persistence data.
    ::include("battle_brothers_jp/hooks/semantic_name_safety");

    // Translate display-only values inserted after Rosetta's template pass.
    ::include("battle_brothers_jp/hooks/event_variable_boundaries");

    // Normalize independently reviewed player-facing placeholder/brace defects
    // in the exact installed snapshot at their narrow final-display boundaries.
    ::include("battle_brothers_jp/hooks/source_defect_boundaries");

    // Translation-only boundary hooks for player-facing strings that Rosetta
    // 0.5.0 does not intercept in the supported snapshot.
    ::include("battle_brothers_jp/hooks/ui_boundaries");

    // Modern Hooks loads these before non-root screens are instantiated.
    ::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/generated_strings.js");
    ::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/main.js");
    ::Hooks.registerCSS("ui/mods/mod_battle_brothers_jp/main.css");
}, ::Hooks.QueueBucket.Late);
