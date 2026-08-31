#!/usr/bin/env python3
"""Create exact mixed-context split plans from a completed occurrence audit."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from squirrel_literal_roles import (  # noqa: E402
    GATE_MANUAL_REVIEW,
    GATE_REVIEW_REQUIRED,
    PARSER_PROVEN,
    ROLE_BINDING_KEY,
)
from ledger_integrity import unique_unit_index  # noqa: E402


def reason_code(finding: dict[str, Any]) -> str | None:
    value = finding.get("prior_note_classification")
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("classification"), str):
        return value["classification"]
    fallback = finding.get("candidate_classification")
    return fallback if isinstance(fallback, str) and fallback.strip() else None


def build_plan(
    audit: dict[str, Any],
    units_payload: dict[str, Any],
    plan_id: str,
    *,
    require_role_evidence: bool = False,
) -> dict[str, Any]:
    unit_index = unique_unit_index(units_payload["units"])
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
        strict_role_gate = unit.get("role_gate") == GATE_REVIEW_REQUIRED or any(
            finding.get("unit_role_gate") == GATE_REVIEW_REQUIRED for finding in findings
        )
        if require_role_evidence and not strict_role_gate:
            raise ValueError(f"Mixed split is missing a source-bound role gate: {unit_id}")
        if strict_role_gate:
            if any(finding.get("role_metadata_verified") is not True for finding in findings):
                raise ValueError(f"Mixed split has unverified role metadata: {unit_id}")
            if any(
                not isinstance(finding.get("occurrence_evidence"), dict)
                or not finding["occurrence_evidence"].get("evidence_fingerprint")
                for finding in findings
            ):
                raise ValueError(f"Mixed split has incomplete role evidence: {unit_id}")
        audited_keys = [finding["stable_key"] for finding in findings]
        if len(audited_keys) != len(set(audited_keys)) or set(audited_keys) != set(unit["occurrences"]):
            raise ValueError(f"Mixed audit must exactly cover canonical occurrences: {unit_id}")

        excluded = [finding for finding in findings if finding["classification"] == "RESOLVED_EXCLUSION"]
        visible = [
            finding for finding in findings
            if finding["classification"] == "PLAYER_FACING_REVIEW_REQUIRED"
        ]
        if strict_role_gate:
            if any(
                finding["occurrence_evidence"].get("literal_role") != ROLE_BINDING_KEY
                or finding["occurrence_evidence"].get("role_confidence") != PARSER_PROVEN
                for finding in excluded
            ):
                raise ValueError(f"Excluded mixed partition is not proven internal keys: {unit_id}")
            if any(
                finding["occurrence_evidence"].get("literal_role") == ROLE_BINDING_KEY
                for finding in visible
            ):
                raise ValueError(f"Visible mixed partition contains a binding key: {unit_id}")
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
                        "occurrence_evidence": [
                            finding.get("occurrence_evidence") for finding in excluded
                        ] if strict_role_gate else [],
                    },
                    {
                        "stable_keys": sorted(finding["stable_key"] for finding in visible),
                        "resolution": "UNTRANSLATED",
                        "review_status": "NOT_REVIEWED",
                        "notes": list(dict.fromkeys(finding["reason"] for finding in visible)),
                        "role_gate_after_review": GATE_MANUAL_REVIEW,
                        "occurrence_evidence": [
                            finding.get("occurrence_evidence") for finding in visible
                        ] if strict_role_gate else [],
                    },
                ],
            }
        )
    if not splits:
        raise ValueError("Audit contains no fully reviewed mixed-context units")
    return {
        "schema_version": 2 if require_role_evidence else 1,
        "role_evidence_required": require_role_evidence,
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
    plan = build_plan(
        audit, units_payload, args.plan_id, require_role_evidence=True
    )
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
