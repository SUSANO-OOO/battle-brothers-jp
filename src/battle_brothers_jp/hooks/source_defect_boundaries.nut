// Display-only normalizations for independently reviewed defects in the exact
// installed source snapshot. These wrappers run after Rosetta and repair only
// malformed placeholder spellings or one unmatched variant brace in returned
// player-facing text. They do not write event/background state, actor data,
// save data, or gameplay values.

local mod = ::BattleBrothersJP.Mod;

// Vanilla 1.5.2-3 has one extra closing variant brace in the B1 prose of the
// Kraken cult entrance event. Hook the exact event class and normalize only
// the final returned display for that exact installed-source prefix/suffix.
// The source screen, reply flags, option results, and event state stay raw.
local krakenB1Prefix = "[img]gfx/ui/events/event_120.png[/img]{She turns to her tomes and stares at them as though they were gravestones.";
local krakenB1Suffix = "but that many tales is a little suspicious.}}";

mod.hook("scripts/events/events/dlc2/location/kraken_cult_enter_event", function (q) {
    q.buildText = @(__original) function (_text) {
        local ret = __original(_text);
        if (typeof _text != "string" || typeof ret != "string") return ret;
        if (!::std.Str.startswith(_text, krakenB1Prefix)
            || !::std.Str.endswith(_text, krakenB1Suffix)) return ret;

        // The native template consumer removes the balanced variant braces;
        // the installed unmatched second close survives as one raw trailing
        // brace. Remove exactly that final display byte if it is present.
        if (::std.Str.endswith(ret, "}")) return ret.slice(0, ret.len() - 1);
        return ret;
    }
});

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
