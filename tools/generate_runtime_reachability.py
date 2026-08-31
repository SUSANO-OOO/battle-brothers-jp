#!/usr/bin/env python3
"""Map every pre-migration Rosetta-reachable unit to a JP-owned boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SOURCE_AUDIT_SHA256 = "6BD64E08ED9DAA0034889AF9CEFA517F1349C3C435C084998B2981726010C3CD"
EXPECTED_UNIT_COUNT = 181

ROUTES: dict[str, dict[str, str]] = {
    "ROSETTA_SKILL_GETTER": {
        "boundary": "BBJP_DISPLAY_SCOPED_SKILL_GETTER",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": 'hookTree("scripts/skills/skill"',
    },
    "LEGENDS_EFFECT_DEF_TO_SKILL_GETTER": {
        "boundary": "BBJP_DISPLAY_SCOPED_SKILL_GETTER",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": 'hookTree("scripts/skills/skill"',
    },
    "VANILLA_PERK_CONST_TO_SKILL_GETTER": {
        "boundary": "BBJP_DISPLAY_SCOPED_SKILL_GETTER",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": 'hookTree("scripts/skills/skill"',
    },
    "LEGENDS_ACTIVE_DEF_TO_SKILL_GETTER": {
        "boundary": "BBJP_DISPLAY_SCOPED_SKILL_GETTER",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": 'hookTree("scripts/skills/skill"',
    },
    "LEGENDS_PERK_NAME_CONST_TO_SKILL_GETTER": {
        "boundary": "BBJP_DISPLAY_SCOPED_SKILL_GETTER",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": 'hookTree("scripts/skills/skill"',
    },
    "ROSETTA_COMPLETED_TOOLTIP_TEXT": {
        "boundary": "BBJP_TOOLTIP_RETURN_CLONE",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": "cloneTranslatedTooltip",
    },
    "TACTICAL_ENTITY_NAME_IN_COMPLETED_TOOLTIP_TEXT": {
        "boundary": "BBJP_TOOLTIP_RETURN_CLONE",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": "cloneTranslatedTooltip",
    },
    "ROSETTA_ITEM_GETTER": {
        "boundary": "BBJP_DISPLAY_SCOPED_ITEM_GETTER",
        "file": "src/battle_brothers_jp/hooks/semantic_name_safety.nut",
        "token": 'hookTree("scripts/items/item"',
    },
    "VANILLA_ITEM_NAME_TO_ITEM_GETTER": {
        "boundary": "BBJP_DISPLAY_SCOPED_ITEM_GETTER",
        "file": "src/battle_brothers_jp/hooks/semantic_name_safety.nut",
        "token": 'hookTree("scripts/items/item"',
    },
    "PROJECT_LEGENDS_CRAFTING_QUERY_LOAD": {
        "boundary": "BBJP_LEGENDS_CAMP_QUERY_LOAD",
        "file": "src/battle_brothers_jp/hooks/ui_boundaries.nut",
        "token": "camp_crafting_dialog_module",
    },
    "ROSETTA_LOADING_SCREEN_TEXT": {
        "boundary": "BBJP_LOADING_SCREEN_RETURN_CLONE",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": 'hook("scripts/ui/screens/loading/loading_screen"',
    },
    "ROSETTA_MSU_SETTINGS_UI_DATA": {
        "boundary": "BBJP_MSU_SETTINGS_UI_DATA_CLONE",
        "file": "src/battle_brothers_jp/hooks/msu_display_boundaries.nut",
        "token": "hookGetUIData(::MSU.Class.SettingsPage",
    },
    "ROSETTA_MSU_TOOLTIP_TEXT": {
        "boundary": "BBJP_MSU_TOOLTIP_RETURN_CLONE",
        "file": "src/battle_brothers_jp/hooks/msu_display_boundaries.nut",
        "token": "onQueryMSUTooltipData",
    },
    "ROSETTA_COMBAT_RESULT_TITLE": {
        "boundary": "BBJP_COMBAT_RESULT_RETURN_CLONE",
        "file": "src/battle_brothers_jp/hooks/runtime_display_boundaries.nut",
        "token": "onQueryCombatInformation",
    },
    "PROJECT_AMBITION_GET_UI_TEXT": {
        "boundary": "BBJP_AMBITION_UI_TEXT",
        "file": "src/battle_brothers_jp/hooks/ui_boundaries.nut",
        "token": 'hookTree("scripts/ambitions/ambition"',
    },
    "ROSETTA_TEMPLATE_BEFORE_PERCENT_SUBSTITUTION": {
        "boundary": "BBJP_TEMPLATE_BEFORE_PERCENT_SUBSTITUTION",
        "file": "src/battle_brothers_jp/hooks/event_variable_boundaries.nut",
        "token": "::buildTextFromTemplate = function",
    },
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    source = repo / "work" / "review_batches" / "literal_reachability_audit_001.json"
    source_bytes = source.read_bytes()
    if sha256(source_bytes) != SOURCE_AUDIT_SHA256:
        raise SystemExit("ERROR: literal reachability source audit hash changed")
    audit = json.loads(source_bytes.decode("utf-8"))

    implementation_hashes: dict[str, str] = {}
    for route in ROUTES.values():
        path = repo / route["file"]
        text = path.read_text(encoding="utf-8")
        if route["token"] not in text:
            raise SystemExit(f"ERROR: missing runtime reachability token: {route}")
        implementation_hashes[route["file"]] = sha256(path.read_bytes())

    units: list[dict[str, Any]] = []
    missing_boundaries: set[str] = set()
    for unit in audit.get("units", []):
        if unit.get("classification") != "REACHABLE_ROSETTA":
            continue
        routes = []
        for occurrence in unit.get("occurrences", []):
            if occurrence.get("state") != "REACHABLE_ROSETTA":
                continue
            old_boundary = occurrence.get("boundary")
            if old_boundary not in ROUTES:
                missing_boundaries.add(str(old_boundary))
                continue
            route = ROUTES[old_boundary]
            routes.append({
                "stable_key": occurrence["stable_key"],
                "module": occurrence["module"],
                "source": occurrence["source"],
                "context": occurrence["context"],
                "pre_migration_boundary": old_boundary,
                "current_boundary": route["boundary"],
                "implementation_file": route["file"],
                "status": "STATICALLY_REACHABLE_RUNTIME_NOT_TESTED",
            })
        if not routes:
            raise SystemExit(f"ERROR: Rosetta-classified unit has no current routes: {unit.get('translation_unit')}")
        units.append({
            "translation_unit": unit["translation_unit"],
            "english": unit["english"],
            "routes": routes,
            "status": "STATICALLY_REACHABLE_RUNTIME_NOT_TESTED",
        })

    if missing_boundaries:
        raise SystemExit(f"ERROR: unmapped pre-migration boundaries: {sorted(missing_boundaries)}")
    if len(units) != EXPECTED_UNIT_COUNT:
        raise SystemExit(f"ERROR: expected {EXPECTED_UNIT_COUNT} units, got {len(units)}")

    payload = {
        "schema_version": 1,
        "generator": "tools/generate_runtime_reachability.py",
        "installed_snapshot_id": "BBJP-CF88150E7B355ECD32D9",
        "source_audit": "work/review_batches/literal_reachability_audit_001.json",
        "source_audit_sha256": SOURCE_AUDIT_SHA256,
        "pre_migration_classification": "REACHABLE_ROSETTA",
        "current_runtime": "BattleBrothersJP.Runtime/v1",
        "unit_count": len(units),
        "route_count": sum(len(unit["routes"]) for unit in units),
        "unresolved_count": 0,
        "runtime_game_qa": "NOT_TESTED",
        "implementation_sha256": dict(sorted(implementation_hashes.items())),
        "units": units,
    }
    output = repo / "reports" / "runtime-reachability-map.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("unit_count", "route_count", "unresolved_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
