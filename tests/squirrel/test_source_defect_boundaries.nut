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
::SourceDefectTranslationCalls <- 0;

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/runtime/core.nut", true);
::BattleBrothersJP.Runtime.translate = function (_text) {
    ::SourceDefectTranslationCalls += 1;
    return _text in ::SourceDefectTestTranslations
        ? ::SourceDefectTestTranslations[_text]
        : _text;
};

local function replaceText(_text, _needle, _replacement, _maximum = null)
{
    local ret = "";
    local position = 0;
    local replaced = 0;
    while (position <= _text.len())
    {
        local at = _text.find(_needle, position);
        if (at == null || (_maximum != null && replaced >= _maximum))
            return ret + _text.slice(position);
        ret += _text.slice(position, at) + _replacement;
        position = at + _needle.len();
        replaced += 1;
    }
    return ret;
}

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/source_defect_boundaries.nut", true);
local firstUnfriendlyFactory = hooks["scripts/events/events/enter_unfriendly_town_event"].buildText;
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/source_defect_boundaries.nut", true);
if (hooks["scripts/events/events/enter_unfriendly_town_event"].buildText != firstUnfriendlyFactory)
    throw "source defect boundaries initialized twice";

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

local unfriendlyTownSource = "[img]gfx/ui/events/event_43.png[/img]{The {denizens | citizens | peasants | laymen | townfolk} of %townname% greet you with {a few rotten eggs thrown at you. | a tarred doll. | a few children. | a burning effigy. They stand around it, making sure you can't see what's left of the you-shapened wood.}";
local unfriendlyTownJapanese = "[img]gfx/ui/events/event_43.png[/img]{%townname%の{住民 | 市民 | 農民 | 庶民 | 町人}は、{腐った卵で迎える。 | 瀝青を塗った人形で迎える。 | 子供たちで迎える。 | 自分を象った燃える人形で迎える。豚の飼葉桶へ沈めた木の残骸を見せまいと、その周りへ立ちはだかる。}";
::SourceDefectTestTranslations[unfriendlyTownSource] <- unfriendlyTownJapanese;
local unfriendlyTownCalls = 0;
local unfriendlyTownOriginalInput = null;
local unfriendlyTownWrapper = hooks["scripts/events/events/enter_unfriendly_town_event"].buildText(function (_text) {
    unfriendlyTownCalls += 1;
    unfriendlyTownOriginalInput = _text;
    return "敵対的な町の表示";
});
assertEqual(unfriendlyTownWrapper(unfriendlyTownSource), "敵対的な町の表示");
assertEqual(unfriendlyTownOriginalInput, unfriendlyTownJapanese + "}");
assertEqual(unfriendlyTownCalls, 1);

local balancedUnfriendlyTownSource = unfriendlyTownSource + "}";
assertEqual(unfriendlyTownWrapper(balancedUnfriendlyTownSource), "敵対的な町の表示");
assertEqual(unfriendlyTownOriginalInput, balancedUnfriendlyTownSource);
assertEqual(unfriendlyTownCalls, 2);

local wrongPipeUnfriendlyTown = replaceText(unfriendlyTownSource, " | a tarred doll.", " / a tarred doll.");
assertEqual(unfriendlyTownWrapper(wrongPipeUnfriendlyTown), "敵対的な町の表示");
assertEqual(unfriendlyTownOriginalInput, wrongPipeUnfriendlyTown);
assertEqual(unfriendlyTownCalls, 3);

local wrongTownTokenUnfriendlyTown = replaceText(unfriendlyTownSource, "%townname%", "%townname%%townname%");
assertEqual(unfriendlyTownWrapper(wrongTownTokenUnfriendlyTown), "敵対的な町の表示");
assertEqual(unfriendlyTownOriginalInput, wrongTownTokenUnfriendlyTown);
assertEqual(unfriendlyTownCalls, 4);

local invalidUnfriendlyTownTranslation = replaceText(unfriendlyTownJapanese, "%townname%", "町");
::SourceDefectTestTranslations[unfriendlyTownSource] = invalidUnfriendlyTownTranslation;
assertEqual(unfriendlyTownWrapper(unfriendlyTownSource), "敵対的な町の表示");
assertEqual(unfriendlyTownOriginalInput, invalidUnfriendlyTownTranslation);
assertEqual(unfriendlyTownCalls, 5);
::SourceDefectTestTranslations[unfriendlyTownSource] = unfriendlyTownJapanese;

assertEqual(unfriendlyTownWrapper(null), "敵対的な町の表示");
assertEqual(unfriendlyTownOriginalInput, null);
assertEqual(unfriendlyTownCalls, 6);

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
local greenskinsWrongTokens = replaceText(greenskinsSource, "%nobleman%", "%nobleman%%nobleman%");
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
local greenskinsWrongNewlines = replaceText(greenskinsSource, "\n\n", "\n");
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
local graveWrongSpeech = replaceText(graveSource, "%SPEECH_ON%", "", 1);
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
local graveWrongNewlines = replaceText(graveSource, "\n\n", "\n", 1);
assertEqual(graveWrapper.call(graveF, graveWrongNewlines), "grave rendered");
assertEqual(graveOriginalInput, graveWrongNewlines);
assertEqual(graveCalls, 6);

local sourceCalls = 0;
local englishSource = function () {
    sourceCalls += 1;
    return "English source with %name's face and h%name%.";
};
// The JP-owned exact runtime entry translates the returned source template;
// the class boundary then repairs only the two installed placeholder defects.
::SourceDefectTestTranslations["English source with %name's face and h%name%."] <-
    "鷲に%name's faceを引き裂かれた。h%name%は剣の刃を握った。%randomtown%はそのまま。";
local wrapper = hooks["scripts/skills/backgrounds/legend_ranger_commander_background"].onBuildDescription(englishSource);
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

function assertTrue(_condition, _message)
{
    if (!_condition) throw _message;
}

function testCountOccurrences(_text, _needle)
{
    local count = 0;
    local pos = 0;
    while ((pos = _text.find(_needle, pos)) != null) {
        count += 1;
        pos += _needle.len();
    }
    return count;
}

function testExtractPercentTokens(_text)
{
    local tokens = [];
    local cursor = 0;
    while (true) {
        local tokenStart = _text.find("%", cursor);
        if (tokenStart == null) return tokens;
        local tokenEnd = _text.find("%", tokenStart + 1);
        if (tokenEnd == null) throw "unbalanced percent token in fixture";
        tokens.push(_text.slice(tokenStart, tokenEnd + 1));
        cursor = tokenEnd + 1;
    }
}

function makeMissingOuterVariantEventState(_screenID, _source)
{
    local activeScreen = { ID = _screenID, Text = _source };
    return {
        m = {
            ActiveScreen = activeScreen,
            Screens = [activeScreen, { ID = "sentinel", Text = "sentinel screen" }],
            Options = [{ Text = "raw option", Result = "raw result" }],
            Results = ["raw result"]
        },
        EventField = "raw event field",
        Actor = { ID = "raw actor", Name = "raw actor name" },
        Settlement = { ID = "raw settlement", Name = "raw settlement name" },
        SerializationInput = "raw serialization input"
    };
}

function snapshotMissingOuterVariantEventState(_event)
{
    return _event.m.ActiveScreen.ID + "\x1f" + _event.m.ActiveScreen.Text
        + "\x1f" + _event.m.Screens[0].ID + "\x1f" + _event.m.Screens[0].Text
        + "\x1f" + _event.m.Screens[1].ID + "\x1f" + _event.m.Screens[1].Text
        + "\x1f" + _event.m.Options[0].Text + "\x1f" + _event.m.Options[0].Result
        + "\x1f" + _event.m.Results[0] + "\x1f" + _event.EventField
        + "\x1f" + _event.Actor.ID + "\x1f" + _event.Actor.Name
        + "\x1f" + _event.Settlement.ID + "\x1f" + _event.Settlement.Name
        + "\x1f" + _event.SerializationInput;
}

