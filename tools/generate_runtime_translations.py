#!/usr/bin/env python3
"""Generate deterministic runtime files from independently reviewed ledger units.

The ignored ledger is the canonical review record.  Only REVIEWED literal units
are emitted automatically.  Raw Rosetta extractor patterns require a separate
runtime-pattern audit because hints such as ``<this.m.Name>`` are not valid
Rosetta captures and may represent only one fragment of a larger display string.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


MODULES = {
    "vanilla": ("vanilla", "1.5.2-3"),
    "legends": ("mod_legends", "19.4.20"),
    "legends_assets": ("mod_legends_assets", "19.4.3"),
    "msu": ("mod_msu", "1.9.0"),
    "modern_hooks": ("mod_modern_hooks", "0.6.0"),
}
MODULE_PRIORITY = {name: index for index, name in enumerate(("vanilla", "legends", "msu", "modern_hooks", "legends_assets"))}
JAVASCRIPT_MODULE_PROFILES = {
    "vanilla_ui": "vanilla",
    "legends": "legends",
    "msu": "msu",
    "modern_hooks": "modern_hooks",
}
JAVASCRIPT_MODULE_PRIORITY = {
    name: index
    for index, name in enumerate(("vanilla_ui", "legends", "msu", "modern_hooks"))
}
RUNTIME_CAPTURE = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*):([A-Za-z_]+)>")
RUNTIME_ANCHOR_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
RUNTIME_CAPTURE_TYPES = {"int", "val", "word", "str", "tag", "int_tag", "val_tag", "str_tag"}
ACTOR_TITLE_CONTEXT = re.compile(r"(?:^|\.)titles(?:\.|$)", re.IGNORECASE)
ACTOR_TITLE_CONST = re.compile(r"(?:^|[:.])Const\.Strings\.[^.]*Titles(?:\.|$)")
ACTOR_TITLE_DISPLAY_STRATEGY = "ACTOR_TITLE_DISPLAY_FRAGMENT"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def stable_list_hash(values: list[str]) -> str:
    return sha256_bytes(("\n".join(sorted(values)) + "\n").encode("utf-8"))


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def runtime_pattern_signature(value: str) -> str:
    """Normalize capture names so regex-equivalent Rosetta rules collide."""
    return RUNTIME_CAPTURE.sub(lambda match: f"<:{match.group(2)}>", value)


def runtime_pattern_anchor(value: str) -> str:
    """Choose one deterministic literal word present in every matching input."""
    literal = RUNTIME_CAPTURE.sub(" ", value)
    words = [word.lower() for word in RUNTIME_ANCHOR_WORD.findall(literal)]
    if not words:
        raise ValueError(f"Runtime pattern has no literal anchor word: {value!r}")
    return sorted(set(words), key=lambda word: (-len(word), word))[0]


def compile_runtime_pattern(value: str) -> tuple[list[Any], set[str]]:
    """Compile a reviewed Rosetta-style source pattern during the build."""
    parts: list[Any] = []
    names: set[str] = set()
    bare_string_captures = 0
    position = 0
    for match in RUNTIME_CAPTURE.finditer(value):
        if match.start() > position:
            parts.append(value[position : match.start()])
        name, subtype = match.groups()
        if subtype not in RUNTIME_CAPTURE_TYPES:
            raise ValueError(f"Unsupported runtime capture type {subtype!r}: {value!r}")
        if name in names:
            raise ValueError(f"Duplicate runtime capture name {name!r}: {value!r}")
        if subtype == "str":
            bare_string_captures += 1
            if bare_string_captures > 1:
                raise ValueError(
                    f"Runtime pattern has more than one unbounded string capture: {value!r}"
                )
        names.add(name)
        parts.append({"name": name, "sub": subtype})
        position = match.end()
    if position < len(value):
        parts.append(value[position:])
    if not parts and value:
        parts.append(value)
    return parts, names


def compile_runtime_replacement(value: str, capture_names: set[str]) -> list[Any]:
    """Compile and validate a replacement; literal angle markup is rejected."""
    parts: list[Any] = []
    position = 0
    while position < len(value):
        opening = value.find("<", position)
        if opening < 0:
            parts.append(value[position:])
            break
        closing = value.find(">", opening + 1)
        if closing < 0:
            raise ValueError(f"Unclosed runtime replacement capture: {value!r}")
        if opening > position:
            parts.append(value[position:opening])
        body = value[opening + 1 : closing]
        name, separator, flags = body.partition(":")
        if not name or name not in capture_names or (separator and flags != "t"):
            raise ValueError(f"Invalid runtime replacement capture <{body}>: {value!r}")
        parts.append({"name": name, "flags": flags if separator else None})
        position = closing + 1
    return parts


def squirrel_parts(parts: list[Any]) -> str:
    rendered: list[str] = []
    for part in parts:
        if isinstance(part, str):
            rendered.append(quoted(part))
        elif "sub" in part:
            rendered.append(f"{{ name = {quoted(part['name'])}, sub = {quoted(part['sub'])} }}")
        else:
            flags = "null" if part.get("flags") is None else quoted(part["flags"])
            rendered.append(f"{{ name = {quoted(part['name'])}, flags = {flags} }}")
    return "[" + ", ".join(rendered) + "]"


def actor_title_sort_key(pair: tuple[str, str]) -> tuple[int, str, str]:
    """Put longer English titles first so prefixes cannot shadow full titles."""
    english, japanese = pair
    return (-len(english), english, japanese)


def reviewed_literal_units(
    units_payload: dict[str, Any], ledger: dict[str, Any]
) -> tuple[dict[str, list[dict[str, str]]], dict[str, dict[str, str]], list[str], list[str], list[str]]:
    occurrences = {entry["stable_key"]: entry for entry in ledger["entries"]}
    squirrel_by_module: dict[str, dict[str, str]] = defaultdict(dict)
    javascript_by_module: dict[str, dict[str, str]] = defaultdict(dict)
    emitted_ids: list[str] = []
    pending_pattern_ids: list[str] = []
    boundary_hook_ids: list[str] = []

    for unit in units_payload["units"]:
        if unit.get("status") != "TRANSLATED" or unit.get("review_status") != "REVIEWED":
            continue
        unit_id = unit["translation_unit"]
        if unit.get("mode") != "literal":
            pending_pattern_ids.append(unit_id)
            continue
        strategy = unit.get("runtime_strategy")
        if strategy == ACTOR_TITLE_DISPLAY_STRATEGY:
            # The unit is emitted by reviewed_actor_title_fragments into the
            # dedicated Squirrel/JavaScript display registry, not by either
            # global literal map. Count it once as emitted runtime coverage.
            emitted_ids.append(unit_id)
            continue
        if strategy == "BOUNDARY_HOOK":
            boundary_hook_ids.append(unit_id)
            continue
        if strategy == "ROSETTA_PATTERN":
            # Some installed sources expose a semantic literal only while
            # constructing a persisted value (for example an honorific). Its
            # safe runtime shape is a reviewed, anchored final-display pattern,
            # handled by reviewed_pattern_units instead of a global literal.
            continue
        japanese = unit.get("japanese")
        if not isinstance(japanese, str) or not japanese.strip():
            raise ValueError(f"Reviewed unit has empty Japanese: {unit_id}")
        used = False
        squirrel_modules: set[str] = set()
        javascript_modules: set[str] = set()
        for stable_key in unit["occurrences"]:
            occurrence = occurrences[stable_key]
            channel = occurrence["channel"]
            module = occurrence["module"]
            if channel.startswith("squirrel") and strategy != "JAVASCRIPT_LITERAL":
                if module not in MODULES:
                    raise ValueError(f"No runtime module metadata for reviewed Squirrel unit: {module}")
                squirrel_modules.add(module)
                used = True
            elif channel == "javascript" and strategy != "ROSETTA_LITERAL":
                if module not in JAVASCRIPT_MODULE_PROFILES:
                    raise ValueError(f"No JavaScript runtime profile for reviewed unit: {module}")
                javascript_modules.add(module)
                used = True
        if squirrel_modules:
            module = min(squirrel_modules, key=lambda name: (MODULE_PRIORITY.get(name, 999), name))
            previous = squirrel_by_module[module].setdefault(unit["english"], japanese)
            if previous != japanese:
                raise ValueError(f"Conflicting Squirrel literal translation: {unit['english']!r}")
        if javascript_modules:
            module = min(
                javascript_modules,
                key=lambda name: (JAVASCRIPT_MODULE_PRIORITY.get(name, 999), name),
            )
            previous = javascript_by_module[module].setdefault(unit["english"], japanese)
            if previous != japanese:
                raise ValueError(f"Conflicting JavaScript literal translation: {unit['english']!r}")
        if used:
            emitted_ids.append(unit_id)

    normalized = {
        module: [{"en": english, "ja": pairs[english]} for english in sorted(pairs)]
        for module, pairs in sorted(squirrel_by_module.items())
    }
    normalized_javascript = {
        module: dict(sorted(pairs.items()))
        for module, pairs in sorted(javascript_by_module.items())
    }
    return normalized, normalized_javascript, emitted_ids, pending_pattern_ids, boundary_hook_ids


def is_actor_title_occurrence(occurrence: dict[str, Any]) -> bool:
    """Classify source occurrences that assign a runtime actor title.

    The classification uses extractor context rather than English shape. This
    keeps common prose such as ``the Hunter`` out of the fragment registry
    unless the installed source actually uses that literal as an actor title.
    """
    if not occurrence.get("channel", "").startswith("squirrel"):
        return False
    context = occurrence.get("context", "")
    source = occurrence.get("source", "").replace("\\", "/")
    if ACTOR_TITLE_CONTEXT.search(context) or ACTOR_TITLE_CONST.search(context):
        return True
    if ".setTitle()" in context:
        return True
    return ".m.Title" in context and any(
        marker in source
        for marker in (
            "scripts/entity/tactical/",
            "scripts/skills/backgrounds/",
            "scripts/skills/traits/",
        )
    )


def reviewed_actor_title_fragments(
    units_payload: dict[str, Any], ledger: dict[str, Any]
) -> tuple[dict[str, str], list[str]]:
    """Return canonical reviewed title fragments for display-only boundaries."""
    occurrences = {entry["stable_key"]: entry for entry in ledger["entries"]}
    pairs: dict[str, str] = {}
    emitted_ids: list[str] = []
    for unit in units_payload["units"]:
        if (
            unit.get("status") != "TRANSLATED"
            or unit.get("review_status") != "REVIEWED"
            or unit.get("mode") != "literal"
        ):
            continue
        # A unit with an explicit runtime strategy has already been routed to
        # a narrower boundary or an anchored Rosetta pattern. Emitting its bare
        # source literal here would bypass that reviewed contract (for example
        # ``Dame <first><rest>`` -> ``デイム・<first><rest>``).
        if unit.get("runtime_strategy") not in {None, ACTOR_TITLE_DISPLAY_STRATEGY}:
            continue
        if not any(is_actor_title_occurrence(occurrences[key]) for key in unit["occurrences"]):
            continue
        english = unit.get("english")
        japanese = unit.get("japanese")
        if not isinstance(english, str) or not isinstance(japanese, str) or not japanese.strip():
            raise ValueError(f"Reviewed actor title has invalid text: {unit['translation_unit']}")
        previous = pairs.setdefault(english, japanese)
        if previous != japanese:
            raise ValueError(f"Conflicting reviewed actor title translation: {english!r}")
        emitted_ids.append(unit["translation_unit"])
    return dict(sorted(pairs.items(), key=actor_title_sort_key)), emitted_ids


def reviewed_generic_actor_title_fragments(
    units_payload: dict[str, Any], ledger: dict[str, Any]
) -> tuple[dict[str, str], list[str]]:
    """Return opt-in fragments allowed when actor provenance is unavailable."""
    all_pairs, all_ids = reviewed_actor_title_fragments(units_payload, ledger)
    unit_index = {unit["translation_unit"]: unit for unit in units_payload["units"]}
    strict_ids = [
        unit_id
        for unit_id in all_ids
        if unit_index[unit_id].get("runtime_strategy") == ACTOR_TITLE_DISPLAY_STRATEGY
    ]
    strict_english = {unit_index[unit_id]["english"] for unit_id in strict_ids}
    strict_pairs = {
        english: japanese
        for english, japanese in all_pairs.items()
        if english in strict_english
    }
    return dict(sorted(strict_pairs.items(), key=actor_title_sort_key)), strict_ids


def reviewed_pattern_units(
    units_payload: dict[str, Any], ledger: dict[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[str], list[str], list[str], list[dict[str, str]]]:
    occurrences = {entry["stable_key"]: entry for entry in ledger["entries"]}
    by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
    emitted: list[str] = []
    pending: list[str] = []
    boundaries: list[str] = []
    samples: list[dict[str, str]] = []
    runtime_keys: dict[str, str] = {}
    runtime_signatures: dict[str, tuple[str, str]] = {}
    for unit in units_payload["units"]:
        is_runtime_pattern = unit.get("mode") == "pattern" or unit.get("runtime_strategy") == "ROSETTA_PATTERN"
        if not is_runtime_pattern or unit.get("status") != "TRANSLATED" or unit.get("review_status") != "REVIEWED":
            continue
        unit_id = unit["translation_unit"]
        contract = unit.get("runtime_contract", {})
        if contract.get("resolution_status") != "RESOLVED":
            pending.append(unit_id)
            continue
        strategy = contract.get("strategy")
        if strategy == "BOUNDARY_HOOK":
            boundaries.append(unit_id)
            continue
        if strategy != "ROSETTA_PATTERN":
            raise ValueError(f"Unknown resolved runtime pattern strategy: {unit_id}")
        runtime_en = contract["runtime_en"]
        if unit.get("mode") != "pattern":
            if not RUNTIME_CAPTURE.search(runtime_en):
                raise ValueError(
                    f"Literal source runtime pattern requires at least one capture: {unit_id}"
                )
            if runtime_en == unit.get("english"):
                raise ValueError(
                    f"Literal source runtime pattern must differ from source English: {unit_id}"
                )
        modules = {
            occurrences[key]["module"]
            for key in unit["occurrences"]
            if occurrences[key]["channel"].startswith("squirrel")
        }
        if not modules or any(module not in MODULES for module in modules):
            raise ValueError(f"Resolved Rosetta pattern has no supported Squirrel module: {unit_id}")
        module = min(modules, key=lambda name: (MODULE_PRIORITY.get(name, 999), name))
        runtime_ja = contract["runtime_ja"]
        signature = runtime_pattern_signature(runtime_en)
        previous_signature = runtime_signatures.setdefault(signature, (runtime_en, unit_id))
        if previous_signature[0] != runtime_en:
            raise ValueError(
                "Regex-equivalent Rosetta patterns use different capture contracts: "
                f"{previous_signature[1]} and {unit_id}; signature={signature!r}"
            )
        is_new_runtime_key = runtime_en not in runtime_keys
        previous = runtime_keys.setdefault(runtime_en, runtime_ja)
        if previous != runtime_ja:
            raise ValueError(f"Conflicting runtime Rosetta pattern: {runtime_en!r}")
        if is_new_runtime_key:
            by_module[module].append({"en": runtime_en, "ja": runtime_ja, "mode": "pattern"})
        emitted.append(unit_id)
        for sample in contract.get("samples", []):
            samples.append({"translation_unit": unit_id, "english": sample["english"], "japanese": sample["japanese"]})
    normalized = {
        module: sorted(pairs, key=lambda pair: (pair["en"], pair["ja"]))
        for module, pairs in sorted(by_module.items())
    }
    return normalized, emitted, pending, boundaries, samples


def supplemental_runtime_patterns(
    path: Path,
    units_payload: dict[str, Any],
    ledger_sha256: str,
    units_sha256: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[str], list[dict[str, str]], dict[str, Any]]:
    """Load small reviewed display contracts not expressible in the ledger schema.

    This preserves independently audited exact/pattern display contracts that
    are unsafe to infer from the generic ledger schema.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported supplemental runtime contract schema")
    if payload.get("canonical_ledger_sha256") != ledger_sha256:
        raise ValueError("Supplemental runtime contracts target a different canonical ledger")
    if payload.get("translation_units_sha256") != units_sha256:
        raise ValueError("Supplemental runtime contracts target different translation units")
    unit_index = {unit["translation_unit"]: unit for unit in units_payload["units"]}
    by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
    emitted: list[str] = []
    samples: list[dict[str, str]] = []
    runtime_keys: dict[str, str] = {}
    for contract in payload.get("contracts", []):
        unit_id = contract.get("translation_unit")
        contract_mode = contract.get("mode", "pattern")
        if contract.get("review_status") != "REVIEWED" or unit_id not in unit_index:
            raise ValueError(f"Supplemental runtime contract is not canonical-reviewed: {unit_id}")
        unit = unit_index[unit_id]
        if (
            unit.get("status") != "TRANSLATED"
            or unit.get("review_status") != "REVIEWED"
            or (
                contract_mode != "canonical_literal"
                and (
                    unit.get("english") != contract.get("canonical_english")
                    or unit.get("japanese") != contract.get("canonical_japanese")
                )
            )
        ):
            raise ValueError(f"Supplemental runtime contract drifted from canonical unit: {unit_id}")
        module = contract.get("module")
        if module not in MODULES or module not in unit.get("modules", []):
            raise ValueError(f"Supplemental runtime contract has invalid module: {unit_id}")
        runtime_en = unit.get("english") if contract_mode == "canonical_literal" else contract.get("runtime_en")
        runtime_ja = unit.get("japanese") if contract_mode == "canonical_literal" else contract.get("runtime_ja")
        if not isinstance(runtime_en, str) or not isinstance(runtime_ja, str):
            raise ValueError(f"Supplemental runtime contract has invalid text: {unit_id}")
        mode = "literal" if contract_mode == "canonical_literal" else contract_mode
        if mode not in {"literal", "pattern"}:
            raise ValueError(f"Supplemental runtime contract has invalid mode: {unit_id}")
        if mode == "pattern":
            pattern_parts, capture_names = compile_runtime_pattern(runtime_en)
            if not capture_names:
                raise ValueError(
                    f"Supplemental runtime pattern must contain at least one capture: {unit_id}"
                )
            compile_runtime_replacement(runtime_ja, capture_names)
            runtime_pattern_anchor(runtime_en)
        elif RUNTIME_CAPTURE.search(runtime_en) or RUNTIME_CAPTURE.search(runtime_ja):
            raise ValueError(f"Supplemental literal contract contains runtime captures: {unit_id}")
        previous = runtime_keys.setdefault(runtime_en, runtime_ja)
        if previous != runtime_ja:
            raise ValueError(f"Conflicting supplemental runtime pattern: {runtime_en!r}")
        if previous == runtime_ja and not any(pair["en"] == runtime_en for pair in by_module[module]):
            by_module[module].append({"en": runtime_en, "ja": runtime_ja, "mode": mode})
        emitted.append(unit_id)
        for sample in contract.get("samples", []):
            if not isinstance(sample.get("english"), str) or not isinstance(sample.get("japanese"), str):
                raise ValueError(f"Supplemental runtime sample is invalid: {unit_id}")
            samples.append(
                {
                    "translation_unit": unit_id,
                    "english": sample["english"],
                    "japanese": sample["japanese"],
                }
            )
    normalized = {
        module: sorted(pairs, key=lambda pair: (pair["en"], pair["ja"]))
        for module, pairs in sorted(by_module.items())
    }
    return normalized, emitted, samples, payload


