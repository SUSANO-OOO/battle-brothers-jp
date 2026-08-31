// Display-only normalizations for independently reviewed defects in the exact
// installed source snapshot. These wrappers compose with Rosetta and repair
// only malformed placeholder spellings or unmatched variant braces in a
// temporary template/final player-facing return. They do not write event or
// background state, actor data, save data, or gameplay values.

if ("SourceDefectBoundariesInstalled" in ::BattleBrothersJP) return;
::BattleBrothersJP.SourceDefectBoundariesInstalled <- true;

local mod = ::BattleBrothersJP.Mod;
local legendsEnabled = !("ModuleStatus" in ::BattleBrothersJP)
    || ::BattleBrothersJP.ModuleStatus.legends.Enabled;
local dlcUnholdEnabled = !("ModuleStatus" in ::BattleBrothersJP)
    || ::BattleBrothersJP.ModuleStatus.dlc_unhold.Enabled;
local dlcWildmenEnabled = !("ModuleStatus" in ::BattleBrothersJP)
    || ::BattleBrothersJP.ModuleStatus.dlc_wildmen.Enabled;
local dlcDesertEnabled = !("ModuleStatus" in ::BattleBrothersJP)
    || ::BattleBrothersJP.ModuleStatus.dlc_desert.Enabled;
local dlcPaladinsEnabled = !("ModuleStatus" in ::BattleBrothersJP)
    || ::BattleBrothersJP.ModuleStatus.dlc_paladins.Enabled;

local function safeTranslate(_value)
{
    try { return ::BattleBrothersJP.Runtime.translate(_value); }
    catch (jpError) { return _value; }
}

// Vanilla 1.5.2-3 has one extra closing variant brace in the B1 prose of the
// Kraken cult entrance event. Hook the exact event class and normalize only
// the final returned display for that exact installed-source prefix/suffix.
// The source screen, reply flags, option results, and event state stay raw.
local krakenB1Prefix = "[img]gfx/ui/events/event_120.png[/img]{She turns to her tomes and stares at them as though they were gravestones.";
local krakenB1Suffix = "but that many tales is a little suspicious.}}";

