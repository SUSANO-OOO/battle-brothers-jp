#!/usr/bin/env python3
"""Expand reviewed exclusion candidates into every occurrence of each deduplicated unit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from squirrel_literal_roles import (  # noqa: E402
    GATE_MANUAL_REVIEW,
    enrich_occurrence_role,
    occurrence_evidence,
    occurrence_role_gate,
    source_structural_proof,
)
from ledger_integrity import (  # noqa: E402
    canonical_indexes,
    unique_occurrence_index,
    unique_unit_index,
)


def build_audit_batch(
    review_batch: dict[str, Any],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
    *,
    require_role_evidence: bool = False,
) -> dict[str, Any]:
    candidates = review_batch.get("review_metadata", {}).get("excluded_entries", [])
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Review batch has no review_metadata.excluded_entries")
    candidate_index: dict[str, dict[str, Any]] = {}
    already_resolved = []
    if require_role_evidence:
        occurrence_index, unit_index = canonical_indexes(ledger, units_payload)
    else:
        occurrence_index = unique_occurrence_index(ledger["entries"])
        unit_index = unique_unit_index(units_payload["units"])
    for candidate in candidates:
        unit_id = candidate.get("translation_unit")
        if not isinstance(unit_id, str):
            raise ValueError("Excluded candidate has no translation_unit")
        original_unit_id = unit_id
        if unit_id not in unit_index:
            stable_key = candidate.get("stable_key")
            occurrence = occurrence_index.get(stable_key)
            if occurrence is None:
                raise ValueError(f"Excluded candidate references unknown unit and occurrence: {unit_id}")
            if occurrence.get("status") == "RESOLVED_EXCLUSION":
                already_resolved.append(
                    {
                        "original_translation_unit": unit_id,
                        "stable_key": stable_key,
                        "current_status": "RESOLVED_EXCLUSION",
                        "current_notes": occurrence.get("notes", []),
                    }
                )
                continue
            current_unit = occurrence.get("translation_unit")
            if current_unit not in unit_index:
                raise ValueError(f"Excluded candidate cannot be mapped to a current unit: {unit_id}")
            unit_id = current_unit
            candidate = dict(candidate)
            candidate["translation_unit"] = unit_id
            candidate["split_from"] = original_unit_id
        if unit_id in candidate_index:
            raise ValueError(f"Duplicate excluded candidate: {unit_id}")
        candidate_index[unit_id] = candidate

    findings = []
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for unit_id, candidate in sorted(candidate_index.items()):
        unit = unit_index[unit_id]
        if unit.get("status") != "UNTRANSLATED":
            raise ValueError(f"Excluded candidate is no longer unresolved: {unit_id}")
        raw_occurrences = [occurrence_index[key] for key in unit["occurrences"]]
        if require_role_evidence:
            module_roots = ledger.get("module_roots", {})
            if not module_roots:
                raise ValueError("strict occurrence audit requires module source roots")
            occurrences = [
                enrich_occurrence_role(occurrence, module_roots, analysis_cache)
                for occurrence in raw_occurrences
            ]
            role_gate = occurrence_role_gate(
                occurrences,
                lambda occurrence: source_structural_proof(
                    occurrence, module_roots, analysis_cache
                ),
            )
        else:
            occurrences = raw_occurrences
            role_gate = unit.get("role_gate", GATE_MANUAL_REVIEW)
        for occurrence in occurrences:
            stable_key = occurrence["stable_key"]
            evidence = occurrence_evidence(occurrence)
            findings.append(
                {
                    "stable_key": stable_key,
                    "translation_unit": unit_id,
                    "module": occurrence["module"],
                    "english": unit["english"],
                    "source": occurrence["source"],
                    "context": occurrence["context"],
                    "channel": occurrence["channel"],
                    "mode": occurrence["mode"],
                    "source_code": occurrence.get("source_code", []),
                    "candidate_classification": candidate.get("classification"),
                    "candidate_reason": candidate.get("reason"),
                    "unit_role_gate": role_gate,
                    "occurrence_evidence": evidence,
                    "role_metadata_verified": False,
                    "classification": "AUDIT_REQUIRED",
                    "reason": "",
                    "source_evidence": {"verified": False},
                }
            )
    return {
        "schema_version": 2 if require_role_evidence else 1,
        "role_evidence_required": require_role_evidence,
        "audit_id": f"{review_batch.get('batch_id', 'unknown')}-occurrence-audit",
        "source_review_batch": review_batch.get("batch_id"),
        "candidate_units": len(candidate_index),
        "occurrence_count": len(findings),
        "already_resolved_candidates": already_resolved,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-batch", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    paths = [(repo / value).resolve() for value in (args.review_batch, args.output, args.ledger, args.units)]
    if any(work not in path.parents for path in paths):
        raise SystemExit("ERROR: review, audit, and canonical ledger data must remain below ignored work/")
    review_path, output_path, ledger_path, units_path = paths
    review = json.loads(review_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    units = json.loads(units_path.read_text(encoding="utf-8"))
    payload = build_audit_batch(review, ledger, units, require_role_evidence=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "audit_id": payload["audit_id"],
                "candidate_units": payload["candidate_units"],
                "occurrences": payload["occurrence_count"],
                "already_resolved_candidates": len(payload["already_resolved_candidates"]),
                "output": str(output_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