def render_squirrel(
    squirrel_by_module: dict[str, list[dict[str, str]]],
    actor_titles: dict[str, str],
    generic_actor_titles: dict[str, str],
) -> str:
    lines = [
        "// Generated by tools/generate_runtime_translations.py. Do not edit by hand.",
        "// Only independently REVIEWED literal units are present.",
        "",
    ]
    for module, pairs in squirrel_by_module.items():
        mod_id, version = MODULES[module]
        enabled = (
            f'!("ModuleStatus" in ::BattleBrothersJP) '
            f'|| ::BattleBrothersJP.ModuleStatus.{module}.Enabled'
        )
        lines.extend(
            [
                "::BattleBrothersJP.Runtime.add({",
                f"    module = {quoted(mod_id)}",
                f"    version = {quoted(version)}",
                f"    enabled = {enabled}",
                "}, [",
            ]
        )
        for pair in pairs:
            compiled_lines: list[str] = []
            if pair.get("mode") == "pattern":
                pattern_parts, capture_names = compile_runtime_pattern(pair["en"])
                replacement_parts = compile_runtime_replacement(pair["ja"], capture_names)
                compiled_lines = [
                    '        mode = "pattern"',
                    f"        anchor = {quoted(runtime_pattern_anchor(pair['en']))}",
                    f"        parts = {squirrel_parts(pattern_parts)}",
                    f"        replacement = {squirrel_parts(replacement_parts)}",
                ]
            lines.extend(
                [
                    "    {",
                    *compiled_lines,
                    f"        en = {quoted(pair['en'])}",
                    f"        ja = {quoted(pair['ja'])}",
                    "    }",
                ]
            )
        lines.extend(["]);", ""])
    lines.extend(
        [
            "// Reviewed actor-title fragments used only by final display boundaries.",
            "// Actor identity getters and persisted state remain source-language.",
            "::BattleBrothersJP.ActorTitleDisplayFragments <- [",
        ]
    )
    for english, japanese in sorted(actor_titles.items(), key=actor_title_sort_key):
        lines.extend(
            [
                "    {",
                f"        english = {quoted(english)}",
                f"        japanese = {quoted(japanese)}",
                "    }",
            ]
        )
    lines.extend(["];", ""])
    lines.extend(
        [
            "// Explicit opt-in subset for text without proven actor provenance.",
            "::BattleBrothersJP.ActorTitleGenericDisplayFragments <- [",
        ]
    )
    for english, japanese in sorted(generic_actor_titles.items(), key=actor_title_sort_key):
        lines.extend(
            [
                "    {",
                f"        english = {quoted(english)}",
                f"        japanese = {quoted(japanese)}",
                "    }",
            ]
        )
    lines.extend(["];", ""])
    return "\n".join(lines)


