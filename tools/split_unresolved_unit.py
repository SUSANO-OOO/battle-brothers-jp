#!/usr/bin/env python3
"""Split one unresolved deduplicated unit into unresolved and resolved-exclusion contexts."""

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
    GATE_MANUAL_REVIEW,
    enrich_occurrence_role,
    occurrence_evidence,
    role_summary,
    source_binding_key_proof,
)
from ledger_integrity import (  # noqa: E402
    canonical_indexes,
    unique_occurrence_index,
    unique_unit_index,
)


def variant_id(original_id: str, stable_keys: list[str], resolution: str) -> str:
    basis = "\x1f".join((original_id, resolution, *sorted(stable_keys)))
    return f"unitctx:{hashlib.sha256(basis.encode('utf-8')).hexdigest().upper()[:24]}"


def apply_splits(
    plan: dict[str, Any],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
    *,
    enforce_role_evidence: bool = True,
) -> dict[str, Any]:
    if enforce_role_evidence and (
        plan.get("schema_version") != 2
        or plan.get("role_evidence_required") is not True
    ):
        raise ValueError("Split plan must require schema-v2 source-bound role evidence")
    if enforce_role_evidence:
        occurrence_index, unit_index = canonical_indexes(ledger, units_payload)
    else:
        occurrence_index = unique_occurrence_index(ledger["entries"])
        unit_index = unique_unit_index(units_payload["units"])
    created: list[dict[str, Any]] = []
    removed: set[str] = set()
    reason_counts: Counter[str] = Counter()
    excluded_occurrences = 0
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] = {}

    for split in plan.get("splits", []):
        original_id = split.get("original_unit")
        if original_id not in unit_index:
            raise ValueError(f"Unknown original unit: {original_id}")
        original = unit_index[original_id]
        if original.get("status") != "UNTRANSLATED" or original.get("review_status") != "NOT_REVIEWED":
            raise ValueError(f"Only unresolved units can be split: {original_id}")
        variants = split.get("variants", [])
        if len(variants) < 2:
            raise ValueError(f"Context split requires at least two variants: {original_id}")
        expected = set(original["occurrences"])
        assigned: list[str] = []

        for variant in variants:
            stable_keys = variant.get("stable_keys", [])
            if not stable_keys or len(stable_keys) != len(set(stable_keys)):
                raise ValueError(f"Invalid stable key list in split: {original_id}")
            unknown = set(stable_keys) - expected
            if unknown:
                raise ValueError(f"Unknown stable keys in split {original_id}: {sorted(unknown)}")
            assigned.extend(stable_keys)
            occurrences = [occurrence_index[key] for key in stable_keys]
            resolution = variant.get("resolution")
            notes = variant.get("notes", [])
            if isinstance(notes, str):
                notes = [notes]
            if not isinstance(notes, list) or not all(isinstance(note, str) for note in notes):
                raise ValueError(f"Invalid notes in split: {original_id}")
            reviewed_evidence = variant.get("occurrence_evidence", [])
            if enforce_role_evidence and not reviewed_evidence:
                raise ValueError(f"Split variant is missing mandatory role evidence: {original_id}")
            enriched_occurrences = occurrences
            if reviewed_evidence:
                if not isinstance(reviewed_evidence, list):
                    raise ValueError(f"Invalid role evidence in split: {original_id}")
                evidence_index = {
                    item.get("stable_key"): item
                    for item in reviewed_evidence
                    if isinstance(item, dict)
                }
                if len(evidence_index) != len(reviewed_evidence) or set(evidence_index) != set(stable_keys):
                    raise ValueError(f"Role evidence must exactly cover split variant: {original_id}")
                module_roots = ledger.get("module_roots", {})
                if not module_roots:
                    raise ValueError(f"Role-evidence split requires module source roots: {original_id}")
                enriched_occurrences = [
                    enrich_occurrence_role(
                        occurrence,
                        module_roots,
                        analysis_cache,
                        force_reanalysis=True,
                    )
                    for occurrence in occurrences
                ]
                for enriched in enriched_occurrences:
                    if evidence_index[enriched["stable_key"]] != occurrence_evidence(enriched):
                        raise ValueError(
                            f"Role/source evidence drift in split {original_id}: {enriched['stable_key']}"
                        )
                if resolution == "RESOLVED_EXCLUSION" and any(
                    not source_binding_key_proof(enriched, module_roots, analysis_cache)
                    for enriched in enriched_occurrences
                ):
                    raise ValueError(f"Excluded split variant is not proven binding keys: {original_id}")

            if resolution == "UNTRANSLATED":
                if variant.get("review_status") != "NOT_REVIEWED":
                    raise ValueError(f"Untranslated variants must be NOT_REVIEWED: {original_id}")
                new_id = variant_id(original_id, stable_keys, resolution)
                for occurrence in occurrences:
                    occurrence["translation_unit"] = new_id
                    occurrence["japanese"] = ""
                    occurrence["status"] = "UNTRANSLATED"
                    occurrence["review_status"] = "NOT_REVIEWED"
                    occurrence["notes"] = list(notes)
                created.append(
                    {
                        "translation_unit": new_id,
                        "english": original["english"],
                        "japanese": "",
                        "mode": original["mode"],
                        "placeholder_signature": original["placeholder_signature"],
                        "status": "UNTRANSLATED",
                        "review_status": "NOT_REVIEWED",
                        "occurrence_count": len(occurrences),
                        "modules": sorted({entry["module"] for entry in occurrences}),
                        "occurrences": stable_keys,
                        "notes": list(notes),
                        "split_from": original_id,
                        "role_gate": variant.get(
                            "role_gate_after_review", GATE_MANUAL_REVIEW
                        ),
                        "role_summary": role_summary(enriched_occurrences),
                    }
                )
            elif resolution == "RESOLVED_EXCLUSION":
                if variant.get("review_status") != "NOT_APPLICABLE":
                    raise ValueError(f"Excluded variants must be NOT_APPLICABLE: {original_id}")
                reason = variant.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError(f"Excluded variants require a reason: {original_id}")
                reason = reason.strip()
                for occurrence in occurrences:
                    occurrence.pop("translation_unit", None)
                    occurrence["japanese"] = ""
                    occurrence["status"] = "RESOLVED_EXCLUSION"
                    occurrence["review_status"] = "NOT_APPLICABLE"
                    occurrence["notes"] = list(dict.fromkeys([reason, *notes]))
                    reason_counts[reason] += 1
                    excluded_occurrences += 1
            else:
                raise ValueError(f"Unsupported resolution in split {original_id}: {resolution}")

        if set(assigned) != expected or len(assigned) != len(set(assigned)):
            raise ValueError(f"Variants must partition every occurrence exactly once: {original_id}")
        removed.add(original_id)

    units_payload["units"] = sorted(
        [unit for unit in units_payload["units"] if unit["translation_unit"] not in removed] + created,
        key=lambda unit: (unit["modules"], unit["english"], unit["translation_unit"]),
    )
    stored_reasons = Counter(
        ledger.setdefault("classification", {}).get("resolved_exclusion_reasons", {})
    )
    stored_reasons.update(reason_counts)
    ledger["classification"]["resolved_exclusion_reasons"] = dict(sorted(stored_reasons.items()))
    return {
        "removed_units": len(removed),
        "created_untranslated_units": len(created),
        "excluded_occurrences": excluded_occurrences,
        "reason_counts": dict(sorted(reason_counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    plan_path = (repo / args.plan).resolve()
    ledger_path = (repo / args.ledger).resolve()
    units_path = (repo / args.units).resolve()
    if any(work not in path.parents for path in (plan_path, ledger_path, units_path)):
        raise SystemExit("ERROR: split plan and canonical ledger files must remain below ignored work/")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    result = apply_splits(plan, ledger, units_payload)
    if args.dry_run:
        print(json.dumps({"plan_id": plan.get("plan_id"), **result, "dry_run": True}, indent=2))
        return 0

    sys.path.insert(0, str(repo / "tools"))
    from apply_exclusion_batch import sha256, update_coverage

    applied_at = datetime.now(tz=timezone.utc).isoformat()
    metadata = {"plan_id": plan.get("plan_id"), "applied_at_utc": applied_at}
    ledger["last_unresolved_context_split"] = metadata
    units_payload["last_unresolved_context_split"] = metadata
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
                "plan_id": plan.get("plan_id"),
                **result,
                "ledger_sha256": sha256(ledger_path),
                "units_sha256": sha256(units_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
