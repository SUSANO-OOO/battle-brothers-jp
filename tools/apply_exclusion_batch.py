#!/usr/bin/env python3
"""Apply independently reviewed non-player-facing exclusions to the canonical ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from squirrel_literal_roles import (  # noqa: E402
    enrich_occurrence_role,
    occurrence_evidence,
    source_binding_key_proof,
)
from ledger_integrity import canonical_indexes, validate_unit_membership  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_batch(
    batch: dict[str, Any],
    units: dict[str, dict[str, Any]],
    occurrence_index: dict[str, dict[str, Any]] | None = None,
    module_roots: dict[str, str] | None = None,
    *,
    enforce_role_evidence: bool = True,
) -> list[dict[str, Any]]:
    if enforce_role_evidence and (
        batch.get("schema_version") != 2
        or batch.get("role_evidence_required") is not True
    ):
        raise ValueError("Exclusion batch must require schema-v2 source-bound role evidence")
    entries = batch.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Batch must contain a non-empty entries list")
    duplicates = sorted(
        key for key, count in Counter(entry.get("translation_unit") for entry in entries).items() if count > 1
    )
    if duplicates:
        raise ValueError(f"Duplicate translation units in batch: {duplicates}")

    validated = []
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for index, entry in enumerate(entries):
        unit_id = entry.get("translation_unit")
        if unit_id not in units:
            raise ValueError(f"Entry {index} references unknown translation unit: {unit_id}")
        unit = units[unit_id]
        if entry.get("english") != unit["english"]:
            raise ValueError(f"Entry {index} English/source mismatch: {unit_id}")
        if unit.get("status") != "UNTRANSLATED" or unit.get("review_status") != "NOT_REVIEWED":
            raise ValueError(f"Entry {index} is not an unresolved unit: {unit_id}")
        stable_keys = entry.get("stable_keys")
        if not isinstance(stable_keys, list) or not stable_keys or len(stable_keys) != len(set(stable_keys)):
            raise ValueError(f"Entry {index} must list unique stable_keys: {unit_id}")
        if set(stable_keys) != set(unit["occurrences"]):
            raise ValueError(
                f"Entry {index} exclusion scope does not cover the whole unit; split contexts first: {unit_id}"
            )
        evidence = entry.get("occurrence_evidence", [])
        if enforce_role_evidence and not evidence:
            raise ValueError(f"Entry {index} is missing mandatory exclusion evidence: {unit_id}")
        if entry.get("requires_parser_proven_binding") is True and not evidence:
            raise ValueError(f"Entry {index} parser-key exclusion requires evidence: {unit_id}")
        if evidence:
            if occurrence_index is None or not module_roots:
                raise ValueError(f"Entry {index} exclusion evidence requires source indexes: {unit_id}")
            evidence_index = {
                item.get("stable_key"): item for item in evidence if isinstance(item, dict)
            }
            if len(evidence_index) != len(evidence) or set(evidence_index) != set(stable_keys):
                raise ValueError(f"Entry {index} exclusion evidence must exactly cover unit: {unit_id}")
            validate_unit_membership(unit_id, unit, occurrence_index)
            enriched_occurrences = []
            for stable_key in stable_keys:
                current = occurrence_index.get(stable_key)
                if current is None:
                    raise ValueError(f"Entry {index} missing canonical occurrence: {stable_key}")
                enriched = enrich_occurrence_role(
                    current,
                    module_roots,
                    analysis_cache,
                    force_reanalysis=True,
                )
                if evidence_index[stable_key] != occurrence_evidence(enriched):
                    raise ValueError(f"Entry {index} exclusion source/role evidence drift: {stable_key}")
                enriched_occurrences.append(enriched)
            if entry.get("requires_parser_proven_binding") is True and any(
                not source_binding_key_proof(occurrence, module_roots, analysis_cache)
                for occurrence in enriched_occurrences
            ):
                raise ValueError(f"Entry {index} exclusion is not parser-proven binding keys: {unit_id}")
        if entry.get("review_status") != "NOT_APPLICABLE":
            raise ValueError(f"Entry {index} must have review_status NOT_APPLICABLE: {unit_id}")
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"Entry {index} has empty exclusion reason: {unit_id}")
        notes = entry.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        if not isinstance(notes, list) or not all(isinstance(note, str) for note in notes):
            raise ValueError(f"Entry {index} notes must be a string or list of strings: {unit_id}")
        entry["reason"] = reason.strip()
        entry["notes"] = notes
        validated.append(entry)
    return validated


def apply_entries(
    validated: list[dict[str, Any]],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
) -> Counter[str]:
    occurrence_index, unit_index = canonical_indexes(ledger, units_payload)
    remove_ids: set[str] = set()
    reason_counts: Counter[str] = Counter()

    for entry in validated:
        unit_id = entry["translation_unit"]
        unit = unit_index[unit_id]
        remove_ids.add(unit_id)
        for stable_key in unit["occurrences"]:
            occurrence = occurrence_index[stable_key]
            occurrence["japanese"] = ""
            occurrence["status"] = "RESOLVED_EXCLUSION"
            occurrence["review_status"] = "NOT_APPLICABLE"
            occurrence["notes"] = list(
                dict.fromkeys([*occurrence.get("notes", []), entry["reason"], *entry["notes"]])
            )
            occurrence.pop("translation_unit", None)
            reason_counts[entry["reason"]] += 1

    units_payload["units"] = [
        unit for unit in units_payload["units"] if unit["translation_unit"] not in remove_ids
    ]
    classification = ledger.setdefault("classification", {})
    stored_reasons = Counter(classification.get("resolved_exclusion_reasons", {}))
    stored_reasons.update(reason_counts)
    classification["resolved_exclusion_reasons"] = dict(sorted(stored_reasons.items()))
    return reason_counts


def update_coverage(
    coverage: dict[str, Any],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
    ledger_path: Path,
    units_path: Path,
) -> None:
    entries = ledger["entries"]
    units = units_payload["units"]
    resolved = sum(entry["status"] == "RESOLVED_EXCLUSION" for entry in entries)
    coverage.update(
        {
            "status": "TRANSLATION_IN_PROGRESS",
            "detailed_ledger_sha256": sha256(ledger_path),
            "translation_units_sha256": sha256(units_path),
            "resolved_exclusion_occurrences": resolved,
            "translatable_occurrences": len(entries) - resolved,
            "unique_translation_units": len(units),
            "untranslated_units": sum(unit["status"] == "UNTRANSLATED" for unit in units),
            "translated_needs_review_units": sum(
                unit["status"] == "TRANSLATED" and unit["review_status"] != "REVIEWED" for unit in units
            ),
            "reviewed_units": sum(
                unit["status"] == "TRANSLATED" and unit["review_status"] == "REVIEWED" for unit in units
            ),
            "resolved_exclusion_reasons": ledger.get("classification", {}).get(
                "resolved_exclusion_reasons", {}
            ),
        }
    )
    for module, values in coverage.get("per_module", {}).items():
        subset = [entry for entry in entries if entry["module"] == module]
        values.update(
            {
                "occurrences": len(subset),
                "resolved_exclusions": sum(entry["status"] == "RESOLVED_EXCLUSION" for entry in subset),
                "translatable_occurrences": sum(
                    entry["status"] != "RESOLVED_EXCLUSION" for entry in subset
                ),
                "translated_occurrences": sum(entry["status"] == "TRANSLATED" for entry in subset),
                "reviewed_occurrences": sum(
                    entry["status"] == "TRANSLATED" and entry["review_status"] == "REVIEWED"
                    for entry in subset
                ),
            }
        )
    coverage["release_gate"] = (
        "MET"
        if coverage["untranslated_units"] == 0
        and coverage["translated_needs_review_units"] == 0
        and not coverage.get("extraction_failures")
        else "NOT_MET"
    )
    coverage["updated_at_utc"] = datetime.now(tz=timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate without changing canonical files")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    batch_path = (repo / args.batch).resolve()
    ledger_path = (repo / args.ledger).resolve()
    units_path = (repo / args.units).resolve()
    for path in (batch_path, ledger_path, units_path):
        if work not in path.parents:
            raise SystemExit(f"ERROR: proprietary/review data must remain below ignored work/: {path}")

    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    unit_index = {unit["translation_unit"]: unit for unit in units_payload["units"]}
    occurrence_index = {entry["stable_key"]: entry for entry in ledger["entries"]}
    validated = validate_batch(
        batch, unit_index, occurrence_index, ledger.get("module_roots", {})
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "batch_id": batch.get("batch_id"),
                    "validated_entries": len(validated),
                    "excluded_occurrences": sum(
                        len(entry["stable_keys"]) for entry in validated
                    ),
                    "dry_run": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    validated = validate_batch(
        batch, unit_index, occurrence_index, ledger.get("module_roots", {})
    )
    reason_counts = apply_entries(validated, ledger, units_payload)
    applied_at = datetime.now(tz=timezone.utc).isoformat()
    metadata = {"batch_id": batch.get("batch_id"), "applied_at_utc": applied_at}
    ledger["last_exclusion_batch"] = metadata
    units_payload["last_exclusion_batch"] = metadata
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    units_payload["source_ledger_sha256"] = sha256(ledger_path)
    units_path.write_text(json.dumps(units_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    coverage_path = repo / "reports" / "translation-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    update_coverage(coverage, ledger, units_payload, ledger_path, units_path)
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "batch_id": batch.get("batch_id"),
                "excluded_units": len(validated),
                "excluded_occurrences": sum(reason_counts.values()),
                "reason_counts": dict(sorted(reason_counts.items())),
                "ledger_sha256": sha256(ledger_path),
                "units_sha256": sha256(units_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
