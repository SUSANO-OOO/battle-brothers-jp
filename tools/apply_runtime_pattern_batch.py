#!/usr/bin/env python3
"""Validate and attach reviewed runtime contracts to canonical pattern units."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CAPTURE = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*):([A-Za-z_]+)>")
REPLACEMENT = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*)(?::([A-Za-z_]+))?>")
ANY_ANGLE = re.compile(r"<[^>\r\n]+>")
ALLOWED_TYPES = {"int", "val", "word", "str", "line", "tag", "img", "int_tag", "val_tag", "str_tag"}
ALLOWED_FLAGS = {None, "t"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_rosetta_contract(entry: dict[str, Any]) -> None:
    unit_id = entry["translation_unit"]
    runtime_en = entry.get("runtime_en")
    runtime_ja = entry.get("runtime_ja")
    samples = entry.get("samples")
    if not isinstance(runtime_en, str) or not isinstance(runtime_ja, str):
        raise ValueError(f"Missing runtime pattern strings: {unit_id}")
    en_matches = list(CAPTURE.finditer(runtime_en))
    ja_matches = list(REPLACEMENT.finditer(runtime_ja))
    if ANY_ANGLE.findall(runtime_en) != [match.group(0) for match in en_matches]:
        raise ValueError(f"Raw or invalid Rosetta capture in runtime_en: {unit_id}")
    if ANY_ANGLE.findall(runtime_ja) != [match.group(0) for match in ja_matches]:
        raise ValueError(f"Raw or invalid Rosetta replacement in runtime_ja: {unit_id}")
    en_names = [match.group(1) for match in en_matches]
    ja_names = [match.group(1) for match in ja_matches]
    if len(en_names) != len(set(en_names)):
        raise ValueError(f"Duplicate capture name: {unit_id}")
    if set(en_names) != set(ja_names) or len(ja_names) != len(set(ja_names)):
        raise ValueError(f"Runtime capture/replacement mismatch: {unit_id}")
    invalid_types = [match.group(2) for match in en_matches if match.group(2) not in ALLOWED_TYPES]
    invalid_flags = [match.group(2) for match in ja_matches if match.group(2) not in ALLOWED_FLAGS]
    if invalid_types or invalid_flags:
        raise ValueError(f"Unsupported Rosetta capture type/flag: {unit_id}; {invalid_types}; {invalid_flags}")
    if not isinstance(samples, list) or not samples:
        raise ValueError(f"At least one runtime sample is required: {unit_id}")
    for sample in samples:
        if not isinstance(sample.get("english"), str) or not isinstance(sample.get("japanese"), str):
            raise ValueError(f"Malformed runtime sample: {unit_id}")


def validate_boundary_contract(entry: dict[str, Any]) -> None:
    unit_id = entry["translation_unit"]
    for field in ("hook_target", "hook_method", "boundary_operation"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ValueError(f"Missing {field} for boundary contract: {unit_id}")
    samples = entry.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError(f"Boundary contract needs a representative sample: {unit_id}")


def merge_runtime_contract(unit: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    """Apply a bounded correction without discarding prior source evidence."""
    update = {key: value for key, value in entry.items() if key not in {"translation_unit", "english"}}
    return {**unit.get("runtime_contract", {}), **update}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    paths = [(repo / value).resolve() for value in (args.batch, args.ledger, args.units)]
    if any(work not in path.parents for path in paths):
        raise SystemExit("ERROR: runtime batches and canonical ledgers must remain below ignored work/")
    batch_path, ledger_path, units_path = paths
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    unit_index = {unit["translation_unit"]: unit for unit in units_payload["units"]}
    occurrence_index = {entry["stable_key"]: entry for entry in ledger["entries"]}
    entries = batch.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Runtime pattern batch must contain entries")
    ids = [entry.get("translation_unit") for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate translation_unit in runtime pattern batch")
    resolved = []
    unresolved = []
    for entry in entries:
        unit_id = entry.get("translation_unit")
        if unit_id not in unit_index:
            raise ValueError(f"Unknown pattern unit: {unit_id}")
        unit = unit_index[unit_id]
        if unit.get("mode") != "pattern" or unit.get("review_status") != "REVIEWED":
            raise ValueError(f"Runtime contract requires a reviewed pattern unit: {unit_id}")
        if entry.get("english") != unit.get("english"):
            raise ValueError(f"Pattern batch English mismatch: {unit_id}")
        strategy = entry.get("strategy")
        status = entry.get("resolution_status")
        if status == "UNRESOLVED" or strategy == "UNRESOLVED":
            unresolved.append(entry)
            continue
        if status != "RESOLVED" or strategy not in {"ROSETTA_PATTERN", "BOUNDARY_HOOK"}:
            raise ValueError(f"Invalid runtime resolution status/strategy: {unit_id}")
        if strategy == "ROSETTA_PATTERN":
            validate_rosetta_contract(entry)
        else:
            validate_boundary_contract(entry)
        resolved.append(entry)

    if args.dry_run:
        print(json.dumps({"batch_id": batch.get("batch_id"), "entries": len(entries), "resolved": len(resolved), "unresolved": len(unresolved), "dry_run": True}, indent=2))
        return 0

    for entry in resolved:
        unit = unit_index[entry["translation_unit"]]
        contract = merge_runtime_contract(unit, entry)
        unit["runtime_strategy"] = entry["strategy"]
        unit["runtime_contract"] = contract
        unit["notes"] = list(dict.fromkeys([*unit.get("notes", []), "RUNTIME_PATTERN_AUDITED"]))
        for stable_key in unit["occurrences"]:
            occurrence = occurrence_index[stable_key]
            occurrence["runtime_strategy"] = entry["strategy"]
            occurrence["runtime_contract_status"] = "RESOLVED"
            occurrence["notes"] = list(dict.fromkeys([*occurrence.get("notes", []), "RUNTIME_PATTERN_AUDITED"]))
    for entry in unresolved:
        unit = unit_index[entry["translation_unit"]]
        unit["runtime_contract_status"] = "UNRESOLVED"
        unit["runtime_contract_notes"] = entry.get("notes", [])

    applied_at = datetime.now(tz=timezone.utc).isoformat()
    ledger["last_runtime_pattern_batch"] = {"batch_id": batch.get("batch_id"), "applied_at_utc": applied_at}
    units_payload["last_runtime_pattern_batch"] = {"batch_id": batch.get("batch_id"), "applied_at_utc": applied_at}
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    units_path.write_text(json.dumps(units_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    coverage_path = repo / "reports" / "translation-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage["detailed_ledger_sha256"] = sha256(ledger_path)
    coverage["translation_units_sha256"] = sha256(units_path)
    coverage["runtime_pattern_resolved_units"] = sum(
        unit.get("mode") == "pattern" and unit.get("runtime_contract", {}).get("resolution_status") == "RESOLVED"
        for unit in units_payload["units"]
    )
    coverage["runtime_pattern_unresolved_units"] = sum(
        unit.get("mode") == "pattern" and unit.get("review_status") == "REVIEWED" and unit.get("runtime_contract", {}).get("resolution_status") != "RESOLVED"
        for unit in units_payload["units"]
    )
    coverage["updated_at_utc"] = applied_at
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"batch_id": batch.get("batch_id"), "resolved": len(resolved), "unresolved": len(unresolved), "ledger_sha256": sha256(ledger_path), "units_sha256": sha256(units_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
