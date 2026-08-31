// Generated pattern harness executes all 147 independently reviewed samples and
// leaves the complete namespaced runtime loaded for the measurements below.
dofile(getenv("BBJP_ROOT") + "tests/squirrel/test_reviewed_runtime_patterns.nut", true);

local runtime = ::BattleBrothersJP.Runtime;
local exactInput = "Have at least 50,000 crowns.";
if (!(exactInput in runtime.Exact)) throw "exact performance fixture missing";

// Exact lookup must remain a bounded wrapper over the native table lookup.
local exactIterations = 300000;
local checksum = 0;
local directStart = clock();
for (local i = 0; i < exactIterations; i++) checksum += runtime.Exact[exactInput].len();
local directSeconds = clock() - directStart;
local exactStart = clock();
for (local i = 0; i < exactIterations; i++) checksum += runtime.translate(exactInput).len();
local exactSeconds = clock() - exactStart;
if (exactSeconds > directSeconds * 8.0 + 0.05)
    throw "exact translation overhead ratio exceeded: direct=" + directSeconds + " translated=" + exactSeconds;

// Build-time anchors bound candidate scans. Gate both the largest bucket and a
// synthetic string containing every registered anchor.
local totalRules = 0;
local maxBucket = 0;
local allAnchors = "";
foreach (anchor, rules in runtime.RulesByAnchor)
{
    totalRules += rules.len();
    if (rules.len() > maxBucket) maxBucket = rules.len();
    allAnchors += (allAnchors == "" ? "" : " ") + anchor;
}
if (totalRules != 123) throw "reviewed pattern rule count drifted: " + totalRules;
if (runtime.RulesByAnchor.len() != 80) throw "reviewed anchor count drifted";
if (maxBucket > 8) throw "runtime anchor bucket exceeded audited maximum: " + maxBucket;
local allAnchorCandidates = runtime.candidateRules(allAnchors).len();
if (allAnchorCandidates > totalRules) throw "candidate de-duplication failed";
local stressStart = clock();
for (local i = 0; i < 200; i++) checksum += runtime.translate(allAnchors).len();
local stressSeconds = clock() - stressStart;
if (stressSeconds > 3.0) throw "all-anchor candidate stress exceeded 3 seconds: " + stressSeconds;

local inputs = [
    exactInput,
    "Crafting [color=#135213]+5%[/color]",
    "Dazed for one turn",
    "Unknown MOD string that must remain unchanged",
    "日本語とEnglishが混ざったunknown string"
];
local iterations = 20000;
local baselineStart = clock();
for (local i = 0; i < iterations; i++)
    foreach (value in inputs) checksum += value.len();
local baselineSeconds = clock() - baselineStart;
local translationStart = clock();
for (local i = 0; i < iterations; i++)
    foreach (value in inputs) checksum += runtime.translate(value).len();
local translationSeconds = clock() - translationStart;
if (translationSeconds > 10.0)
    throw "representative runtime workload exceeded 10 seconds: " + translationSeconds;

// Unknown text cost must scale approximately with input length, not rule count
// squared. Both fixtures contain no registered anchor.
local function repeated(_text, _length)
{
    local ret = "";
    while (ret.len() < _length) ret += _text;
    return ret.slice(0, _length);
}
local shortUnknown = repeated("zzzz ", 1024);
local longUnknown = repeated("zzzz ", 8192);
local unknownIterations = 300;
local shortStart = clock();
for (local i = 0; i < unknownIterations; i++) checksum += runtime.translate(shortUnknown).len();
local shortSeconds = clock() - shortStart;
local longStart = clock();
for (local i = 0; i < unknownIterations; i++) checksum += runtime.translate(longUnknown).len();
local longSeconds = clock() - longStart;
// Eight times the bytes may take at most three times that normalized cost;
// the additive allowance covers the millisecond-resolution test clock.
if (longSeconds > shortSeconds * 24.0 + 0.10)
    throw "long unknown input scaled super-linearly: short=" + shortSeconds + " long=" + longSeconds;

if (checksum <= 0) throw "performance harness checksum invalid";
print("RUNTIME_PERFORMANCE_TEST_OK|pattern_samples=147|rules=" + totalRules
    + "|anchors=" + runtime.RulesByAnchor.len() + "|max_bucket=" + maxBucket
    + "|all_anchor_candidates=" + allAnchorCandidates
    + "|direct_seconds=" + directSeconds + "|exact_seconds=" + exactSeconds
    + "|calls=" + (iterations * inputs.len())
    + "|baseline_seconds=" + baselineSeconds + "|translation_seconds=" + translationSeconds
    + "|short_unknown_seconds=" + shortSeconds + "|long_unknown_seconds=" + longSeconds
    + "|stress_seconds=" + stressSeconds + "\n");
