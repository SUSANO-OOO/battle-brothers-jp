// Translate event/contract templates before the engine inserts
// %variables%. Legends adds several English display words only during that
// later substitution, so global literal rules cannot reach them. Translate a
// cloned variable list at this exact display boundary and leave caller-owned
// data, PronounTable, internal keys, IDs, and source templates untouched.

if ("EventVariableBoundariesInstalled" in ::BattleBrothersJP) return;
::BattleBrothersJP.EventVariableBoundariesInstalled <- true;

local mod = ::BattleBrothersJP.Mod;
local originalBuildTextFromTemplate = ::buildTextFromTemplate;

local function translateReviewedActorNameDisplay(_text)
{
    if (typeof _text != "string") return _text;

    local translatedText = ::BattleBrothersJP.Runtime.translate(_text);
    // Template variables are heterogeneous (items, settlements, factions,
    // prose, and actor names). Only explicit identity-sensitive opt-ins may be
    // fragment-rewritten without actor provenance; all other values receive
    // exact/full Rosetta translation only.
    foreach (pair in ::BattleBrothersJP.ActorTitleGenericDisplayFragments)
    {
        local english = pair.english;
        local japanese = pair.japanese;
        local at = translatedText.find(english);
        if (at == null) continue;
        local after = at + english.len();
        local beforeChar = at == 0 ? "" : translatedText.slice(at - 1, at);
        local afterChar = after == translatedText.len() ? "" : translatedText.slice(after, after + 1);
        local beforeOK = at == 0 || [" ", "\n", ">", "]", "(", ":", "\"", "'"].find(beforeChar) != null;
        local afterOK = after == translatedText.len()
            || [" ", "\n", "'", "<", "[", ")", ".", ",", ":", "!", "?", "\""].find(afterChar) != null;
        if (!beforeOK || !afterOK || translatedText.find(english, after) != null) continue;
        translatedText = translatedText.slice(0, at) + japanese + translatedText.slice(after);
    }
    return translatedText;
}

// Legends extends the final template variable list with gender-aware English
// pronouns and person words. They are not safe as global Rosetta literals, so
// map only an exact PronounTable family/value pair on the cloned display list.
local pronounDisplayValues = {
    they = { they = "その者", he = "彼", she = "彼女" },
    them = { them = "その者", him = "彼", her = "彼女" },
    their = { their = "その者の", his = "彼の", her = "彼女の" },
    theirs = { theirs = "その者のもの", his = "彼のもの", hers = "彼女のもの" },
    themselves = { themselves = "その者自身", himself = "彼自身", herself = "彼女自身" },
    person = { person = "者", man = "男", woman = "女" },
    people = { people = "人々", men = "男たち", women = "女たち" },
    swordsman = { swordsman = "剣士", swordswoman = "剣士" },
    child = { child = "子供", boy = "少年", girl = "少女" },
    offspring = { child = "子", son = "息子", daughter = "娘" },
    ["they are"] = { ["they are"] = "その者は", ["he is"] = "彼は", ["she is"] = "彼女は" },
    ["they were"] = { ["they were"] = "その者は", ["he was"] = "彼は", ["she was"] = "彼女は" },
    ["they will"] = { ["they will"] = "その者は", ["he will"] = "彼は", ["she will"] = "彼女は" },
    ["they're"] = { ["they're"] = "その者は", ["he's"] = "彼は", ["she's"] = "彼女は" },
    ["they'll"] = { ["they'll"] = "その者は", ["he'll"] = "彼は", ["she'll"] = "彼女は" },
    ["are they"] = { ["are they"] = "その者は", ["is he"] = "彼は", ["is she"] = "彼女は" },
    ["were they"] = { ["were they"] = "その者は", ["was he"] = "彼は", ["was she"] = "彼女は" }
};

