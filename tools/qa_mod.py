#!/usr/bin/env python3
"""Static QA for the repository-owned Battle Brothers localization MOD."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


TEXT_SUFFIXES = {".nut", ".js", ".css", ".md", ".txt", ".json"}
MOJIBAKE = ("\ufffd", "???", "Ã", "Â", "縺", "譁", "繧")
PERCENT_TOKEN = re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%")
CAPTURE_TOKEN = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*)(?::[A-Za-z_]+)?>")
BBCODE_TOKEN = re.compile(r"\[/?(?:color|img|imgtooltip|b|i|p)(?:=[^\]]+)?\]", re.I)
PAIR_RE = re.compile(
    r"\{(?P<body>[^{}]*?\ben\s*=\s*(?P<en>\"(?:\\.|[^\"\\])*\")"
    r"[^{}]*?\bja\s*=\s*(?P<ja>\"(?:\\.|[^\"\\])*\")[^{}]*?)\}",
    re.S,
)
JS_PAIR_RE = re.compile(
    r'^\s*(?P<en>"(?:\\.|[^"\\])*")\s*:\s*'
    r'(?P<ja>"(?:\\.|[^"\\])*")\s*,?\s*$',
    re.M,
)
DISTRIBUTABLE_ROOTS = {"scripts", "battle_brothers_jp", "ui", "gfx"}


def result(name: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def skipped(name: str, detail: Any) -> dict[str, Any]:
    return {"name": name, "status": "NOT_RUN", "detail": detail}


def decode_squirrel_string(value: str) -> str:
    return json.loads(value)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def text_files(src: Path) -> list[Path]:
    return sorted(path for path in src.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES)


def check_text_encoding(src: Path) -> dict[str, Any]:
    errors = []
    boms = []
    mojibake = []
    for path in text_files(src):
        data = path.read_bytes()
        relative = path.relative_to(src).as_posix()
        if data.startswith(b"\xef\xbb\xbf"):
            boms.append(relative)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            errors.append({"file": relative, "error": str(error)})
            continue
        for marker in MOJIBAKE:
            if marker in text:
                mojibake.append({"file": relative, "marker": marker})
    passed = not errors and not boms and not mojibake
    return result("encoding_bom_mojibake", passed, {"utf8_errors": errors, "boms": boms, "markers": mojibake})


def extract_pairs(src: Path) -> tuple[list[dict[str, str]], list[str]]:
    pairs = []
    parse_errors = []
    for path in sorted(src.rglob("*.nut")):
        text = path.read_text(encoding="utf-8")
        for match in PAIR_RE.finditer(text):
            try:
                pairs.append(
                    {
                        "file": path.relative_to(src).as_posix(),
                        "en": decode_squirrel_string(match.group("en")),
                        "ja": decode_squirrel_string(match.group("ja")),
                    }
                )
            except (ValueError, json.JSONDecodeError) as error:
                parse_errors.append(f"{path.relative_to(src).as_posix()}: {error}")
    return pairs, parse_errors


def check_translation_pairs(src: Path) -> list[dict[str, Any]]:
    pairs, parse_errors = extract_pairs(src)
    duplicate_counts = Counter(pair["en"] for pair in pairs)
    duplicates = sorted(value for value, count in duplicate_counts.items() if count > 1)
    placeholder_errors = []
    empty = []
    for pair in pairs:
        if not pair["ja"].strip():
            empty.append({"file": pair["file"], "en": pair["en"]})
        signatures = {
            "percent": (PERCENT_TOKEN.findall(pair["en"]), PERCENT_TOKEN.findall(pair["ja"])),
            "captures": (CAPTURE_TOKEN.findall(pair["en"]), CAPTURE_TOKEN.findall(pair["ja"])),
            "bbcode": (BBCODE_TOKEN.findall(pair["en"]), BBCODE_TOKEN.findall(pair["ja"])),
        }
        for kind, (english, japanese) in signatures.items():
            if Counter(english) != Counter(japanese):
                placeholder_errors.append(
                    {"file": pair["file"], "kind": kind, "en_tokens": english, "ja_tokens": japanese}
                )
    return [
        result("translation_pair_parse", not parse_errors and bool(pairs), {"pairs": len(pairs), "errors": parse_errors}),
        result("duplicate_literal_keys", not duplicates, duplicates),
        result("untranslated_generated_pairs", not empty, empty),
        result("placeholder_tag_integrity", not placeholder_errors, placeholder_errors),
    ]


def check_registration(src: Path) -> dict[str, Any]:
    preload = src / "scripts" / "!mods_preload" / "mod_battle_brothers_jp.nut"
    required = {
        'ID = "mod_battle_brothers_jp"': "mod id",
        '"vanilla = 1.5.2-3"': "vanilla pin",
        '"mod_legends = 19.4.20"': "Legends pin",
        '"mod_legends_assets = 19.4.3"': "Legends Assets pin",
        '"mod_rosetta = 0.5.0"': "Rosetta pin",
        '"stdlib >= 2.5"': "stdlib requirement",
        '">mod_rosetta"': "queue after Rosetta",
        '::Hooks.QueueBucket.Late': "same Late queue bucket as Rosetta hooks",
        '">mod_legends"': "queue after Legends",
        '::Rosetta.activate("ja")': "explicit Japanese activation",
        '::include("battle_brothers_jp/hooks/semantic_name_safety")': "semantic name safety hooks",
        '::include("battle_brothers_jp/hooks/event_variable_boundaries")': "event-variable boundary hooks",
        '::include("battle_brothers_jp/hooks/ui_boundaries")': "UI-boundary hooks",
        '::include("battle_brothers_jp/translations/reviewed_literals")': "reviewed translation include",
        '::include("battle_brothers_jp/translations/context_patterns")': "context pattern include",
        '::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/generated_strings.js")': "generated JS strings",
        '::Hooks.registerJS("ui/mods/mod_battle_brothers_jp/main.js")': "JS registration",
        '::Hooks.registerCSS("ui/mods/mod_battle_brothers_jp/main.css")': "CSS registration",
    }
    if not preload.exists():
        return result("preload_registration_dependency_queue", False, {"missing": [str(preload)]})
    text = preload.read_text(encoding="utf-8")
    missing = [description for token, description in required.items() if token not in text]
    return result("preload_registration_dependency_queue", not missing, {"missing": missing})


def check_reachability(repo: Path, src: Path) -> dict[str, Any]:
    manifest_path = repo / "reports" / "vertical-slice-reachability.json"
    if not manifest_path.exists():
        return result("vertical_slice_static_reachability", False, {"error": "reachability manifest missing"})
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return result("vertical_slice_static_reachability", False, {"error": str(error)})

    entries = manifest.get("entries", [])
    malformed = [
        index for index, entry in enumerate(entries)
        if not all(entry.get(field) for field in ("english", "channel", "source_evidence", "boundary_id", "boundary_evidence", "status"))
    ]
    non_reachable = [entry.get("english") for entry in entries if entry.get("status") != "STATICALLY_REACHABLE"]
    duplicate_manifest = sorted(value for value, count in Counter(entry.get("english") for entry in entries).items() if count > 1)

    rosetta_pairs, parse_errors = extract_pairs(src)
    registered_rosetta = {pair["en"] for pair in rosetta_pairs}
    manifest_rosetta = {entry["english"] for entry in entries if entry.get("channel") == "rosetta"}

    js_path = src / "ui" / "mods" / "mod_battle_brothers_jp" / "generated_strings.js"
    js_pairs = {
        decode_squirrel_string(match.group("en")): decode_squirrel_string(match.group("ja"))
        for match in JS_PAIR_RE.finditer(js_path.read_text(encoding="utf-8"))
    }
    manifest_js = {entry["english"] for entry in entries if str(entry.get("channel", "")).startswith("js_")}

    hook_source = "\n".join(
        (src / "battle_brothers_jp" / "hooks" / name).read_text(encoding="utf-8")
        for name in ("ui_boundaries.nut", "event_variable_boundaries.nut", "source_defect_boundaries.nut")
    )
    main_js = (src / "ui" / "mods" / "mod_battle_brothers_jp" / "main.js").read_text(encoding="utf-8")
    boundary_tokens = {
        "bbjp_ambition_get_ui_text": 'hookTree("scripts/ambitions/ambition"',
        "bbjp_legends_camp_query_load": 'hook("scripts/ui/screens/world/modules/camp_screen/camp_crafting_dialog_module"',
        "bbjp_create_text_button": "$.fn.createTextButton = function",
    }
    combined_boundary_source = hook_source + "\n" + main_js
    used_boundary_ids = {entry["boundary_id"] for entry in entries}
    missing_boundaries = [
        boundary_id for boundary_id, token in boundary_tokens.items()
        if boundary_id in used_boundary_ids and token not in combined_boundary_source
    ]

    errors = {
        "malformed_entry_indexes": malformed,
        "non_reachable": non_reachable,
        "duplicate_manifest_keys": duplicate_manifest,
        "pair_parse_errors": parse_errors,
        "rosetta_missing_from_manifest": [],
        "rosetta_missing_from_source": sorted(manifest_rosetta - registered_rosetta),
        "js_missing_from_manifest": [],
        "js_missing_from_source": sorted(manifest_js - set(js_pairs)),
        "missing_boundary_implementations": missing_boundaries,
    }
    passed = bool(entries) and all(not value for value in errors.values())
    return result(
        "vertical_slice_static_reachability",
        passed,
        {
            "manifest_status": manifest.get("status"),
            "entries": len(entries),
            "rosetta_entries": len(manifest_rosetta),
            "js_entries": len(manifest_js),
            "additional_reviewed_rosetta_pairs": len(registered_rosetta - manifest_rosetta),
            "additional_reviewed_js_pairs": len(set(js_pairs) - manifest_js),
            "runtime_proof": "NOT_TESTED",
            "errors": errors,
        },
    )


def check_runtime_translation_manifest(repo: Path, src: Path) -> list[dict[str, Any]]:
    manifest_path = repo / "reports" / "runtime-translation-manifest.json"
    coverage_path = repo / "reports" / "translation-coverage.json"
    boundary_path = repo / "reports" / "context-translation-boundaries.json"
    runtime_boundary_path = repo / "reports" / "runtime-pattern-boundaries.json"
    units_path = repo / "work" / "ledger" / "translation-units.json"
    missing = [
        str(path.relative_to(repo))
        for path in (manifest_path, coverage_path, boundary_path, runtime_boundary_path, units_path)
        if not path.is_file()
    ]
    if missing:
        return [result("reviewed_runtime_accounting", False, {"missing": missing})]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    boundaries = json.loads(boundary_path.read_text(encoding="utf-8"))
    runtime_boundaries = json.loads(runtime_boundary_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    output_mismatches = []
    for relative, expected_hash in manifest.get("outputs", {}).items():
        path = repo / relative
        if not path.is_file() or sha256_bytes(path.read_bytes()) != expected_hash:
            output_mismatches.append(relative)
    accounted = (
        manifest.get("reviewed_emitted_unit_count", 0)
        + manifest.get("reviewed_boundary_hook_units", 0)
        + manifest.get("reviewed_pattern_units_pending_runtime_audit", 0)
    )
    ledger_hash_match = (
        manifest.get("canonical_ledger_sha256") == coverage.get("detailed_ledger_sha256")
        and manifest.get("translation_units_sha256") == coverage.get("translation_units_sha256")
    )
    boundary_entries = boundaries.get("entries", []) + runtime_boundaries.get("entries", [])
    hook_source = "\n".join(
        (src / "battle_brothers_jp" / "hooks" / name).read_text(encoding="utf-8")
        for name in ("ui_boundaries.nut", "event_variable_boundaries.nut", "source_defect_boundaries.nut")
    )
    boundary_tokens = {
        "unitctx:007A8E49C6608DAD89C7B212": ['_name == "Play"', 'return "戯れ"', 'scripts/items/legend_armor/legend_named_armor'],
        "unitctx:9EEB2A948FF195DB1859FB7E": ['key == "nemesiss"', 'copiedPair[1] = "将軍"'],
        "unit:41E565CD32CA5352335D1980": ['hook("scripts/skills/perks/perk_legend_adaptive"', 'translatedList += "、または "'],
        "unit:8D0924A29562F179D3CA3621": ['hook("scripts/skills/perks/perk_legend_barter_greed"', '" Melee Defense", "近接防御"'],
        "unit:88561C218D4FB8A7A6212629": ['hook("scripts/skills/perks/perk_legend_barter_greed"', '" Ranged Defense", "射撃防御"'],
        "unit:FAE4E7959008C0721E12BACD": ['hook("scripts/skills/perks/perk_legend_perfect_fit"', '" Initiative", "先制値"'],
        "unit:C010FE228CD6B0BD27C1B5B0": ['hook("scripts/skills/perks/perk_legend_small_target"', '" Melee Defense", "近接防御"'],
        "unit:6C197E5C6CF0F7073AA7F2D9": ['hook("scripts/skills/perks/perk_legend_small_target"', '" Ranged Defense", "射撃防御"'],
        "unitctx:782145616606560F62C9239B": ['key == "justbeggar"', 'copiedPair[1] = "物乞い"'],
        "unitctx:F08DCB4E125B5D2B0F8036B3": ['family == "sib"', 'copiedPair[1] = "仲間"'],
        "unitctx:CEBBE38E9CEB0AC57E1318E4": ['family == "sibling"', '? "きょうだい"', ': "団員"'],
        "unitctx:9D71C7B95AB3E2372E37D3C3": ['family == "noble"', 'copiedPair[1] = "貴族"'],
        "unit:2FF9E58973B541A9CA070734": [
            'hook("scripts/entity/world/settlements/buildings/port_building"',
            'entry.ListName == exactEnglishListName',
            '? "船で" + translatedName + "へ向かう"',
        ],
        "unit:44A4E3DBF3F21D9A682865FE": [
            'hookTree("scripts/skills/backgrounds/legend_ranger_commander_background"',
            'replace(ret, "%name\'s face", "%name%の顔")',
            'replace(ret, "h%name%", "%name%")',
        ],
    }
    missing_boundary_tokens = {
        entry["translation_unit"]: [token for token in boundary_tokens.get(entry["translation_unit"], []) if token not in hook_source]
        for entry in boundary_entries
        if any(token not in hook_source for token in boundary_tokens.get(entry.get("translation_unit"), []))
    }
    boundary_ids = {entry.get("translation_unit") for entry in boundary_entries}
    expected_boundary_ids = set(boundary_tokens)
    unit_index = {unit["translation_unit"]: unit for unit in units_payload.get("units", [])}
    contract_expectations = {
        "unitctx:782145616606560F62C9239B": {
            "hook_target": "global::buildTextFromTemplate",
            "hook_method": "variable-copy wrapper",
        },
        "unit:2FF9E58973B541A9CA070734": {
            "hook_target": "scripts/entity/world/settlements/buildings/port_building",
            "hook_method": "getUITravelRoster",
        },
        "unit:44A4E3DBF3F21D9A682865FE": {
            "hook_target": "scripts/skills/backgrounds/legend_ranger_commander_background.onBuildDescription",
            "hook_method": "mod.hookTree on the exact ranger class, registered in QueueBucket.Late after mod_rosetta",
        },
    }
    contract_mismatches = {}
    for unit_id, expected in contract_expectations.items():
        contract = unit_index.get(unit_id, {}).get("runtime_contract", {})
        actual = {key: contract.get(key) for key in expected}
        if actual != expected or contract.get("resolution_status") != "RESOLVED":
            contract_mismatches[unit_id] = {
                "expected": expected,
                "actual": actual,
                "resolution_status": contract.get("resolution_status"),
            }
    accounting_passed = (
        not output_mismatches
        and ledger_hash_match
        and accounted == coverage.get("reviewed_units")
        and manifest.get("reviewed_boundary_hook_units") == len(boundary_entries)
        and boundary_ids == expected_boundary_ids
        and not missing_boundary_tokens
        and not contract_mismatches
    )
    return [
        result(
            "reviewed_runtime_accounting",
            accounting_passed,
            {
                "reviewed_units": coverage.get("reviewed_units"),
                "accounted_units": accounted,
                "literal_emitted": manifest.get("reviewed_emitted_unit_count"),
                "boundary_hooks": manifest.get("reviewed_boundary_hook_units"),
                "pending_patterns": manifest.get("reviewed_pattern_units_pending_runtime_audit"),
                "ledger_hash_match": ledger_hash_match,
                "output_mismatches": output_mismatches,
                "boundary_ids_match": boundary_ids == expected_boundary_ids,
                "missing_boundary_tokens": missing_boundary_tokens,
                "canonical_contract_mismatches": contract_mismatches,
            },
        ),
        result(
            "reviewed_runtime_pattern_completion",
            manifest.get("reviewed_pattern_units_pending_runtime_audit") == 0,
            {"pending": manifest.get("reviewed_pattern_units_pending_runtime_audit")},
        ),
    ]


def check_literal_reachability_remediation(repo: Path, src: Path) -> dict[str, Any]:
    path = repo / "reports" / "literal-reachability-summary.json"
    if not path.is_file():
        return result("reviewed_literal_static_reachability", False, {"error": "summary missing"})
    payload = json.loads(path.read_text(encoding="utf-8"))
    hook_source = (src / "battle_brothers_jp" / "hooks" / "ui_boundaries.nut").read_text(encoding="utf-8")
    js_source = (src / "ui" / "mods" / "mod_battle_brothers_jp" / "main.js").read_text(encoding="utf-8")
    pattern_source = (src / "battle_brothers_jp" / "translations" / "context_patterns.nut").read_text(encoding="utf-8")
    tokens = {
        "jquery_init": "$.fn.init = function" in js_source,
        "killed_string": 'hookTree("scripts/skills/skill"' in hook_source and "getKilledString" in hook_source,
        "crafting_pattern": 'en = "Crafting <value:val_tag>"' in pattern_source,
        "adaptive_tooltip": 'hook("scripts/skills/perks/perk_legend_adaptive"' in hook_source
        and "translateAdaptiveHintText" in hook_source,
    }
    total = payload.get("audited_reviewed_literal_units")
    counts = payload.get("initial_classification", {})
    initial_sum = sum(counts.get(name, 0) for name in ("REACHABLE_ROSETTA", "REACHABLE_JS", "NEEDS_BOUNDARY_HOOK", "UNRESOLVED"))
    remaining = payload.get("remaining_unreachable_units")
    passed = total == 277 and initial_sum == total and all(tokens.values()) and remaining == 0
    return result(
        "reviewed_literal_static_reachability",
        passed,
        {
            "audited_units": total,
            "initial_accounting_sum": initial_sum,
            "remediated_units": payload.get("remediated_units"),
            "remaining_unreachable_units": remaining,
            "implementation_tokens": tokens,
            "runtime_qa": "NOT_TESTED",
        },
    )


def check_supported_snapshot_lock(repo: Path) -> dict[str, Any]:
    paths = {
        "lock": repo / "reports" / "supported-snapshot-lock.json",
        "snapshot": repo / "reports" / "source-snapshot.json",
        "coverage": repo / "reports" / "translation-coverage.json",
    }
    missing_files = [name for name, path in paths.items() if not path.is_file()]
    if missing_files:
        return result("supported_snapshot_fingerprint_lock", False, {"missing_files": missing_files})
    lock = json.loads(paths["lock"].read_text(encoding="utf-8"))
    snapshot = json.loads(paths["snapshot"].read_text(encoding="utf-8"))
    coverage = json.loads(paths["coverage"].read_text(encoding="utf-8"))
    mismatches = []
    for field in ("installed_snapshot_id", "snapshot_basis_sha256"):
        if snapshot.get(field) != lock.get(field):
            mismatches.append(f"snapshot.{field}")
        if coverage.get(field) != lock.get(field):
            mismatches.append(f"coverage.{field}")
    if snapshot.get("steam", {}).get("buildid") != lock.get("steam_build_id"):
        mismatches.append("steam_build_id")
    if snapshot.get("executable", {}).get("sha256") != lock.get("executable_sha256"):
        mismatches.append("executable_sha256")
    snapshot_data = {item["relative_path"]: item["sha256"] for item in snapshot.get("data_files", [])}
    if snapshot_data != lock.get("data_files"):
        mismatches.append("data_files")
    ledger_mismatches = []
    for relative, expected in lock.get("ledger_files", {}).items():
        path = repo / relative
        if not path.is_file() or sha256_bytes(path.read_bytes()) != expected:
            ledger_mismatches.append(relative)
    build_source = (repo / "tools" / "build_mod.py").read_text(encoding="utf-8")
    gate_tokens = [
        "--snapshot-report",
        "max_snapshot_age_hours",
        "snapshot_basis_sha256",
        "ledger_files",
        "write_count_to_user_environment",
        "verify_semantic_limitations",
    ]
    missing_gate_tokens = [token for token in gate_tokens if token not in build_source]
    passed = not mismatches and not ledger_mismatches and not missing_gate_tokens
    return result(
        "supported_snapshot_fingerprint_lock",
        passed,
        {
            "installed_snapshot_id": lock.get("installed_snapshot_id"),
            "data_files": len(lock.get("data_files", {})),
            "ledger_files": len(lock.get("ledger_files", {})),
            "mismatches": mismatches,
            "ledger_mismatches": ledger_mismatches,
            "missing_release_gate_tokens": missing_gate_tokens,
            "freshness": "ENFORCED_AT_RELEASE_BUILD_NOT_THIS_STATIC_CHECK",
        },
    )


def ledger_partition_errors(
    ledger: dict[str, Any], units_payload: dict[str, Any], coverage: dict[str, Any]
) -> dict[str, Any]:
    entries = ledger.get("entries", [])
    units = units_payload.get("units", [])
    occurrence_index = {entry.get("stable_key"): entry for entry in entries}
    duplicate_stable_keys = sorted(
        key for key, count in Counter(entry.get("stable_key") for entry in entries).items() if count > 1
    )
    duplicate_unit_ids = sorted(
        key for key, count in Counter(unit.get("translation_unit") for unit in units).items() if count > 1
    )
    assignments: Counter[str] = Counter()
    unit_errors = []
    for unit in units:
        unit_id = unit.get("translation_unit")
        occurrences = unit.get("occurrences", [])
        for stable_key in occurrences:
            assignments[stable_key] += 1
            occurrence = occurrence_index.get(stable_key)
            if occurrence is None:
                unit_errors.append(f"{unit_id}: missing occurrence {stable_key}")
                continue
            if occurrence.get("translation_unit") != unit_id:
                unit_errors.append(f"{unit_id}: reverse reference mismatch {stable_key}")
            if occurrence.get("status") == "RESOLVED_EXCLUSION":
                unit_errors.append(f"{unit_id}: contains resolved exclusion {stable_key}")
        actual_modules = sorted(
            {occurrence_index[key]["module"] for key in occurrences if key in occurrence_index}
        )
        if unit.get("occurrence_count") != len(occurrences):
            unit_errors.append(f"{unit_id}: occurrence_count mismatch")
        if unit.get("modules") != actual_modules:
            unit_errors.append(f"{unit_id}: modules mismatch")

    entry_errors = []
    for entry in entries:
        stable_key = entry.get("stable_key")
        if entry.get("status") == "RESOLVED_EXCLUSION":
            if entry.get("translation_unit") is not None:
                entry_errors.append(f"{stable_key}: exclusion retains translation_unit")
            if entry.get("review_status") != "NOT_APPLICABLE":
                entry_errors.append(f"{stable_key}: exclusion review_status mismatch")
            if entry.get("japanese"):
                entry_errors.append(f"{stable_key}: exclusion has Japanese text")
            if assignments[stable_key] != 0:
                entry_errors.append(f"{stable_key}: exclusion assigned to a unit")
        else:
            if not entry.get("translation_unit"):
                entry_errors.append(f"{stable_key}: translatable occurrence has no unit")
            if assignments[stable_key] != 1:
                entry_errors.append(f"{stable_key}: assigned {assignments[stable_key]} times")

    resolved = sum(entry.get("status") == "RESOLVED_EXCLUSION" for entry in entries)
    count_mismatches = []
    expected_counts = {
        "total_occurrences": len(entries),
        "resolved_exclusion_occurrences": resolved,
        "translatable_occurrences": len(entries) - resolved,
        "unique_translation_units": len(units),
        "untranslated_units": sum(unit.get("status") == "UNTRANSLATED" for unit in units),
        "translated_needs_review_units": sum(
            unit.get("status") == "TRANSLATED" and unit.get("review_status") != "REVIEWED"
            for unit in units
        ),
        "reviewed_units": sum(
            unit.get("status") == "TRANSLATED" and unit.get("review_status") == "REVIEWED"
            for unit in units
        ),
    }
    for name, expected in expected_counts.items():
        if coverage.get(name) != expected:
            count_mismatches.append(
                {"field": name, "coverage": coverage.get(name), "canonical": expected}
            )
    return {
        "duplicate_stable_keys": duplicate_stable_keys,
        "duplicate_unit_ids": duplicate_unit_ids,
        "unit_errors": unit_errors,
        "entry_errors": entry_errors,
        "count_mismatches": count_mismatches,
        "canonical_counts": expected_counts,
    }


def check_ledger_partition(repo: Path) -> dict[str, Any]:
    paths = {
        "ledger": repo / "work" / "ledger" / "translation-ledger.json",
        "units": repo / "work" / "ledger" / "translation-units.json",
        "coverage": repo / "reports" / "translation-coverage.json",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        return result("canonical_ledger_partition", False, {"missing": missing})
    ledger = json.loads(paths["ledger"].read_text(encoding="utf-8"))
    units = json.loads(paths["units"].read_text(encoding="utf-8"))
    coverage = json.loads(paths["coverage"].read_text(encoding="utf-8"))
    errors = ledger_partition_errors(ledger, units, coverage)
    passed = not any(
        errors[name]
        for name in (
            "duplicate_stable_keys",
            "duplicate_unit_ids",
            "unit_errors",
            "entry_errors",
            "count_mismatches",
        )
    )
    return result("canonical_ledger_partition", passed, errors)


def check_semantic_limitation_tracking(repo: Path) -> dict[str, Any]:
    path = repo / "reports" / "upstream-source-limitations.json"
    if not path.is_file():
        return result("upstream_semantic_limitation_tracking", False, {"error": "report missing"})
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    malformed = []
    for index, entry in enumerate(entries):
        missing = [
            field
            for field in (
                "translation_unit",
                "module",
                "source",
                "context",
                "installed_source_text",
                "reviewed_japanese",
                "source_evidence",
                "localization_action",
                "gameplay_change",
                "runtime_qa",
                "release_resolution",
            )
            if not entry.get(field)
        ]
        if missing or entry.get("gameplay_change") != "NONE":
            malformed.append(
                {"index": index, "missing": missing, "gameplay_change": entry.get("gameplay_change")}
            )
    allowed_statuses = {
        "OPEN_SEMANTIC_LIMITATION",
        "RESOLVED",
        "RESOLVED_FOR_LOCALIZATION_WITH_KNOWN_UPSTREAM_LIMITATIONS",
    }
    passed = payload.get("status") in allowed_statuses and not malformed
    return result(
        "upstream_semantic_limitation_tracking",
        passed,
        {
            "status": payload.get("status"),
            "entries": len(entries),
            "localization_release_blocked": payload.get("status") == "OPEN_SEMANTIC_LIMITATION",
            "known_upstream_runtime_limitations": payload.get("status")
            == "RESOLVED_FOR_LOCALIZATION_WITH_KNOWN_UPSTREAM_LIMITATIONS",
            "malformed": malformed,
        },
    )


def check_legends_event_boundary_audit(repo: Path, src: Path) -> dict[str, Any]:
    report_path = repo / "reports" / "legends-events-boundary-audit.json"
    units_path = repo / "work" / "ledger" / "translation-units.json"
    if not report_path.is_file() or not units_path.is_file():
        return result(
            "legends_event_boundary_audit",
            False,
            {"missing": [str(path.relative_to(repo)) for path in (report_path, units_path) if not path.is_file()]},
        )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    units = {
        unit["translation_unit"]: unit
        for unit in json.loads(units_path.read_text(encoding="utf-8")).get("units", [])
    }
    evidence_errors = []
    for label in ("source_audit", "initial_review", "exclusion_batch", "boundary_remediation_review"):
        relative = payload.get("evidence", {}).get(label)
        expected = payload.get("evidence", {}).get(label + "_sha256")
        path = repo / relative if isinstance(relative, str) else None
        if path is None or not path.is_file() or sha256_bytes(path.read_bytes()) != expected:
            evidence_errors.append(label)

    remediation_path = repo / payload.get("evidence", {}).get("boundary_remediation_review", "")
    remediation = json.loads(remediation_path.read_text(encoding="utf-8")) if remediation_path.is_file() else {}
    remediation_ids = [entry.get("translation_unit") for entry in remediation.get("entries", [])]
    unit_errors = [
        unit_id
        for unit_id in remediation_ids
        if unit_id not in units
        or units[unit_id].get("review_status") != "REVIEWED"
        or units[unit_id].get("status") != "TRANSLATED"
        or units[unit_id].get("runtime_strategy") == "BOUNDARY_HOOK"
    ]

    event_source = (src / "battle_brothers_jp" / "hooks" / "event_variable_boundaries.nut").read_text(encoding="utf-8")
    ui_source = (src / "battle_brothers_jp" / "hooks" / "ui_boundaries.nut").read_text(encoding="utf-8")
    vertical_source = (repo / "tests" / "squirrel" / "test_vertical_slice.nut").read_text(encoding="utf-8")
    required_tokens = {
        "pronoun_family_map": "pronounDisplayValues" in event_source,
        "pronoun_unknown_fail_closed": 'family in pronounDisplayValues)' in event_source,
        "obituary_allowlist": "obituaryDisplayCauses" in ui_source,
        "obituary_dto_hook": 'hook("scripts/ui/screens/world/world_obituary_screen"' in ui_source,
        "production_obituary_pairs": all(
            value in vertical_source
            for value in (
                "Deserted the company",
                "Got a better paying offer",
                "Handed over to authorities",
                "Hanged for attempted murder",
                "Left to claim their birthright",
            )
        ),
        "production_pronoun_sample": "Is %their% former self again" in vertical_source,
    }
    passed = (
        payload.get("status") == "FULL_STATIC_REMEDIATION_GREEN_RUNTIME_NOT_TESTED"
        and payload.get("source_units") == 300
        and payload.get("independently_reviewed_units") == 294
        and payload.get("resolved_internal_units") == 6
        and payload.get("remaining_runtime_blockers") == 0
        and len(remediation_ids) == 48
        and not evidence_errors
        and not unit_errors
        and all(required_tokens.values())
        and payload.get("actual_user_environment_writes") == 0
    )
    return result(
        "legends_event_boundary_audit",
        passed,
        {
            "source_units": payload.get("source_units"),
            "reviewed_units": payload.get("independently_reviewed_units"),
            "resolved_internal_units": payload.get("resolved_internal_units"),
            "remediation_units": len(remediation_ids),
            "evidence_errors": evidence_errors,
            "unit_errors": unit_errors,
            "implementation_tokens": required_tokens,
            "runtime_qa": payload.get("runtime_game_qa"),
        },
    )


def check_dependency_graph(repo: Path) -> dict[str, Any]:
    path = repo / "reports" / "mod-dependency-graph.json"
    graph = json.loads(path.read_text(encoding="utf-8"))
    nodes = {node["id"] for node in graph.get("nodes", [])}
    relations = graph.get("relations", [])
    allowed_types = {"requirement", "incompatibility", "queue_before", "queue_after"}
    invalid_types = sorted({edge.get("type") for edge in relations if edge.get("type") not in allowed_types})
    dangling = [
        {"from": edge.get("from"), "to": edge.get("to")}
        for edge in relations
        if edge.get("from") not in nodes or edge.get("to") not in nodes
    ]
    actual_jp = {(edge["type"], edge["to"]) for edge in relations if edge.get("from") == "mod_battle_brothers_jp"}
    expected_jp = {
        ("requirement", "vanilla"),
        ("requirement", "mod_legends"),
        ("requirement", "mod_legends_assets"),
        ("requirement", "mod_msu"),
        ("requirement", "mod_modern_hooks"),
        ("requirement", "mod_rosetta"),
        ("requirement", "stdlib"),
        ("queue_after", "mod_rosetta"),
        ("queue_after", "mod_msu"),
        ("queue_after", "mod_legends"),
    }
    missing_jp = sorted(expected_jp - actual_jp)
    extra_jp = sorted(actual_jp - expected_jp)
    passed = not invalid_types and not dangling and not missing_jp and not extra_jp
    return result(
        "dependency_graph_semantics",
        passed,
        {
            "nodes": len(nodes),
            "relations": len(relations),
            "allowed_types": sorted(allowed_types),
            "invalid_types": invalid_types,
            "dangling_relations": dangling,
            "jp_relation_count": len(actual_jp),
            "missing_jp_relations": missing_jp,
            "extra_jp_relations": extra_jp,
        },
    )


def check_scope(src: Path) -> list[dict[str, Any]]:
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in text_files(src))
    forbidden_paths = [
        pattern for pattern in (r"D:\\SteamLibrary", r"Documents\\Battle Brothers", r"ドキュメント\\Battle Brothers")
        if re.search(pattern, all_text, re.I)
    ]
    write_apis = sorted(set(re.findall(r"\b(?:writeFile|removeFile|renameFile|moveFile|deleteFile)\b", all_text)))
    hook_targets = []
    for path in src.rglob("*.nut"):
        if "translations" in path.parts:
            continue
        code = path.read_text(encoding="utf-8")
        hook_targets.extend(
            match.group(1)
            for match in re.finditer(r"\b(?:hookTree|hookExactClass|hook)\s*\(\s*\"([^\"]+)\"", code)
        )
    allowed_translation_hooks = {
        "scripts/ambitions/ambition",
        "scripts/contracts/contract",
        "scripts/contracts/contracts/arena_contract",
        "scripts/entity/world/location",
        "scripts/entity/world/party",
        "scripts/entity/world/settlement",
        "scripts/entity/world/settlements/buildings/port_building",
        "scripts/entity/world/world_entity",
        "scripts/items/item",
        "scripts/items/legend_armor/legend_named_armor",
        "scripts/items/legend_armor/legend_named_armor_upgrade",
        "scripts/items/legend_helmets/legend_named_helmet",
        "scripts/items/legend_helmets/legend_named_helmet_upgrade",
        "scripts/skills/backgrounds/character_background",
        "scripts/skills/backgrounds/legend_ranger_commander_background",
        "scripts/skills/skill",
        "scripts/skills/perks/perk_legend_adaptive",
        "scripts/skills/perks/perk_legend_barter_greed",
        "scripts/skills/perks/perk_legend_perfect_fit",
        "scripts/skills/perks/perk_legend_small_target",
        "scripts/skills/perks/perk_legend_specialist_poacher",
        "scripts/skills/traits/legend_intensive_training_trait",
        "scripts/ui/screens/world/modules/camp_screen/camp_crafting_dialog_module",
        "scripts/ui/screens/tooltip/tooltip_events",
        "scripts/ui/screens/world/world_obituary_screen",
        "scripts/ui/global/data_helper",
    }
    unexpected_hooks = sorted(set(hook_targets) - allowed_translation_hooks)
    missing_hooks = sorted(allowed_translation_hooks - set(hook_targets))
    return [
        result("actual_game_path_write_absence", not forbidden_paths and not write_apis, {"paths": forbidden_paths, "write_apis": write_apis}),
        result(
            "translation_only_hook_scope",
            not unexpected_hooks and not missing_hooks,
            {"allowed_ui_boundaries": sorted(set(hook_targets)), "unexpected": unexpected_hooks, "missing": missing_hooks},
        ),
    ]


def check_third_party(src: Path) -> dict[str, Any]:
    binaries = [path.relative_to(src).as_posix() for path in src.rglob("*") if path.is_file() and path.suffix.lower() not in TEXT_SUFFIXES]
    allowed = {"gfx/fonts/battle_brothers_jp/NotoSansCJKjp-Regular.otf"}
    unexpected = sorted(set(binaries) - allowed)
    license_exists = (src / "gfx/fonts/battle_brothers_jp/OFL.txt").exists()
    return result("third_party_allowlist_and_license", not unexpected and license_exists, {"unexpected": unexpected, "license": license_exists})


def check_font(repo: Path, src: Path) -> dict[str, Any]:
    package_root = repo / "work" / "python-packages-local"
    if package_root.exists():
        import sys
        sys.path.insert(0, str(package_root))
    try:
        from fontTools.ttLib import TTFont  # type: ignore
    except ImportError as error:
        return result("font_glyph_coverage", False, {"error": str(error)})
    font_path = src / "gfx/fonts/battle_brothers_jp/NotoSansCJKjp-Regular.otf"
    font = TTFont(font_path)
    cmap = set()
    for table in font["cmap"].tables:
        if table.isUnicode():
            cmap.update(table.cmap)
    required = set()
    for path in text_files(src):
        for character in path.read_text(encoding="utf-8"):
            if ord(character) > 127 and character not in "\ufeff":
                required.add(ord(character))
    missing = sorted(f"U+{codepoint:04X}" for codepoint in required if codepoint not in cmap)
    expected_hash = "68A3FC98800B2A27B371F2FB79991DAF3633BD89309D4FFAA6946FD587F375B5"
    actual_hash = sha256_bytes(font_path.read_bytes())
    return result(
        "font_glyph_coverage",
        not missing and actual_hash == expected_hash,
        {"required_codepoints": len(required), "missing": missing, "sha256": actual_hash},
    )


def check_syntax(repo: Path, src: Path, sq: Path | None, node: Path | None) -> list[dict[str, Any]]:
    checks = []
    if sq is None or not sq.exists():
        checks.append(result("squirrel_syntax", False, {"error": "Squirrel compiler not supplied"}))
    else:
        failures = []
        with tempfile.TemporaryDirectory(dir=repo / "work") as temp:
            for index, path in enumerate(sorted(src.rglob("*.nut"))):
                completed = subprocess.run(
                    [str(sq), "-c", "-o", str(Path(temp) / f"{index}.cnut"), str(path)],
                    capture_output=True,
                    text=True,
                )
                if completed.returncode != 0 or "Error" in completed.stderr:
                    failures.append({"file": path.relative_to(src).as_posix(), "stderr": completed.stderr})
        checks.append(result("squirrel_syntax", not failures, failures))
        stdlib = repo / "work" / "upstream" / "battle-brothers-stdlib"
        rosetta = repo / "work" / "upstream" / "battle-brothers-rosetta"
        harness = repo / "tests" / "squirrel" / "test_vertical_slice.nut"
        if stdlib.exists() and rosetta.exists() and harness.exists():
            environment = os.environ.copy()
            environment.update(
                {
                    "STDLIB_DIR": str(stdlib.resolve()) + os.sep,
                    "ROSETTA_DIR": str(rosetta.resolve()) + os.sep,
                    "BBJP_ROOT": str(repo.resolve()) + os.sep,
                }
            )
            completed = subprocess.run(
                [str(sq), str(harness)], capture_output=True, text=True, env=environment
            )
            output = completed.stdout + completed.stderr
            passed = completed.returncode == 0 and "VERTICAL_SLICE_ROSETTA_TEST_OK" in output
            checks.append(
                result(
                    "optional_target_absence_harness",
                    passed,
                    {
                        "optional_mod_objects_defined": False,
                        "marker_found": "VERTICAL_SLICE_ROSETTA_TEST_OK" in output,
                        "returncode": completed.returncode,
                        "output_tail": output[-2000:],
                    },
                )
            )
            pattern_harness = repo / "tests" / "squirrel" / "test_reviewed_runtime_patterns.nut"
            if pattern_harness.exists():
                completed = subprocess.run(
                    [str(sq), str(pattern_harness)], capture_output=True, text=True, env=environment
                )
                output = completed.stdout + completed.stderr
                passed = completed.returncode == 0 and "REVIEWED_RUNTIME_PATTERNS_OK" in output
                checks.append(
                    result(
                        "reviewed_runtime_pattern_harness",
                        passed,
                        {
                            "marker_found": "REVIEWED_RUNTIME_PATTERNS_OK" in output,
                            "returncode": completed.returncode,
                            "output_tail": output[-4000:],
                        },
                    )
                )
            boundary_harness = repo / "tests" / "squirrel" / "test_ui_boundaries.nut"
            if boundary_harness.exists():
                completed = subprocess.run(
                    [str(sq), str(boundary_harness)], capture_output=True, text=True, env=environment
                )
                output = completed.stdout + completed.stderr
                passed = completed.returncode == 0 and "UI_BOUNDARIES_TEST_OK" in output
                checks.append(
                    result(
                        "ui_boundary_harness",
                        passed,
                        {
                            "marker_found": "UI_BOUNDARIES_TEST_OK" in output,
                            "returncode": completed.returncode,
                            "output_tail": output[-4000:],
                        },
                    )
                )
            semantic_harness = repo / "tests" / "squirrel" / "test_semantic_name_safety.nut"
            if semantic_harness.exists():
                completed = subprocess.run(
                    [str(sq), str(semantic_harness)], capture_output=True, text=True, env=environment
                )
                output = completed.stdout + completed.stderr
                passed = completed.returncode == 0 and "SEMANTIC_NAME_SAFETY_TEST_OK" in output
                checks.append(
                    result(
                        "squirrel_semantic_name_safety_harness",
                        passed,
                        {
                            "marker_found": "SEMANTIC_NAME_SAFETY_TEST_OK" in output,
                            "returncode": completed.returncode,
                            "output_tail": output[-4000:],
                        },
                    )
                )
            event_variable_harness = repo / "tests" / "squirrel" / "test_event_variable_boundaries.nut"
            if event_variable_harness.exists():
                completed = subprocess.run(
                    [str(sq), str(event_variable_harness)], capture_output=True, text=True, env=environment
                )
                output = completed.stdout + completed.stderr
                passed = completed.returncode == 0 and "EVENT_VARIABLE_BOUNDARIES_TEST_OK" in output
                checks.append(
                    result(
                        "squirrel_event_variable_boundary_harness",
                        passed,
                        {
                            "marker_found": "EVENT_VARIABLE_BOUNDARIES_TEST_OK" in output,
                            "returncode": completed.returncode,
                            "output_tail": output[-4000:],
                        },
                    )
                )
            source_defect_harness = repo / "tests" / "squirrel" / "test_source_defect_boundaries.nut"
            if source_defect_harness.exists():
                completed = subprocess.run(
                    [str(sq), str(source_defect_harness)], capture_output=True, text=True, env=environment
                )
                output = completed.stdout + completed.stderr
                passed = completed.returncode == 0 and "SOURCE_DEFECT_BOUNDARIES_TEST_OK" in output
                checks.append(
                    result(
                        "squirrel_source_defect_boundary_harness",
                        passed,
                        {
                            "marker_found": "SOURCE_DEFECT_BOUNDARIES_TEST_OK" in output,
                            "returncode": completed.returncode,
                            "output_tail": output[-4000:],
                        },
                    )
                )
            collision_harness = repo / "tests" / "squirrel" / "test_runtime_pattern_collisions.nut"
            if collision_harness.exists():
                completed = subprocess.run(
                    [str(sq), str(collision_harness)], capture_output=True, text=True, env=environment
                )
                output = completed.stdout + completed.stderr
                passed = completed.returncode == 0 and "RUNTIME_PATTERN_COLLISION_AUDIT_OK" in output
                checks.append(
                    result(
                        "runtime_pattern_collision_harness",
                        passed,
                        {
                            "marker_found": "RUNTIME_PATTERN_COLLISION_AUDIT_OK" in output,
                            "returncode": completed.returncode,
                            "output_tail": output[-12000:],
                        },
                    )
                )
        else:
            checks.append(skipped("optional_target_absence_harness", {"reason": "Local Rosetta/stdlib test inputs unavailable"}))
    if node is None or not node.exists():
        checks.append(result("javascript_syntax", False, {"error": "Node executable not supplied"}))
    else:
        failures = []
        for path in sorted(src.rglob("*.js")):
            completed = subprocess.run([str(node), "--check", str(path)], capture_output=True, text=True)
            if completed.returncode != 0:
                failures.append({"file": path.relative_to(src).as_posix(), "stderr": completed.stderr})
        checks.append(result("javascript_syntax", not failures, failures))
        js_harness = repo / "tests" / "js" / "test_ui_translation.js"
        if js_harness.exists():
            completed = subprocess.run([str(node), str(js_harness)], capture_output=True, text=True)
            output = completed.stdout + completed.stderr
            checks.append(
                result(
                    "javascript_ui_boundary_harness",
                    completed.returncode == 0 and "UI_TRANSLATION_TEST_OK" in output,
                    {
                        "marker_found": "UI_TRANSLATION_TEST_OK" in output,
                        "returncode": completed.returncode,
                        "output_tail": output[-4000:],
                    },
                )
            )
    return checks


def check_archive(src: Path, archive_path: Path | None) -> dict[str, Any]:
    if archive_path is None:
        return skipped("archive_structure_and_content", {"reason": "No archive supplied"})
    errors = []
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        source_names = {
            path.relative_to(src).as_posix()
            for path in src.rglob("*")
            if path.is_file() and path.relative_to(src).parts[0] in DISTRIBUTABLE_ROOTS
        }
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts or "\\" in name:
                errors.append(f"unsafe entry: {name}")
            if pure.parts and pure.parts[0] not in DISTRIBUTABLE_ROOTS:
                errors.append(f"unexpected root: {name}")
            source = src.joinpath(*pure.parts)
            if not source.is_file():
                errors.append(f"not sourced from src/: {name}")
            elif sha256_bytes(archive.read(name)) != sha256_bytes(source.read_bytes()):
                errors.append(f"content mismatch: {name}")
        required = {
            "scripts/!mods_preload/mod_battle_brothers_jp.nut",
            "battle_brothers_jp/translations/reviewed_literals.nut",
            "battle_brothers_jp/translations/context_patterns.nut",
            "battle_brothers_jp/hooks/semantic_name_safety.nut",
            "battle_brothers_jp/hooks/event_variable_boundaries.nut",
            "battle_brothers_jp/hooks/ui_boundaries.nut",
            "ui/mods/mod_battle_brothers_jp/generated_strings.js",
            "ui/mods/mod_battle_brothers_jp/main.js",
            "ui/mods/mod_battle_brothers_jp/main.css",
            "gfx/fonts/battle_brothers_jp/NotoSansCJKjp-Regular.otf",
            "gfx/fonts/battle_brothers_jp/OFL.txt",
        }
        errors.extend(f"missing entry: {name}" for name in sorted(required - set(names)))
        errors.extend(f"source omitted from archive: {name}" for name in sorted(source_names - set(names)))
        errors.extend(f"archive entry absent from src: {name}" for name in sorted(set(names) - source_names))
        for name in names:
            if not name.endswith(".nut"):
                continue
            try:
                text = archive.read(name).decode("utf-8")
            except UnicodeDecodeError:
                continue
            for include in re.findall(r'::include\(\"(battle_brothers_jp/[^\"]+)\"\)', text):
                target = include + ".nut"
                if target not in names:
                    errors.append(f"unresolved repository include: {name} -> {target}")
    return result(
        "archive_structure_and_content",
        not errors,
        {
            "artifact_sha256": sha256_bytes(archive_path.read_bytes()),
            "archive_entries": len(names),
            "source_entries": len(source_names),
            "errors": errors,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive")
    parser.add_argument("--sq")
    parser.add_argument("--node")
    parser.add_argument("--report", default="reports/qa-static.json")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    src = repo / "src"
    archive = Path(args.archive).resolve() if args.archive else None
    sq = Path(args.sq).resolve() if args.sq else None
    node = Path(args.node).resolve() if args.node else None

    checks = [
        check_text_encoding(src),
        *check_translation_pairs(src),
        check_registration(src),
        check_reachability(repo, src),
        *check_runtime_translation_manifest(repo, src),
        check_literal_reachability_remediation(repo, src),
        check_ledger_partition(repo),
        check_supported_snapshot_lock(repo),
        check_semantic_limitation_tracking(repo),
        check_legends_event_boundary_audit(repo, src),
        check_dependency_graph(repo),
        *check_scope(src),
        check_third_party(src),
        check_font(repo, src),
        *check_syntax(repo, src, sq, node),
        check_archive(src, archive),
    ]
    failed = any(check["status"] == "FAIL" for check in checks)
    not_run = any(check["status"] == "NOT_RUN" for check in checks)
    status = "FAIL" if failed else "PASS_WITH_NOT_RUN" if not_run else "PASS"
    report = {
        "schema_version": 2,
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "scope": "static repository-owned MOD sources only",
        "status": status,
        "checks": checks,
    }
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = repo / report_path
    if repo not in report_path.resolve().parents:
        raise SystemExit("ERROR: report must stay inside the repository")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