local missingOuterVariantFixtures = [
    { Path = "scripts/events/events/dlc8/anatomist_bummed_at_mutations_event", Screen = "A", Source = "{[img]gfx/ui/events/event_05.png[/img]{%anatomist% is sitting near to the campfire. Almost too close. You pull him back a ways so he doesn't burn himself. He looks up, his face dotted with pustules and slathered in the grease of ones which have already popped.%SPEECH_ON%I'm beginning to wonder if I made a great mistake in drinking that potion.%SPEECH_OFF%He scoots back toward the flames, and there's a sense in his eyes that he wants to pitch himself into it. You can't do much for him, mostly because he looks awfully gross at the moment and you'd rather not touch him again. | You find %anatomist% standing beside the company wagon with a sleeve unfurled and his finger picking at some strange markings there. Curious, you ask if they are birthmarks. The anatomist turns, shaking his head. He lifts up his shirt to show that these markings are all over his body, mottling the flesh with unsightly colors which look rough to the touch, like scabs that cannot be peeled.%SPEECH_ON%The potion I drank did this and I know not what to with myself.%SPEECH_OFF%You nod and tell him it'll surely get better. He sighs and simply lowers his shirt and looks away. | %anatomist% stands over a bucket of water, looking at his darkened reflection in it. He sighs. You ask how he is doing, and he turns to reveal horrific rashes and boils upon his skin.%SPEECH_ON%I am not doing so well, to be honest. The concoction I imbibed seems to have had a gravely ill-effect on me, though I am being perhaps a little giving with my vocabulary there. I will survive, but it has wounded me in ways that are not just of the skin and the body, but of the mind. I thought myself distanced from such matters, but now, seeing my horrible face...I am in a state of perpetual unease.%SPEECH_OFF%You grab his shoulder and give it a squeeze, then pat him on the back and make some recommendations like he should drink some water and of course to not feel bad. You weren't ever that great at consoling other men, much less ones suffering from terrible maladies sprung from scientific madness. | %anatomist% the anatomist is in a despondent state. The potion he made, and was in such a hurry to drink, has resulted in his entire body being overcome with maladies ranging from rashes to boils to what appear to be unusual spasms and plenty of snot from the nose. You assure him that he will get better, but his horrific appearance is taking a toll on him. | The strange concoctions %anatomist% the anatomist has been making, are strange concoctions that he has also been drinking. Unsurprisingly, the effects have not been good: rashes, infections, smells, hair falling out, and more. While on the outside he proclaims that what he is doing is in the name of science, you can tell that all these maladies and disfigurations are debilitating to the man's morale. You can only hope he gets better with time. | Matters of science, which are far outside your understanding, always do seem to come with risks. You remember as a child that your friend took the risk of swinging out on a rope into a river, and by happenstance you all found out just how much weight a branch can hold while in the throes of Fall.\n\nNow, it seems %anatomist% the anatomist is finding out the debilitating nature of drinking one of his bizarre potions. He is overwhelmed with rashes and infections, and for some reason he is a siren to ants, who for who knows what reason now love to crawl on him at all hours of day and night. Hopefully, with time, these maladies will depart, and hopefully take the damned ants with them. | You always knew the anatomists to be a bit wrong in the head, but the way they've been creating potions and drinking them has really floored you. Water alone can be poisonous if sipped from the wrong cup, nevermind wholesale concoctions which are distilled in the mire of whatever scientific notions the anatomists are carrying that day. Naturally, it isn't long until one of the eggheads, %anatomist%, falls ill. He is still capable of moving and day-to-day tasks, but the giant warts and leaking pustules makes him a horror to look at, and though he may see himself distanced from society, you've little doubt that walking around looking like a rag that's mopped up pigshite is healthy for the mind and spirit. Hopefully, with a bit of time, he might get better. | %anatomist% isn't necessarily sick from drinking his potions. After all, he is still able to move and get around, and even fight if necessary. But he is certainly affected by said potions in a manner most unsightly. Great boils have appeared on his cheeks, and occasionally his eyes spring from their sockets and he has to push them back in which is something you wished you hadn't seen. Strings of drool come down the corners of his lips and his nostril is home to snails of snot and boogers and blood. As you can imagine, he is rather down about the whole looking uglier than a dead pig carcass-thing, but you've faith that in good time he will get better.}" },
    { Path = "scripts/events/events/dlc8/bad_reputation_event", Screen = "A", Source = "{[img]gfx/ui/events/event_05.png[/img]{A few of the Oathtakers bring a piece of paper to your attention. On it is the name of the %companyname%, a rather amusing drawing of yourself that is not remotely in proportion, and a few choice descriptors of your lowly character. It seems that your reputation in this world is not nearly as high and mighty as you assumed it to be.%SPEECH_ON%We must rectify this, captain! For people to think of the Oathtakers in this manner is a great insult to us, and especially to Young Anselm!%SPEECH_OFF%You agree. | As the company camps, a few of the Oathtakers are grousing about the reputation of the %companyname%.%SPEECH_ON%Young Anselm would not be happy with the way the world sees us. We should be setting an example of how to behave!%SPEECH_OFF%You agree, though it may take some time to repair the Oathtakers' honor. | Young Anselm founded the Oathtakers with the belief that they should be paragons reestablishing a precedence of honor, virtue, and sound character, elements which he believed the world had lost sight of. Unfortunately, you've struggled to maintain these ideals, slipping the %companyname%'s reputation a little lower than it ought to be. A few of the men are rightfully complaining, and if they're not outwardly complaining it is obvious that these faults are draining morale anyway. You think it best to perhaps start mending the %companyname%'s reputation as soon as possible lest the men lose faith in its ultimate purpose.}" },
    { Path = "scripts/events/events/dlc8/anatomist_ok_with_mutations_event", Screen = "A", Source = "{[img]gfx/ui/events/event_05.png[/img]{After spending some time with his new malformed shapes, %anatomist% has come to accept who he is now. He sees these horrific scars and ever growing pustules as evidence that he is on the right path. In some way, he is right. These strange changes have made him a far superior fighter than he was before, which is saying a lot for you personally had no hope that these foolish eggheads ever had a shot of becoming even competent fighters at best. Whatever fears and worries he had prior are now gone entirely, replaced by a renewed sense of purpose and desire to do more. | %anatomist% has stopped moping around worrying about his scars and horrible appearance. It seems he has made peace with how he looks now, or possibly he has simply become so ingratiated with the godawful smell emanating from every part of him that he no longer notices. While his stink brings you to nearly vomit every time you're near him, at the very least he has recovered from the dourness which was occupying his every waking minute. Maybe now he can continue on his righteous path to scientific discovery, or however else he put it. | It is hard to come to terms with who you are and, despite the superficiality, it is even more difficult to make peace with how you look. This is even more true when how you look was not the manner in which you were born, but shaped by the actions you took in life. If your own decisions brought you to this newfound state, you have only your own choices to dwell upon for the rest of your life. You've seen it many a time, particularly with sellswords who lose their ears, noses, lips, and worse. It can take a long time for a man to come to peace with his newformed circumstances, and %anatomist% was no different. But come to peace he has. Whatever horrific scars and mutations he has suffered from his own actions are no more - at least mentally. He has moved on and is ready to continue his path in this world as someone seeking scientific endeavors, and the great risks to himself that those endeavors might one day pose. | %anatomist% has come to terms with his new appearances. At first, his body's reactions to the potions and concoctions he's been imbibing were so disturbing that he reeled into a shell of his former self. You could hardly blame him, for he did and does look quite hideous. But after a while, you simply realize that life goes on, and if nothing can be done about it then nothing can be done about it. And, at the very least, the real purpose of the choices made were to satisfy scientific inquiries, and it seems re-realizing that has revivified %anatomist%'s sense of purpose. He is still ungainly and disgusting and you have a hard time looking at him, but least he's happier now. | Once wounded by maladies and disfigurements, %anatomist% the anatomist is starting to look a lot better now. That is to say, he has come to realize that there is little he can do about his physical appearance which is, to be terse, still something that takes courage and willpower to just look at. But the man has remembered the true reason he sought the concoctions and strange mixtures and tinctures which have turned him into a walking and talking monstrosity, and that reason is a matter of scientific endeavor. The anatomist is now a happier man and as long as he can be kept far away from even the smallest of mirrors you imagine that can more or less remain the case. | %anatomist%'s habit of sucking down any every potion he concocts did eventually come to bite him in the ass. His last imbibement when horribly wrong, turning his face into fleshy dough, and arising across his skin all manner of bumps and bruises and pustules and pusses. Naturally, these changes had a deep morale impact on the man. But, finally, he has gotten over it. He is still a walking, talking monstrosity in every sense of the word, but on the inside he is at peace with it, and what's on the inside is what counts. Or at least it better count, because what's on the outside you can barely muster the courage to look at. | %anatomist% the anatomist calls the changes to his body 'mutations', which must be some sort of egghead word for looking like shite. For a while, his appearance was a drag on his day to day life. You can hardly blame him, he inflicted these maladies upon himself which is always far worse than when the world does it to you and leaves little doubt as to how you could have unfarked yourself. Thankfully, the anatomist has gotten over his depression and angst about his horrendous appearance. He might even be more willing than ever to keep imbibing his potions and concoctions. Surely he can't look much worse than he already does and at a certain point of looking completely hideous even the ladyfolk take a turn, like seeing a dog so mangy and decrepit that one can't help but pet it out of curiosity. | After he drank a number of questionable potions, %anatomist% the anatomist's body began to change and, like any grown man, change at that age is rarely a good thing. His face became disfigured, his body mottled with sores and scars. For a time, the anatomist fell into a deep depression over the matter and you wondered if he had been irreversibly damaged not just on the outside, but the inside as well. Thankfully, it is the morale of a man that can be the hardest to break. %anatomist% has come to terms with his new appearance. It's not as though there is much he can do about it, and he now sees it as a sort of fundamental rite by fire that he is the way he is, and that he has helped pursue the scientific endeavors which brought him to these lands in the first place. You yourself just have to make sure that he's not the first thing you see in the morning.}" },
    { Path = "scripts/events/events/dlc8/captured_oathbringer_event", Screen = "A", Source = "{[img]gfx/ui/events/event_05.png[/img]{One of the men rushes into your tent exclaiming that someone has been caught sneaking into the camp. You ask if it's a thief. The man shakes his head.%SPEECH_ON%No, worse. He's an Oathbringer.%SPEECH_OFF%Sonuvabitch. You jump to your feet and rush out, finding this interloper already tied up and being battered by the Oathtakers. You break it up, coming to stand before him.%SPEECH_ON%Oathbringer, where is Anselm's jaw?%SPEECH_OFF%The man spits on your boot and tells you he'd never give that up, and that the Oathtakers can go to the hells where they belong, and that Anselm himself would walk them there if he could. This blaspheming of Young Anselm's name draws gasps from you and your men. %randombrother% leans over.%SPEECH_ON%Just give the word, captain, and we'll show this Oathbringer the error of his ways.%SPEECH_OFF%}" },
    { Path = "scripts/events/events/dlc8/captured_oathbringer_event", Screen = "E", Source = "{[img]gfx/ui/events/event_05.png[/img]{This man has nothing of value. You tell the men to cut him loose. They protest, saying that an Oathbringer has but one choice, to submit to the Oathtakers and to the true Final Path, or to die. There is also room for one who returns Young Anselm's jawbone, but the codes on how to treat an Oathbringer who does that have not yet been worked out. But, as far as this man is concerned, he is of no real use and you're in no mood for bloodspilling. Just as you reiterate to cut him loose, %randombrother% cuts the man's throat, much to the cheering of the others.%SPEECH_ON%You said cut him, right captain? Right?%SPEECH_OFF%You realize the Oathtaker is covering for you, and to keep denying that the Oathbringer had to die might put you in a prickly situation. You nod.%SPEECH_ON%Yes, of course, the little rat had to die, same as all the pathless Oathbringers! And die they all shall!%SPEECH_OFF%The men roar again though you have a feeling that a few will remember your ridiculous suggestion to let an Oathbringer walk.}" },
    { Path = "scripts/events/events/dlc8/captured_oathbringer_event", Screen = "B", Source = "{[img]gfx/ui/events/event_05.png[/img]{You draw your sword and plunge it into the man's heart.%SPEECH_ON%Anselm will not await you in the next life, heretic.%SPEECH_OFF%The man's body sags around the steel, his eyes briefly wide before settling into a half-lidded gaze at the ground. You draw out your sword and the %companyname% cheers.%SPEECH_ON%Death to all Oathbringers!%SPEECH_OFF%The Oathtakers draw out their swords and raise them to the skies as a ravenous mood sweeps over the company.}" },
    { Path = "scripts/events/events/dlc8/captured_oathbringer_event", Screen = "C", Source = "{[img]gfx/ui/events/event_05.png[/img]{You nod.%SPEECH_ON%Torture him until his tongue points us to Young Anselm's jaw. I don't care how you do it, just do it.%SPEECH_OFF%Turning away, the prisoner screams out that Anselm would not approve. He then just starts screaming indiscriminately and eventually shouting out things that don't make a whole lot of sense. You retire to your tent, bouncing your foot to the screams that now take a rhythmic sort of wailing. Eventually, %randombrother% reappears. He has with him some weapons and armor you know weren't in inventory.%SPEECH_ON%He led us to a location that had these hidden away, but Anselm's jawbone is still missing. I'm afraid the Oathbringers must have it in their own camp, but he wouldn't say where that was. We, uh, we had some difficulties communicating after we cut his tongue out.%SPEECH_OFF%Sighing, you ask where the prisoner is now. The man clears his throat.%SPEECH_ON%Oh he went all white and fell over. He's dead, sir.%SPEECH_OFF%We did right by Young Anselm, at least.}" },
    { Path = "scripts/events/events/dlc8/captured_oathbringer_event", Screen = "D", Source = "{[img]gfx/ui/events/event_05.png[/img]{You tell the men to torture the man for information. If there's one thing every Oathbringer knows, it's where Young Anselm's jawbone is and that is something every Oathtaker wishes to find out. The man screams as he's dragged away, and you retire to your tent to drown out the annoyances of things like shrieking and crying which really put a crimp on your mood. A moment later, %torturer% enters the tent, blood on his shirt. He looks to speak, then collapses to the ground. Another Oathtaker comes in saying the prisoner escaped, shanking his torturer before fleeing. You tell the men to help %torturer% before he bleeds out.%SPEECH_ON%Those damned Oathbringers have no honor! We'll find and kill him dead, so sayeth Young Anselm, so sayeth us all!%SPEECH_OFF%You speak with a clenched jaw, and an air of theatrics. The truth is the bastard got away and those Oathbringers are hard to catch, the rats that they are. You just hope that %torturer% survives.}" },
    { Path = "scripts/events/events/dlc6/crisis/holywar_crucified_1_event", Screen = "A", Source = "{[img]gfx/ui/events/event_161.png[/img]{In the middle of the desert wastes one has to be somewhat suspicious of anything they come across, especially if it's a lone man on a cross. The crucified figure looks entirely dead, given the buzzards clerically perched on each shoulder, but as you draw near the birds take flight and the man lifts is head. Despite gruesome injuries to hands and feet, he's rather lively and asks for water. Instead of giving it to him, you ask why he's here. The man sighs.%SPEECH_ON%I was a crusader. Came in with the army looking to gain glory for the old gods. Except when I got down here, and got to talking with the locals and the priests, I had a change of heart.%SPEECH_OFF%}" },
    { Path = "scripts/events/events/dlc6/crisis/holywar_crucified_1_event", Screen = "B", Source = "{[img]gfx/ui/events/event_161.png[/img]{The man nods.%SPEECH_ON%Aye, that they did. Mind, I was there when they crucified someone else on account of the same reason. So in part I'm not the brightest fella to follow in his footsteps, nor am I clean of heart, for I cheered it on when they did it to him. But perhaps the Gilder will see the true light I carry within, you know?%SPEECH_OFF%He turns his head to the skies, and to the buzzards cycling above.%SPEECH_ON%I'm still one open to fight, no matter who it is, south, north, doesn't matter. I've the Gilder in my heart.%SPEECH_OFF%}" },
    { Path = "scripts/events/events/dlc6/crisis/holywar_crucified_1_event", Screen = "C", Source = "{[img]gfx/ui/events/event_161.png[/img]{You draw out your dagger and cut the man down. He's got injuries aplenty but is no doubt of strong enough constitution to one day recover. He thanks you with remarkable mildness given the doom which awaited him.%SPEECH_ON%Glad to stretch. I mean, you know, stretch on my terms. Lead the way, captain of the Gilder's circumstance, captain of His mighty sublimity.%SPEECH_OFF%Many in the company do not care for taking in a man who has turned his back not only on his fellow man, but his own gods.}" },
    { Path = "scripts/events/events/dlc6/crisis/holywar_crucified_1_event", Screen = "D", Source = "{[img]gfx/ui/events/event_161.png[/img]{You tell the man he'll be talking to his god or gods real soon. He sighs.%SPEECH_ON%In a manner, I deserve this, but I am at peace with it.%SPEECH_OFF%There's mixed reactions about the company on it, and by mixed it is mostly varying levels of exuberance. After all, the man is a traitor to both terra and celestial, making him easily hated by anyone and everyone.}" },
    { Path = "scripts/events/events/dlc8/oathtakers_skull_cracked_event", Screen = "A", Source = "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker% bursts into the tent with trembling hands holding Young Anselm's skull.%SPEECH_ON%It's broken!%SPEECH_OFF%You jump out of your seat and take a look at Young Anselm's holy remains. There's a sliver of a crack going down the back of the skull. At first it doesn't look too bad, but when you stick a pinky finger in and lift, the bone splits apart. You both gasp and set the skull on the table. There's no doubt the skull could be broken apart with only a little bit more effort.%SPEECH_ON%What should we do? How do we fix it?%SPEECH_OFF%You ponder the question very carefully. The last time this happened Young Anselm's jawbone broke off, and so too did break the Oathtakers - with one group remaining as the Oathtakers, and the other forming the savage blasphemers, the Oathbringers. You're not going to let that happen again.}" },
    { Path = "scripts/events/events/dlc8/oathtaker_happy_with_company_event", Screen = "A", Source = "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker% the oathtaker joins you by the campfire. He nods.%SPEECH_ON%Respectfully, captain, I can say that it is a big ask to require a man to be of genuine goodness. When I first knew ya, I didn't think you had the chops for such an undertaking. I thought this world's creeping darkness would wither you away, grind you down like sand to a stone. But here you are. Stalwart. Keeping to the Oaths, one after the other. Good on ya. I think Young Anselm would be proud.%SPEECH_OFF%You thank the Oathtaker for the kind words.}" },
    { Path = "scripts/events/events/dlc8/oathtakers_skull_event", Screen = "A", Source = "{[img]gfx/ui/events/event_183.png[/img]{You find %oathtaker% staring intently into the eyesockets of Young Anselm's skull, the weight of the bone resting on his outstretched palm. He nods now and again and murmurs to himself in a sort of whispering prayer. Sensing your presence, the Oathtaker turns around.%SPEECH_ON%I was worried, but despite the seas of chaos, we have here Young Anselm, and he is provenance of courage such that I would swim into the world's ocean with full assurance that he would see me through it. I should spread Young Anselm's teachings with the others.%SPEECH_OFF%Absolutely he should. | The Oathtakers are enjoying a fine meal beside the fire. %oathtaker% has Young Anselm's skull on a stump. He occasionally turns, spoon of gristle in hand, and seems to think about feeding some to the bony maw. These moments make you uneasy, but for whatever reason the little skull has a tendency to compel the Oathtakers into a better mood by mere presence alone, so much so that you'll let these simultaneously girly and grisly peculiarities pass. | %oathtaker% is looking over a text with felt covers and a gilt bookmark. Beside him, Young Anselm's skull rests near a dying candle. You ask the Oathtaker what he's reading. The man looks up.%SPEECH_ON%Seeing to matters of the Oaths, as Young Anselm had written them. Remember the lad's wise words: ink is the strongest of memories, so it is wise to not depend solely on one's own capacities to follow the Oaths, but instead to refresh the springs of the mind through the writings themselves. This, too, was a part of Young Anselm's teachings. You would know if you tended to the texts as he advised.%SPEECH_OFF%A little snippy there, but he's not wrong. | You see %oathtaker% cleaning off the skull of Young Anselm. Wishing to test the man's faith in the First Oathtaker, you ask something you already know: how did Anselm die. The Oathtaker straightens up, staring at you with a sincere look of offense.%SPEECH_ON%Captain, it matters not how he died, or even when or why or to whom, and maybe there even isn't a whom, but what matters is that he was on the Oath of the Final Path, and so we are also with him, and will be to the end. We are not just Oathtakers, but the Final Oathtakers.%SPEECH_OFF%He turns around, flicking a bug off the bone and then cleaning the skull as though it had been profaned by the insect's steps.%SPEECH_ON%This is a grand experience we are undertaking here captain, but sometimes I think you're just along for the ride.%SPEECH_OFF%It is at the very least a grand experience in deepening your pockets. Thankfully, the only one who seems capable of noticing your more cynical nature is a supposedly poignant skull, Young Anselm's eyesockets emptily staring at you as the Oathtaker spit shines the bone. | %oathtaker% kneels before Young Anselm's skull.%SPEECH_ON%Give me strength in our Oaths, Young Anselm, for I cannot do it alone and certainly not with just the captain's help.%SPEECH_OFF%You almost tell him that he's not alone, he's with the %companyname% and you're not a slouch yourself, but figure this probably isn't the place for that sorta realist talk. The man suddenly jumps to his feet and nods.%SPEECH_ON%Such guidance is much appreciated, Young Anselm.%SPEECH_OFF%A part of you wishes you could look at a young lad's skull for guidance and actually find it, but the only thing you take from Young Anselm's bony visage is an empty stare. | The company has had its up and downs, but Young Anselm is still seen as its primary piety purveyor. You have to admit, sometimes you find yourself staring at the skull with a bit of contempt. Despite you leading the band, and despite you leading it quite well, much of the company's successes are given to the skull. When the men need help, they often go to the skull just as well, skipping right past their captain. %oathtaker% is an example of this, having had a rough go lately but, instead of talking to you, you find him scooping up Young Anselm for some bony counsel on Oathtaking matters. You sometimes dream of taking the First Oathtaker's dome and skipping it across a lake like a rock. | Young Anselm's skull is a touchstone for the most faithful of the Oathtakers, a source of knowledge and guidance and more, all springing out from a silent, bony vessel. %oathtaker%, who has been feeling rather down and out about his past few days, is given access to the skull. Even in this brief keeping, he is renewed in his belief in the Oaths. | You set Young Anselm's skull onto a stick and start spinning it, the bone rattling as it goes round and round, the hollow clatter horribly amusing. %oathtaker% comes through the bushes asking something and you grab the skull and set it down in an instant. The Oathtaker looks at you, the stick, the skull, then back to you. He clears his throat and explains he's been having a rough go of it the past few days. For guidance, and out of laziness, you hand him Young Anselm's skull, telling him to find within the First Oathtaker a revivification of his vitality, a renewal of his faiths, and a resurgence of his courage. The man nods dutifully.%SPEECH_ON%Young Anselm might be the First Oathtaker, but I still believe you are wise beyond your years, captain. I should have seen to Anselm in the first place!%SPEECH_OFF% | You got Young Anselm's skull set on a stump and are throwing pebbles through the eyesockets. One swooshes right through the hole and you pump your fist. Just then, %oathtaker% comes around. He looks at you, your clenched fist, and Young Anselm. The Oathtaker nods.%SPEECH_ON%If even a cynic such as you may be given courage by Young Anselm, then surely the First Oathtaker's abilities go beyond what even I believed. I will leave you alone so that you may find further guidance from Young Anselm.%SPEECH_OFF%Nodding, you thank the Oathtaker, but after he leaves you return to the sport. Unfortunately, all you can muster is plinking pebble after pebble off Anselm's dome. It seems you've lost the touch of the toss. | You have a thick stick in hand and are tossing rocks into the air and slamming them off into the distance. Each crack is deep and pleasing, and the sight of the stones sailing immensely satisfying. As you lean down to pick up another stone, you see Young Anselm's skull there, staring up at you. Naturally, you take it up, weighing it one hand. It's so light. You toss it up and smash it with the stick, fragments of skull spiraling outward in every direction, the fine bonemeal powdering the air around you as though you'd cast a magic trick. Suddenly, you feel something in your side, and this world snaps away and you blink awake to %oathtaker% prodding you with his toe. Blinking your eyes, you realize you dozed off near the campfire. The Oathtaker sets a skull down beside you and nods.%SPEECH_ON%I sought counsel with Young Anselm and found it, captain, but seeing that you were sweating in your sleep I thought maybe you would like a moment with the First Oathtaker as well.%SPEECH_OFF%The man turns and leaves and you're left alone with the skull. It stares at you knowingly. A little too knowingly. You turn the head to look elsewhere and then go back to sleep. | %oathtaker% has had a rough go of it the past few days. You bring him Young Anselm's skull and tell him to sit with his thoughts, and to reflect on the Oaths. The man nods, and just a few minutes later he comes to you, skull in hand.%SPEECH_ON%You were right, captain. I had strayed from the path, but through the First Oathtaker's guidance I have found it again.%SPEECH_OFF% | Young Anselm's skull is starting to look a little ragged. Pieces of grass, mud, couple of bugs, all these things are smattered onto the bone. %oathtaker% comes up asking some inane question about inventory. You cut him off and hand him the skull and tell him to clean it. He nods, staring at the skull as though it were a pound of pure gold. He finishes the job within ten minutes, and when he gets back his disposition is entirely fresh, himself admitting that time alone with Young Anselm invigorated him, and reminded him why he took to the Oathtakers in the first place. That's all well and good, but the priority here is that he's also forgotten to talk to you about inventory which is fantastic.}" },
    { Path = "scripts/events/events/dlc8/oathtakers_skull_cracked_event", Screen = "C", Source = "{[img]gfx/ui/events/event_183.png[/img]{You hush %oathtaker% and tell him to close the tent tarp. Taking the skull, you set it on the table and immediately work to fix it. Unfortunately, the second your hands put in any kind of effort, the crack widens and there's even fragments that fly off and scatter to who knows where. You let go of the skull as though it had burned you, Anselm's grace clopping hollowly on the table. %oathtaker% looks at you.%SPEECH_ON%What now? What should we do? Maybe we should take the best part and run off and form a new band?%SPEECH_OFF%Scoffing, you ask the fool if he takes you for an Oathtaker or an Oathbringer. He swallows and confirms the former. Damn right, and there's only one thing to do if that is the case: claim it is Young Anselm's desire to have this here skull crack, and that it is a display of how the %companyname% are not owning up to being true Oathtakers. He agrees, and you do end up showing the rest of the men the skull and its newly acquired bony demarcations.\n\nAt first they are fearful of its crack, but soon agree with you, that Young Anselm's influence is waning, not because of the First Oathtaker himself, but because you all, the last of the Oathtakers, are not owning up to your Oaths! And that you all must do better to follow the path of a true Oathtaker! The men roar and cheer, their convictions renewed by Young Anselm's crack.}" },
    { Path = "scripts/events/events/dlc8/oathtakers_skull_cracked_event", Screen = "B", Source = "{[img]gfx/ui/events/event_183.png[/img]{You take out a piece of string and coat it in ivy and sap. Then you gently lift Young Anselm's crack and run your finger down it with more sap. %oathtaker% stares nervously. Satisfied, you then insert the string along the crack and set the skull's parts back down, chomping down on the string and the sticky ivy with it.  You stand back, looking at your work. %oathtaker% swallows.%SPEECH_ON%I...I don't think anyone will notice.%SPEECH_OFF%You actually worry that it may be preferable that they find the crack in the skull absent of one's attempt to fix it, than to see the handiwork of some skulking skull restorer who tried to sneak one by. Either way, it's done, and Young Anselm's honor has been restored. %oathtaker% wipes the sweat from his brow.%SPEECH_ON%I believe this to have been a test, captain, and that Young Anselm has seen us through. His strength flows through me, and no words are capable of describing the honor I feel right now.%SPEECH_OFF%What? Young Anselm probably had no idea about sticky saps and ivies, and he presumably knew even less now that he's an unspeaking skull. But...you leave %oathtaker% to his interpretations, as shortchanging as they are to yourself.}" },
    { Path = "scripts/events/events/dlc8/anatomist_old_patient_event", Screen = "A", Source = "{[img]gfx/ui/events/event_77.png[/img]{%townname%'s denizens have mostly looked upon you and the anatomists as though you were wayward devils. But out of the blue, a man comes down off his porch and strides across the road toward %anatomist% the anatomist, carrying with him an upright posture, swinging gait, and a fat grin. He grabs the anatomist by the hand and starts vigorously shaking it.%SPEECH_ON%Shitfire, I'd figured you'd be back one of these days! You don't recognize me? You done come by this way years ago, many years ago, we both looked a fair bit younger then. I had that fat sack on m'back that you cut out, and my whole life's been much better since! Hells, gimme one second, don't you move a muscle I'll be right back!%SPEECH_OFF%The man quickly returns to his home. You look at %anatomist% who remarks that he remembers the man: he had a giant tumor growing on his spine, and the anatomist in his younger days had successfully cut it out using tongs, shearing blades, and a good number of rags. He laments that he did not keep the fleshy mass for study, but that he was a different sort of physician in those days. The man returns with a weapon which he holds out.%SPEECH_ON%Once I was of good health, I took to the fightin' fields. Was pretty good at it, too, but you know, lives change, and keep on changing. I'd seen you with this sellsword here so I suppose it had done changed for you as well. Please, take it.%SPEECH_OFF%The second the anatomist hesitates, you take the weapon yourself, lest the charitable opportunity be shortlived. You thank the man. He shakes %anatomist%'s hands again, then bids goodbye. The anatomist stares at him as he departs.%SPEECH_ON%We could experiment on him, now that I fully recollect my knowledge of him. That mass from his back is likely to return, I could perhaps...just...open him up and take a look...%SPEECH_OFF%You stop the anatomist from fancying any dissecting of the local laity and get back on the road.}" },
];