local function prepareDisplayTemplate(_text, _vars)
{
    if (typeof _vars != "array")
        return {
            Text = ::BattleBrothersJP.Runtime.translate(_text)
            Vars = _vars
        };

    // return_item supplies both the raw title-case item identity and a
    // lowercase derivative. The derivative cannot match an exact reviewed
    // display rule. Resolve it only from the unique matching sibling pair and
    // only in the clone; Flags.Item and caller-owned variables stay raw.
    local rawItem = null;
    local rawItemMatches = 0;
    foreach (candidate in _vars)
    {
        if (typeof candidate != "array" || candidate.len() < 2
            || typeof candidate[0] != "string" || candidate[0].tolower() != "item"
            || typeof candidate[1] != "string") continue;
        rawItem = candidate[1];
        rawItemMatches += 1;
    }

    local displayVars = [];
    foreach (pair in _vars)
    {
        if (typeof pair != "array" || pair.len() < 2 || typeof pair[0] != "string")
        {
            displayVars.push(pair);
            continue;
        }

        local copiedPair = pair.slice(0);
        local key = copiedPair[0].tolower();
        local separator = key.find("_");
        local family = separator == null ? key : key.slice(0, separator);

        if (typeof copiedPair[1] == "string")
        {
            local value = copiedPair[1];
            if (family == "noble" && (value == "noble" || value == "nobleman" || value == "noblewoman"))
            {
                copiedPair[1] = "貴族";
            }
            else if (family == "sib" && (value == "sib" || value == "bro" || value == "sis"))
            {
                copiedPair[1] = "仲間";
            }
            else if (family == "sibling" && (value == "sibling" || value == "brother" || value == "sister"))
            {
                // The installed disowned-noble background is the sole current
                // snapshot consumer where this placeholder is actual kinship.
                copiedPair[1] = typeof _text == "string" && _text.find("older %sibling%") != null
                     ? "きょうだい"
                     : "団員";
            }
            else if (family in pronounDisplayValues && value.tolower() in pronounDisplayValues[family])
            {
                copiedPair[1] = pronounDisplayValues[family][value.tolower()];
            }
            else if (family == "noble" || family == "sib" || family == "sibling"
                || family in pronounDisplayValues)
            {
                // A known semantic family with an unknown value is not a
                // general display literal. Preserve it verbatim rather than
                // allowing an unrelated Rosetta rule to overmatch.
                copiedPair[1] = value;
            }
            else if (key == "justbeggar" && value == "beggar")
            {
                copiedPair[1] = "物乞い";
            }
            else if (key == "nemesiss" && value == "General")
            {
                copiedPair[1] = "将軍";
            }
            else if (key == "itemlower" && rawItemMatches == 1 && rawItem.tolower() == value)
            {
                local translatedItem = ::BattleBrothersJP.Runtime.translate(rawItem);
                if (translatedItem != rawItem) copiedPair[1] = translatedItem;
            }
            else
            {
                // This clone exists only for final template rendering. It is
                // therefore safe to translate settlement/item/skill/faction
                // display values here without changing the caller's save,
                // identity, pronoun table, or gameplay data.
                copiedPair[1] = translateReviewedActorNameDisplay(::BattleBrothersJP.Runtime.translate(value));
            }
        }

        displayVars.push(copiedPair);
    }

    return {
        Text = ::BattleBrothersJP.Runtime.translate(_text)
        Vars = displayVars
    };
}

::buildTextFromTemplate = function (_text, _vars)
{
    // The exact generated-name scope is semantic/persistent, not display.
    if ("SemanticNameScopes" in ::BattleBrothersJP
        && ::BattleBrothersJP.SemanticNameScopes.RawTemplate > 0)
    {
        return originalBuildTextFromTemplate(_text, _vars);
    }

    local prepared = null;
    try
    {
        prepared = prepareDisplayTemplate(_text, _vars);
    }
    catch (jpError)
    {
        // JP-only processing failure must not suppress or rerun original game
        // behavior. The original is called exactly once below with raw input.
        prepared = { Text = _text, Vars = _vars };
    }
    return originalBuildTextFromTemplate(prepared.Text, prepared.Vars);
}
