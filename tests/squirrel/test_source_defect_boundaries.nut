dofile(getenv("STDLIB_DIR") + "load.nut", true);

local hooks = {};
::BattleBrothersJP <- {
    Mod = {
        hook = function (_target, _callback) {
            local q = { buildText = null };
            _callback(q);
            hooks[_target] <- q;
        },
        hookTree = function (_target, _callback) {
            local q = { onBuildDescription = null };
            _callback(q);
            hooks[_target] <- q;
        }
    }
};

::SourceDefectTestTranslations <- {};
::Rosetta <- {
    _ = function (_text) {
        return _text in ::SourceDefectTestTranslations
            ? ::SourceDefectTestTranslations[_text]
            : _text;
    }
};

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/source_defect_boundaries.nut", true);

function assertEqual(_actual, _expected)
{
    if (_actual != _expected) throw "Expected '" + _expected + "', got '" + _actual + "'";
}

local krakenSource = "[img]gfx/ui/events/event_120.png[/img]{She turns to her tomes and stares at them as though they were gravestones. Middle prose but that many tales is a little suspicious.}}";
local krakenRendered = "女は書物へ向き直る。話の数が多すぎるのは少しばかり怪しい。}";
local krakenCalls = 0;
local krakenWrapper = hooks["scripts/events/events/dlc2/location/kraken_cult_enter_event"].buildText(function (_text) {
    krakenCalls += 1;
    return krakenRendered;
});
assertEqual(krakenWrapper(krakenSource), "女は書物へ向き直る。話の数が多すぎるのは少しばかり怪しい。");
assertEqual(krakenCalls, 1);

local balancedSource = "[img]gfx/ui/events/event_120.png[/img]{She turns to her tomes and stares at them as though they were gravestones. Middle prose but that many tales is a little suspicious.}";
assertEqual(krakenWrapper(balancedSource), krakenRendered);
assertEqual(krakenCalls, 2);

local unrelatedKrakenText = "Option text ending in }";
assertEqual(krakenWrapper(unrelatedKrakenText), krakenRendered);
assertEqual(krakenCalls, 3);

local alreadyCleanWrapper = hooks["scripts/events/events/dlc2/location/kraken_cult_enter_event"].buildText(function (_text) {
    return "すでに正常な表示。";
});
assertEqual(alreadyCleanWrapper(krakenSource), "すでに正常な表示。");

local nullKrakenWrapper = hooks["scripts/events/events/dlc2/location/kraken_cult_enter_event"].buildText(function (_text) {
    return null;
});
assertEqual(nullKrakenWrapper(krakenSource), null);

local barbarianSource = "[img]gfx/ui/events/event_26.png[/img]{%barbarian% shares tales around the campfire of northern heroics and monsters. Intro. {First tale. | Second tale. | Third tale, but by the end of the story they clap and nod as though they wish it really were the truth.}";
local barbarianJapanese = "[img]gfx/ui/events/event_26.png[/img]{%barbarian%は焚き火を囲んで北方の武勇伝や怪物の話をする。導入。{一つ目の話。 | 二つ目の話。 | 三つ目の話。最後には皆が拍手し、これが真実ならと願うように頷いた。}";
::SourceDefectTestTranslations[barbarianSource] <- barbarianJapanese;
local barbarianCalls = 0;
local barbarianOriginalInput = null;
local barbarianWrapper = hooks["scripts/events/events/dlc4/barbarian_tells_story_event"].buildText(function (_text) {
    barbarianCalls += 1;
    barbarianOriginalInput = _text;
    return "正常化された表示";
});
assertEqual(barbarianWrapper(barbarianSource), "正常化された表示");
assertEqual(barbarianOriginalInput, barbarianJapanese + "}");
assertEqual(barbarianCalls, 1);

local balancedBarbarianSource = barbarianSource + "}";
assertEqual(barbarianWrapper(balancedBarbarianSource), "正常化された表示");
assertEqual(barbarianOriginalInput, balancedBarbarianSource);
assertEqual(barbarianCalls, 2);

local balancedBarbarianJapanese = barbarianJapanese + "}";
::SourceDefectTestTranslations[barbarianSource] = balancedBarbarianJapanese;
assertEqual(barbarianWrapper(barbarianSource), "正常化された表示");
assertEqual(barbarianOriginalInput, balancedBarbarianJapanese);
assertEqual(barbarianCalls, 3);
::SourceDefectTestTranslations[barbarianSource] = barbarianJapanese;