if (dlcUnholdEnabled) mod.hook("scripts/events/events/dlc2/location/kraken_cult_enter_event", function (q) {
    q.buildText = @(__original) function (_text) {
        local ret = __original(_text);
        if (typeof _text != "string" || typeof ret != "string") return ret;
        if (!::BattleBrothersJP.Runtime.Str.startsWith(_text, krakenB1Prefix)
            || !::BattleBrothersJP.Runtime.Str.endsWith(_text, krakenB1Suffix)) return ret;

        // The native template consumer removes the balanced variant braces;
        // the installed unmatched second close survives as one raw trailing
        // brace. Remove exactly that final display byte if it is present.
        if (::BattleBrothersJP.Runtime.Str.endsWith(ret, "}")) return ret.slice(0, ret.len() - 1);
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

if (dlcWildmenEnabled) mod.hook("scripts/events/events/dlc4/barbarian_tells_story_event", function (q) {
    q.buildText = @(__original) function (_text) {
        if (typeof _text != "string"
            || !::BattleBrothersJP.Runtime.Str.startsWith(_text, barbarianStoryPrefix)
            || !::BattleBrothersJP.Runtime.Str.endsWith(_text, barbarianStorySuffix)
            || !hasExactBraceSignature(_text, 2, 1)) return __original(_text);

        local translated = safeTranslate(_text);
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
            || !::BattleBrothersJP.Runtime.Str.startsWith(_text, unfriendlyTownPrefix)
            || !::BattleBrothersJP.Runtime.Str.endsWith(_text, unfriendlyTownSuffix)
            || !hasExactBraceSignature(_text, 3, 2)
            || countOccurrences(_text, " | ") != 7
            || countOccurrences(_text, "%townname%") != 1
            || countOccurrences(_text, "\n") != 0) return __original(_text);

        local translated = safeTranslate(_text);
        if (typeof translated != "string") return __original(_text);
        if (!hasExactBraceSignature(translated, 3, 2)
            || countOccurrences(translated, " | ") != 7
            || countOccurrences(translated, "%townname%") != 1
            || countOccurrences(translated, "\n") != 0) return __original(translated);
        return __original(translated + "}");
    }
});

// Vanilla 1.5.2-3 contains eighteen event templates whose outer variant
// group is missing its final close. Each exact installed English source is
// allowlisted by event class and active screen. Rosetta translates the raw
// source first; only a structurally exact translated temporary receives one
// close before the inherited renderer runs. Event screens and state stay raw.
local missingOuterVariantTargets = {
    ["scripts/events/events/dlc8/anatomist_bummed_at_mutations_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_05.png[/img]{%anatomist% is sitting near to the campfire. Almost too close. You pull him back a ways so he doesn't burn himself. He looks up, his face dotted with pustules and slathered in the grease of ones which have already popped.%SPEECH_ON%I'm beginning to wonder if I made a great mistake in drinking that potion.%SPEECH_OFF%He scoots back toward the flames, and there's a sense in his eyes that he wants to pitch himself into it. You can't do much for him, mostly because he looks awfully gross at the moment and you'd rather not touch him again. | You find %anatomist% standing beside the company wagon with a sleeve unfurled and his finger picking at some strange markings there. Curious, you ask if they are birthmarks. The anatomist turns, shaking his head. He lifts up his shirt to show that these markings are all over his body, mottling the flesh with unsightly colors which look rough to the touch, like scabs that cannot be peeled.%SPEECH_ON%The potion I drank did this and I know not what to with myself.%SPEECH_OFF%You nod and tell him it'll surely get better. He sighs and simply lowers his shirt and looks away. | %anatomist% stands over a bucket of water, looking at his darkened reflection in it. He sighs. You ask how he is doing, and he turns to reveal horrific rashes and boils upon his skin.%SPEECH_ON%I am not doing so well, to be honest. The concoction I imbibed seems to have had a gravely ill-effect on me, though I am being perhaps a little giving with my vocabulary there. I will survive, but it has wounded me in ways that are not just of the skin and the body, but of the mind. I thought myself distanced from such matters, but now, seeing my horrible face...I am in a state of perpetual unease.%SPEECH_OFF%You grab his shoulder and give it a squeeze, then pat him on the back and make some recommendations like he should drink some water and of course to not feel bad. You weren't ever that great at consoling other men, much less ones suffering from terrible maladies sprung from scientific madness. | %anatomist% the anatomist is in a despondent state. The potion he made, and was in such a hurry to drink, has resulted in his entire body being overcome with maladies ranging from rashes to boils to what appear to be unusual spasms and plenty of snot from the nose. You assure him that he will get better, but his horrific appearance is taking a toll on him. | The strange concoctions %anatomist% the anatomist has been making, are strange concoctions that he has also been drinking. Unsurprisingly, the effects have not been good: rashes, infections, smells, hair falling out, and more. While on the outside he proclaims that what he is doing is in the name of science, you can tell that all these maladies and disfigurations are debilitating to the man's morale. You can only hope he gets better with time. | Matters of science, which are far outside your understanding, always do seem to come with risks. You remember as a child that your friend took the risk of swinging out on a rope into a river, and by happenstance you all found out just how much weight a branch can hold while in the throes of Fall.\n\nNow, it seems %anatomist% the anatomist is finding out the debilitating nature of drinking one of his bizarre potions. He is overwhelmed with rashes and infections, and for some reason he is a siren to ants, who for who knows what reason now love to crawl on him at all hours of day and night. Hopefully, with time, these maladies will depart, and hopefully take the damned ants with them. | You always knew the anatomists to be a bit wrong in the head, but the way they've been creating potions and drinking them has really floored you. Water alone can be poisonous if sipped from the wrong cup, nevermind wholesale concoctions which are distilled in the mire of whatever scientific notions the anatomists are carrying that day. Naturally, it isn't long until one of the eggheads, %anatomist%, falls ill. He is still capable of moving and day-to-day tasks, but the giant warts and leaking pustules makes him a horror to look at, and though he may see himself distanced from society, you've little doubt that walking around looking like a rag that's mopped up pigshite is healthy for the mind and spirit. Hopefully, with a bit of time, he might get better. | %anatomist% isn't necessarily sick from drinking his potions. After all, he is still able to move and get around, and even fight if necessary. But he is certainly affected by said potions in a manner most unsightly. Great boils have appeared on his cheeks, and occasionally his eyes spring from their sockets and he has to push them back in which is something you wished you hadn't seen. Strings of drool come down the corners of his lips and his nostril is home to snails of snot and boogers and blood. As you can imagine, he is rather down about the whole looking uglier than a dead pig carcass-thing, but you've faith that in good time he will get better.}",
            Prefix = "{[img]gfx/ui/events/event_05.png[/img]{%anatomist% is sitting near to the campfire. Almost too close. You pull him back a ways so he doesn't burn himself. He lo",
            Suffix = "ood. As you can imagine, he is rather down about the whole looking uglier than a dead pig carcass-thing, but you've faith that in good time he will get better.}",
            ImagePrefix = "{[img]gfx/ui/events/event_05.png[/img]{",
            Pipes = 7, Newlines = 2,
            Tokens = ["%anatomist%", "%SPEECH_ON%", "%SPEECH_OFF%", "%anatomist%", "%SPEECH_ON%", "%SPEECH_OFF%", "%anatomist%", "%SPEECH_ON%", "%SPEECH_OFF%", "%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%"]
        },
    },
    ["scripts/events/events/dlc8/bad_reputation_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_05.png[/img]{A few of the Oathtakers bring a piece of paper to your attention. On it is the name of the %companyname%, a rather amusing drawing of yourself that is not remotely in proportion, and a few choice descriptors of your lowly character. It seems that your reputation in this world is not nearly as high and mighty as you assumed it to be.%SPEECH_ON%We must rectify this, captain! For people to think of the Oathtakers in this manner is a great insult to us, and especially to Young Anselm!%SPEECH_OFF%You agree. | As the company camps, a few of the Oathtakers are grousing about the reputation of the %companyname%.%SPEECH_ON%Young Anselm would not be happy with the way the world sees us. We should be setting an example of how to behave!%SPEECH_OFF%You agree, though it may take some time to repair the Oathtakers' honor. | Young Anselm founded the Oathtakers with the belief that they should be paragons reestablishing a precedence of honor, virtue, and sound character, elements which he believed the world had lost sight of. Unfortunately, you've struggled to maintain these ideals, slipping the %companyname%'s reputation a little lower than it ought to be. A few of the men are rightfully complaining, and if they're not outwardly complaining it is obvious that these faults are draining morale anyway. You think it best to perhaps start mending the %companyname%'s reputation as soon as possible lest the men lose faith in its ultimate purpose.}",
            Prefix = "{[img]gfx/ui/events/event_05.png[/img]{A few of the Oathtakers bring a piece of paper to your attention. On it is the name of the %companyname%, a rather amusin",
            Suffix = "g morale anyway. You think it best to perhaps start mending the %companyname%'s reputation as soon as possible lest the men lose faith in its ultimate purpose.}",
            ImagePrefix = "{[img]gfx/ui/events/event_05.png[/img]{",
            Pipes = 2, Newlines = 0,
            Tokens = ["%companyname%", "%SPEECH_ON%", "%SPEECH_OFF%", "%companyname%", "%SPEECH_ON%", "%SPEECH_OFF%", "%companyname%", "%companyname%"]
        },
    },
    ["scripts/events/events/dlc8/anatomist_ok_with_mutations_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_05.png[/img]{After spending some time with his new malformed shapes, %anatomist% has come to accept who he is now. He sees these horrific scars and ever growing pustules as evidence that he is on the right path. In some way, he is right. These strange changes have made him a far superior fighter than he was before, which is saying a lot for you personally had no hope that these foolish eggheads ever had a shot of becoming even competent fighters at best. Whatever fears and worries he had prior are now gone entirely, replaced by a renewed sense of purpose and desire to do more. | %anatomist% has stopped moping around worrying about his scars and horrible appearance. It seems he has made peace with how he looks now, or possibly he has simply become so ingratiated with the godawful smell emanating from every part of him that he no longer notices. While his stink brings you to nearly vomit every time you're near him, at the very least he has recovered from the dourness which was occupying his every waking minute. Maybe now he can continue on his righteous path to scientific discovery, or however else he put it. | It is hard to come to terms with who you are and, despite the superficiality, it is even more difficult to make peace with how you look. This is even more true when how you look was not the manner in which you were born, but shaped by the actions you took in life. If your own decisions brought you to this newfound state, you have only your own choices to dwell upon for the rest of your life. You've seen it many a time, particularly with sellswords who lose their ears, noses, lips, and worse. It can take a long time for a man to come to peace with his newformed circumstances, and %anatomist% was no different. But come to peace he has. Whatever horrific scars and mutations he has suffered from his own actions are no more - at least mentally. He has moved on and is ready to continue his path in this world as someone seeking scientific endeavors, and the great risks to himself that those endeavors might one day pose. | %anatomist% has come to terms with his new appearances. At first, his body's reactions to the potions and concoctions he's been imbibing were so disturbing that he reeled into a shell of his former self. You could hardly blame him, for he did and does look quite hideous. But after a while, you simply realize that life goes on, and if nothing can be done about it then nothing can be done about it. And, at the very least, the real purpose of the choices made were to satisfy scientific inquiries, and it seems re-realizing that has revivified %anatomist%'s sense of purpose. He is still ungainly and disgusting and you have a hard time looking at him, but least he's happier now. | Once wounded by maladies and disfigurements, %anatomist% the anatomist is starting to look a lot better now. That is to say, he has come to realize that there is little he can do about his physical appearance which is, to be terse, still something that takes courage and willpower to just look at. But the man has remembered the true reason he sought the concoctions and strange mixtures and tinctures which have turned him into a walking and talking monstrosity, and that reason is a matter of scientific endeavor. The anatomist is now a happier man and as long as he can be kept far away from even the smallest of mirrors you imagine that can more or less remain the case. | %anatomist%'s habit of sucking down any every potion he concocts did eventually come to bite him in the ass. His last imbibement when horribly wrong, turning his face into fleshy dough, and arising across his skin all manner of bumps and bruises and pustules and pusses. Naturally, these changes had a deep morale impact on the man. But, finally, he has gotten over it. He is still a walking, talking monstrosity in every sense of the word, but on the inside he is at peace with it, and what's on the inside is what counts. Or at least it better count, because what's on the outside you can barely muster the courage to look at. | %anatomist% the anatomist calls the changes to his body 'mutations', which must be some sort of egghead word for looking like shite. For a while, his appearance was a drag on his day to day life. You can hardly blame him, he inflicted these maladies upon himself which is always far worse than when the world does it to you and leaves little doubt as to how you could have unfarked yourself. Thankfully, the anatomist has gotten over his depression and angst about his horrendous appearance. He might even be more willing than ever to keep imbibing his potions and concoctions. Surely he can't look much worse than he already does and at a certain point of looking completely hideous even the ladyfolk take a turn, like seeing a dog so mangy and decrepit that one can't help but pet it out of curiosity. | After he drank a number of questionable potions, %anatomist% the anatomist's body began to change and, like any grown man, change at that age is rarely a good thing. His face became disfigured, his body mottled with sores and scars. For a time, the anatomist fell into a deep depression over the matter and you wondered if he had been irreversibly damaged not just on the outside, but the inside as well. Thankfully, it is the morale of a man that can be the hardest to break. %anatomist% has come to terms with his new appearance. It's not as though there is much he can do about it, and he now sees it as a sort of fundamental rite by fire that he is the way he is, and that he has helped pursue the scientific endeavors which brought him to these lands in the first place. You yourself just have to make sure that he's not the first thing you see in the morning.}",
            Prefix = "{[img]gfx/ui/events/event_05.png[/img]{After spending some time with his new malformed shapes, %anatomist% has come to accept who he is now. He sees these horri",
            Suffix = "ntific endeavors which brought him to these lands in the first place. You yourself just have to make sure that he's not the first thing you see in the morning.}",
            ImagePrefix = "{[img]gfx/ui/events/event_05.png[/img]{",
            Pipes = 7, Newlines = 0,
            Tokens = ["%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%", "%anatomist%"]
        },
    },
    ["scripts/events/events/dlc8/captured_oathbringer_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_05.png[/img]{One of the men rushes into your tent exclaiming that someone has been caught sneaking into the camp. You ask if it's a thief. The man shakes his head.%SPEECH_ON%No, worse. He's an Oathbringer.%SPEECH_OFF%Sonuvabitch. You jump to your feet and rush out, finding this interloper already tied up and being battered by the Oathtakers. You break it up, coming to stand before him.%SPEECH_ON%Oathbringer, where is Anselm's jaw?%SPEECH_OFF%The man spits on your boot and tells you he'd never give that up, and that the Oathtakers can go to the hells where they belong, and that Anselm himself would walk them there if he could. This blaspheming of Young Anselm's name draws gasps from you and your men. %randombrother% leans over.%SPEECH_ON%Just give the word, captain, and we'll show this Oathbringer the error of his ways.%SPEECH_OFF%}",
            Prefix = "{[img]gfx/ui/events/event_05.png[/img]{One of the men rushes into your tent exclaiming that someone has been caught sneaking into the camp. You ask if it's a th",
            Suffix = "ps from you and your men. %randombrother% leans over.%SPEECH_ON%Just give the word, captain, and we'll show this Oathbringer the error of his ways.%SPEECH_OFF%}",
            ImagePrefix = "{[img]gfx/ui/events/event_05.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%SPEECH_ON%", "%SPEECH_OFF%", "%SPEECH_ON%", "%SPEECH_OFF%", "%randombrother%", "%SPEECH_ON%", "%SPEECH_OFF%"]
        },
        ["E"] = {
            Source = "{[img]gfx/ui/events/event_05.png[/img]{This man has nothing of value. You tell the men to cut him loose. They protest, saying that an Oathbringer has but one choice, to submit to the Oathtakers and to the true Final Path, or to die. There is also room for one who returns Young Anselm's jawbone, but the codes on how to treat an Oathbringer who does that have not yet been worked out. But, as far as this man is concerned, he is of no real use and you're in no mood for bloodspilling. Just as you reiterate to cut him loose, %randombrother% cuts the man's throat, much to the cheering of the others.%SPEECH_ON%You said cut him, right captain? Right?%SPEECH_OFF%You realize the Oathtaker is covering for you, and to keep denying that the Oathbringer had to die might put you in a prickly situation. You nod.%SPEECH_ON%Yes, of course, the little rat had to die, same as all the pathless Oathbringers! And die they all shall!%SPEECH_OFF%The men roar again though you have a feeling that a few will remember your ridiculous suggestion to let an Oathbringer walk.}",
            Prefix = "{[img]gfx/ui/events/event_05.png[/img]{This man has nothing of value. You tell the men to cut him loose. They protest, saying that an Oathbringer has but one ch",
            Suffix = "And die they all shall!%SPEECH_OFF%The men roar again though you have a feeling that a few will remember your ridiculous suggestion to let an Oathbringer walk.}",
            ImagePrefix = "{[img]gfx/ui/events/event_05.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%randombrother%", "%SPEECH_ON%", "%SPEECH_OFF%", "%SPEECH_ON%", "%SPEECH_OFF%"]
        },
        ["B"] = {
            Source = "{[img]gfx/ui/events/event_05.png[/img]{You draw your sword and plunge it into the man's heart.%SPEECH_ON%Anselm will not await you in the next life, heretic.%SPEECH_OFF%The man's body sags around the steel, his eyes briefly wide before settling into a half-lidded gaze at the ground. You draw out your sword and the %companyname% cheers.%SPEECH_ON%Death to all Oathbringers!%SPEECH_OFF%The Oathtakers draw out their swords and raise them to the skies as a ravenous mood sweeps over the company.}",
            Prefix = "{[img]gfx/ui/events/event_05.png[/img]{You draw your sword and plunge it into the man's heart.%SPEECH_ON%Anselm will not await you in the next life, heretic.%SP",
            Suffix = "s.%SPEECH_ON%Death to all Oathbringers!%SPEECH_OFF%The Oathtakers draw out their swords and raise them to the skies as a ravenous mood sweeps over the company.}",
            ImagePrefix = "{[img]gfx/ui/events/event_05.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%SPEECH_ON%", "%SPEECH_OFF%", "%companyname%", "%SPEECH_ON%", "%SPEECH_OFF%"]
        },
        ["C"] = {
            Source = "{[img]gfx/ui/events/event_05.png[/img]{You nod.%SPEECH_ON%Torture him until his tongue points us to Young Anselm's jaw. I don't care how you do it, just do it.%SPEECH_OFF%Turning away, the prisoner screams out that Anselm would not approve. He then just starts screaming indiscriminately and eventually shouting out things that don't make a whole lot of sense. You retire to your tent, bouncing your foot to the screams that now take a rhythmic sort of wailing. Eventually, %randombrother% reappears. He has with him some weapons and armor you know weren't in inventory.%SPEECH_ON%He led us to a location that had these hidden away, but Anselm's jawbone is still missing. I'm afraid the Oathbringers must have it in their own camp, but he wouldn't say where that was. We, uh, we had some difficulties communicating after we cut his tongue out.%SPEECH_OFF%Sighing, you ask where the prisoner is now. The man clears his throat.%SPEECH_ON%Oh he went all white and fell over. He's dead, sir.%SPEECH_OFF%We did right by Young Anselm, at least.}",
            Prefix = "{[img]gfx/ui/events/event_05.png[/img]{You nod.%SPEECH_ON%Torture him until his tongue points us to Young Anselm's jaw. I don't care how you do it, just do it.%",
            Suffix = "he prisoner is now. The man clears his throat.%SPEECH_ON%Oh he went all white and fell over. He's dead, sir.%SPEECH_OFF%We did right by Young Anselm, at least.}",
            ImagePrefix = "{[img]gfx/ui/events/event_05.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%SPEECH_ON%", "%SPEECH_OFF%", "%randombrother%", "%SPEECH_ON%", "%SPEECH_OFF%", "%SPEECH_ON%", "%SPEECH_OFF%"]
        },
        ["D"] = {
            Source = "{[img]gfx/ui/events/event_05.png[/img]{You tell the men to torture the man for information. If there's one thing every Oathbringer knows, it's where Young Anselm's jawbone is and that is something every Oathtaker wishes to find out. The man screams as he's dragged away, and you retire to your tent to drown out the annoyances of things like shrieking and crying which really put a crimp on your mood. A moment later, %torturer% enters the tent, blood on his shirt. He looks to speak, then collapses to the ground. Another Oathtaker comes in saying the prisoner escaped, shanking his torturer before fleeing. You tell the men to help %torturer% before he bleeds out.%SPEECH_ON%Those damned Oathbringers have no honor! We'll find and kill him dead, so sayeth Young Anselm, so sayeth us all!%SPEECH_OFF%You speak with a clenched jaw, and an air of theatrics. The truth is the bastard got away and those Oathbringers are hard to catch, the rats that they are. You just hope that %torturer% survives.}",
            Prefix = "{[img]gfx/ui/events/event_05.png[/img]{You tell the men to torture the man for information. If there's one thing every Oathbringer knows, it's where Young Ansel",
            Suffix = "n air of theatrics. The truth is the bastard got away and those Oathbringers are hard to catch, the rats that they are. You just hope that %torturer% survives.}",
            ImagePrefix = "{[img]gfx/ui/events/event_05.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%torturer%", "%torturer%", "%SPEECH_ON%", "%SPEECH_OFF%", "%torturer%"]
        },
    },
    ["scripts/events/events/dlc6/crisis/holywar_crucified_1_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_161.png[/img]{In the middle of the desert wastes one has to be somewhat suspicious of anything they come across, especially if it's a lone man on a cross. The crucified figure looks entirely dead, given the buzzards clerically perched on each shoulder, but as you draw near the birds take flight and the man lifts is head. Despite gruesome injuries to hands and feet, he's rather lively and asks for water. Instead of giving it to him, you ask why he's here. The man sighs.%SPEECH_ON%I was a crusader. Came in with the army looking to gain glory for the old gods. Except when I got down here, and got to talking with the locals and the priests, I had a change of heart.%SPEECH_OFF%}",
            Prefix = "{[img]gfx/ui/events/event_161.png[/img]{In the middle of the desert wastes one has to be somewhat suspicious of anything they come across, especially if it's a ",
            Suffix = "y looking to gain glory for the old gods. Except when I got down here, and got to talking with the locals and the priests, I had a change of heart.%SPEECH_OFF%}",
            ImagePrefix = "{[img]gfx/ui/events/event_161.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%SPEECH_ON%", "%SPEECH_OFF%"]
        },
        ["B"] = {
            Source = "{[img]gfx/ui/events/event_161.png[/img]{The man nods.%SPEECH_ON%Aye, that they did. Mind, I was there when they crucified someone else on account of the same reason. So in part I'm not the brightest fella to follow in his footsteps, nor am I clean of heart, for I cheered it on when they did it to him. But perhaps the Gilder will see the true light I carry within, you know?%SPEECH_OFF%He turns his head to the skies, and to the buzzards cycling above.%SPEECH_ON%I'm still one open to fight, no matter who it is, south, north, doesn't matter. I've the Gilder in my heart.%SPEECH_OFF%}",
            Prefix = "{[img]gfx/ui/events/event_161.png[/img]{The man nods.%SPEECH_ON%Aye, that they did. Mind, I was there when they crucified someone else on account of the same re",
            Suffix = " the buzzards cycling above.%SPEECH_ON%I'm still one open to fight, no matter who it is, south, north, doesn't matter. I've the Gilder in my heart.%SPEECH_OFF%}",
            ImagePrefix = "{[img]gfx/ui/events/event_161.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%SPEECH_ON%", "%SPEECH_OFF%", "%SPEECH_ON%", "%SPEECH_OFF%"]
        },
        ["C"] = {
            Source = "{[img]gfx/ui/events/event_161.png[/img]{You draw out your dagger and cut the man down. He's got injuries aplenty but is no doubt of strong enough constitution to one day recover. He thanks you with remarkable mildness given the doom which awaited him.%SPEECH_ON%Glad to stretch. I mean, you know, stretch on my terms. Lead the way, captain of the Gilder's circumstance, captain of His mighty sublimity.%SPEECH_OFF%Many in the company do not care for taking in a man who has turned his back not only on his fellow man, but his own gods.}",
            Prefix = "{[img]gfx/ui/events/event_161.png[/img]{You draw out your dagger and cut the man down. He's got injuries aplenty but is no doubt of strong enough constitution t",
            Suffix = "n of His mighty sublimity.%SPEECH_OFF%Many in the company do not care for taking in a man who has turned his back not only on his fellow man, but his own gods.}",
            ImagePrefix = "{[img]gfx/ui/events/event_161.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%SPEECH_ON%", "%SPEECH_OFF%"]
        },
        ["D"] = {
            Source = "{[img]gfx/ui/events/event_161.png[/img]{You tell the man he'll be talking to his god or gods real soon. He sighs.%SPEECH_ON%In a manner, I deserve this, but I am at peace with it.%SPEECH_OFF%There's mixed reactions about the company on it, and by mixed it is mostly varying levels of exuberance. After all, the man is a traitor to both terra and celestial, making him easily hated by anyone and everyone.}",
            Prefix = "{[img]gfx/ui/events/event_161.png[/img]{You tell the man he'll be talking to his god or gods real soon. He sighs.%SPEECH_ON%In a manner, I deserve this, but I a",
            Suffix = "y mixed it is mostly varying levels of exuberance. After all, the man is a traitor to both terra and celestial, making him easily hated by anyone and everyone.}",
            ImagePrefix = "{[img]gfx/ui/events/event_161.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%SPEECH_ON%", "%SPEECH_OFF%"]
        },
    },
    ["scripts/events/events/dlc8/oathtakers_skull_cracked_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker% bursts into the tent with trembling hands holding Young Anselm's skull.%SPEECH_ON%It's broken!%SPEECH_OFF%You jump out of your seat and take a look at Young Anselm's holy remains. There's a sliver of a crack going down the back of the skull. At first it doesn't look too bad, but when you stick a pinky finger in and lift, the bone splits apart. You both gasp and set the skull on the table. There's no doubt the skull could be broken apart with only a little bit more effort.%SPEECH_ON%What should we do? How do we fix it?%SPEECH_OFF%You ponder the question very carefully. The last time this happened Young Anselm's jawbone broke off, and so too did break the Oathtakers - with one group remaining as the Oathtakers, and the other forming the savage blasphemers, the Oathbringers. You're not going to let that happen again.}",
            Prefix = "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker% bursts into the tent with trembling hands holding Young Anselm's skull.%SPEECH_ON%It's broken!%SPEECH_OFF%Yo",
            Suffix = "takers - with one group remaining as the Oathtakers, and the other forming the savage blasphemers, the Oathbringers. You're not going to let that happen again.}",
            ImagePrefix = "{[img]gfx/ui/events/event_183.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%SPEECH_ON%", "%SPEECH_OFF%"]
        },
        ["C"] = {
            Source = "{[img]gfx/ui/events/event_183.png[/img]{You hush %oathtaker% and tell him to close the tent tarp. Taking the skull, you set it on the table and immediately work to fix it. Unfortunately, the second your hands put in any kind of effort, the crack widens and there's even fragments that fly off and scatter to who knows where. You let go of the skull as though it had burned you, Anselm's grace clopping hollowly on the table. %oathtaker% looks at you.%SPEECH_ON%What now? What should we do? Maybe we should take the best part and run off and form a new band?%SPEECH_OFF%Scoffing, you ask the fool if he takes you for an Oathtaker or an Oathbringer. He swallows and confirms the former. Damn right, and there's only one thing to do if that is the case: claim it is Young Anselm's desire to have this here skull crack, and that it is a display of how the %companyname% are not owning up to being true Oathtakers. He agrees, and you do end up showing the rest of the men the skull and its newly acquired bony demarcations.\n\nAt first they are fearful of its crack, but soon agree with you, that Young Anselm's influence is waning, not because of the First Oathtaker himself, but because you all, the last of the Oathtakers, are not owning up to your Oaths! And that you all must do better to follow the path of a true Oathtaker! The men roar and cheer, their convictions renewed by Young Anselm's crack.}",
            Prefix = "{[img]gfx/ui/events/event_183.png[/img]{You hush %oathtaker% and tell him to close the tent tarp. Taking the skull, you set it on the table and immediately work",
            Suffix = " your Oaths! And that you all must do better to follow the path of a true Oathtaker! The men roar and cheer, their convictions renewed by Young Anselm's crack.}",
            ImagePrefix = "{[img]gfx/ui/events/event_183.png[/img]{",
            Pipes = 0, Newlines = 2,
            Tokens = ["%oathtaker%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%companyname%"]
        },
        ["B"] = {
            Source = "{[img]gfx/ui/events/event_183.png[/img]{You take out a piece of string and coat it in ivy and sap. Then you gently lift Young Anselm's crack and run your finger down it with more sap. %oathtaker% stares nervously. Satisfied, you then insert the string along the crack and set the skull's parts back down, chomping down on the string and the sticky ivy with it.  You stand back, looking at your work. %oathtaker% swallows.%SPEECH_ON%I...I don't think anyone will notice.%SPEECH_OFF%You actually worry that it may be preferable that they find the crack in the skull absent of one's attempt to fix it, than to see the handiwork of some skulking skull restorer who tried to sneak one by. Either way, it's done, and Young Anselm's honor has been restored. %oathtaker% wipes the sweat from his brow.%SPEECH_ON%I believe this to have been a test, captain, and that Young Anselm has seen us through. His strength flows through me, and no words are capable of describing the honor I feel right now.%SPEECH_OFF%What? Young Anselm probably had no idea about sticky saps and ivies, and he presumably knew even less now that he's an unspeaking skull. But...you leave %oathtaker% to his interpretations, as shortchanging as they are to yourself.}",
            Prefix = "{[img]gfx/ui/events/event_183.png[/img]{You take out a piece of string and coat it in ivy and sap. Then you gently lift Young Anselm's crack and run your finger",
            Suffix = "d he presumably knew even less now that he's an unspeaking skull. But...you leave %oathtaker% to his interpretations, as shortchanging as they are to yourself.}",
            ImagePrefix = "{[img]gfx/ui/events/event_183.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%oathtaker%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%"]
        },
    },
    ["scripts/events/events/dlc8/oathtaker_happy_with_company_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker% the oathtaker joins you by the campfire. He nods.%SPEECH_ON%Respectfully, captain, I can say that it is a big ask to require a man to be of genuine goodness. When I first knew ya, I didn't think you had the chops for such an undertaking. I thought this world's creeping darkness would wither you away, grind you down like sand to a stone. But here you are. Stalwart. Keeping to the Oaths, one after the other. Good on ya. I think Young Anselm would be proud.%SPEECH_OFF%You thank the Oathtaker for the kind words.}",
            Prefix = "{[img]gfx/ui/events/event_183.png[/img]{%oathtaker% the oathtaker joins you by the campfire. He nods.%SPEECH_ON%Respectfully, captain, I can say that it is a bi",
            Suffix = "e. Stalwart. Keeping to the Oaths, one after the other. Good on ya. I think Young Anselm would be proud.%SPEECH_OFF%You thank the Oathtaker for the kind words.}",
            ImagePrefix = "{[img]gfx/ui/events/event_183.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%"]
        },
    },
    ["scripts/events/events/dlc8/oathtakers_skull_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_183.png[/img]{You find %oathtaker% staring intently into the eyesockets of Young Anselm's skull, the weight of the bone resting on his outstretched palm. He nods now and again and murmurs to himself in a sort of whispering prayer. Sensing your presence, the Oathtaker turns around.%SPEECH_ON%I was worried, but despite the seas of chaos, we have here Young Anselm, and he is provenance of courage such that I would swim into the world's ocean with full assurance that he would see me through it. I should spread Young Anselm's teachings with the others.%SPEECH_OFF%Absolutely he should. | The Oathtakers are enjoying a fine meal beside the fire. %oathtaker% has Young Anselm's skull on a stump. He occasionally turns, spoon of gristle in hand, and seems to think about feeding some to the bony maw. These moments make you uneasy, but for whatever reason the little skull has a tendency to compel the Oathtakers into a better mood by mere presence alone, so much so that you'll let these simultaneously girly and grisly peculiarities pass. | %oathtaker% is looking over a text with felt covers and a gilt bookmark. Beside him, Young Anselm's skull rests near a dying candle. You ask the Oathtaker what he's reading. The man looks up.%SPEECH_ON%Seeing to matters of the Oaths, as Young Anselm had written them. Remember the lad's wise words: ink is the strongest of memories, so it is wise to not depend solely on one's own capacities to follow the Oaths, but instead to refresh the springs of the mind through the writings themselves. This, too, was a part of Young Anselm's teachings. You would know if you tended to the texts as he advised.%SPEECH_OFF%A little snippy there, but he's not wrong. | You see %oathtaker% cleaning off the skull of Young Anselm. Wishing to test the man's faith in the First Oathtaker, you ask something you already know: how did Anselm die. The Oathtaker straightens up, staring at you with a sincere look of offense.%SPEECH_ON%Captain, it matters not how he died, or even when or why or to whom, and maybe there even isn't a whom, but what matters is that he was on the Oath of the Final Path, and so we are also with him, and will be to the end. We are not just Oathtakers, but the Final Oathtakers.%SPEECH_OFF%He turns around, flicking a bug off the bone and then cleaning the skull as though it had been profaned by the insect's steps.%SPEECH_ON%This is a grand experience we are undertaking here captain, but sometimes I think you're just along for the ride.%SPEECH_OFF%It is at the very least a grand experience in deepening your pockets. Thankfully, the only one who seems capable of noticing your more cynical nature is a supposedly poignant skull, Young Anselm's eyesockets emptily staring at you as the Oathtaker spit shines the bone. | %oathtaker% kneels before Young Anselm's skull.%SPEECH_ON%Give me strength in our Oaths, Young Anselm, for I cannot do it alone and certainly not with just the captain's help.%SPEECH_OFF%You almost tell him that he's not alone, he's with the %companyname% and you're not a slouch yourself, but figure this probably isn't the place for that sorta realist talk. The man suddenly jumps to his feet and nods.%SPEECH_ON%Such guidance is much appreciated, Young Anselm.%SPEECH_OFF%A part of you wishes you could look at a young lad's skull for guidance and actually find it, but the only thing you take from Young Anselm's bony visage is an empty stare. | The company has had its up and downs, but Young Anselm is still seen as its primary piety purveyor. You have to admit, sometimes you find yourself staring at the skull with a bit of contempt. Despite you leading the band, and despite you leading it quite well, much of the company's successes are given to the skull. When the men need help, they often go to the skull just as well, skipping right past their captain. %oathtaker% is an example of this, having had a rough go lately but, instead of talking to you, you find him scooping up Young Anselm for some bony counsel on Oathtaking matters. You sometimes dream of taking the First Oathtaker's dome and skipping it across a lake like a rock. | Young Anselm's skull is a touchstone for the most faithful of the Oathtakers, a source of knowledge and guidance and more, all springing out from a silent, bony vessel. %oathtaker%, who has been feeling rather down and out about his past few days, is given access to the skull. Even in this brief keeping, he is renewed in his belief in the Oaths. | You set Young Anselm's skull onto a stick and start spinning it, the bone rattling as it goes round and round, the hollow clatter horribly amusing. %oathtaker% comes through the bushes asking something and you grab the skull and set it down in an instant. The Oathtaker looks at you, the stick, the skull, then back to you. He clears his throat and explains he's been having a rough go of it the past few days. For guidance, and out of laziness, you hand him Young Anselm's skull, telling him to find within the First Oathtaker a revivification of his vitality, a renewal of his faiths, and a resurgence of his courage. The man nods dutifully.%SPEECH_ON%Young Anselm might be the First Oathtaker, but I still believe you are wise beyond your years, captain. I should have seen to Anselm in the first place!%SPEECH_OFF% | You got Young Anselm's skull set on a stump and are throwing pebbles through the eyesockets. One swooshes right through the hole and you pump your fist. Just then, %oathtaker% comes around. He looks at you, your clenched fist, and Young Anselm. The Oathtaker nods.%SPEECH_ON%If even a cynic such as you may be given courage by Young Anselm, then surely the First Oathtaker's abilities go beyond what even I believed. I will leave you alone so that you may find further guidance from Young Anselm.%SPEECH_OFF%Nodding, you thank the Oathtaker, but after he leaves you return to the sport. Unfortunately, all you can muster is plinking pebble after pebble off Anselm's dome. It seems you've lost the touch of the toss. | You have a thick stick in hand and are tossing rocks into the air and slamming them off into the distance. Each crack is deep and pleasing, and the sight of the stones sailing immensely satisfying. As you lean down to pick up another stone, you see Young Anselm's skull there, staring up at you. Naturally, you take it up, weighing it one hand. It's so light. You toss it up and smash it with the stick, fragments of skull spiraling outward in every direction, the fine bonemeal powdering the air around you as though you'd cast a magic trick. Suddenly, you feel something in your side, and this world snaps away and you blink awake to %oathtaker% prodding you with his toe. Blinking your eyes, you realize you dozed off near the campfire. The Oathtaker sets a skull down beside you and nods.%SPEECH_ON%I sought counsel with Young Anselm and found it, captain, but seeing that you were sweating in your sleep I thought maybe you would like a moment with the First Oathtaker as well.%SPEECH_OFF%The man turns and leaves and you're left alone with the skull. It stares at you knowingly. A little too knowingly. You turn the head to look elsewhere and then go back to sleep. | %oathtaker% has had a rough go of it the past few days. You bring him Young Anselm's skull and tell him to sit with his thoughts, and to reflect on the Oaths. The man nods, and just a few minutes later he comes to you, skull in hand.%SPEECH_ON%You were right, captain. I had strayed from the path, but through the First Oathtaker's guidance I have found it again.%SPEECH_OFF% | Young Anselm's skull is starting to look a little ragged. Pieces of grass, mud, couple of bugs, all these things are smattered onto the bone. %oathtaker% comes up asking some inane question about inventory. You cut him off and hand him the skull and tell him to clean it. He nods, staring at the skull as though it were a pound of pure gold. He finishes the job within ten minutes, and when he gets back his disposition is entirely fresh, himself admitting that time alone with Young Anselm invigorated him, and reminded him why he took to the Oathtakers in the first place. That's all well and good, but the priority here is that he's also forgotten to talk to you about inventory which is fantastic.}",
            Prefix = "{[img]gfx/ui/events/event_183.png[/img]{You find %oathtaker% staring intently into the eyesockets of Young Anselm's skull, the weight of the bone resting on his",
            Suffix = "e Oathtakers in the first place. That's all well and good, but the priority here is that he's also forgotten to talk to you about inventory which is fantastic.}",
            ImagePrefix = "{[img]gfx/ui/events/event_183.png[/img]{",
            Pipes = 11, Newlines = 0,
            Tokens = ["%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%companyname%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%", "%oathtaker%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%", "%SPEECH_ON%", "%SPEECH_OFF%", "%oathtaker%"]
        },
    },
    ["scripts/events/events/dlc8/anatomist_old_patient_event"] = {
        ["A"] = {
            Source = "{[img]gfx/ui/events/event_77.png[/img]{%townname%'s denizens have mostly looked upon you and the anatomists as though you were wayward devils. But out of the blue, a man comes down off his porch and strides across the road toward %anatomist% the anatomist, carrying with him an upright posture, swinging gait, and a fat grin. He grabs the anatomist by the hand and starts vigorously shaking it.%SPEECH_ON%Shitfire, I'd figured you'd be back one of these days! You don't recognize me? You done come by this way years ago, many years ago, we both looked a fair bit younger then. I had that fat sack on m'back that you cut out, and my whole life's been much better since! Hells, gimme one second, don't you move a muscle I'll be right back!%SPEECH_OFF%The man quickly returns to his home. You look at %anatomist% who remarks that he remembers the man: he had a giant tumor growing on his spine, and the anatomist in his younger days had successfully cut it out using tongs, shearing blades, and a good number of rags. He laments that he did not keep the fleshy mass for study, but that he was a different sort of physician in those days. The man returns with a weapon which he holds out.%SPEECH_ON%Once I was of good health, I took to the fightin' fields. Was pretty good at it, too, but you know, lives change, and keep on changing. I'd seen you with this sellsword here so I suppose it had done changed for you as well. Please, take it.%SPEECH_OFF%The second the anatomist hesitates, you take the weapon yourself, lest the charitable opportunity be shortlived. You thank the man. He shakes %anatomist%'s hands again, then bids goodbye. The anatomist stares at him as he departs.%SPEECH_ON%We could experiment on him, now that I fully recollect my knowledge of him. That mass from his back is likely to return, I could perhaps...just...open him up and take a look...%SPEECH_OFF%You stop the anatomist from fancying any dissecting of the local laity and get back on the road.}",
            Prefix = "{[img]gfx/ui/events/event_77.png[/img]{%townname%'s denizens have mostly looked upon you and the anatomists as though you were wayward devils. But out of the bl",
            Suffix = "uld perhaps...just...open him up and take a look...%SPEECH_OFF%You stop the anatomist from fancying any dissecting of the local laity and get back on the road.}",
            ImagePrefix = "{[img]gfx/ui/events/event_77.png[/img]{",
            Pipes = 0, Newlines = 0,
            Tokens = ["%townname%", "%anatomist%", "%SPEECH_ON%", "%SPEECH_OFF%", "%anatomist%", "%SPEECH_ON%", "%SPEECH_OFF%", "%anatomist%", "%SPEECH_ON%", "%SPEECH_OFF%"]
        },
    },
};
local function hasExactOrderedPercentTokens(_text, _tokens)
{
    local cursor = 0;
    foreach (token in _tokens) {
        local tokenStart = _text.find("%", cursor);
        if (tokenStart == null) return false;
        local tokenEnd = _text.find("%", tokenStart + 1);
        if (tokenEnd == null || _text.slice(tokenStart, tokenEnd + 1) != token) return false;
        cursor = tokenEnd + 1;
    }
    return _text.find("%", cursor) == null;
}

