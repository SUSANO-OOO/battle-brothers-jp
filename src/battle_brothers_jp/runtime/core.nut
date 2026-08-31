// Battle Brothers JP minimum localization runtime.
//
// Pattern matching is adapted from battle-brothers-rosetta 0.5.0
// (Copyright 2024 Alexander Schepanovski, BSD-2-Clause). See
// THIRD_PARTY_NOTICES.md in the MOD archive. This file registers only the JP
// namespace; it does not register ::Rosetta or ::std.

if (!("Runtime" in ::BattleBrothersJP))
{
    local runtime = ::BattleBrothersJP.Runtime <- {
        Version = "1"
        MaxInputLength = 65536
        MaxTranslationDepth = 8
        MaxMatchDepth = 32
        MaxPatternParts = 128
        Exact = {}
        RulesByAnchor = {}
        RuleKeys = {}
        PatternOutputs = {}
        Profiles = {}
        Diagnostics = []
        NextRuleID = 1
        CaptureRes = {}
        WordRe = regexp(@"[A-Za-z][A-Za-z0-9_\-]*")

        Str = {
            function startsWith(_text, _prefix)
            {
                return typeof _text == "string" && typeof _prefix == "string"
                    && _text.len() >= _prefix.len()
                    && _text.slice(0, _prefix.len()) == _prefix;
            }

            function endsWith(_text, _suffix)
            {
                return typeof _text == "string" && typeof _suffix == "string"
                    && _text.len() >= _suffix.len()
                    && _text.slice(_text.len() - _suffix.len()) == _suffix;
            }

            function cutSuffix(_text, _suffix)
            {
                return endsWith(_text, _suffix)
                    ? _text.slice(0, _text.len() - _suffix.len())
                    : _text;
            }

            function replace(_text, _needle, _replacement)
            {
                if (typeof _text != "string" || typeof _needle != "string"
                    || typeof _replacement != "string" || _needle == "") return _text;
                local ret = "";
                local pos = 0;
                while (pos <= _text.len())
                {
                    local at = _text.find(_needle, pos);
                    if (at == null)
                    {
                        ret += _text.slice(pos);
                        return ret;
                    }
                    ret += _text.slice(pos, at) + _replacement;
                    pos = at + _needle.len();
                }
                return ret;
            }

            function split(_separator, _text)
            {
                if (typeof _text != "string" || typeof _separator != "string"
                    || _separator == "") return [_text];
                local ret = [];
                local pos = 0;
                while (pos <= _text.len())
                {
                    local at = _text.find(_separator, pos);
                    if (at == null)
                    {
                        ret.push(_text.slice(pos));
                        return ret;
                    }
                    ret.push(_text.slice(pos, at));
                    pos = at + _separator.len();
                }
                return ret;
            }

            function join(_separator, _items)
            {
                if (typeof _items != "array") return "";
                local ret = "";
                foreach (i, item in _items)
                {
                    if (i != 0) ret += _separator;
                    ret += item;
                }
                return ret;
            }
        }

        function configure()
        {
            local open = @"\[[^\]]+\]";
            local close = @"\[/[^\]]+\]";
            local integer = @"[+\-]?\d+";
            local value = @"[+\-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?";
            CaptureRes.int <- regexp(integer);
            CaptureRes.val <- regexp(value);
            CaptureRes.word <- regexp(@"[^ \t\n,.:;!\[\]()]+");
            CaptureRes.str <- null;
            CaptureRes.tag <- regexp(open);
            CaptureRes.int_tag <- regexp(open + integer + close);
            CaptureRes.val_tag <- regexp(open + value + close);
            CaptureRes.str_tag <- regexp(open + @"[^\[\]]*" + close);
        }

        function add(_definition, _pairs)
        {
            if (typeof _definition == "table" && "enabled" in _definition
                && _definition.enabled != true) return;
            if (typeof _definition != "table" || !("module" in _definition)
                || !("version" in _definition) || typeof _definition.module != "string"
                || typeof _definition.version != "string" || _definition.module == ""
                || _definition.version == "")
                throw "BattleBrothersJP invalid runtime profile";
            if (_definition.module in Profiles && Profiles[_definition.module] != _definition.version)
            {
                Diagnostics.push({
                    code = "PROFILE_VERSION_MISMATCH"
                    module = _definition.module
                    accepted = Profiles[_definition.module]
                    rejected = _definition.version
                });
                return;
            }
            if (typeof _pairs != "array") throw "BattleBrothersJP runtime pairs must be an array";
            local stagedExact = {};
            local stagedPatternOutputs = {};
            local stagedRuleKeys = {};
            local stagedRules = [];
            local stagedNextRuleID = NextRuleID;
            foreach (pair in _pairs)
            {
                if (typeof pair != "table" || !("en" in pair) || !("ja" in pair)
                    || typeof pair.en != "string" || typeof pair.ja != "string"
                    || pair.en == "" || pair.ja == "")
                    throw "BattleBrothersJP invalid translation pair";

                if (!("mode" in pair) || pair.mode != "pattern")
                {
                    if (pair.en in Exact && Exact[pair.en] != pair.ja)
                        throw "BattleBrothersJP conflicting exact translation: " + pair.en;
                    if (pair.en in stagedExact && stagedExact[pair.en] != pair.ja)
                        throw "BattleBrothersJP conflicting staged exact translation: " + pair.en;
                    if (!(pair.en in Exact) && !(pair.en in stagedExact))
                        stagedExact[pair.en] <- pair.ja;
                    continue;
                }

                if (!("anchor" in pair) || typeof pair.anchor != "string" || pair.anchor == "")
                    throw "BattleBrothersJP pattern has no anchor: " + pair.en;
                if (!("parts" in pair) || typeof pair.parts != "array"
                    || !("replacement" in pair) || typeof pair.replacement != "array")
                    throw "BattleBrothersJP pattern is not build-time compiled: " + pair.en;
                local anchor = pair.anchor.tolower();
                if (pair.en in PatternOutputs && PatternOutputs[pair.en] != pair.ja)
                    throw "BattleBrothersJP conflicting pattern translation: " + pair.en;
                if (pair.en in stagedPatternOutputs && stagedPatternOutputs[pair.en] != pair.ja)
                    throw "BattleBrothersJP conflicting staged pattern translation: " + pair.en;
                if (!(pair.en in PatternOutputs) && !(pair.en in stagedPatternOutputs))
                    stagedPatternOutputs[pair.en] <- pair.ja;
                local bareStringCaptures = 0;
                foreach (part in pair.parts)
                {
                    if (typeof part == "table" && "sub" in part && part.sub == "str")
                        bareStringCaptures++;
                }
                if (bareStringCaptures > 1)
                    throw "BattleBrothersJP pattern has more than one unbounded string capture: " + pair.en;
                local ruleKey = pair.en + "\x1f" + pair.ja;
                if (ruleKey in RuleKeys || ruleKey in stagedRuleKeys) continue;
                local rule = {
                    id = stagedNextRuleID++
                    en = pair.en
                    ja = pair.ja
                    anchor = anchor
                    parts = pair.parts
                    replacement = pair.replacement
                };
                stagedRuleKeys[ruleKey] <- true;
                stagedRules.push(rule);
            }

            // Commit only after the complete profile has validated. A malformed
            // or conflicting later pair must not leave an accepted profile or
            // a partially registered translation table behind.
            Profiles[_definition.module] <- _definition.version;
            foreach (english, japanese in stagedExact) Exact[english] <- japanese;
            foreach (english, japanese in stagedPatternOutputs) PatternOutputs[english] <- japanese;
            foreach (ruleKey, ignored in stagedRuleKeys) RuleKeys[ruleKey] <- true;
            foreach (rule in stagedRules)
            {
                if (!(rule.anchor in RulesByAnchor)) RulesByAnchor[rule.anchor] <- [];
                RulesByAnchor[rule.anchor].push(rule);
            }
            NextRuleID = stagedNextRuleID;
        }

        function matchParts(_text, _parts, _matchDepth = 0)
        {
            if (typeof _text != "string" || typeof _parts != "array"
                || _text.len() > MaxInputLength || _parts.len() > MaxPatternParts
                || _matchDepth > MaxMatchDepth) return null;
            local bareStringCaptures = 0;
            foreach (part in _parts)
            {
                if (typeof part == "table" && "sub" in part && part.sub == "str")
                    bareStringCaptures++;
            }
            if (bareStringCaptures > 1) return null;
            local pos = 0;
            local matches = {};
            local textLength = _text.len();
            for (local i = 0; i < _parts.len(); i++)
            {
                local part = _parts[i];
                if (typeof part == "string")
                {
                    local partLength = part.len();
                    if (pos + partLength > textLength
                        || _text.slice(pos, pos + partLength) != part) return null;
                    pos += partLength;
                    continue;
                }

                if (typeof part != "table" || !("sub" in part) || !("name" in part)
                    || typeof part.sub != "string" || typeof part.name != "string"
                    || !(part.sub in CaptureRes)) return null;

                if (part.sub != "str")
                {
                    local capture = CaptureRes[part.sub].search(_text, pos);
                    if (capture == null || capture.begin != pos) return null;
                    matches[part.name] <- _text.slice(capture.begin, capture.end);
                    pos = capture.end;
                    continue;
                }

                if (i == _parts.len() - 1)
                {
                    matches[part.name] <- _text.slice(pos);
                    return matches;
                }

                local next = _parts[i + 1];
                if (typeof next != "string"
                    && (typeof next != "table" || !("sub" in next) || !("name" in next)
                        || typeof next.sub != "string" || typeof next.name != "string"
                        || !(next.sub in CaptureRes) || next.sub == "str")) return null;
                local nextPos = pos;
                while (true)
                {
                    local capture = null;
                    if (typeof next == "string")
                    {
                        nextPos = _text.find(next, nextPos);
                        if (nextPos == null) return null;
                        capture = { begin = nextPos, end = nextPos + next.len() };
                    }
                    else
                    {
                        capture = CaptureRes[next.sub].search(_text, nextPos);
                        if (capture == null) return null;
                        nextPos = capture.begin;
                    }

                    local tail = matchParts(
                        _text.slice(capture.end), _parts.slice(i + 2), _matchDepth + 1
                    );
                    if (tail != null)
                    {
                        matches[part.name] <- _text.slice(pos, nextPos);
                        if (typeof next != "string")
                            matches[next.name] <- _text.slice(capture.begin, capture.end);
                        foreach (key, value in tail) matches[key] <- value;
                        return matches;
                    }
                    nextPos += 1;
                }
            }
            return pos == textLength ? matches : null;
        }

        function wordKeys(_text)
        {
            local keys = [];
            local seen = {};
            local pos = 0;
            while (pos < _text.len())
            {
                local match = WordRe.search(_text, pos);
                if (match == null) break;
                local key = _text.slice(match.begin, match.end).tolower();
                if (!(key in seen))
                {
                    seen[key] <- true;
                    keys.push(key);
                }
                pos = match.end > pos ? match.end : pos + 1;
            }
            return keys;
        }

        function candidateRules(_text, _skipRuleID = null)
        {
            local ret = [];
            local seen = {};
            foreach (key in wordKeys(_text))
            {
                if (!(key in RulesByAnchor)) continue;
                foreach (rule in RulesByAnchor[key])
                {
                    if (rule.id == _skipRuleID || rule.id in seen) continue;
                    seen[rule.id] <- true;
                    ret.push(rule);
                }
            }
            return ret;
        }

        function useRule(_rule, _matches, _depth)
        {
            local ret = "";
            foreach (part in _rule.replacement)
            {
                if (typeof part == "string")
                {
                    ret += part;
                    continue;
                }
                if (!(part.name in _matches)) return null;
                local value = _matches[part.name];
                if (part.flags == "t")
                {
                    local translated = translateInternal(value, _rule.id, _depth + 1);
                    if (translated == value) return null;
                    value = translated;
                }
                ret += value;
            }
            return ret;
        }

        function debugMatchOutputs(_text, _skipRuleID = null, _depth = 0)
        {
            local outputs = [];
            foreach (rule in candidateRules(_text, _skipRuleID))
            {
                local matches = matchParts(_text, rule.parts);
                if (matches == null) continue;
                local output = useRule(rule, matches, _depth);
                if (output != null) outputs.push({ id = rule.id, en = rule.en, output = output });
            }
            return outputs;
        }

        function translateInternal(_value, _skipRuleID = null, _depth = 0)
        {
            if (typeof _value != "string" || _value.len() > MaxInputLength
                || _depth > MaxTranslationDepth) return _value;
            if (_value in Exact) return Exact[_value];
            local matches = debugMatchOutputs(_value, _skipRuleID, _depth);
            return matches.len() == 1 ? matches[0].output : _value;
        }

        function translate(_value)
        {
            return translateInternal(_value, null, 0);
        }
    };

    runtime.configure();
}
