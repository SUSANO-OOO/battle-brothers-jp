#!/usr/bin/env python3
"""Validate and apply one reviewed or draft translation batch to the canonical ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOKEN_PATTERNS = {
    "percent_vars": re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%"),
    "printf": re.compile(r"%(?:\d+\$)?[sdif](?![A-Za-z0-9_]*%)"),
    "bbcode_tags": re.compile(r"\[[^\]\r\n]+\]"),
    "captures": re.compile(r"<[^>\r\n]+>"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def signature(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {name: pattern.findall(text) for name, pattern in TOKEN_PATTERNS.items()}
    result.update(
        {
            "newlines": text.count("\n"),
            "brace_open": text.count("{"),
            "brace_close": text.count("}"),
            "template_pipes": text.count("|") if "{" in text or "}" in text else 0,
        }
    )
    return result


def normalize_notes(value: Any) -> list[str]:
    """Keep one textual note as one note instead of splitting it into characters."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(note, str) for note in value):
        return list(value)
    raise ValueError("notes must be a string, a list of strings, or null")


def validate_batch(batch: dict[str, Any], units: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    entries = batch.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Batch must contain a non-empty entries list")
    duplicates = sorted(
        key for key, count in Counter(entry.get("translation_unit") for entry in entries).items() if count > 1
    )
    if duplicates:
        raise ValueError(f"Duplicate translation units in batch: {duplicates}")

    validated = []
    for index, entry in enumerate(entries):
        unit_id = entry.get("translation_unit")
        if unit_id not in units:
            raise ValueError(f"Entry {index} references unknown translation unit: {unit_id}")
        unit = units[unit_id]
        if entry.get("english") != unit["english"]:
            raise ValueError(f"Entry {index} English/source mismatch: {unit_id}")
        japanese = entry.get("japanese")
        if not isinstance(japanese, str) or not japanese.strip():
            raise ValueError(f"Entry {index} has empty Japanese: {unit_id}")
        if entry.get("placeholder_signature") != unit["placeholder_signature"]:
            raise ValueError(f"Entry {index} recorded placeholder signature mismatch: {unit_id}")
        japanese_signature = signature(japanese)
        if japanese_signature != unit["placeholder_signature"]:
            raise ValueError(
                f"Entry {index} Japanese placeholder/tag/newline signature mismatch: {unit_id}; "
                f"expected={unit['placeholder_signature']}, actual={japanese_signature}"
            )
        review_status = entry.get("review_status")
        if review_status not in {"DRAFT_INDEPENDENT_REVIEW_REQUIRED", "REVIEWED"}:
            raise ValueError(f"Entry {index} has invalid review_status: {review_status}")
        entry["notes"] = normalize_notes(entry.get("notes"))
        validated.append(entry)
    return validated


def update_coverage(
    repo: Path,
    coverage: dict[str, Any],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
    ledger_path: Path,
    units_path: Path,
) -> None:
    units = units_payload["units"]
    entries = ledger["entries"]
    coverage.update(
        {
            "status": "TRANSLATION_IN_PROGRESS",
            "detailed_ledger_sha256": sha256(ledger_path),
            "translation_units_sha256": sha256(units_path),
            "untranslated_units": sum(unit["status"] == "UNTRANSLATED" for unit in units),
            "translated_needs_review_units": sum(
                unit["status"] == "TRANSLATED" and unit["review_status"] != "REVIEWED" for unit in units
            ),
            "reviewed_units": sum(unit["status"] == "TRANSLATED" and unit["review_status"] == "REVIEWED" for unit in units),
        }
    )
    for module, values in coverage.get("per_module", {}).items():
        subset = [entry for entry in entries if entry["module"] == module]
        values["translated_occurrences"] = sum(entry["status"] == "TRANSLATED" for entry in subset)
        values["reviewed_occurrences"] = sum(
            entry["status"] == "TRANSLATED" and entry["review_status"] == "REVIEWED" for entry in subset
        )
    coverage["release_gate"] = (
        "MET"
        if coverage["untranslated_units"] == 0
        and coverage["translated_needs_review_units"] == 0
        and not coverage.get("extraction_failures")
        else "NOT_MET"
    )
    coverage["updated_at_utc"] = datetime.now(tz=timezone.utc).isoformat()
    (repo / "reports" / "translation-coverage.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    parser.add_argument(
        "--reviewed-only",
        action="store_true",
        help="Apply only entries whose review_status is REVIEWED; leave drafts untouched.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without changing canonical files")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    batch_path = (repo / args.batch).resolve()
    ledger_path = (repo / args.ledger).resolve()
    units_path = (repo / args.units).resolve()
    for path in (batch_path, ledger_path, units_path):
        if work not in path.parents:
            raise SystemExit(f"ERROR: proprietary/draft data must remain below ignored work/: {path}")

    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    skipped_entries = 0
    if args.reviewed_only:
        all_entries = batch.get("entries", [])
        reviewed_entries = [entry for entry in all_entries if entry.get("review_status") == "REVIEWED"]
        skipped_entries = len(all_entries) - len(reviewed_entries)
        batch = dict(batch)
        batch["entries"] = reviewed_entries
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    unit_index = {unit["translation_unit"]: unit for unit in units_payload["units"]}
    occurrence_index = {entry["stable_key"]: entry for entry in ledger["entries"]}
    validated = validate_batch(batch, unit_index)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "batch_id": batch.get("batch_id"),
                    "validated_entries": len(validated),
                    "reviewed_entries": sum(entry["review_status"] == "REVIEWED" for entry in validated),
                    "skipped_non_reviewed_entries": skipped_entries,
                    "dry_run": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    for entry in validated:
        unit = unit_index[entry["translation_unit"]]
        unit["japanese"] = entry["japanese"]
        unit["status"] = "TRANSLATED"
        unit["review_status"] = entry["review_status"]
        unit["notes"] = entry["notes"]
        for stable_key in unit["occurrences"]:
            occurrence = occurrence_index[stable_key]
            occurrence["japanese"] = entry["japanese"]
            occurrence["status"] = "TRANSLATED"
            occurrence["review_status"] = entry["review_status"]
            occurrence["notes"] = entry["notes"]

    applied_at = datetime.now(tz=timezone.utc).isoformat()
    ledger["last_translation_batch"] = {"batch_id": batch.get("batch_id"), "applied_at_utc": applied_at}
    units_payload["last_translation_batch"] = {"batch_id": batch.get("batch_id"), "applied_at_utc": applied_at}
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    units_path.write_text(json.dumps(units_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    coverage_path = repo / "reports" / "translation-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    update_coverage(repo, coverage, ledger, units_payload, ledger_path, units_path)
    print(
        json.dumps(
            {
                "batch_id": batch.get("batch_id"),
                "applied_entries": len(validated),
                "reviewed_entries": sum(entry["review_status"] == "REVIEWED" for entry in validated),
                "skipped_non_reviewed_entries": skipped_entries,
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
