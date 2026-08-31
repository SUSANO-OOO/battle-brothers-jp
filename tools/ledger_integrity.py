#!/usr/bin/env python3
"""Fail-closed canonical ledger/unit indexing and membership invariants."""

from __future__ import annotations

from typing import Any


def unique_occurrence_index(entries: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(entries, list):
        raise ValueError("Canonical ledger entries must be a list")
    result: dict[str, dict[str, Any]] = {}
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Canonical ledger entry {position} is not an object")
        stable_key = entry.get("stable_key")
        if not isinstance(stable_key, str) or not stable_key:
            raise ValueError(f"Canonical ledger entry {position} has no stable_key")
        if stable_key in result:
            raise ValueError(f"Duplicate canonical stable_key: {stable_key}")
        result[stable_key] = entry
    return result


def unique_unit_index(units: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(units, list):
        raise ValueError("Canonical translation units must be a list")
    result: dict[str, dict[str, Any]] = {}
    for position, unit in enumerate(units):
        if not isinstance(unit, dict):
            raise ValueError(f"Canonical translation unit {position} is not an object")
        unit_id = unit.get("translation_unit")
        if not isinstance(unit_id, str) or not unit_id:
            raise ValueError(f"Canonical translation unit {position} has no ID")
        if unit_id in result:
            raise ValueError(f"Duplicate canonical translation_unit: {unit_id}")
        occurrences = unit.get("occurrences")
        if not isinstance(occurrences, list) or not all(
            isinstance(stable_key, str) and stable_key for stable_key in occurrences
        ):
            raise ValueError(f"Canonical unit has an invalid occurrence list: {unit_id}")
        if len(occurrences) != len(set(occurrences)):
            raise ValueError(f"Duplicate occurrence ID in canonical unit: {unit_id}")
        result[unit_id] = unit
    return result


def validate_unit_membership(
    unit_id: str,
    unit: dict[str, Any],
    occurrence_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    occurrences = []
    for stable_key in unit.get("occurrences", []):
        occurrence = occurrence_index.get(stable_key)
        if occurrence is None:
            raise ValueError(f"Canonical unit references unknown occurrence: {unit_id}: {stable_key}")
        if occurrence.get("translation_unit") != unit_id:
            raise ValueError(
                f"Canonical occurrence translation-unit mismatch: {stable_key}: "
                f"expected {unit_id}, got {occurrence.get('translation_unit')}"
            )
        occurrences.append(occurrence)
    return occurrences


def canonical_indexes(
    ledger: dict[str, Any], units_payload: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    occurrence_index = unique_occurrence_index(ledger.get("entries"))
    unit_index = unique_unit_index(units_payload.get("units"))
    for unit_id, unit in unit_index.items():
        validate_unit_membership(unit_id, unit, occurrence_index)
    return occurrence_index, unit_index