local missingOuterVariantReviewedJapanese = [
    "{[img]gfx/ui/events/event_05.png[/img]{%anatomist%は焚火のすぐそばに座っている。近すぎるほどだ。火傷しないよう少し後ろへ引っ張る。見上げた顔には膿疱が点々と浮かび、すでに潰れたものの脂じみた膿でべっとりしている。%SPEECH_ON%あの薬を飲んだのは、とんでもない間違いだったのではないかと思い始めています。%SPEECH_OFF%男はまた炎のほうへ尻をずらす。その目には、このまま自分を火へ投げ込みたいという思いが見て取れる。だが今の彼はあまりに気味が悪く、もう一度触れたくもないので、あなたにしてやれることはほとんどない。 | 傭兵団の荷馬車の脇に立つ%anatomist%を見つける。袖をまくり上げ、そこにある奇妙な斑紋を指でいじっていた。興味を引かれ、生まれつきの痣かと尋ねる。解剖学者は振り向き、首を振る。シャツをめくると、その斑紋は全身を覆っていた。剥がせない瘡蓋のようにざらついて見える、醜い色むらが皮膚を染めている。%SPEECH_ON%飲んだ薬のせいでこうなりました。どうすればよいのか、自分でもわかりません。%SPEECH_OFF%きっと良くなると頷いてやる。男はため息をつき、シャツを下ろして目を逸らす。 | %anatomist%は水桶にかがみ込み、暗い水面に映る自分を見つめている。ため息をついた。具合はどうかと声をかけると、振り向いた皮膚にはおぞましい発疹と腫れ物が広がっている。%SPEECH_ON%正直に申し上げれば、あまり良くありません。私が飲んだ調合薬は、どうやら甚大な悪影響を及ぼしたようです。いや、「甚大」では言葉が甘すぎるかもしれません。命は助かるでしょう。ですが傷ついたのは皮膚や肉体だけではなく、精神までなのです。自分はそうした悩みとは無縁だと思っていました。しかし今、この恐ろしい顔を見ると……絶えず心が乱されます。%SPEECH_OFF%肩をつかんでぎゅっと握り、背を叩く。そして水を飲めだの、もちろん気を落とすなだのと助言する。他人を慰めるのは元から得意ではない。まして科学の狂気から生まれた恐ろしい病に苦しむ男となればなおさらだ。 | 解剖学者の%anatomist%はすっかり塞ぎ込んでいる。自ら作り、待ちきれずに飲んだ薬のせいで、発疹や腫れ物、奇妙な痙攣らしきもの、止めどなく垂れる鼻水まで、ありとあらゆる症状が全身を襲っている。いずれ良くなると請け合うが、このおぞましい見た目が男の心を蝕んでいる。 | 解剖学者の%anatomist%が作ってきた奇妙な調合薬は、その本人が飲んできた奇妙な調合薬でもある。当然ながら、結果は芳しくない。発疹、感染症、悪臭、抜け落ちる髪、その他諸々。表向きは科学の名の下にやっているのだと言い張るが、こうした病と醜い変形の数々が男の士気を削いでいるのは明らかだ。時が経てば良くなるよう願うほかない。 | あなたには到底理解できない科学というものには、いつも危険がつきまとうらしい。子供の頃、友人が縄にぶら下がって川へ飛び込む危険を冒したことを思い出す。そのおかげで一同は、秋を迎えた枝がどれほどの重さに耐えられるかを偶然にも知ることになった。\n\n今度は解剖学者の%anatomist%が、自作の奇妙な薬を飲むことの危険を身をもって知っている。発疹と感染症に全身を侵され、おまけにどういうわけか蟻を呼び寄せる香りまで放つようになった。理由は誰にもわからないが、昼夜を問わず蟻が男の体を這い回りたがる。時が経てば、この病が治まり、忌々しい蟻どもも一緒に消えてくれることを願うばかりだ。 | 解剖学者たちが少しばかり頭のおかしい連中だとは前から知っていた。だが薬を作っては自分で飲む姿には、さすがのあなたも呆れ果てる。水でさえ、汲む杯を誤れば毒になりうる。まして、その日に頭へ浮かんだ科学的着想の泥沼から蒸留した調合薬を丸ごと飲むなど、なおさらだ。当然、頭でっかちの一人、%anatomist%が病に倒れるまで時間はかからなかった。歩き回り、日々の仕事をこなすことはできる。だが巨大な疣と膿を漏らす膿疱のせいで、見るも無残な姿だ。本人は自分を俗世から超然とした存在だと思っているのかもしれないが、豚糞を拭ったぼろ布のような姿で歩き回ることが心や魂に良いはずはない。少し時が経てば、良くなるかもしれない。 | %anatomist%は、自作の薬を飲んで病に倒れたというわけではない。何しろ今も動き回れ、必要なら戦うことさえできる。だがその薬が、見るに堪えない形で男へ影響したことだけは確かだ。頬には大きな腫れ物が浮かび、ときおり眼球が眼窩から飛び出しては自分で押し戻している。見なければよかったと思う光景だ。口の端からは涎が糸を引き、鼻の穴には鼻水と洟と血が、まるでナメクジのように巣くっている。死んだ豚の死骸より醜くなった件で、男が相当に落ち込んでいるのも無理はない。だが時が経てばきっと良くなると、あなたは信じている。}",
    "{[img]gfx/ui/events/event_05.png[/img]{数人の誓約者が一枚の紙を持ってくる。そこには%companyname%の名と、まるで釣り合いの取れていないあなたの滑稽な似顔絵、そして卑しい人柄を言い表す選りすぐりの悪口がいくつか記されている。どうやら世間におけるあなたの評判は、自分で思っていたほど高くも立派でもないらしい。%SPEECH_ON%これを正さねばなりません、隊長！　世間からこのように思われるとは、我ら誓約者への重大な侮辱です。何より、若きアンセルムへの侮辱です！%SPEECH_OFF%あなたも同意する。 | 傭兵団が野営していると、数人の誓約者が%companyname%の評判について不平を漏らしている。%SPEECH_ON%世間が我らを見る目を知れば、若きアンセルムはお喜びにならないでしょう。我らは正しい振る舞いの模範となるべきです！%SPEECH_OFF%あなたも同意する。ただし、誓約者たちの名誉を取り戻すには、しばらく時間がかかるかもしれない。 | 若きアンセルムは、誓約者とは名誉、美徳、そして正しい品性の先例を再び世へ打ち立てる模範であるべきだと信じ、この一団を創設した。彼は、世がそうしたものを見失ったと考えていたのだ。あいにく、あなたはその理想を守りきれず、%companyname%の評判をあるべき水準より少し低いところまで落としてしまった。数人の男が不満を口にするのも当然だ。口に出さぬ者でさえ、この過ちに士気を削がれているのは明らかである。究極の使命への信頼を男たちが失わぬうちに、なるべく早く%companyname%の評判を立て直し始めるべきだろう。}",
    "{[img]gfx/ui/events/event_05.png[/img]{新たに生じた異形の体でしばらく過ごした末、%anatomist%は今の自分を受け入れるようになった。このおぞましい傷痕と増え続ける膿疱こそ、自分が正しい道を進んでいる証拠だと考えている。ある意味ではそのとおりだ。奇怪な変化のおかげで、男は以前よりはるかに優れた戦士となった。あの愚かな頭でっかちどもが、せいぜい人並みの戦士にさえなれるとは個人的にまったく期待していなかったあなたにとって、これは大したことである。以前抱いていた恐れも不安も完全に消え、代わりに新たな使命感と、さらに先へ進もうとする意欲が宿っている。 | %anatomist%は、傷痕やおぞましい容姿を気にして塞ぎ込むのをやめた。今の姿を受け入れたらしい。あるいは全身から立ち上る凄まじい悪臭に慣れきり、自分ではもう気づかなくなっただけかもしれない。そばへ寄るたび、その臭いにあなたは吐きそうになる。それでも少なくとも、目覚めている間ずっと男を占めていた陰鬱さからは立ち直った。これでまた、科学的発見へ至る正しき道とやらを進めるだろう。本人がどう言っていたかは忘れたが。 | ありのままの自分を受け入れるのは難しい。そして上辺の問題とはいえ、自分の姿を受け入れるのはそれ以上に難しい。生まれ持った姿ではなく、自らの人生における行いによって形作られた姿なら、なおさらだ。自分の決断が新たな境遇を招いたのなら、残りの人生で思い返せるのは自らの選択だけである。耳や鼻や唇、あるいはそれ以上のものを失った傭兵をはじめ、あなたはそんな男を何度も見てきた。変わり果てた境遇を受け入れるまでには、長い時間がかかることもある。%anatomist%も例外ではなかった。だがついに受け入れたのだ。自らの行いで負ったおぞましい傷痕と変異は、少なくとも心の中では、もはや彼を苦しめていない。過去を乗り越え、科学的探究を求める者としてこの世界の道を歩み続ける覚悟ができた。そして、その探究がいつの日か自分へもたらすかもしれない大きな危険も受け入れている。 | %anatomist%は新しい姿を受け入れた。飲み続けた薬や調合物へ体が示した反応は、当初あまりにもおぞましく、男はかつての自分の殻へ閉じこもってしまった。責められたものではない。実際、以前も今もひどく醜いのだから。だがしばらくすれば、人生は続いていくのだと悟る。どうにもできないなら、どうにもできない。少なくとも、あの選択の本来の目的は科学的好奇心を満たすことだった。それを思い出したことで、%anatomist%の使命感は蘇ったらしい。今も不格好で気味が悪く、あなたは顔を見るのもつらいが、少なくとも本人は前より幸せだ。 | かつて病と醜い変形に傷ついた解剖学者の%anatomist%は、今ではずいぶん良い顔をするようになった。つまり、肉体の見た目について自分にできることはほとんどないと悟ったのだ。率直に言えば、その姿は今なお、目を向けるだけでも勇気と意志力を要する代物である。だが男は、歩き、話す怪物へ自分を変えた調合薬や奇妙な混合物、薬酒を求めた本当の理由を思い出した。それは科学的探究のためだった。解剖学者は今や以前より幸福であり、どんな小さな鏡からも遠ざけておけるなら、おおむねそのままでいられるだろう。 | %anatomist%は、作った薬を片端から飲み干す癖の報いをとうとう受けた。最後に飲んだ薬はひどい失敗作で、顔を肉の練り粉のように変え、皮膚の至るところへあらゆる瘤、痣、膿疱、膿溜まりを生じさせた。当然、この変化は男の士気へ深い打撃を与えた。だがついに乗り越えた。今もあらゆる意味で歩き、話す怪物だが、心の内では平穏を得ている。大切なのは中身だ。少なくとも、そうでなければ困る。外見のほうは、あなたでさえ目を向ける勇気をどうにか奮い起こさねばならないのだから。 | 解剖学者の%anatomist%は、自分の体に起きた変化を「変異」と呼ぶ。頭でっかちどもの言葉で、「糞みたいな見た目」を意味するのだろう。しばらくの間、その容姿は男の日常へ重くのしかかっていた。無理もない。自ら招いた病だ。世間から降りかかった災いより常に堪えるし、どうすればこんなしくじりを避けられたかも嫌というほど明白である。幸い、解剖学者はおぞましい見た目への憂鬱と苦悩を乗り越えた。以前にも増して薬や調合物を飲みたがるかもしれない。どうせ今より大きく醜くなることなど、まずないだろう。それに醜さも極まれば、女たちでさえ興味を示すようになる。疥癬だらけでよぼよぼの犬がいると、好奇心から撫でずにはいられないようなものだ。 | いくつもの怪しげな薬を飲んだ後、解剖学者の%anatomist%の体は変わり始めた。いい歳をした男にとって、その年齢での変化が良いものであることなど滅多にない。顔は崩れ、全身はただれと傷痕でまだらになった。しばらくの間、解剖学者はこの件で深い憂鬱に沈んだ。外側だけでなく内側まで、取り返しのつかない傷を負ったのではないかとあなたは案じた。幸い、人の士気ほど折りにくいものもない。%anatomist%は新たな姿を受け入れた。どうにかできることなど、ほとんどない。そして今では、この姿を一種の根源的な火の試練と考えている。今の自分があることも、そもそもこの地へ来る理由となった科学的探究へ力を貸せたことも、その試練の証なのだ。あなたの側で必要なのは、朝一番に男を目へ入れないよう気をつけることだけである。}",
    "{[img]gfx/ui/events/event_05.png[/img]{団員の一人が、何者かが野営地へ忍び込んで捕らえられたと叫びながら天幕へ駆け込んできた。盗賊かと問うと、男は首を振る。%SPEECH_ON%いや、もっと悪い。オースブリンガーです。%SPEECH_OFF%畜生め。飛び起きて外へ出ると、侵入者は縛られ、誓約者たちに打たれていた。あなたは制止して彼の前に立つ。%SPEECH_ON%オースブリンガー、アンセルムの顎はどこだ？%SPEECH_OFF%男はあなたの靴へ唾を吐き、渡すものか、誓約者どもは地獄へ行け、アンセルム本人がいれば案内してやる、と吐き捨てる。若きアンセルムの名を冒涜され、あなたと団員は息をのむ。%randombrother%が身を寄せる。%SPEECH_ON%命令をください、隊長。このオースブリンガーに、自分の誤りを教えてやります。%SPEECH_OFF%}",
    "{[img]gfx/ui/events/event_05.png[/img]{この男に価値あるものはない。解放しろと団員に命じる。彼らは反発する。オースブリンガーには誓約者と真の終末の道に従うか、死ぬかしかないという。若きアンセルムの顎骨を返す者の扱いはまだ定められていないが、この男は役に立たず、あなたも血を流す気分ではない。もう一度放せと言った瞬間、%randombrother%が男の喉を切り、皆が歓声を上げる。%SPEECH_ON%切れと言いましたよね、隊長？ ですよね？%SPEECH_OFF%誓約者があなたをかばっていると悟る。死なねばならなかったと否定し続ければ厄介になる。あなたはうなずく。%SPEECH_ON%そうだ、当然だ。道なきオースブリンガーは皆、この小鼠同様に死なねばならん！ そして皆死ぬのだ！%SPEECH_OFF%再び咆哮が上がるが、何人かはオースブリンガーを逃がせというあなたの愚かな提案を覚えているだろう。}",
    "{[img]gfx/ui/events/event_05.png[/img]{剣を抜き、男の心臓へ突き立てる。%SPEECH_ON%異端者よ、アンセルムは来世でお前を待たぬ。%SPEECH_OFF%男の身体は刃に沿って崩れ、見開かれた目はやがて地面を半眼で見つめる。剣を引き抜くと%companyname%が歓声を上げる。%SPEECH_ON%すべてのオースブリンガーに死を！%SPEECH_OFF%飢えたような熱気が傭兵団を包み、誓約者たちは剣を抜いて空へ掲げる。}",
    "{[img]gfx/ui/events/event_05.png[/img]{あなたはうなずく。%SPEECH_ON%若きアンセルムの顎へ舌が導くまで拷問しろ。手段は問わん、やれ。%SPEECH_OFF%背を向けると、囚人はアンセルムが許さないと叫ぶ。やがて意味の通らないことまで叫び出す。あなたは天幕へ退き、規則的な呻きに変わった悲鳴を聞きながら足を揺らす。やがて%randombrother%が現れ、保管庫になかった武器と防具を携えている。%SPEECH_ON%隠し場所へ案内させましたが、アンセルムの顎骨はまだありません。オースブリンガーの野営地にあるはずですが、場所は言いませんでした。舌を切った後は、少々……意思疎通に難が出まして。%SPEECH_OFF%囚人はどこかとため息交じりに問う。男は咳払いする。%SPEECH_ON%真っ白になって倒れました。死んでおります、隊長。%SPEECH_OFF%少なくとも、若きアンセルムには尽くした。}",
    "{[img]gfx/ui/events/event_05.png[/img]{情報を得るため男を拷問するよう命じる。どのオースブリンガーも若きアンセルムの顎骨の在り処を知っており、誓約者なら誰もが知りたがる。男は引きずられながら叫び、あなたは気分を害す絶叫や泣き声を遮るため天幕へ退く。間もなく、%torturer%が血の付いた服で入ってきて、何か言おうとして倒れた。別の誓約者が、囚人が拷問役を刺して逃げたと告げる。%torturer%が失血死しないよう助けろと命じる。%SPEECH_ON%呪われたオースブリンガーめ、名誉というものがない！ 必ず見つけて殺す。若きアンセルムも、我ら皆もそう言う！%SPEECH_OFF%歯を食いしばり、芝居がかった声で言う。真実は、あの野郎が逃げ、あの鼠どもは捕まえにくいというだけだ。%torturer%が生き延びることを願う。}",
    "{[img]gfx/ui/events/event_161.png[/img]{砂漠の荒野で出会うものは何であれ疑ってかかるべきだ。まして十字架に一人きりの男ならなおさらだ。肩に禿鷲を止まらせた磔の男は死んでいるように見えたが、近づくと鳥が飛び立ち、男は頭を上げた。手足の傷は凄惨だが、妙に元気で水を求める。水を渡す代わりに、なぜここにいるのかを問う。男はため息をつく。%SPEECH_ON%私は十字軍兵でした。古き神々の栄光を得るため軍と共に来たのです。だがここで土地の者や僧侶と話すうち、心変わりしました。%SPEECH_OFF%}",
    "{[img]gfx/ui/events/event_161.png[/img]{男はうなずく。%SPEECH_ON%ああ、奴らはそうしました。ただ、同じ理由で別の者を磔にした時、私はそこにいた。だから同じ道を辿る私は愚かだし、あの時は歓声を上げたので心も清くはない。それでもギルダーなら、私の内にある真の光を見てくれるかもしれません。%SPEECH_OFF%彼は空と、その上を旋回する禿鷲へ顔を向ける。%SPEECH_ON%私はまだ戦えます。相手が南だろうと北だろうと構わない。心にはギルダーがいる。%SPEECH_OFF%}",
    "{[img]gfx/ui/events/event_161.png[/img]{短剣を抜いて男を切り下ろす。傷は多いが、いつか回復できるだけの丈夫さはある。待っていた破滅にしては驚くほど穏やかに礼を言う。%SPEECH_ON%伸びられて助かりました。つまり、自分の意思で伸びられたということです。導いてください、ギルダーの巡り合わせの隊長、御方の偉大なる崇高さの隊長。%SPEECH_OFF%仲間を捨て、自らの神々にも背を向けた男を受け入れることを、傭兵団の多くは快く思わない。}",
    "{[img]gfx/ui/events/event_161.png[/img]{まもなく自分の神か神々と話すことになる、と男に告げる。彼はため息をつく。%SPEECH_ON%ある意味で、私はこれに値します。だが受け入れています。%SPEECH_OFF%傭兵団の反応は割れている。とはいえ大半は程度の違う歓喜だ。地上にも天上にも背いた裏切り者なら、誰からも憎まれやすい。}",
    "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker%が震える両手で若きアンセルムの頭蓋骨を抱え、天幕へ飛び込んでくる。%SPEECH_ON%壊れています！%SPEECH_OFF%椅子から跳び上がり、若きアンセルムの聖なる遺骨を確かめる。頭蓋骨の後ろへ、細い亀裂が一筋走っていた。最初は大したことがないように見える。だが小指を差し込んで持ち上げると、骨が割れて開く。二人で息を呑み、頭蓋骨を卓上へ置く。あと少し力が加わるだけで、ばらばらになりかねないのは疑いようもない。%SPEECH_ON%どうしましょう？　どうやって直せば？%SPEECH_OFF%あなたは慎重に考え込む。前回こんなことが起きた時には、若きアンセルムの顎骨が折れ、誓約者たちまで二つに割れた。一方は誓約者として残り、もう一方は野蛮で冒涜的なオースブリンガーを結成した。二度と同じことを起こすつもりはない。}",
    "{[img]gfx/ui/events/event_183.png[/img]{誓約者の%oathtaker%が焚火のそばへ来て、あなたと並ぶ。男は頷く。%SPEECH_ON%お言葉ですが、隊長。一人の男へ真に善良であれと求めるのは、重い要求です。初めてお会いした頃、あなたにそんな大仕事をやり遂げる器があるとは思っていませんでした。この世界へ忍び寄る闇に萎れさせられ、石を削る砂のようにすり減らされるだろうと思っていた。ですが、ここに立っておられる。揺るぎなく。次から次へと誓約を守り続けている。見事です。若きアンセルムも誇りに思われるでしょう。%SPEECH_OFF%誓約者の温かい言葉に礼を言う。}",
    "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker%が、掌を伸ばして骨の重みを支え、若きアンセルムの頭蓋骨の眼窩をじっと覗き込んでいる。ときおり頷き、囁くような祈りを呟く。あなたの気配を感じ、誓約者は振り向く。%SPEECH_ON%私は案じていました。しかし混沌の海が広がろうと、ここには若きアンセルムがいます。その勇気の源たるお方が必ず渡りきらせてくださると確信し、この世の大海原へ泳ぎ出せるほどです。若きアンセルムの教えを、ほかの者たちにも広めるべきでしょう。%SPEECH_OFF%まったく、そのとおりだ。 | 誓約者たちが焚火のそばで見事な食事を楽しんでいる。%oathtaker%は若きアンセルムの頭蓋骨を切り株へ置いていた。ときおり筋張った肉を載せた匙を持ったまま振り向き、骨の口へ少し食べさせようかと考えているように見える。そんな瞬間には不安を覚える。だが理由はどうあれ、小さな頭蓋骨はそこにあるだけで誓約者たちの気分を良くする傾向がある。この乙女めいていながら陰惨でもある奇行くらいは、大目に見てやろう。 | %oathtaker%が、フェルト張りの表紙と金箔の栞が付いた書物を調べている。傍らでは、消えかけた蝋燭のそばに若きアンセルムの頭蓋骨が置かれていた。何を読んでいるのかと尋ねる。男は顔を上げる。%SPEECH_ON%若きアンセルムが書き残したとおり、誓約にまつわる事柄を確かめています。あの若者の賢明な言葉を覚えておいてください。インクは最も強固な記憶である。ゆえに誓約を守るうえで己の力だけに頼らず、書かれた言葉そのものによって心の泉を新たにするのが賢明である、と。これも若きアンセルムの教えでした。お言葉どおりに文書へ目を通していれば、隊長もご存じだったでしょう。%SPEECH_OFF%少々とげのある言い方だが、間違ってはいない。 | %oathtaker%が若きアンセルムの頭蓋骨を磨いている。最初の誓約者への信仰を試すため、すでに答えを知っている質問をする。アンセルムはどのように死んだのか。誓約者は背筋を伸ばし、心底侮辱されたという顔であなたを見つめる。%SPEECH_ON%隊長、彼がどう死んだかは重要ではありません。いつ、なぜ、誰に殺されたのかもです。そもそも「誰か」などいなかったのかもしれない。重要なのは、彼が最後の道の誓約を歩んでいたことです。ゆえに我らも彼と共にその道を歩み、最後まで共にある。我らは単なる誓約者ではない。最後の誓約者なのです。%SPEECH_OFF%男は背を向け、骨から虫を弾き飛ばす。そして虫の足跡に冒涜されたかのように、頭蓋骨を磨き直す。%SPEECH_ON%隊長、我らが挑んでいるのは壮大な経験です。ですが時折、あなたはただ便乗しているだけではないかと思います。%SPEECH_OFF%少なくとも、財布を膨らませるという意味では壮大な経験だ。幸い、あなたの冷めた本性を見抜けるらしいのは、含蓄のある頭蓋骨とやらだけである。誓約者が骨を唾で磨く傍ら、若きアンセルムの空っぽの眼窩があなたを見つめている。 | %oathtaker%が若きアンセルムの頭蓋骨の前へひざまずく。%SPEECH_ON%若きアンセルムよ、我らの誓約を守る力をお与えください。私一人では成し遂げられず、まして隊長の助けだけでは到底足りません。%SPEECH_OFF%一人ではない、%companyname%の仲間がついているし、自分だって役立たずではない、と言いかける。だが、そういう現実的な話をする場ではなさそうだ。男は突然立ち上がり、頷く。%SPEECH_ON%このご導き、心より感謝いたします、若きアンセルム。%SPEECH_OFF%あなたも若者の頭蓋骨を眺めるだけで導きを見いだせたら、と少しだけ思う。だが若きアンセルムの骨の顔から受け取れるものは、空虚な眼差しだけだ。 | 傭兵団には浮き沈みがあったが、若きアンセルムは今なお信仰を広める第一の存在と見なされている。認めたくはないが、ときおりあなたは頭蓋骨を少しばかり忌々しく見つめてしまう。傭兵団を率いているのはあなたで、それも見事に率いているというのに、成功の多くは頭蓋骨のおかげとされる。男たちは助けが必要な時も、隊長を素通りして同じように頭蓋骨へ頼る。%oathtaker%がその一例だ。近頃つらい日々を送っていたのに、あなたへ相談するどころか、誓約者の務めについて骨の助言を得ようと若きアンセルムを抱え上げている。最初の誓約者の頭を石のように湖面へ投げ、水切りさせる夢を時々見る。 | 若きアンセルムの頭蓋骨は、最も信心深い誓約者にとっての心の支えである。物言わぬ骨の器から、知識や導き、それ以上のものまで湧き出すという。ここ数日ひどく落ち込んでいた%oathtaker%へ、頭蓋骨を預ける。ほんの短い間手元へ置いただけで、誓約への信仰を新たにした。 | 若きアンセルムの頭蓋骨を棒の先へ載せ、くるくる回している。骨は回るたびにがたがた鳴り、その空ろな音がぞっとするほど愉快だ。%oathtaker%が何か尋ねながら茂みを抜けてくる。あなたは頭蓋骨をつかみ、即座に下へ置いた。誓約者はあなたを見て、棒を見て、頭蓋骨を見て、もう一度あなたを見る。咳払いしてから、ここ数日はつらいこと続きだったと話す。導きを与えるため、そして面倒なので、若きアンセルムの頭蓋骨を手渡す。最初の誓約者の内に活力の復活、信仰の再生、勇気の再興を見いだせ、と告げる。男は従順に頷く。%SPEECH_ON%若きアンセルムは最初の誓約者ですが、それでも隊長は年齢をはるかに超えた知恵をお持ちだと信じています。最初からアンセルムを頼るべきでした！%SPEECH_OFF% | 若きアンセルムの頭蓋骨を切り株へ置き、その眼窩を狙って小石を投げている。一つが穴をすっと通り抜け、拳を突き上げた。ちょうどその時、%oathtaker%が姿を現す。男はあなたを見て、握った拳を見て、若きアンセルムを見る。そして頷く。%SPEECH_ON%あなたほどの皮肉屋でさえ若きアンセルムから勇気を授かるのなら、最初の誓約者のお力は私が信じていた以上なのでしょう。若きアンセルムからさらなる導きを得られるよう、お一人にいたします。%SPEECH_OFF%頷いて誓約者へ礼を言う。だが男が去ると、また遊びへ戻った。あいにく、今度はどの小石もアンセルムの頭頂へこつんこつんと当たるばかりだ。どうやら投げる勘を失ったらしい。 | 太い棒を手に、石を宙へ放っては遠くへ打ち飛ばしている。一打ごとの深く心地よい音も、石が勢いよく飛んでいく光景も、この上なく愉快だ。次の石を拾おうとかがむと、若きアンセルムの頭蓋骨がそこから見上げている。当然のように拾い上げ、片手で重さを量る。あまりに軽い。宙へ投げ、棒で打ち砕く。頭蓋の破片があらゆる方向へ渦を巻いて飛び、細かな骨粉が、奇術を披露したかのように周囲の空気を白くする。突然、脇腹に何かを感じた。世界が弾けて消え、瞬きをしながら目覚めると、%oathtaker%が爪先であなたをつついている。焚火のそばで居眠りしていたらしい。誓約者は頭蓋骨を隣へ置き、頷く。%SPEECH_ON%若きアンセルムへ助言を求め、授かりました、隊長。ですが眠りながら汗をかいておられたので、隊長にも最初の誓約者と過ごすひとときが必要かと思いました。%SPEECH_OFF%男は背を向けて去り、頭蓋骨と二人きりになる。骨はこちらの何もかも知っているかのように見つめている。少しばかり知りすぎている。頭を回して別の方角へ向け、また眠りにつく。 | %oathtaker%はここ数日つらいこと続きだった。若きアンセルムの頭蓋骨を持っていき、一人で物思いに耽り、誓約について振り返るよう告げる。男は頷く。わずか数分後、頭蓋骨を手にあなたの元へ戻ってくる。%SPEECH_ON%隊長のおっしゃるとおりでした。私は道から外れていましたが、最初の誓約者の導きによって再び見いだせました。%SPEECH_OFF% | 若きアンセルムの頭蓋骨は、少しくたびれて見え始めている。草の切れ端、泥、二、三匹の虫。そんなものが骨の上へこびりついていた。%oathtaker%が所持品についてくだらない質問をしに来る。言葉を遮って頭蓋骨を手渡し、磨くよう命じる。男は頷き、純金一ポンドでも見つめるかのように頭蓋骨を凝視する。十分もしないうちに仕事を終える。戻ってきた時には気分をすっかり持ち直し、若きアンセルムと二人きりで過ごしたことで活力を取り戻し、そもそもなぜ誓約者になったかを思い出した、と自ら認める。それは何よりだ。だがここで一番大切なのは、所持品の話をすることまで忘れてくれた点である。実に素晴らしい。}",
    "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker%を黙らせ、天幕の垂れ幕を閉じるよう命じる。頭蓋骨を受け取って卓上へ置き、すぐさま修復へ取りかかる。あいにく、両手へほんの少し力を込めただけで亀裂は広がり、骨片までいくつか飛び散って、どこかへ消える。火傷でもしたかのように頭蓋骨から手を放す。アンセルムの尊い骨が、卓上で空ろな音を立てて転がった。%oathtaker%があなたを見る。%SPEECH_ON%今度はどうします？　何をすれば？　一番良い部分を持って逃げ、新しい一団を作るべきでしょうか？%SPEECH_OFF%鼻で笑い、この馬鹿はあなたを誓約者ではなくオースブリンガーだと思っているのか、と尋ねる。男は息を呑み、前者だと認める。そのとおりだ。ならば、やるべきことは一つしかない。この頭蓋骨が割れることこそ若きアンセルムの望みであり、%companyname%が真の誓約者に相応しい責務を果たしていないことを示されたのだ、と主張するのだ。男も同意する。そして実際、残る男たちへ頭蓋骨と、新たに刻まれた骨の境目を見せることになる。\n\n初めは皆、亀裂を見て恐れる。だがすぐにあなたへ同意する。若きアンセルムの影響力が衰えているのは、最初の誓約者本人のせいではない。最後の誓約者たる自分たち全員が、誓約に恥じぬ責務を果たしていないからだ！　真の誓約者の道を歩むため、全員がさらに励まねばならない！　男たちは吠え、歓声を上げる。若きアンセルムの亀裂によって、その信念は新たになった。}",
    "{[img]gfx/ui/events/event_183.png[/img]{一本の糸を取り出し、蔦と樹液を塗りつける。それから若きアンセルムの頭蓋骨のひびをそっと持ち上げ、さらに樹液をつけた指でひびに沿ってなぞる。%oathtaker%は不安げに見つめている。これでよしと、ひびに沿って糸を差し込み、頭蓋骨の破片を元の位置へ戻す。糸と粘つく蔦を一緒に噛ませ、ぴたりと閉じた。二歩下がって出来栄えを眺める。%oathtaker%がごくりと唾を飲む。%SPEECH_ON%だ……誰にも気づかれないと思います。%SPEECH_OFF%こそこそと頭蓋骨を直した者の細工を見られるくらいなら、直そうとした跡のないひびを見つけられる方がまだましだったのでは、と本気で心配になる。ともあれ、もう済んだことだ。若きアンセルムの名誉は取り戻された。%oathtaker%が額の汗をぬぐう。%SPEECH_ON%これは試練だったのだと思います、隊長。そして若きアンセルムが我らを導き、乗り越えさせてくださったのです。その力が私の内を流れています。今この胸にある栄誉は、いかなる言葉でも言い表せません。%SPEECH_OFF%何だって？　若きアンセルムは粘る樹液や蔦のことなど、おそらく何も知らなかったはずだ。物言わぬ頭蓋骨となった今なら、なおさら知りようがない。それでも……あなたは%oathtaker%の解釈に任せることにする。自分の手柄をずいぶん安く見積もった解釈ではあるが。}",
    "{[img]gfx/ui/events/event_77.png[/img]{%townname%の住人たちは、おおむねあなたと解剖学者たちを、道を踏み外した悪魔でも見るような目で見ていた。ところが突然、一人の男が玄関先から降り、背筋を伸ばし、大股で歩き、満面の笑みを浮かべながら、道を横切って解剖学者の%anatomist%へ近づいてくる。男は解剖学者の手をつかみ、勢いよく何度も振った。%SPEECH_ON%ちくしょう、いつかきっと戻ってくると思ってたんだ！　俺が分からんか？　何年も前にここを通っただろ。ずっと昔だ、あの頃は二人とももう少し若かった。俺の背中にあった、あのでかい袋をあんたが切り取ってくれた。それから俺の人生はずっとよくなったんだ！　そうだ、ちょっとだけ待ってくれ。一歩も動くな、すぐ戻る！%SPEECH_OFF%男は急いで家へ戻る。あなたが%anatomist%を見ると、その男を覚えていると言う。背骨に巨大な腫瘍ができており、若き日の解剖学者は、火ばさみ、裁ちばさみ、それに大量のぼろ布を使って見事に切除したそうだ。肉塊を研究用に取っておかなかったことを嘆くが、当時は今とは違う種類の医者だったとも語る。男が戻り、一本の武器を差し出した。%SPEECH_ON%元気になってからは戦場へ出るようになった。俺もなかなか強かったんだぞ。でも、ほら、人生は変わる。変わり続けるもんだ。あんたがこの傭兵と一緒にいるのを見て、あんたの人生も変わったんだろうと思ってな。どうか、受け取ってくれ。%SPEECH_OFF%解剖学者がためらった、その瞬間にあなた自身が武器を受け取る。せっかくの厚意が冷めないうちに。あなたは男に礼を言う。男はもう一度%anatomist%の両手を握って振り、別れを告げた。遠ざかる背を解剖学者が見つめる。%SPEECH_ON%あの男なら実験できる。今では彼について知っていたことをすべて思い出した。背中のあの腫瘤はいずれ再発する可能性が高い。ひょっとすると……ほんの少し……切り開いて、中を見られるかもしれない……。%SPEECH_OFF%地元の庶民を解剖する空想にふける解剖学者を止め、あなたは再び道へ戻る。}",
];

