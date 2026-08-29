#!/usr/bin/env python3
"""Split ambiguous deduplicated units into reviewed context-specific variants."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def variant_id(original_id: str, stable_keys: list[str], strategy: str) -> str:
    basis = "\x1f".join((original_id, strategy, *sorted(stable_keys)))
    return f"unitctx:{hashlib.sha256(basis.encode('utf-8')).hexdigest().upper()[:24]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    paths = [(repo / value).resolve() for value in (args.plan, args.ledger, args.units)]
    if any(work not in path.parents for path in paths):
        raise SystemExit("ERROR: split plan and canonical ledger files must remain below ignored work/")
    plan_path, ledger_path, units_path = paths

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    unit_index = {unit["translation_unit"]: unit for unit in units_payload["units"]}
    occurrence_index = {entry["stable_key"]: entry for entry in ledger["entries"]}
    created: list[dict[str, Any]] = []
    removed: set[str] = set()

    for split in plan.get("splits", []):
        original_id = split["original_unit"]
        if original_id not in unit_index:
            raise ValueError(f"Unknown original unit: {original_id}")
        original = unit_index[original_id]
        expected = set(original["occurrences"])
        assigned: list[str] = []
        variants = split.get("variants", [])
        if len(variants) < 2:
            raise ValueError(f"Context split requires at least two variants: {original_id}")
        for variant in variants:
            stable_keys = variant.get("stable_keys", [])
            if not stable_keys or len(stable_keys) != len(set(stable_keys)):
                raise ValueError(f"Invalid stable key list in split: {original_id}")
            assigned.extend(stable_keys)
            japanese = variant.get("japanese")
            if not isinstance(japanese, str) or not japanese.strip():
                raise ValueError(f"Empty context translation: {original_id}")
            if variant.get("review_status") != "REVIEWED":
                raise ValueError(f"Context variants must be independently resolved before split: {original_id}")
            strategy = variant.get("runtime_strategy")
            if strategy not in {"ROSETTA_LITERAL", "JAVASCRIPT_LITERAL", "BOUNDARY_HOOK"}:
                raise ValueError(f"Invalid runtime strategy for {original_id}: {strategy}")
            new_id = variant_id(original_id, stable_keys, strategy)
            occurrences = [occurrence_index[key] for key in stable_keys]
            notes = list(variant.get("notes", [])) + [f"RUNTIME_STRATEGY:{strategy}"]
            for occurrence in occurrences:
                if occurrence.get("translation_unit") != original_id:
                    raise ValueError(f"Occurrence does not belong to {original_id}: {occurrence['stable_key']}")
                occurrence["translation_unit"] = new_id
                occurrence["japanese"] = japanese
                occurrence["status"] = "TRANSLATED"
                occurrence["review_status"] = "REVIEWED"
                occurrence["notes"] = notes
            created.append(
                {
                    "translation_unit": new_id,
                    "english": original["english"],
                    "japanese": japanese,
                    "mode": original["mode"],
                    "placeholder_signature": original["placeholder_signature"],
                    "status": "TRANSLATED",
                    "review_status": "REVIEWED",
                    "occurrence_count": len(occurrences),
                    "modules": sorted({entry["module"] for entry in occurrences}),
                    "occurrences": stable_keys,
                    "notes": notes,
                    "runtime_strategy": strategy,
                    "split_from": original_id,
                }
            )
        if set(assigned) != expected or len(assigned) != len(set(assigned)):
            raise ValueError(f"Variants must partition every occurrence exactly once: {original_id}")
        removed.add(original_id)

    units_payload["units"] = sorted(
        [unit for unit in units_payload["units"] if unit["translation_unit"] not in removed] + created,
        key=lambda unit: (unit["modules"], unit["english"], unit["translation_unit"]),
    )
    applied_at = datetime.now(tz=timezone.utc).isoformat()
    ledger["last_context_split"] = {"plan_id": plan.get("plan_id"), "applied_at_utc": applied_at}
    units_payload["last_context_split"] = {"plan_id": plan.get("plan_id"), "applied_at_utc": applied_at}
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    units_path.write_text(json.dumps(units_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    coverage_path = repo / "reports" / "translation-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    units = units_payload["units"]
    coverage["unique_translation_units"] = len(units)
    coverage["untranslated_units"] = sum(unit["status"] == "UNTRANSLATED" for unit in units)
    coverage["translated_needs_review_units"] = sum(
        unit["status"] == "TRANSLATED" and unit["review_status"] != "REVIEWED" for unit in units
    )
    coverage["reviewed_units"] = sum(
        unit["status"] == "TRANSLATED" and unit["review_status"] == "REVIEWED" for unit in units
    )
    coverage["detailed_ledger_sha256"] = sha256(ledger_path)
    coverage["translation_units_sha256"] = sha256(units_path)
    coverage["release_gate"] = "NOT_MET"
    coverage["updated_at_utc"] = applied_at
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"plan_id": plan.get("plan_id"), "removed_units": len(removed), "created_units": len(created), "reviewed_units": coverage["reviewed_units"], "ledger_sha256": sha256(ledger_path), "units_sha256": sha256(units_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