def render_pattern_harness(samples: list[dict[str, str]]) -> str:
    lines = [
        '::BattleBrothersJP <- { Author = "SUSANO-OOO" };',
        'dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/runtime/core.nut", true);',
        'dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/translations/reviewed_literals.nut", true);',
        "",
        "function assertPattern(_actual, _expected, _unit) {",
        '    if (_actual != _expected) throw "Pattern " + _unit + " expected \'" + _expected + "\', got \'" + _actual + "\'";',
        "}",
        "",
    ]
    for sample in samples:
        lines.append(
            f"assertPattern(::BattleBrothersJP.Runtime.translate({quoted(sample['english'])}), {quoted(sample['japanese'])}, {quoted(sample['translation_unit'])});"
        )
    lines.extend(["", 'print("REVIEWED_RUNTIME_PATTERNS_OK\\n");', ""])
    return "\n".join(lines)


def render_pattern_collision_harness(samples: list[dict[str, str]]) -> str:
    lines = [
        '::BattleBrothersJP <- { Author = "SUSANO-OOO" };',
        'dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/runtime/core.nut", true);',
        'dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/translations/reviewed_literals.nut", true);',
        "",
        "local issueCount = 0;",
        "function auditPattern(_english, _expected, _unit) {",
        "    local matches = ::BattleBrothersJP.Runtime.debugMatchOutputs(_english);",
        "    if (matches.len() != 1 || matches[0].output != _expected) {",
        "        issueCount++;",
        '        print("PATTERN_AUDIT|" + _unit + "|matches=" + matches.len() + "|expected=" + _expected + "\\n");',
        '        foreach (match in matches) print("  RULE|" + match.en + "|output=" + match.output + "\\n");',
        "    }",
        "}",
        "",
    ]
    for sample in samples:
        lines.append(
            f"auditPattern({quoted(sample['english'])}, {quoted(sample['japanese'])}, {quoted(sample['translation_unit'])});"
        )
    lines.extend(
        [
            "",
            'if (issueCount > 0) throw "RUNTIME_PATTERN_AUDIT_ISSUES=" + issueCount;',
            'print("RUNTIME_PATTERN_COLLISION_AUDIT_OK\\n");',
            "",
        ]
    )
    return "\n".join(lines)