// Every exact class/screen/source composition must translate once, call the
// inherited renderer once, append one temporary close, and leave raw state.
local balancedClassSeen = {};
foreach (fixtureIndex, fixture in missingOuterVariantFixtures) {
    local translated = missingOuterVariantReviewedJapanese[fixtureIndex];
    ::SourceDefectTestTranslations[fixture.Source] <- translated;
    local originalCalls = 0;
    local originalInput = null;
    local wrapped = hooks[fixture.Path].buildText(function (_text) {
        originalCalls += 1;
        originalInput = _text;
        return "grouped rendered";
    });
    local eventState = makeMissingOuterVariantEventState(fixture.Screen, fixture.Source);
    local activeScreenRef = eventState.m.ActiveScreen;
    local screensRef = eventState.m.Screens;
    local stateBefore = snapshotMissingOuterVariantEventState(eventState);
    local translationsBefore = ::SourceDefectTranslationCalls;
    assertEqual(wrapped.call(eventState, fixture.Source), "grouped rendered");
    assertEqual(originalInput, translated + "}");
    assertEqual(originalCalls, 1);
    assertEqual(::SourceDefectTranslationCalls, translationsBefore + 1);
    assertEqual(snapshotMissingOuterVariantEventState(eventState), stateBefore);
    assertTrue(eventState.m.ActiveScreen == activeScreenRef, "ActiveScreen identity changed");
    assertTrue(eventState.m.Screens == screensRef, "Screens identity changed");
    assertEqual(eventState.m.Screens[0].Text, fixture.Source);

    // A valid alternate screen in each multi-screen class must never select
    // the source signature belonging to another screen.
    local wrongScreen = "Z";
    if (fixture.Path == "scripts/events/events/dlc8/captured_oathbringer_event") {
        wrongScreen = fixture.Screen == "A" ? "B" : "A";
    }
    else if (fixture.Path == "scripts/events/events/dlc8/oathtakers_skull_cracked_event") {
        wrongScreen = fixture.Screen == "A" ? "B" : "A";
    }
    local wrongState = makeMissingOuterVariantEventState(wrongScreen, fixture.Source);
    translationsBefore = ::SourceDefectTranslationCalls;
    local callsBefore = originalCalls;
    assertEqual(wrapped.call(wrongState, fixture.Source), "grouped rendered");
    assertEqual(originalInput, fixture.Source);
    assertEqual(originalCalls, callsBefore + 1);
    assertEqual(::SourceDefectTranslationCalls, translationsBefore);

    // One representative per exact class proves a balanced source receives no
    // second close and bypasses Rosetta entirely.
    if (!(fixture.Path in balancedClassSeen)) {
        balancedClassSeen[fixture.Path] <- true;
        local balancedInput = fixture.Source + "}";
        local balancedState = makeMissingOuterVariantEventState(fixture.Screen, fixture.Source);
        translationsBefore = ::SourceDefectTranslationCalls;
        callsBefore = originalCalls;
        assertEqual(wrapped.call(balancedState, balancedInput), "grouped rendered");
        assertEqual(originalInput, balancedInput);
        assertEqual(originalCalls, callsBefore + 1);
        assertEqual(::SourceDefectTranslationCalls, translationsBefore);
    }
}
assertEqual(missingOuterVariantFixtures.len(), 18);
assertEqual(missingOuterVariantReviewedJapanese.len(), 18);
assertEqual(balancedClassSeen.len(), 9);