local function hasExactMissingOuterVariantStructure(_text, _target)
{
    return hasExactBraceSignature(_text, 2, 1)
        && ::BattleBrothersJP.Runtime.Str.startsWith(_text, _target.ImagePrefix)
        && countOccurrences(_text, "[img]") == 1
        && countOccurrences(_text, "[/img]") == 1
        && countOccurrences(_text, "|") == _target.Pipes
        && countOccurrences(_text, "\n") == _target.Newlines
        && hasExactOrderedPercentTokens(_text, _target.Tokens);
}

local function isExactInstalledMissingOuterVariantSource(_text, _target)
{
    return typeof _text == "string"
        && _text == _target.Source
        && ::BattleBrothersJP.Runtime.Str.startsWith(_text, _target.Prefix)
        && ::BattleBrothersJP.Runtime.Str.endsWith(_text, _target.Suffix)
        && hasExactMissingOuterVariantStructure(_text, _target);
}

local function installMissingOuterVariantBoundary(_q, _screenTargets)
{
    _q.buildText = @(__original) function (_text) {
        local originalInput = _text;
        local screenID = "m" in this && typeof this.m == "table"
            && "ActiveScreen" in this.m && typeof this.m.ActiveScreen == "table"
            && "ID" in this.m.ActiveScreen && typeof this.m.ActiveScreen.ID == "string"
            ? this.m.ActiveScreen.ID : null;

        if (screenID != null && screenID in _screenTargets) {
            local target = _screenTargets[screenID];
            if (isExactInstalledMissingOuterVariantSource(_text, target)) {
                local translated = safeTranslate(_text);
                if (typeof translated == "string") {
                    originalInput = translated;
                    if (hasExactMissingOuterVariantStructure(translated, target)) {
                        originalInput += "}";
                    }
                }
            }
        }
        return __original(originalInput);
    }
}

