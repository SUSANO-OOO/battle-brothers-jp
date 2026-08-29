// Display-only normalizations for independently reviewed defects in the exact
// installed source snapshot. These wrappers run after Rosetta and repair only
// malformed placeholder spellings in returned player-facing templates. They do
// not write background state, actor data, save data, or gameplay values.

local mod = ::BattleBrothersJP.Mod;

// Use hookTree rather than a normal exact hook. Modern Hooks finalizes normal
// hooks before tree hooks regardless of registration time; Rosetta translates
// onBuildDescription through a tree hook. Registering this tree hook later in
// the same Late bucket makes this repair the outer wrapper in the real chain.
mod.hookTree("scripts/skills/backgrounds/legend_ranger_commander_background", function (q) {
    q.onBuildDescription = @(__original) function () {
        local ret = __original();
        if (typeof ret != "string") return ret;

        // Installed Legends 19.4.20 contains one missing closing percent and
        // one stray leading 'h'. The outer wrapper receives Rosetta's reviewed
        // Japanese template, then makes both occurrences valid %name% tokens
        // before character_background.buildDescription() performs substitution.
        ret = ::std.Str.replace(ret, "%name's face", "%name%の顔");
        ret = ::std.Str.replace(ret, "h%name%", "%name%");
        return ret;
    }
});