local driftFixture = missingOuterVariantFixtures[3];
local driftTranslation = missingOuterVariantReviewedJapanese[3];
::SourceDefectTestTranslations[driftFixture.Source] = driftTranslation;
local driftCalls = 0;
local driftInput = null;
local driftWrapper = hooks[driftFixture.Path].buildText(function (_text) {
    driftCalls += 1;
    driftInput = _text;
    return "drift rendered";
});
local driftState = makeMissingOuterVariantEventState(driftFixture.Screen, driftFixture.Source);
local assertSourceFailClosed = function (_input) {
    local callsBefore = driftCalls;
    local translationsBefore = ::SourceDefectTranslationCalls;
    assertEqual(driftWrapper.call(driftState, _input), "drift rendered");
    assertEqual(driftInput, _input);
    assertEqual(driftCalls, callsBefore + 1);
    assertEqual(::SourceDefectTranslationCalls, translationsBefore);
};

local source = driftFixture.Source;
local middleAt = source.len() / 2;
assertSourceFailClosed(source.slice(0, middleAt) + "MIDDLE_DRIFT" + source.slice(middleAt));
local proseAt = source.find("[/img]{") + "[/img]{".len();
assertSourceFailClosed(source.slice(0, proseAt) + "X" + source.slice(proseAt + 1));
assertSourceFailClosed(source.slice(0, source.len() - 2) + "X" + source.slice(source.len() - 1));
assertSourceFailClosed(source.slice(0, middleAt) + "{" + source.slice(middleAt));
assertSourceFailClosed(source.slice(0, middleAt) + "|" + source.slice(middleAt));
assertSourceFailClosed(source.slice(0, middleAt) + "\n" + source.slice(middleAt));
assertSourceFailClosed(replaceText(source, "event_05.png", "event_99.png", 1));
assertSourceFailClosed(source.slice(0, middleAt) + "%SPEECH_ON%" + source.slice(middleAt));