def render_exact_harness(squirrel_by_module: dict[str, list[dict[str, str]]]) -> str:
    exact: dict[str, str] = {}
    for pairs in squirrel_by_module.values():
        for pair in pairs:
            previous = exact.setdefault(pair["en"], pair["ja"])
            if previous != pair["ja"]:
                raise ValueError(f"Conflicting exact parity sample: {pair['en']!r}")
    lines = [
        '::BattleBrothersJP <- { Author = "SUSANO-OOO" };',
        'dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/runtime/core.nut", true);',
        'dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/translations/reviewed_literals.nut", true);',
        "",
        "function assertExact(_actual, _expected, _english) {",
        '    if (_actual != _expected) throw "Exact expected \'" + _expected + "\' for \'" + _english + "\', got \'" + _actual + "\'";',
        "}",
        "",
    ]
    for english, japanese in sorted(exact.items()):
        lines.append(
            f"assertExact(::BattleBrothersJP.Runtime.translate({quoted(english)}), {quoted(japanese)}, {quoted(english)});"
        )
    lines.extend(["", 'print("NAMESPACED_RUNTIME_EXACT_CORPUS_OK\\n");', ""])
    return "\n".join(lines)


def render_javascript_base(
    pairs: dict[str, str], actor_titles: dict[str, str], generic_actor_titles: dict[str, str]
) -> str:
    payload = json.dumps(pairs, ensure_ascii=False, indent=4, sort_keys=True)
    ordered_actor_titles = dict(sorted(actor_titles.items(), key=actor_title_sort_key))
    actor_title_payload = json.dumps(ordered_actor_titles, ensure_ascii=False, indent=4)
    ordered_generic_actor_titles = dict(
        sorted(generic_actor_titles.items(), key=actor_title_sort_key)
    )
    generic_actor_title_payload = json.dumps(
        ordered_generic_actor_titles, ensure_ascii=False, indent=4
    )
    return (
        "/* Generated by tools/generate_runtime_translations.py. Do not edit by hand. */\n"
        "(function () {\n"
        '    "use strict";\n'
        f"    window.BattleBrothersJPStrings = {payload};\n"
        f"    window.BattleBrothersJPActorTitleFragments = {actor_title_payload};\n"
        f"    window.BattleBrothersJPGenericActorTitleFragments = {generic_actor_title_payload};\n"
        "}());\n"
    )


