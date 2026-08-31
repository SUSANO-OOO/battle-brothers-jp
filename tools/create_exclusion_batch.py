#!/usr/bin/env python3
"""Create whole-unit exclusion batches from independently reviewed occurrence audits."""

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

from squirrel_literal_roles import PARSER_PROVEN, ROLE_BINDING_KEY  # noqa: E402
from ledger_integrity import unique_unit_index  # noqa: E402


TEMPLATE_KEY_REASONS = {
    "INTERNAL_TEMPLATE_VARIABLE_KEY",
    "INTERNAL_REPLACEMENT_KEY",
    "template_variable_key",
}


def exclusion_reason_code(finding: dict[str, Any]) -> str | None:
    """Read the reviewer reason code from audit schema v1 or v2."""
    value = finding.get("prior_note_classification")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        classification = value.get("classification")
        return classification if isinstance(classification, str) else None
    fallback = finding.get("candidate_classification")
    return fallback if isinstance(fallback, str) and fallback.strip() else None


def build_batch(
    audit: dict[str, Any],
    units_payload: dict[str, Any],
    batch_id: str,
    *,
    require_role_evidence: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    unit_index = unique_unit_index(units_payload["units"])
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
        if len(stable_keys) != len(set(stable_keys)):
            raise ValueError(f"Duplicate audited occurrence for whole unit: {unit_id}")
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
        reason_codes = {exclusion_reason_code(finding) for finding in findings}
        if None in reason_codes:
            raise ValueError(f"Whole unit has a missing exclusion reason code: {unit_id}")
        sorted_reason_codes = sorted(reason_codes)
        reason = (
            sorted_reason_codes[0]
            if len(sorted_reason_codes) == 1
            else "MULTIPLE_RESOLVED_EXCLUSION_REASONS"
        )
        notes = list(dict.fromkeys(finding["reason"] for finding in findings))
        role_evidence = [finding.get("occurrence_evidence") for finding in findings]
        strict_role_evidence = any(item is not None for item in role_evidence)
        if strict_role_evidence:
            if any(
                finding.get("role_metadata_verified") is not True
                or not isinstance(finding.get("occurrence_evidence"), dict)
                or not finding["occurrence_evidence"].get("evidence_fingerprint")
                for finding in findings
            ):
                raise ValueError(f"Whole-unit exclusion has unverified role evidence: {unit_id}")
        elif require_role_evidence:
            raise ValueError(f"Whole-unit exclusion is missing role evidence: {unit_id}")
        requires_parser_key = bool(set(sorted_reason_codes) & TEMPLATE_KEY_REASONS)
        if requires_parser_key and strict_role_evidence and any(
            finding["occurrence_evidence"].get("literal_role") != ROLE_BINDING_KEY
            or finding["occurrence_evidence"].get("role_confidence") != PARSER_PROVEN
            for finding in findings
        ):
            raise ValueError(f"Template-key exclusion lacks parser-proven keys: {unit_id}")
        entries.append(
            {
                "translation_unit": unit_id,
                "english": unit["english"],
                "review_status": "NOT_APPLICABLE",
                "reason": reason,
                "reason_codes": sorted_reason_codes,
                "stable_keys": stable_keys,
                "notes": notes,
                "unit_role_gate": findings[0].get("unit_role_gate"),
                "requires_parser_proven_binding": requires_parser_key,
                "occurrence_evidence": sorted(
                    role_evidence,
                    key=lambda item: item.get("stable_key", "") if isinstance(item, dict) else "",
                ) if strict_role_evidence else [],
            }
        )
    if not entries:
        raise ValueError("Audit produced no whole-unit exclusions")
    return (
        {
            "schema_version": 2 if require_role_evidence else 1,
            "role_evidence_required": require_role_evidence,
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
    batch, skipped_partial = build_batch(
        audit, units_payload, args.batch_id, require_role_evidence=True
    )
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
