#!/usr/bin/env python3
"""Create exact mixed-context split plans from a completed occurrence audit."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def reason_code(finding: dict[str, Any]) -> str | None:
    value = finding.get("prior_note_classification")
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("classification"), str):
        return value["classification"]
    fallback = finding.get("candidate_classification")
    return fallback if isinstance(fallback, str) and fallback.strip() else None


def build_plan(audit: dict[str, Any], units_payload: dict[str, Any], plan_id: str) -> dict[str, Any]:
    unit_index = {unit["translation_unit"]: unit for unit in units_payload["units"]}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in audit.get("findings", []):
        grouped[finding["translation_unit"]].append(finding)

    splits = []
    for unit_id, findings in sorted(grouped.items()):
        classifications = {finding.get("classification") for finding in findings}
        if classifications != {"RESOLVED_EXCLUSION", "PLAYER_FACING_REVIEW_REQUIRED"}:
            continue
        if unit_id not in unit_index:
            raise ValueError(f"Audit references unknown mixed unit: {unit_id}")
        unit = unit_index[unit_id]
        if unit.get("status") != "UNTRANSLATED" or unit.get("review_status") != "NOT_REVIEWED":
            raise ValueError(f"Mixed split requires an unresolved canonical unit: {unit_id}")
        if any(finding.get("source_evidence", {}).get("verified") is not True for finding in findings):
            raise ValueError(f"Mixed split has unverified source evidence: {unit_id}")
        audited_keys = [finding["stable_key"] for finding in findings]
        if len(audited_keys) != len(set(audited_keys)) or set(audited_keys) != set(unit["occurrences"]):
            raise ValueError(f"Mixed audit must exactly cover canonical occurrences: {unit_id}")

        excluded = [finding for finding in findings if finding["classification"] == "RESOLVED_EXCLUSION"]
        visible = [
            finding for finding in findings
            if finding["classification"] == "PLAYER_FACING_REVIEW_REQUIRED"
        ]
        reason_codes = sorted({reason_code(finding) for finding in excluded})
        if not reason_codes or None in reason_codes:
            raise ValueError(f"Mixed split has missing exclusion reason: {unit_id}")
        exclusion_reason = (
            reason_codes[0]
            if len(reason_codes) == 1
            else "MULTIPLE_RESOLVED_EXCLUSION_REASONS"
        )
        splits.append(
            {
                "original_unit": unit_id,
                "english": unit["english"],
                "variants": [
                    {
                        "stable_keys": sorted(finding["stable_key"] for finding in excluded),
                        "resolution": "RESOLVED_EXCLUSION",
                        "review_status": "NOT_APPLICABLE",
                        "reason": exclusion_reason,
                        "reason_codes": reason_codes,
                        "notes": list(dict.fromkeys(finding["reason"] for finding in excluded)),
                    },
                    {
                        "stable_keys": sorted(finding["stable_key"] for finding in visible),
                        "resolution": "UNTRANSLATED",
                        "review_status": "NOT_REVIEWED",
                        "notes": list(dict.fromkeys(finding["reason"] for finding in visible)),
                    },
                ],
            }
        )
    if not splits:
        raise ValueError("Audit contains no fully reviewed mixed-context units")
    return {
        "schema_version": 1,
        "plan_id": plan_id,
        "source_audit_id": audit.get("audit_id"),
        "splits": splits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    audit_path = (repo / args.audit).resolve()
    output_path = (repo / args.output).resolve()
    units_path = (repo / args.units).resolve()
    if any(work not in path.parents for path in (audit_path, output_path, units_path)):
        raise SystemExit("ERROR: audit, split plan, and canonical units must remain below ignored work/")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    plan = build_plan(audit, units_payload, args.plan_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "plan_id": args.plan_id,
        "mixed_units": len(plan["splits"]),
        "excluded_occurrences": sum(len(split["variants"][0]["stable_keys"]) for split in plan["splits"]),
        "player_facing_occurrences": sum(len(split["variants"][1]["stable_keys"]) for split in plan["splits"]),
        "output": str(output_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