def render_javascript_extension(pairs: dict[str, str]) -> str:
    payload = json.dumps(pairs, ensure_ascii=False, indent=4, sort_keys=True)
    return (
        "/* Generated by tools/generate_runtime_translations.py. Do not edit by hand. */\n"
        "(function () {\n"
        '    "use strict";\n'
        "    window.BattleBrothersJPStrings = window.BattleBrothersJPStrings || {};\n"
        f"    var moduleStrings = {payload};\n"
        "    Object.keys(moduleStrings).forEach(function (english) {\n"
        "        window.BattleBrothersJPStrings[english] = moduleStrings[english];\n"
        "    });\n"
        "}());\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    ledger_path = (repo / args.ledger).resolve()
    units_path = (repo / args.units).resolve()
    for path in (ledger_path, units_path):
        if work not in path.parents:
            raise SystemExit(f"ERROR: canonical ledger input must remain below ignored work/: {path}")

    ledger_bytes = ledger_path.read_bytes()
    units_bytes = units_path.read_bytes()
    ledger_sha256 = sha256_bytes(ledger_bytes)
    units_sha256 = sha256_bytes(units_bytes)
    ledger = json.loads(ledger_bytes.decode("utf-8"))
    units_payload = json.loads(units_bytes.decode("utf-8"))
    literal_squirrel, javascript_by_module, literal_emitted_ids, _, literal_boundary_ids = reviewed_literal_units(units_payload, ledger)
    actor_titles, actor_title_unit_ids = reviewed_actor_title_fragments(units_payload, ledger)
    generic_actor_titles, generic_actor_title_unit_ids = reviewed_generic_actor_title_fragments(
        units_payload, ledger
    )
    expected_actor_title_strategy_ids = {
        unit["translation_unit"]
        for unit in units_payload["units"]
        if unit.get("status") == "TRANSLATED"
        and unit.get("review_status") == "REVIEWED"
        and unit.get("runtime_strategy") == ACTOR_TITLE_DISPLAY_STRATEGY
    }
    missing_actor_title_strategy_ids = expected_actor_title_strategy_ids - set(actor_title_unit_ids)
    if missing_actor_title_strategy_ids:
        raise ValueError(
            "ACTOR_TITLE_DISPLAY_FRAGMENT unit has no classified actor-title occurrence: "
            + ", ".join(sorted(missing_actor_title_strategy_ids))
        )
    pattern_squirrel, pattern_emitted_ids, pending_ids, pattern_boundary_ids, pattern_samples = reviewed_pattern_units(units_payload, ledger)
    supplemental_path = repo / "reports" / "runtime-supplemental-contracts.json"
    supplemental_squirrel, supplemental_ids, supplemental_samples, supplemental_payload = supplemental_runtime_patterns(
        supplemental_path, units_payload, ledger_sha256, units_sha256
    )
    supplemental_seen: dict[str, str] = {
        pair["en"]: pair["ja"]
        for pairs in pattern_squirrel.values()
        for pair in pairs
    }
    for module, pairs in supplemental_squirrel.items():
        destination = pattern_squirrel.setdefault(module, [])
        for pair in pairs:
            previous = supplemental_seen.setdefault(pair["en"], pair["ja"])
            if previous != pair["ja"]:
                raise ValueError(f"Supplemental runtime pattern conflicts with canonical pattern: {pair['en']!r}")
            if not any(existing["en"] == pair["en"] for existing in destination):
                destination.append(pair)
        destination.sort(key=lambda pair: (pair["en"], pair["ja"]))
    boundary_ids = [*literal_boundary_ids, *pattern_boundary_ids]
    pattern_emitted_ids.extend(
        unit_id for unit_id in supplemental_ids if unit_id not in set(boundary_ids)
    )
    pattern_samples.extend(supplemental_samples)
    pattern_samples.sort(key=lambda sample: (sample["translation_unit"], sample["english"], sample["japanese"]))
    squirrel: dict[str, list[dict[str, Any]]] = {}
    for module in sorted(set(literal_squirrel) | set(pattern_squirrel)):
        squirrel[module] = sorted(
            [*literal_squirrel.get(module, []), *pattern_squirrel.get(module, [])],
            key=lambda pair: (pair.get("mode", "literal"), pair["en"], pair["ja"]),
        )
    emitted_ids = [*literal_emitted_ids, *pattern_emitted_ids]

    squirrel_path = repo / "src" / "battle_brothers_jp" / "translations" / "reviewed_literals.nut"
    javascript_root = repo / "src" / "ui" / "mods" / "mod_battle_brothers_jp"
    javascript_paths = {
        "vanilla_ui": javascript_root / "generated_strings.js",
        "legends": javascript_root / "generated_strings_legends.js",
        "msu": javascript_root / "generated_strings_msu.js",
        "modern_hooks": javascript_root / "generated_strings_modern_hooks.js",
    }
    pattern_harness_path = repo / "tests" / "squirrel" / "test_reviewed_runtime_patterns.nut"
    collision_harness_path = repo / "tests" / "squirrel" / "test_runtime_pattern_collisions.nut"
    exact_harness_path = repo / "tests" / "squirrel" / "test_namespaced_runtime_exact_corpus.nut"
    squirrel_path.parent.mkdir(parents=True, exist_ok=True)
    javascript_root.mkdir(parents=True, exist_ok=True)
    squirrel_text = render_squirrel(squirrel, actor_titles, generic_actor_titles)
    javascript_texts = {
        "vanilla_ui": render_javascript_base(
            javascript_by_module.get("vanilla_ui", {}), actor_titles, generic_actor_titles
        )
    }
    for module in ("legends", "msu", "modern_hooks"):
        javascript_texts[module] = render_javascript_extension(
            javascript_by_module.get(module, {})
        )
    pattern_harness_text = render_pattern_harness(pattern_samples)
    collision_harness_text = render_pattern_collision_harness(pattern_samples)
    exact_harness_text = render_exact_harness({
        module: [pair for pair in pairs if pair.get("mode", "literal") == "literal"]
        for module, pairs in squirrel.items()
    })
    squirrel_path.write_text(squirrel_text, encoding="utf-8", newline="\n")
    for module, path in javascript_paths.items():
        path.write_text(javascript_texts[module], encoding="utf-8", newline="\n")
    pattern_harness_path.write_text(pattern_harness_text, encoding="utf-8", newline="\n")
    collision_harness_path.write_text(collision_harness_text, encoding="utf-8", newline="\n")
    exact_harness_path.write_text(exact_harness_text, encoding="utf-8", newline="\n")

    manifest = {
        "schema_version": 2,
        "generator": "tools/generate_runtime_translations.py",
        "installed_snapshot_id": "BBJP-CF88150E7B355ECD32D9",
        "canonical_ledger_sha256": ledger_sha256,
        "translation_units_sha256": units_sha256,
        "reviewed_emitted_unit_count": len(set(emitted_ids)),
        "reviewed_emitted_unit_ids_sha256": stable_list_hash(list(set(emitted_ids))),
        "reviewed_literal_squirrel_pairs_by_module": {
            module: len(pairs) for module, pairs in literal_squirrel.items()
        },
        "reviewed_runtime_pattern_pairs_by_module": {
            module: sum(1 for pair in pairs if pair.get("mode", "pattern") == "pattern")
            for module, pairs in pattern_squirrel.items()
        },
        "reviewed_supplemental_literal_pairs_by_module": {
            module: sum(1 for pair in pairs if pair.get("mode") == "literal")
            for module, pairs in pattern_squirrel.items()
        },
        "reviewed_runtime_pattern_samples": len(pattern_samples),
        "reviewed_supplemental_runtime_contracts": len(supplemental_payload.get("contracts", [])),
        "supplemental_runtime_contracts_sha256": sha256_bytes(supplemental_path.read_bytes()),
        "reviewed_literal_javascript_pairs": sum(
            len(pairs) for pairs in javascript_by_module.values()
        ),
        "reviewed_literal_javascript_pairs_by_module": {
            module: len(javascript_by_module.get(module, {}))
            for module in JAVASCRIPT_MODULE_PROFILES
        },
        "reviewed_actor_title_display_fragments": len(actor_titles),
        "reviewed_actor_title_unit_ids_sha256": stable_list_hash(list(set(actor_title_unit_ids))),
        "reviewed_generic_actor_title_display_fragments": len(generic_actor_titles),
        "reviewed_generic_actor_title_unit_ids_sha256": stable_list_hash(
            list(set(generic_actor_title_unit_ids))
        ),
        "reviewed_pattern_units_pending_runtime_audit": len(set(pending_ids)),
        "pending_pattern_unit_ids_sha256": stable_list_hash(list(set(pending_ids))),
        "reviewed_boundary_hook_units": len(set(boundary_ids)),
        "boundary_hook_unit_ids_sha256": stable_list_hash(list(set(boundary_ids))),
        "runtime_pattern_policy": "RAW_EXTRACTOR_HINTS_ARE_NOT_EMITTED",
        "squirrel_runtime": "BattleBrothersJP.Runtime/v1",
        "runtime_pattern_anchor_policy": "LONGEST_LITERAL_ASCII_WORD; BUILD_TIME_COMPILED_PARTS",
        "external_rosetta_required": False,
        "external_stdlib_required": False,
        "static_reachability": "PAIR_EMITTED_ONLY; CALL_PATH_AUDIT_REMAINS_REQUIRED",
        "runtime_qa": "NOT_TESTED",
        "outputs": {
            squirrel_path.relative_to(repo).as_posix(): sha256_bytes(squirrel_text.encode("utf-8")),
            **{
                javascript_paths[module].relative_to(repo).as_posix(): sha256_bytes(
                    javascript_texts[module].encode("utf-8")
                )
                for module in javascript_paths
            },
            pattern_harness_path.relative_to(repo).as_posix(): sha256_bytes(pattern_harness_text.encode("utf-8")),
            collision_harness_path.relative_to(repo).as_posix(): sha256_bytes(collision_harness_text.encode("utf-8")),
            exact_harness_path.relative_to(repo).as_posix(): sha256_bytes(exact_harness_text.encode("utf-8")),
        },
    }
    manifest_path = repo / "reports" / "runtime-translation-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