local orderedTokens = testExtractPercentTokens(source);
local firstTokenAt = source.find(orderedTokens[0]);
local secondTokenAt = source.find(orderedTokens[1], firstTokenAt + orderedTokens[0].len());
local reorderedSource = source.slice(0, firstTokenAt) + orderedTokens[1]
    + source.slice(firstTokenAt + orderedTokens[0].len(), secondTokenAt)
    + orderedTokens[0] + source.slice(secondTokenAt + orderedTokens[1].len());
assertSourceFailClosed(reorderedSource);
assertSourceFailClosed(null);

local malformedStates = [
    {},
    { m = { ActiveScreen = null } },
    { m = { ActiveScreen = "A" } },
    { m = { ActiveScreen = { ID = [driftFixture.Screen] } } }
];
foreach (malformedState in malformedStates) {
    local callsBefore = driftCalls;
    local translationsBefore = ::SourceDefectTranslationCalls;
    assertEqual(driftWrapper.call(malformedState, source), "drift rendered");
    assertEqual(driftInput, source);
    assertEqual(driftCalls, callsBefore + 1);
    assertEqual(::SourceDefectTranslationCalls, translationsBefore);
}

local assertTranslationFailClosed = function (_translation, _expectedInput) {
    ::SourceDefectTestTranslations[source] = _translation;
    local callsBefore = driftCalls;
    local translationsBefore = ::SourceDefectTranslationCalls;
    assertEqual(driftWrapper.call(driftState, source), "drift rendered");
    assertEqual(driftInput, _expectedInput);
    assertEqual(driftCalls, callsBefore + 1);
    assertEqual(::SourceDefectTranslationCalls, translationsBefore + 1);
};
assertTranslationFailClosed(null, source);
assertTranslationFailClosed(driftTranslation + "}", driftTranslation + "}");
assertTranslationFailClosed(driftTranslation + "|", driftTranslation + "|");
assertTranslationFailClosed(driftTranslation + "\n", driftTranslation + "\n");
local wrongImageTranslation = replaceText(driftTranslation, "event_05.png", "event_99.png", 1);
assertTranslationFailClosed(wrongImageTranslation, wrongImageTranslation);
local missingTokenTranslation = replaceText(driftTranslation, orderedTokens[0], "", 1);
assertTranslationFailClosed(missingTokenTranslation, missingTokenTranslation);
::SourceDefectTestTranslations[source] = driftTranslation;

