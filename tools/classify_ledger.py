#!/usr/bin/env python3
"""Classify extracted occurrences and generate deduplicated translation units."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from squirrel_literal_roles import (  # noqa: E402
    GATE_AUTO_EXCLUDE,
    GATE_MANUAL_REVIEW,
    GATE_REVIEW_REQUIRED,
    ROLE_SUBSTITUTION_VALUE,
    occurrence_role_gate,
    role_summary,
    source_structural_proof,
)


PATHISH = re.compile(
    r"(?i)(?:^|[/\\])(?:ui|gfx|scripts|mods?|screens?|assets?)(?:[/\\]|$)|"
    r"\.(?:png|jpg|jpeg|gif|js|css|nut|cnut|wav|ogg|brush|html)$"
)
CONTROL_CONTEXT = re.compile(r"(?:\.ID|\.getResult|\.setScreen\(\)|\.setID\(\))$")
RESOURCE_CONTEXT = re.compile(
    r"(?i)(?:hasSprite|getSprite|addSprite|setBrush|\.Icon|\.Image|"
    r"\.Script|\.Filename|\.ClassName|\.Path)(?:\.|$)"
)
TECHNICAL_PATTERN = re.compile(r"(?:^\^|\$$|\\[dws]|\(\?:|\(\?P|\[A-Za-z0-9_-]+\]\+)")
TOKEN_ONLY = re.compile(r"^[A-Za-z0-9_.:/\\#-]+$")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def exclusion_reason(entry: dict[str, Any]) -> str | None:
    english = entry["english"].strip()
    context = entry["context"]
    source = entry["source"].lower()
    source_code = " ".join(entry.get("source_code", []))

    if CONTROL_CONTEXT.search(context):
        return "INTERNAL_CONTROL_OR_SCREEN_ID"
    if re.fullmatch(r"[A-Z](?:\d+)?", english) and re.search(
        r"(?i)(?:screen|option|result|state|stage|id)", context
    ):
        return "INTERNAL_CONTROL_OR_SCREEN_ID"
    if PATHISH.search(english) and not re.search(r"\s", english) and re.search(r"[/\\.]", english):
        return "RESOURCE_OR_SCRIPT_PATH"
    if RESOURCE_CONTEXT.search(context) and TOKEN_ONLY.fullmatch(english):
        return "RESOURCE_OR_ENGINE_KEY"
    if TECHNICAL_PATTERN.search(english) and entry["channel"] == "squirrel_fallback":
        return "TECHNICAL_REGEX_OR_FORMAT_PATTERN"
    if "debug" in Path(source).parts:
        return "DEBUG_ONLY_SOURCE"
    if re.search(r"(?i)\b(?:logInfo|logDebug|logWarning|logError)\s*\(", source_code):
        return "LOG_DIAGNOSTIC_ONLY"
    return None


def unit_key(entry: dict[str, Any]) -> str:
    # Rosetta literal maps are global. Mode/signature keep genuinely different
    # runtime matching contracts apart while deduplicating repeated occurrences.
    signature = json.dumps(entry["placeholder_signature"], ensure_ascii=False, sort_keys=True)
    basis = "\x1f".join((entry["english"], entry["mode"], signature))
    return f"unit:{sha256_text(basis)[:24]}"


def require_fresh_extraction(ledger: dict[str, Any]) -> None:
    """Refuse destructive rebuilds of translated or previously classified state."""
    if ledger.get("classification") is not None:
        raise ValueError("classification rebuild requires a fresh extracted ledger")
    for entry in ledger.get("entries", []):
        if (
            entry.get("status") != "UNTRANSLATED"
            or entry.get("review_status") != "NOT_REVIEWED"
            or bool(entry.get("japanese"))
            or "translation_unit" in entry
        ):
            raise ValueError(
                "classification rebuild refuses translated, excluded, or unit-bound canonical state"
            )


def classify_entries(
    entries: list[dict[str, Any]], module_roots: dict[str, str]
) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Classify complete global units; no representative may decide a unit role."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for entry in entries:
        entry.pop("translation_unit", None)
        grouped[unit_key(entry)].append(entry)

    units = []
    reason_counts: Counter[str] = Counter()
    for key, occurrences in grouped.items():
        role_gate = occurrence_role_gate(
            occurrences,
            lambda occurrence: source_structural_proof(
                occurrence, module_roots, analysis_cache
            ),
        )
        heuristic_reasons = [exclusion_reason(entry) for entry in occurrences]
        unit_diagnostics: list[str] = []

        if role_gate == GATE_AUTO_EXCLUDE:
            reason = "INTERNAL_TEMPLATE_VARIABLE_KEY"
            for entry in occurrences:
                entry["status"] = "RESOLVED_EXCLUSION"
                entry["review_status"] = "NOT_APPLICABLE"
                entry["notes"] = list(dict.fromkeys([*entry.get("notes", []), reason]))
                reason_counts[reason] += 1
            continue

        if role_gate == GATE_REVIEW_REQUIRED:
            effective_gate = GATE_REVIEW_REQUIRED
            unit_diagnostics.append("STRUCTURAL_ROLE_REVIEW_REQUIRED")
        elif any(
            entry.get("literal_role") == ROLE_SUBSTITUTION_VALUE
            for entry in occurrences
        ):
            # A parser-proven pair index 1 is data substituted into displayed
            # text.  Its shape may resemble a path or engine token, but it may
            # never be auto-excluded by legacy lexical heuristics.
            effective_gate = GATE_MANUAL_REVIEW
            unit_diagnostics.append("TEMPLATE_SUBSTITUTION_VALUE_TRANSLATION_REVIEW")
        elif all(reason is not None for reason in heuristic_reasons):
            for entry, reason in zip(occurrences, heuristic_reasons):
                assert reason is not None
                entry["status"] = "RESOLVED_EXCLUSION"
                entry["review_status"] = "NOT_APPLICABLE"
                entry["notes"] = list(dict.fromkeys([*entry.get("notes", []), reason]))
                reason_counts[reason] += 1
            continue
        elif any(reason is not None for reason in heuristic_reasons):
            effective_gate = GATE_REVIEW_REQUIRED
            unit_diagnostics.append("MIXED_HEURISTIC_CONTEXT_REVIEW_REQUIRED")
        else:
            effective_gate = GATE_MANUAL_REVIEW

        for entry in occurrences:
            entry["status"] = "UNTRANSLATED"
            entry["review_status"] = "NOT_REVIEWED"
            entry["translation_unit"] = key
            if unit_diagnostics:
                entry["notes"] = list(
                    dict.fromkeys([*entry.get("notes", []), *unit_diagnostics])
                )
        first = occurrences[0]
        units.append(
            {
                "translation_unit": key,
                "english": first["english"],
                "japanese": "",
                "mode": first["mode"],
                "placeholder_signature": first["placeholder_signature"],
                "status": "UNTRANSLATED",
                "review_status": "NOT_REVIEWED",
                "occurrence_count": len(occurrences),
                "modules": sorted({entry["module"] for entry in occurrences}),
                "occurrences": [entry["stable_key"] for entry in occurrences],
                "role_gate": effective_gate,
                "role_summary": role_summary(occurrences),
                "classification_diagnostics": unit_diagnostics,
                "notes": [],
            }
        )
    units.sort(key=lambda unit: (unit["modules"], unit["english"]))
    return units, reason_counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    parser.add_argument("--coverage", default="reports/translation-coverage.json")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    ledger_path = (repo / args.ledger).resolve()
    units_path = (repo / args.units).resolve()
    coverage_path = (repo / args.coverage).resolve()
    work = (repo / "work").resolve()
    if work not in ledger_path.parents or work not in units_path.parents:
        raise SystemExit("ERROR: detailed ledger and units must remain below ignored work/")
    if repo not in coverage_path.parents:
        raise SystemExit("ERROR: coverage report must remain in repository")

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    snapshot_lock = json.loads(
        (repo / "reports" / "supported-snapshot-lock.json").read_text(encoding="utf-8")
    )
    require_fresh_extraction(ledger)
    units, reason_counts = classify_entries(ledger["entries"], ledger.get("module_roots", {}))

    ledger["classified_at_utc"] = datetime.now(tz=timezone.utc).isoformat()
    ledger["classification"] = {
        "method": "parser-bound all-occurrence roles plus conservative call-site heuristics",
        "resolved_exclusion_reasons": dict(sorted(reason_counts.items())),
        "manual_review_required_for_all_remaining_units": True,
    }
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    units_payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "source_ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper(),
        "units": units,
    }
    units_path.parent.mkdir(parents=True, exist_ok=True)
    units_path.write_text(json.dumps(units_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    per_module: dict[str, dict[str, int]] = {}
    modules = sorted({entry["module"] for entry in ledger["entries"]})
    for module in modules:
        subset = [entry for entry in ledger["entries"] if entry["module"] == module]
        per_module[module] = {
            "occurrences": len(subset),
            "resolved_exclusions": sum(entry["status"] == "RESOLVED_EXCLUSION" for entry in subset),
            "translatable_occurrences": sum(entry["status"] != "RESOLVED_EXCLUSION" for entry in subset),
            "translated_occurrences": sum(entry["status"] == "TRANSLATED" for entry in subset),
            "reviewed_occurrences": sum(entry["review_status"] == "REVIEWED" for entry in subset),
        }
    coverage = {
        "schema_version": 1,
        "installed_snapshot_id": snapshot_lock["installed_snapshot_id"],
        "snapshot_basis_sha256": snapshot_lock["snapshot_basis_sha256"],
        "status": "CLASSIFIED_CANDIDATES",
        "detailed_ledger_location": "work/ledger/translation-ledger.json (gitignored)",
        "translation_units_location": "work/ledger/translation-units.json (gitignored)",
        "detailed_ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper(),
        "translation_units_sha256": hashlib.sha256(units_path.read_bytes()).hexdigest().upper(),
        "rosetta_extractor": ledger["rosetta"],
        "total_occurrences": len(ledger["entries"]),
        "resolved_exclusion_occurrences": sum(reason_counts.values()),
        "translatable_occurrences": len(ledger["entries"]) - sum(reason_counts.values()),
        "unique_translation_units": len(units),
        "untranslated_units": sum(unit["status"] == "UNTRANSLATED" for unit in units),
        "translated_needs_review_units": 0,
        "reviewed_units": 0,
        "extraction_failures": ledger["extraction_failures"],
        "extraction_warnings": ledger.get("extraction_warnings", []),
        "duplicate_stable_keys": ledger["duplicate_stable_keys"],
        "resolved_exclusion_reasons": dict(sorted(reason_counts.items())),
        "per_module": per_module,
        "release_gate": "NOT_MET",
    }
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: coverage[key] for key in ("total_occurrences", "resolved_exclusion_occurrences", "translatable_occurrences", "unique_translation_units", "untranslated_units")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
