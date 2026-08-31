#!/usr/bin/env python3
"""Create a deterministic untranslated-unit batch for one reviewed category."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from squirrel_literal_roles import (  # noqa: E402
    GATE_AUTO_EXCLUDE,
    GATE_MANUAL_REVIEW,
    GATE_REVIEW_REQUIRED,
    enrich_occurrence_role,
    occurrence_evidence,
    occurrence_role_gate,
    source_structural_proof,
)
from ledger_integrity import canonical_indexes, unique_occurrence_index  # noqa: E402


def assigned_unit_ids(payload: dict[str, Any]) -> set[str]:
    """Collect units from translation batches, audits, and review metadata."""
    containers = [payload.get("entries", []), payload.get("findings", [])]
    metadata = payload.get("review_metadata", {})
    if isinstance(metadata, dict):
        containers.append(metadata.get("excluded_entries", []))
    return {
        entry["translation_unit"]
        for entries in containers
        if isinstance(entries, list)
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("translation_unit"), str)
    }


def select_entries(
    units_payload: dict[str, Any],
    ledger: dict[str, Any],
    *,
    module: str | None,
    source_pattern: re.Pattern[str] | None,
    channel: str | None,
    mode: str | None,
    limit: int,
    excluded_unit_ids: set[str] | None = None,
    require_role_evidence: bool = False,
) -> list[dict[str, Any]]:
    if require_role_evidence:
        occurrence_index, _ = canonical_indexes(ledger, units_payload)
    else:
        occurrence_index = unique_occurrence_index(ledger["entries"])
    selected = []
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] = {}
    excluded_unit_ids = excluded_unit_ids or set()
    for unit in units_payload["units"]:
        if unit.get("status") != "UNTRANSLATED":
            continue
        if unit.get("translation_unit") in excluded_unit_ids:
            continue
        all_occurrences = [occurrence_index[key] for key in unit["occurrences"]]
        if require_role_evidence:
            module_roots = ledger.get("module_roots", {})
            if not module_roots:
                raise ValueError("strict category selection requires module source roots")
            all_occurrences = [
                enrich_occurrence_role(occurrence, module_roots, analysis_cache)
                for occurrence in all_occurrences
            ]
            role_gate = occurrence_role_gate(
                all_occurrences,
                lambda occurrence: source_structural_proof(
                    occurrence, module_roots, analysis_cache
                ),
            )
        else:
            role_gate = unit.get("role_gate", GATE_MANUAL_REVIEW)
        if role_gate in {GATE_AUTO_EXCLUDE, GATE_REVIEW_REQUIRED}:
            continue
        candidates = [
            occurrence
            for occurrence in all_occurrences
            if (module is None or occurrence["module"] == module)
            and (source_pattern is None or source_pattern.search(occurrence["source"]))
            and (channel is None or occurrence["channel"] == channel)
            and (mode is None or occurrence["mode"] == mode)
        ]
        if not candidates:
            continue
        occurrence = sorted(
            candidates,
            key=lambda item: (item["module"], item["source"], item["context"], item["stable_key"]),
        )[0]
        selected.append(
            {
                "translation_unit": unit["translation_unit"],
                "stable_key": occurrence["stable_key"],
                "english": unit["english"],
                "japanese": "",
                "source": occurrence["source"],
                "context": occurrence["context"],
                "channel": occurrence["channel"],
                "mode": occurrence["mode"],
                "source_code": occurrence.get("source_code", []),
                "placeholder_signature": unit["placeholder_signature"],
                "unit_role_gate": role_gate,
                "occurrence_evidence": [
                    occurrence_evidence(item)
                    for item in sorted(
                        all_occurrences,
                        key=lambda item: (
                            item["module"], item["source"], item["context"], item["stable_key"]
                        ),
                    )
                ],
                "review_status": "DRAFT_INDEPENDENT_REVIEW_REQUIRED",
                "notes": [],
            }
        )
        if len(selected) >= limit:
            break
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--module")
    parser.add_argument("--source-regex")
    parser.add_argument("--channel")
    parser.add_argument("--mode", choices=("literal", "pattern"))
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--exclude-batch",
        action="append",
        default=[],
        help="Ignored work/ batch whose translation_unit IDs must not be selected; repeatable.",
    )
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    args = parser.parse_args()
    if args.limit <= 0:
        raise SystemExit("ERROR: limit must be positive")
    repo = Path(__file__).resolve().parents[1]
    work = (repo / "work").resolve()
    paths = [
        (repo / value).resolve()
        for value in (args.output, args.ledger, args.units, *args.exclude_batch)
    ]
    if any(work not in path.parents for path in paths):
        raise SystemExit("ERROR: category batches and canonical ledgers must remain below ignored work/")
    output, ledger_path, units_path = paths[:3]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    excluded_unit_ids: set[str] = set()
    for batch_path in paths[3:]:
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        excluded_unit_ids.update(assigned_unit_ids(batch))
    source_pattern = re.compile(args.source_regex) if args.source_regex else None
    entries = select_entries(
        units_payload,
        ledger,
        module=args.module,
        source_pattern=source_pattern,
        channel=args.channel,
        mode=args.mode,
        limit=args.limit,
        excluded_unit_ids=excluded_unit_ids,
        require_role_evidence=True,
    )
    if not entries:
        raise SystemExit("ERROR: no untranslated units matched the category filter")
    payload = {
        "schema_version": 2,
        "role_evidence_required": True,
        "batch_id": args.batch_id,
        "installed_snapshot_id": json.loads((repo / "reports" / "translation-coverage.json").read_text(encoding="utf-8"))["installed_snapshot_id"],
        "filters": {
            "module": args.module,
            "source_regex": args.source_regex,
            "channel": args.channel,
            "mode": args.mode,
            "exclude_batches": args.exclude_batch,
            "excluded_unit_count": len(excluded_unit_ids),
        },
        "entry_count": len(entries),
        "entries": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"batch_id": args.batch_id, "entries": len(entries), "output": str(output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
