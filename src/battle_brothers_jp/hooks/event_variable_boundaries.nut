// Rosetta 0.5.0 translates event/contract templates before the engine inserts
// %variables%. Legends adds several English display words only during that
// later substitution, so global literal rules cannot reach them. Translate a
// cloned variable list at this exact display boundary and leave caller-owned
// data, PronounTable, internal keys, IDs, and source templates untouched.

local mod = ::BattleBrothersJP.Mod;
local rosettaBuildTextFromTemplate = ::buildTextFromTemplate;

::buildTextFromTemplate = function (_text, _vars)
{
    if (typeof _vars != "array") return rosettaBuildTextFromTemplate(_text, _vars);

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
            else if (key == "justbeggar" && value == "beggar")
            {
                copiedPair[1] = "物乞い";
            }
            else if (key == "nemesiss" && value == "General")
            {
                copiedPair[1] = "将軍";
            }
            else
            {
                // This clone exists only for final template rendering. It is
                // therefore safe to translate settlement/item/skill/faction
                // display values here without changing the caller's save,
                // identity, pronoun table, or gameplay data.
                copiedPair[1] = ::Rosetta._(value);
            }
        }

        displayVars.push(copiedPair);
    }

    return rosettaBuildTextFromTemplate(_text, displayVars);
}