local barbarianMiddle = barbarianSource.find(" Intro.");
local wrongStructureBarbarian = barbarianSource.slice(0, barbarianMiddle)
    + " {unexpected}" + barbarianSource.slice(barbarianMiddle);
assertEqual(barbarianWrapper(wrongStructureBarbarian), "正常化された表示");
assertEqual(barbarianOriginalInput, wrongStructureBarbarian);
assertEqual(barbarianCalls, 4);

local unrelatedBarbarian = "[img]gfx/ui/events/event_26.png[/img]Unrelated option.";
assertEqual(barbarianWrapper(unrelatedBarbarian), "正常化された表示");
assertEqual(barbarianOriginalInput, unrelatedBarbarian);
assertEqual(barbarianCalls, 5);

local nonStringBarbarian = null;
assertEqual(barbarianWrapper(nonStringBarbarian), "正常化された表示");
assertEqual(barbarianOriginalInput, null);
assertEqual(barbarianCalls, 6);

local invalidTranslationSource = "[img]gfx/ui/events/event_26.png[/img]{%barbarian% shares tales around the campfire of northern heroics and monsters. {Invalid translation fixture, but by the end of the story they clap and nod as though they wish it really were the truth.}";
::SourceDefectTestTranslations[invalidTranslationSource] <- null;
assertEqual(barbarianWrapper(invalidTranslationSource), "正常化された表示");
assertEqual(barbarianOriginalInput, invalidTranslationSource);
assertEqual(barbarianCalls, 7);

local greenskinsSource = "[img]gfx/ui/events/event_31.png[/img]You close the door and lock it, ensuring that the murderer will not be able to flee.\n\n %nobleman% reports.%SPEECH_ON%Orders.%SPEECH_OFF%a litany of horrors to keep bored soldiers entertained for hours.";
local greenskinsCalls = 0;
local greenskinsOriginalInput = null;
local greenskinsWrapper = hooks["scripts/events/events/crisis/greenskins_investigation_event"].buildText(function (_text) {
    greenskinsCalls += 1;
    greenskinsOriginalInput = _text;
    return "greenskins rendered";
});
local greenskinsJ = { m = { ActiveScreen = { ID = "J" } } };
local greenskinsI = { m = { ActiveScreen = { ID = "I" } } };
assertEqual(greenskinsWrapper.call(greenskinsJ, greenskinsSource), "greenskins rendered");
assertEqual(greenskinsOriginalInput, "[img]gfx/ui/events/event_31.png[/img]あなたは見習いの秘密を守る。約束どおり、見習いは自ら鍛えた剣を差し出した。");
assertEqual(greenskinsCalls, 1);
assertEqual(greenskinsWrapper.call(greenskinsI, greenskinsSource), "greenskins rendered");
assertEqual(greenskinsOriginalInput, greenskinsSource);
assertEqual(greenskinsCalls, 2);
local greenskinsWrongTokens = ::std.Str.replace(greenskinsSource, "%nobleman%", "%nobleman%%nobleman%");
assertEqual(greenskinsWrapper.call(greenskinsJ, greenskinsWrongTokens), "greenskins rendered");
assertEqual(greenskinsOriginalInput, greenskinsWrongTokens);
assertEqual(greenskinsCalls, 3);
local noActiveScreen = { m = { ActiveScreen = null } };
assertEqual(greenskinsWrapper.call(noActiveScreen, greenskinsSource), "greenskins rendered");
assertEqual(greenskinsOriginalInput, greenskinsSource);
assertEqual(greenskinsCalls, 4);
local noEventState = {};
assertEqual(greenskinsWrapper.call(noEventState, greenskinsSource), "greenskins rendered");
assertEqual(greenskinsOriginalInput, greenskinsSource);
assertEqual(greenskinsCalls, 5);
local malformedActiveScreen = { m = { ActiveScreen = "J" } };
assertEqual(greenskinsWrapper.call(malformedActiveScreen, greenskinsSource), "greenskins rendered");
assertEqual(greenskinsOriginalInput, greenskinsSource);
assertEqual(greenskinsCalls, 6);
local greenskinsWrongNewlines = ::std.Str.replace(greenskinsSource, "\n\n", "\n");
assertEqual(greenskinsWrapper.call(greenskinsJ, greenskinsWrongNewlines), "greenskins rendered");
assertEqual(greenskinsOriginalInput, greenskinsWrongNewlines);
assertEqual(greenskinsCalls, 7);
assertEqual(greenskinsWrapper.call(greenskinsJ, null), "greenskins rendered");
assertEqual(greenskinsOriginalInput, null);
assertEqual(greenskinsCalls, 8);

