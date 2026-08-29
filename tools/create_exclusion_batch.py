#!/usr/bin/env python3
"""Create whole-unit exclusion batches from independently reviewed occurrence audits."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def build_batch(
    audit: dict[str, Any], units_payload: dict[str, Any], batch_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    unit_index = {unit["translation_unit"]: unit for unit in units_payload["units"]}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in audit.get("findings", []):
        if finding.get("classification") == "RESOLVED_EXCLUSION":
            if finding.get("source_evidence", {}).get("verified") is not True:
                raise ValueError(f"Unverified source evidence: {finding.get('stable_key')}")
            grouped[finding["translation_unit"]].append(finding)

    entries = []
    skipped_partial = []
    for unit_id, findings in sorted(grouped.items()):
        if unit_id not in unit_index:
            raise ValueError(f"Audit references unknown unit: {unit_id}")
        unit = unit_index[unit_id]
        stable_keys = sorted(finding["stable_key"] for finding in findings)
        expected = set(unit["occurrences"])
        if set(stable_keys) != expected:
            skipped_partial.append(
                {
                    "translation_unit": unit_id,
                    "audited_exclusion_occurrences": len(stable_keys),
                    "unit_occurrences": len(expected),
                    "remaining_stable_keys": sorted(expected - set(stable_keys)),
                }
            )
            continue
        reason_codes = {finding.get("prior_note_classification") for finding in findings}
        if None in reason_codes or len(reason_codes) != 1:
            raise ValueError(f"Whole unit must have one exclusion reason code: {unit_id}")
        notes = list(dict.fromkeys(finding["reason"] for finding in findings))
        entries.append(
            {
                "translation_unit": unit_id,
                "english": unit["english"],
                "review_status": "NOT_APPLICABLE",
                "reason": next(iter(reason_codes)),
                "stable_keys": stable_keys,
                "notes": notes,
            }
        )
    if not entries:
        raise ValueError("Audit produced no whole-unit exclusions")
    return (
        {
            "schema_version": 1,
            "batch_id": batch_id,
            "source_audit_id": audit.get("audit_id"),
            "entries": entries,
        },
        skipped_partial,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    audit_path = (repo / args.audit).resolve()
    output_path = (repo / args.output).resolve()
    units_path = (repo / args.units).resolve()
    if any(work not in path.parents for path in (audit_path, output_path, units_path)):
        raise SystemExit("ERROR: audits, batches, and canonical units must remain below ignored work/")

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    batch, skipped_partial = build_batch(audit, units_payload, args.batch_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "batch_id": args.batch_id,
                "whole_units": len(batch["entries"]),
                "whole_unit_occurrences": sum(len(entry["stable_keys"]) for entry in batch["entries"]),
                "skipped_partial_units": skipped_partial,
                "output": str(output_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
