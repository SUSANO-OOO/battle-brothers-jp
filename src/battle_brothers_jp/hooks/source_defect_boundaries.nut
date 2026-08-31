// Display-only normalizations for independently reviewed defects in the exact
// installed source snapshot. These wrappers compose with Rosetta and repair
// only malformed placeholder spellings or unmatched variant braces in a
// temporary template/final player-facing return. They do not write event or
// background state, actor data, save data, or gameplay values.

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

// Vanilla 1.5.2-3 opens an outer variant group around the full campfire
// story, then opens and closes the inner three-story choice, but never closes
// the outer group. Translate the exact installed source first, append the one
// missing brace only to the temporary display template, and let the inherited
// event buildText path perform its normal random-choice and variable work.
// The source screen and canonical reviewed text retain their installed brace
// signature so source drift remains detectable.
local barbarianStoryPrefix = "[img]gfx/ui/events/event_26.png[/img]{%barbarian% shares tales around the campfire of northern heroics and monsters.";
local barbarianStorySuffix = "but by the end of the story they clap and nod as though they wish it really were the truth.}";

local function hasExactBraceSignature(_text, _opens, _closes)
{
    local openCount = 0;
    local closeCount = 0;
    local pos = 0;
    while ((pos = _text.find("{", pos)) != null) {
        openCount += 1;
        pos += 1;
    }
    pos = 0;
    while ((pos = _text.find("}", pos)) != null) {
        closeCount += 1;
        pos += 1;
    }
    return openCount == _opens && closeCount == _closes;
}

local function countOccurrences(_text, _needle)
{
    local count = 0;
    local pos = 0;
    while ((pos = _text.find(_needle, pos)) != null) {
        count += 1;
        pos += _needle.len();
    }
    return count;
}

mod.hook("scripts/events/events/dlc4/barbarian_tells_story_event", function (q) {
    q.buildText = @(__original) function (_text) {
        if (typeof _text != "string"
            || !::std.Str.startswith(_text, barbarianStoryPrefix)
            || !::std.Str.endswith(_text, barbarianStorySuffix)
            || !hasExactBraceSignature(_text, 2, 1)) return __original(_text);

        local translated = ::Rosetta._(_text);
        if (typeof translated != "string") return __original(_text);
        if (!hasExactBraceSignature(translated, 2, 1)) return __original(translated);
        return __original(translated + "}");
    }
});

// Vanilla 1.5.2-3 likewise leaves the outer variant group of the unfriendly
// town greeting open. The two nested groups (resident synonym and hostile
// greeting) are otherwise complete. Keep the reviewed canonical translation
// at the installed open=3/close=2 signature for drift detection, then append
// exactly one close brace only to the temporary template passed to the native
// renderer. Settlement identity, Screen.Text, event state, and save stay raw.
local unfriendlyTownPrefix = "[img]gfx/ui/events/event_43.png[/img]{The {denizens | citizens | peasants | laymen | townfolk} of %townname% greet you with {a few rotten eggs thrown";
local unfriendlyTownSuffix = "They stand around it, making sure you can't see what's left of the you-shapened wood.}";

mod.hook("scripts/events/events/enter_unfriendly_town_event", function (q) {
    q.buildText = @(__original) function (_text) {
        if (typeof _text != "string"
            || !::std.Str.startswith(_text, unfriendlyTownPrefix)
            || !::std.Str.endswith(_text, unfriendlyTownSuffix)
            || !hasExactBraceSignature(_text, 3, 2)
            || countOccurrences(_text, " | ") != 7
            || countOccurrences(_text, "%townname%") != 1
            || countOccurrences(_text, "\n") != 0) return __original(_text);

        local translated = ::Rosetta._(_text);
        if (typeof translated != "string") return __original(_text);
        if (!hasExactBraceSignature(translated, 3, 2)
            || countOccurrences(translated, " | ") != 7
            || countOccurrences(translated, "%townname%") != 1
            || countOccurrences(translated, "\n") != 0) return __original(translated);
        return __original(translated + "}");
    }
});

// The installed Greenskin Investigation event copies screen I's execution and
// doubled-payment prose verbatim into screen J, even though J is reached by
// keeping the apprentice's secret and grants only the promised arming sword.
// Keep I on the normal reviewed Rosetta literal and replace only J's temporary
// display template with the independently reviewed mechanics-faithful summary.
local greenskinsCopiedPrefix = "[img]gfx/ui/events/event_31.png[/img]You close the door and lock it, ensuring that the murderer will not be able to flee.";
local greenskinsCopiedSuffix = "a litany of horrors to keep bored soldiers entertained for hours.";
local greenskinsSecretDisplay = "[img]gfx/ui/events/event_31.png[/img]あなたは見習いの秘密を守る。約束どおり、見習いは自ら鍛えた剣を差し出した。";

mod.hook("scripts/events/events/crisis/greenskins_investigation_event", function (q) {
    q.buildText = @(__original) function (_text) {
        local screenID = "m" in this && typeof this.m == "table"
            && "ActiveScreen" in this.m && typeof this.m.ActiveScreen == "table"
            && "ID" in this.m.ActiveScreen ? this.m.ActiveScreen.ID : null;
        if (screenID != "J" || typeof _text != "string"
            || !::std.Str.startswith(_text, greenskinsCopiedPrefix)
            || !::std.Str.endswith(_text, greenskinsCopiedSuffix)
            || !hasExactBraceSignature(_text, 0, 0)
            || countOccurrences(_text, "%nobleman%") != 1
            || countOccurrences(_text, "%SPEECH_ON%") != 1
            || countOccurrences(_text, "%SPEECH_OFF%") != 1
            || countOccurrences(_text, "\n") != 2) return __original(_text);

        return __original(greenskinsSecretDisplay);
    }
});

// The installed grave-heist event likewise copies the three-choice screen E
// prose into failure screen F. F grants no loot, worsens the graverobber's
// mood, and offers only "All for naught.". Supply the approved minimal result
// at the display boundary while preserving %graverobber% for native insertion.
local graveChoicePrefix = "[img]gfx/ui/events/event_33.png[/img]You and %graverobber% stalk low through the bushes";
local graveChoiceSuffix = "which grave you think it be?%SPEECH_OFF%";
local graveFailureDisplay = "[img]gfx/ui/events/event_33.png[/img]あなたと%graverobber%は選んだ墓を掘り返すが、目当てのものは何も出てこない。骨折り損だった。";

mod.hook("scripts/events/events/graverobber_heist_event", function (q) {
    q.buildText = @(__original) function (_text) {
        local screenID = "m" in this && typeof this.m == "table"
            && "ActiveScreen" in this.m && typeof this.m.ActiveScreen == "table"
            && "ID" in this.m.ActiveScreen ? this.m.ActiveScreen.ID : null;
        if (screenID != "F" || typeof _text != "string"
            || !::std.Str.startswith(_text, graveChoicePrefix)
            || !::std.Str.endswith(_text, graveChoiceSuffix)
            || !hasExactBraceSignature(_text, 0, 0)
            || countOccurrences(_text, "%graverobber%") != 1
            || countOccurrences(_text, "%SPEECH_ON%") != 3
            || countOccurrences(_text, "%SPEECH_OFF%") != 3
            || countOccurrences(_text, "\n") != 4) return __original(_text);

        return __original(graveFailureDisplay);
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