local graveSource = "[img]gfx/ui/events/event_33.png[/img]You and %graverobber% stalk low through the bushes.\n\n Middle.%SPEECH_ON%A.%SPEECH_OFF%\n\nB.%SPEECH_ON%C.%SPEECH_OFF%%SPEECH_ON%D, which grave you think it be?%SPEECH_OFF%";
local graveCalls = 0;
local graveOriginalInput = null;
local graveWrapper = hooks["scripts/events/events/graverobber_heist_event"].buildText(function (_text) {
    graveCalls += 1;
    graveOriginalInput = _text;
    return "grave rendered";
});
local graveF = { m = { ActiveScreen = { ID = "F" } } };
local graveE = { m = { ActiveScreen = { ID = "E" } } };
assertEqual(graveWrapper.call(graveF, graveSource), "grave rendered");
assertEqual(graveOriginalInput, "[img]gfx/ui/events/event_33.png[/img]あなたと%graverobber%は選んだ墓を掘り返すが、目当てのものは何も出てこない。骨折り損だった。");
assertEqual(graveCalls, 1);
assertEqual(graveWrapper.call(graveE, graveSource), "grave rendered");
assertEqual(graveOriginalInput, graveSource);
assertEqual(graveCalls, 2);
local graveWrongSpeech = ::std.Str.replace(graveSource, "%SPEECH_ON%", "", 1);
assertEqual(graveWrapper.call(graveF, graveWrongSpeech), "grave rendered");
assertEqual(graveOriginalInput, graveWrongSpeech);
assertEqual(graveCalls, 3);
assertEqual(graveWrapper.call(graveF, null), "grave rendered");
assertEqual(graveOriginalInput, null);
assertEqual(graveCalls, 4);
local graveMalformedActiveScreen = { m = { ActiveScreen = ["F"] } };
assertEqual(graveWrapper.call(graveMalformedActiveScreen, graveSource), "grave rendered");
assertEqual(graveOriginalInput, graveSource);
assertEqual(graveCalls, 5);
local graveWrongNewlines = ::std.Str.replace(graveSource, "\n\n", "\n", 1);
assertEqual(graveWrapper.call(graveF, graveWrongNewlines), "grave rendered");
assertEqual(graveOriginalInput, graveWrongNewlines);
assertEqual(graveCalls, 6);

local sourceCalls = 0;
local englishSource = function () {
    sourceCalls += 1;
    return "English source with %name's face and h%name%.";
};
// Modern Hooks tree-hook composition for this snapshot: Rosetta registered
// first and therefore becomes the inner wrapper; this MOD registered later and
// becomes the outer wrapper. The Rosetta fixture deliberately returns the
// reviewed Japanese string with the two installed source defects preserved.
local rosettaWrapper = @(__original) function () {
    __original();
    return "鷲に%name's faceを引き裂かれた。h%name%は剣の刃を握った。%randomtown%はそのまま。";
};
local rosettaInner = rosettaWrapper(englishSource);
local wrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(rosettaInner);
assertEqual(wrapper(), "鷲に%name%の顔を引き裂かれた。%name%は剣の刃を握った。%randomtown%はそのまま。");
assertEqual(sourceCalls, 1);

local calls = 0;
local directWrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(function () {
    calls += 1;
    return "鷲に%name's faceを引き裂かれた。h%name%は剣の刃を握った。%randomtown%はそのまま。";
});
assertEqual(directWrapper(), "鷲に%name%の顔を引き裂かれた。%name%は剣の刃を握った。%randomtown%はそのまま。");
assertEqual(calls, 1);

local unrelatedWrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(function () {
    return "unrelated %name% template";
});
assertEqual(unrelatedWrapper(), "unrelated %name% template");

local nullWrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(function () {
    return null;
});
assertEqual(nullWrapper(), null);

print("SOURCE_DEFECT_BOUNDARIES_TEST_OK\n");