// Representative composition: Rosetta once, inherited native path once,
// one variant selected, dynamic company token substituted, no raw brace, and
// the complete event state snapshot remains identical.
local compositionFixture = missingOuterVariantFixtures[1];
local compositionTranslation = missingOuterVariantReviewedJapanese[1];
::SourceDefectTestTranslations[compositionFixture.Source] = compositionTranslation;
local nativeCalls = 0;
local selectedVariants = 0;
local compositionWrapper = hooks[compositionFixture.Path].buildText(function (_text) {
    nativeCalls += 1;
    if (testCountOccurrences(_text, "{") != 2 || testCountOccurrences(_text, "}") != 2) {
        throw "native composition received unbalanced braces";
    }
    if (testCountOccurrences(_text, "|") != 2) throw "native composition pipe signature changed";
    local substituted = replaceText(_text, "%companyname%", "黒旗団");
    if (substituted.find("黒旗団") == null) throw "dynamic company substitution failed";
    selectedVariants += 1;
    return "選択済み変種:黒旗団";
});
local compositionState = makeMissingOuterVariantEventState(compositionFixture.Screen, compositionFixture.Source);
local compositionActiveRef = compositionState.m.ActiveScreen;
local compositionScreensRef = compositionState.m.Screens;
local compositionBefore = snapshotMissingOuterVariantEventState(compositionState);
local compositionTranslationsBefore = ::SourceDefectTranslationCalls;
local compositionDisplay = compositionWrapper.call(compositionState, compositionFixture.Source);
assertEqual(compositionDisplay, "選択済み変種:黒旗団");
assertEqual(nativeCalls, 1);
assertEqual(selectedVariants, 1);
assertEqual(::SourceDefectTranslationCalls, compositionTranslationsBefore + 1);
assertTrue(compositionDisplay.find("{") == null && compositionDisplay.find("}") == null, "raw brace reached display");
assertEqual(snapshotMissingOuterVariantEventState(compositionState), compositionBefore);
assertTrue(compositionState.m.ActiveScreen == compositionActiveRef, "composition ActiveScreen identity changed");
assertTrue(compositionState.m.Screens == compositionScreensRef, "composition Screens identity changed");
assertEqual(compositionState.m.Screens[0].Text, compositionFixture.Source);

print("SOURCE_DEFECT_BOUNDARIES_TEST_OK\n");