if (dlcPaladinsEnabled) mod.hook("scripts/events/events/dlc8/anatomist_bummed_at_mutations_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc8/anatomist_bummed_at_mutations_event"]);
});
if (dlcPaladinsEnabled) mod.hook("scripts/events/events/dlc8/bad_reputation_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc8/bad_reputation_event"]);
});
if (dlcPaladinsEnabled) mod.hook("scripts/events/events/dlc8/anatomist_ok_with_mutations_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc8/anatomist_ok_with_mutations_event"]);
});
if (dlcPaladinsEnabled) mod.hook("scripts/events/events/dlc8/captured_oathbringer_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc8/captured_oathbringer_event"]);
});
if (dlcDesertEnabled) mod.hook("scripts/events/events/dlc6/crisis/holywar_crucified_1_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc6/crisis/holywar_crucified_1_event"]);
});
if (dlcPaladinsEnabled) mod.hook("scripts/events/events/dlc8/oathtakers_skull_cracked_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc8/oathtakers_skull_cracked_event"]);
});
if (dlcPaladinsEnabled) mod.hook("scripts/events/events/dlc8/oathtaker_happy_with_company_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc8/oathtaker_happy_with_company_event"]);
});
if (dlcPaladinsEnabled) mod.hook("scripts/events/events/dlc8/oathtakers_skull_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc8/oathtakers_skull_event"]);
});
if (dlcPaladinsEnabled) mod.hook("scripts/events/events/dlc8/anatomist_old_patient_event", function (q) {
    installMissingOuterVariantBoundary(q, missingOuterVariantTargets["scripts/events/events/dlc8/anatomist_old_patient_event"]);
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
            || !::BattleBrothersJP.Runtime.Str.startsWith(_text, greenskinsCopiedPrefix)
            || !::BattleBrothersJP.Runtime.Str.endsWith(_text, greenskinsCopiedSuffix)
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
            || !::BattleBrothersJP.Runtime.Str.startsWith(_text, graveChoicePrefix)
            || !::BattleBrothersJP.Runtime.Str.endsWith(_text, graveChoiceSuffix)
            || !hasExactBraceSignature(_text, 0, 0)
            || countOccurrences(_text, "%graverobber%") != 1
            || countOccurrences(_text, "%SPEECH_ON%") != 3
            || countOccurrences(_text, "%SPEECH_OFF%") != 3
            || countOccurrences(_text, "\n") != 4) return __original(_text);

        return __original(graveFailureDisplay);
    }
});

// Use hookTree rather than a normal exact hook so subclass overrides are
// reached. Translate the returned display template with the JP-owned runtime,
// then normalize only the two independently reviewed source defects.
if (legendsEnabled) mod.hookTree("scripts/skills/backgrounds/legend_ranger_commander_background", function (q) {
    q.onBuildDescription = @(__original) function () {
        local ret = __original();
        if (typeof ret != "string") return ret;

        // Installed Legends 19.4.20 contains one missing closing percent and
        // one stray leading 'h'. The reviewed Japanese runtime entry retains
        // that source signature, then this display-only return repairs both
        // tokens before character_background performs name substitution.
        ret = safeTranslate(ret);
        ret = ::BattleBrothersJP.Runtime.Str.replace(ret, "%name's face", "%name%の顔");
        ret = ::BattleBrothersJP.Runtime.Str.replace(ret, "h%name%", "%name%");
        return ret;
    }
});
