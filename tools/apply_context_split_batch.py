#!/usr/bin/env python3
"""Atomically apply one audited exact-stable-key display/exclusion context split.

This is intentionally not a generic translation-unit applier.  Every operation
must be backed by an audit whose canonical input hashes and per-occurrence
display/internal partition still match the ledger exactly.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

if os.name == "nt":  # pragma: win32 cover - exercised by Windows CI/local QA
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _KERNEL32.CreateFileW.restype = wintypes.HANDLE
    _KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL32.CloseHandle.restype = wintypes.BOOL

    _GENERIC_READ = 0x80000000
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_DELETE = 0x00000004
    _OPEN_EXISTING = 3
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


TOKEN_PATTERNS = {
    "percent_vars": re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%"),
    "printf": re.compile(r"%(?:\d+\$)?[sdif](?![A-Za-z0-9_]*%)"),
    "bbcode_tags": re.compile(r"\[[^\]\r\n]+\]"),
    "captures": re.compile(r"<[^>\r\n]+>"),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def signature(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        name: pattern.findall(text) for name, pattern in TOKEN_PATTERNS.items()
    }
    result.update(
        {
            "newlines": text.count("\n"),
            "brace_open": text.count("{"),
            "brace_close": text.count("}"),
            "template_pipes": text.count("|") if "{" in text or "}" in text else 0,
        }
    )
    return result


def variant_id(original_id: str, stable_keys: list[str]) -> str:
    """Preserve the deterministic ID produced by the audited unresolved split."""
    basis = "\x1f".join((original_id, "UNTRANSLATED", *sorted(stable_keys)))
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest().upper()[:24]
    return f"unitctx:{digest}"


def json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def normalize_notes(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(note, str) for note in value):
        return list(value)
    raise ValueError(f"{label} notes must be a string, a list of strings, or null")


def unique_index(items: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not items:
        raise ValueError(f"{label} must be a non-empty list")
    values = [item.get(key) if isinstance(item, dict) else None for item in items]
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError(f"{label} contains an empty or non-string {key}")
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate {key} values in {label}: {duplicates}")
    return {item[key]: item for item in items}


def is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def reject_symlink_components(path: Path, boundary: Path, label: str) -> None:
    """Reject symlinks before resolve() can hide an indirection."""
    absolute_path = path.absolute()
    absolute_boundary = boundary.absolute()
    try:
        relative = absolute_path.relative_to(absolute_boundary)
    except ValueError:
        return
    current = absolute_boundary
    if current.is_symlink():
        raise ValueError(f"{label} repository boundary is a symlink: {current}")
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label} contains a symlink component: {current}")


def repo_relative(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path is outside the repository: {path}") from exc


def resolve_declared_path(repo: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must declare a repository-relative path")
    unresolved = repo / value
    reject_symlink_components(unresolved, repo, label)
    path = unresolved.resolve()
    if not is_below(path, (repo / "work").resolve()):
        raise ValueError(f"{label} must remain below ignored work/: {path}")
    return path


def require_sha(actual: str, expected: Any, label: str) -> None:
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9A-Fa-f]{64}", expected):
        raise ValueError(f"{label} has no valid expected SHA-256")
    if actual != expected.upper():
        raise ValueError(f"{label} SHA-256 mismatch: expected={expected.upper()}, actual={actual}")


def validate_top_level_contract(
    *,
    repo: Path,
    audit: dict[str, Any],
    display_batch: dict[str, Any],
    exclusion_batch: dict[str, Any],
    source_batch: dict[str, Any],
    source_audit: dict[str, Any],
    coverage: dict[str, Any],
    paths: dict[str, Path],
    hashes: dict[str, str],
) -> None:
    if audit.get("schema_version") != 1:
        raise ValueError("Audit schema_version must be 1")
    if audit.get("canonical_application_performed") is not False:
        raise ValueError("Audit must describe a pre-canonical-application gate")
    if audit.get("actual_user_environment_write_count") != 0:
        raise ValueError("Audit reports a non-zero actual user environment write count")
    gate = audit.get("gate_b")
    if not isinstance(gate, dict) or gate.get("generic_unit_applier_allowed") is not False:
        raise ValueError("Audit does not prohibit generic mixed-unit application")
    mixed = gate.get("mixed_units")
    if not isinstance(mixed, list) or not mixed:
        raise ValueError("Audit gate_b must contain non-empty mixed_units")
    if gate.get("affected_unit_count") != len(mixed):
        raise ValueError("Audit affected_unit_count does not match mixed_units")

    snapshot = audit.get("installed_snapshot_id")
    if not isinstance(snapshot, str) or not snapshot:
        raise ValueError("Audit installed_snapshot_id is missing")
    for label, payload in (
        ("display batch", display_batch),
        ("exclusion batch", exclusion_batch),
        ("source batch", source_batch),
        ("source audit", source_audit),
    ):
        if payload.get("schema_version") != 1:
            raise ValueError(f"{label} schema_version must be 1")
        if payload.get("installed_snapshot_id") != snapshot:
            raise ValueError(f"{label} installed_snapshot_id mismatch")
        if payload.get("actual_user_environment_write_count", 0) != 0:
            raise ValueError(f"{label} reports a non-zero actual user environment write count")
    if coverage.get("installed_snapshot_id") != snapshot:
        raise ValueError("Coverage installed_snapshot_id mismatch")

    display_entries = display_batch.get("entries")
    exclusion_entries = exclusion_batch.get("entries")
    source_entries = source_batch.get("entries")
    if not isinstance(display_entries, list) or not display_entries:
        raise ValueError("Display batch entries must be non-empty")
    if not isinstance(exclusion_entries, list) or not exclusion_entries:
        raise ValueError("Exclusion batch entries must be non-empty")
    if not isinstance(source_entries, list) or not source_entries:
        raise ValueError("Source batch entries must be non-empty")
    expected_counts = (
        (display_batch, "entry_count", len(display_entries), "display batch"),
        (display_batch, "reviewed_count", len(display_entries), "display batch reviewed"),
        (exclusion_batch, "entry_count", len(exclusion_entries), "exclusion batch"),
        (source_batch, "entry_count", len(source_entries), "source batch"),
    )
    for payload, field, actual, label in expected_counts:
        if payload.get(field) != actual:
            raise ValueError(f"{label} {field} mismatch")
    if display_batch.get("unresolved_count") != 0:
        raise ValueError("Display batch still reports unresolved entries")
    if exclusion_batch.get("unresolved_count") != 0:
        raise ValueError("Exclusion batch still reports unresolved entries")
    if exclusion_batch.get("reviewed_exclusion_count") != len(exclusion_entries):
        raise ValueError("Exclusion batch reviewed_exclusion_count mismatch")
    reviewed_exclusion_occurrences = sum(
        len(entry.get("stable_keys", []))
        for entry in exclusion_entries
        if isinstance(entry, dict)
    )
    if exclusion_batch.get("canonical_occurrence_count") != reviewed_exclusion_occurrences:
        raise ValueError("Exclusion batch canonical_occurrence_count mismatch")
    if exclusion_batch.get("substitution_key_translation_count") != 0:
        raise ValueError("Exclusion batch reports translated substitution keys")

    source_audit_entries = source_audit.get("entries")
    if not isinstance(source_audit_entries, list) or not source_audit_entries:
        raise ValueError("Source audit entries must be non-empty")
    if source_audit.get("audit_id") != exclusion_batch.get("source_audit_id"):
        raise ValueError("Exclusion batch source_audit_id mismatch")
    if source_audit.get("entry_count") != len(source_audit_entries):
        raise ValueError("Source audit entry_count mismatch")
    if source_audit.get("source_root_read_only_copy") is not True:
        raise ValueError("Source audit does not identify a read-only source copy")
    if source_audit.get("validation_error_count") != 0 or source_audit.get("validation_errors") != []:
        raise ValueError("Source audit contains validation errors")
    source_audit_occurrence_count = sum(
        len(entry.get("occurrences", []))
        for entry in source_audit_entries
        if isinstance(entry, dict)
    )
    if source_audit.get("canonical_occurrence_count") != source_audit_occurrence_count:
        raise ValueError("Source audit canonical_occurrence_count mismatch")
    if source_audit.get("exact_occurrence_match_count") != source_audit_occurrence_count:
        raise ValueError("Source audit exact_occurrence_match_count mismatch")

    declared_source = display_batch.get("source_batch")
    if exclusion_batch.get("source_batch") != declared_source:
        raise ValueError("Display and exclusion batches reference different source batches")
    if repo_relative(repo, paths["source"]) != declared_source:
        raise ValueError("Resolved source batch path differs from the reviewed declaration")
    declared_source_sha = display_batch.get("source_batch_sha256")
    if exclusion_batch.get("source_batch_sha256") != declared_source_sha:
        raise ValueError("Display and exclusion source batch SHA-256 values differ")
    require_sha(hashes["source"], declared_source_sha, "source batch")
    if display_batch.get("internal_counterpart_batch") != repo_relative(repo, paths["exclusion"]):
        raise ValueError("Display batch internal counterpart path mismatch")
    if source_audit.get("source_batch") != declared_source:
        raise ValueError("Source audit references a different source batch")

    provenance = audit.get("sha256_provenance")
    if not isinstance(provenance, dict):
        raise ValueError("Audit sha256_provenance is missing")
    for label in ("display", "exclusion", "source", "source_audit"):
        rel = repo_relative(repo, paths[label])
        require_sha(hashes[label], provenance.get(rel), f"audit provenance for {rel}")

    before = gate.get("dry_run_evidence", {}).get("canonical_file_sha_before")
    if not isinstance(before, dict):
        raise ValueError("Audit canonical input SHA-256 evidence is missing")
    require_sha(hashes["ledger"], before.get("translation-ledger.json"), "canonical ledger")
    require_sha(hashes["units"], before.get("translation-units.json"), "canonical units")
    if source_audit.get("canonical_ledger_sha256") != hashes["ledger"]:
        raise ValueError("Source audit canonical ledger SHA-256 mismatch")
    if source_audit.get("canonical_units_sha256") != hashes["units"]:
        raise ValueError("Source audit canonical units SHA-256 mismatch")
    if coverage.get("detailed_ledger_sha256") != hashes["ledger"]:
        raise ValueError("Coverage ledger SHA-256 does not match the supplied canonical ledger")
    if coverage.get("translation_units_sha256") != hashes["units"]:
        raise ValueError("Coverage units SHA-256 does not match the supplied canonical units")


def validate_implementation_review_contract(
    *,
    repo: Path,
    review: dict[str, Any],
    audit: dict[str, Any],
    source_audit: dict[str, Any],
    display_batch: dict[str, Any],
    exclusion_batch: dict[str, Any],
    source_batch: dict[str, Any],
    paths: dict[str, Path],
    hashes: dict[str, str],
) -> None:
    if review.get("schema_version") != 1:
        raise ValueError("Implementation review schema_version must be 1")
    if review.get("status") != "PASS":
        raise ValueError("Implementation review status must be PASS")
    if review.get("review_scope") != "CONTEXT_SPLIT_BATCH_IMPLEMENTATION":
        raise ValueError("Implementation review scope mismatch")
    if review.get("independent_review") is not True:
        raise ValueError("Implementation review must be independent")
    if review.get("tests_status") != "PASS":
        raise ValueError("Implementation review tests_status must be PASS")
    if review.get("canonical_application_authorized") is not True:
        raise ValueError("Implementation review does not authorize canonical application")
    if review.get("canonical_application_performed") is not False:
        raise ValueError("Implementation review must precede canonical application")
    if review.get("actual_user_environment_write_count") != 0:
        raise ValueError("Implementation review reports actual user environment writes")
    snapshot = audit["installed_snapshot_id"]
    if review.get("installed_snapshot_id") != snapshot:
        raise ValueError("Implementation review installed_snapshot_id mismatch")

    authorized_targets = review.get("authorized_targets")
    if not isinstance(authorized_targets, dict):
        raise ValueError("Implementation review authorized_targets is missing")
    for label in ("ledger", "units", "coverage"):
        if authorized_targets.get(label) != repo_relative(repo, paths[label]):
            raise ValueError(f"Implementation review target path mismatch: {label}")

    inputs = review.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("Implementation review inputs are missing")
    reviewed_inputs = {
        "boundary_audit": ("audit", audit.get("audit_id")),
        "source_audit": ("source_audit", source_audit.get("audit_id")),
        "display_batch": ("display", display_batch.get("batch_id")),
        "exclusion_batch": ("exclusion", exclusion_batch.get("batch_id")),
        "source_batch": ("source", source_batch.get("batch_id")),
    }
    for review_label, (path_label, expected_id) in reviewed_inputs.items():
        item = inputs.get(review_label)
        if not isinstance(item, dict):
            raise ValueError(f"Implementation review input is missing: {review_label}")
        if item.get("path") != repo_relative(repo, paths[path_label]):
            raise ValueError(f"Implementation review input path mismatch: {review_label}")
        if item.get("id") != expected_id:
            raise ValueError(f"Implementation review input ID mismatch: {review_label}")
        if item.get("installed_snapshot_id") != snapshot:
            raise ValueError(
                f"Implementation review input snapshot mismatch: {review_label}"
            )
        require_sha(
            hashes[path_label], item.get("sha256"), f"implementation review {review_label}"
        )

    tool_item = inputs.get("tool")
    if not isinstance(tool_item, dict):
        raise ValueError("Implementation review tool input is missing")
    unresolved_tool_path = repo / "tools/apply_context_split_batch.py"
    reject_symlink_components(unresolved_tool_path, repo, "implementation review tool")
    expected_tool_path = unresolved_tool_path.resolve()
    if tool_item.get("path") != repo_relative(repo, expected_tool_path):
        raise ValueError("Implementation review tool path mismatch")
    require_sha(sha256(expected_tool_path), tool_item.get("sha256"), "implementation review tool")

    tests = inputs.get("tests")
    if not isinstance(tests, list) or not tests:
        raise ValueError("Implementation review tests input must be non-empty")
    test_paths = [item.get("path") if isinstance(item, dict) else None for item in tests]
    if len(test_paths) != len(set(test_paths)) or any(
        not isinstance(path, str) or not path for path in test_paths
    ):
        raise ValueError("Implementation review test paths are invalid or duplicated")
    required_test = "tests/test_apply_context_split_batch.py"
    if required_test not in test_paths:
        raise ValueError(f"Implementation review omits required test: {required_test}")
    for item in tests:
        unresolved_test_path = repo / item["path"]
        reject_symlink_components(unresolved_test_path, repo, "implementation review test")
        test_path = unresolved_test_path.resolve()
        if not is_below(test_path, repo) or not is_below(test_path, (repo / "tests").resolve()):
            raise ValueError(f"Implementation review test path is outside tests/: {test_path}")
        require_sha(sha256(test_path), item.get("sha256"), f"implementation review test {item['path']}")

    canonical_prehash = review.get("canonical_prehash")
    if not isinstance(canonical_prehash, dict):
        raise ValueError("Implementation review canonical_prehash is missing")
    for label in ("ledger", "units", "coverage"):
        require_sha(
            hashes[label], canonical_prehash.get(label), f"implementation review canonical {label}"
        )


def validate_implementation_review_projection(
    review: dict[str, Any], result: dict[str, Any]
) -> None:
    projection = review.get("production_dry_run")
    if not isinstance(projection, dict):
        raise ValueError("Implementation review production_dry_run is missing")
    if projection.get("status") != "PASS" or projection.get("dry_run") is not True:
        raise ValueError("Implementation review production_dry_run is not a passing dry-run")
    if projection.get("actual_user_environment_write_count") != 0:
        raise ValueError("Implementation review dry-run reports actual environment writes")
    if projection.get("canonical_write_count") != 0:
        raise ValueError("Implementation review dry-run reports canonical writes")
    fields = (
        "removed_original_units",
        "created_reviewed_display_units",
        "translated_display_occurrences",
        "excluded_occurrences",
        "reason_counts",
    )
    for field in fields:
        if projection.get(field) != result.get(field):
            raise ValueError(f"Implementation review projected {field} mismatch")
    if projection.get("ledger_sha256_before") != result.get("ledger_sha256_before"):
        raise ValueError("Implementation review projected ledger prehash mismatch")
    if projection.get("units_sha256_before") != result.get("units_sha256_before"):
        raise ValueError("Implementation review projected units prehash mismatch")


def validate_split_contract(
    *,
    audit: dict[str, Any],
    display_batch: dict[str, Any],
    exclusion_batch: dict[str, Any],
    source_batch: dict[str, Any],
    source_audit: dict[str, Any],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    occurrence_index = unique_index(ledger.get("entries"), "stable_key", "canonical ledger entries")
    unit_index = unique_index(units_payload.get("units"), "translation_unit", "canonical units")
    display_index = unique_index(display_batch.get("entries"), "translation_unit", "display batch")
    exclusion_index = unique_index(
        exclusion_batch.get("entries"), "translation_unit", "exclusion batch"
    )
    source_index = unique_index(source_batch.get("entries"), "translation_unit", "source batch")
    source_audit_unit_index = unique_index(
        source_audit.get("entries"), "translation_unit", "source audit units"
    )
    source_audit_occurrences: list[dict[str, Any]] = []
    for source_audit_entry in source_audit["entries"]:
        occurrences = source_audit_entry.get("occurrences")
        if not isinstance(occurrences, list) or not occurrences:
            raise ValueError(
                f"Source audit entry has no occurrences: {source_audit_entry['translation_unit']}"
            )
        if source_audit_entry.get("canonical_occurrence_count") != len(occurrences):
            raise ValueError(
                f"Source audit canonical_occurrence_count mismatch: "
                f"{source_audit_entry['translation_unit']}"
            )
        if source_audit_entry.get("audited_occurrence_count") != len(occurrences):
            raise ValueError(
                f"Source audit audited_occurrence_count mismatch: "
                f"{source_audit_entry['translation_unit']}"
            )
        if source_audit_entry.get("all_occurrences_exact_match") is not True:
            raise ValueError(
                f"Source audit entry is not an exact occurrence match: "
                f"{source_audit_entry['translation_unit']}"
            )
        if source_audit_entry.get("placeholder_signature_ok") is not True:
            raise ValueError(
                f"Source audit placeholder signature failed: "
                f"{source_audit_entry['translation_unit']}"
            )
        for occurrence in occurrences:
            occurrence_copy = dict(occurrence)
            occurrence_copy["translation_unit"] = source_audit_entry["translation_unit"]
            occurrence_copy["english"] = source_audit_entry.get("english")
            source_audit_occurrences.append(occurrence_copy)
    source_audit_occurrence_index = unique_index(
        source_audit_occurrences, "stable_key", "source audit occurrences"
    )
    # Duplicated reviewed keys are dangerous even when they occur in unrelated entries.
    display_keys = [entry.get("stable_key") for entry in display_batch["entries"]]
    if any(not isinstance(key, str) or not key for key in display_keys):
        raise ValueError("Display batch contains an empty or non-string stable_key")
    duplicate_display_keys = sorted(
        key for key, count in Counter(display_keys).items() if count > 1
    )
    if duplicate_display_keys:
        raise ValueError(f"Duplicate stable_key values in display batch: {duplicate_display_keys}")
    all_exclusion_keys: list[str] = []
    for entry in exclusion_batch["entries"]:
        keys = entry.get("stable_keys")
        if not isinstance(keys, list) or not keys or any(
            not isinstance(key, str) or not key for key in keys
        ):
            raise ValueError("Exclusion batch contains an invalid stable_keys list")
        all_exclusion_keys.extend(keys)
    duplicate_exclusion_keys = sorted(
        key for key, count in Counter(all_exclusion_keys).items() if count > 1
    )
    if duplicate_exclusion_keys:
        raise ValueError(
            f"Duplicate stable_key values in exclusion batch: {duplicate_exclusion_keys}"
        )

    mixed_units = audit["gate_b"]["mixed_units"]
    audit_index = unique_index(mixed_units, "translation_unit", "audit mixed units")
    if set(display_index) != set(audit_index):
        raise ValueError("Display batch must contain exactly the audited mixed original units")
    missing_exclusions = sorted(set(audit_index) - set(exclusion_index))
    if missing_exclusions:
        raise ValueError(f"Exclusion batch lacks audited mixed units: {missing_exclusions}")

    missing_sources = sorted(set(exclusion_index) - set(source_index))
    if missing_sources:
        raise ValueError(f"Source batch lacks reviewed exclusion units: {missing_sources}")
    missing_source_audits = sorted(set(exclusion_index) - set(source_audit_unit_index))
    if missing_source_audits:
        raise ValueError(
            f"Source audit lacks reviewed exclusion units: {missing_source_audits}"
        )

    validated: list[dict[str, Any]] = []
    output_ids: set[str] = set()
    for original_id in sorted(exclusion_index):
        evidence = audit_index.get(original_id)
        is_mixed = evidence is not None
        if original_id not in unit_index:
            raise ValueError(f"Unknown reviewed exclusion original unit: {original_id}")
        original = unit_index[original_id]
        if original.get("status") != "UNTRANSLATED" or original.get("review_status") != "NOT_REVIEWED":
            raise ValueError(f"Original unit is not UNTRANSLATED/NOT_REVIEWED: {original_id}")
        if original.get("japanese") != "":
            raise ValueError(f"Original unit already contains Japanese: {original_id}")
        occurrences = original.get("occurrences")
        if not isinstance(occurrences, list) or not occurrences or len(occurrences) != len(set(occurrences)):
            raise ValueError(f"Original unit occurrences are invalid: {original_id}")
        if original.get("occurrence_count") != len(occurrences):
            raise ValueError(f"Original unit occurrence_count mismatch: {original_id}")
        excluded = exclusion_index[original_id]
        excluded_keys = excluded.get("stable_keys")
        if not isinstance(excluded_keys, list) or not excluded_keys:
            raise ValueError(f"Excluded stable_keys are invalid: {original_id}")
        display = display_index.get(original_id)
        display_key = display.get("stable_key") if display is not None else None
        assigned = ([display_key] if display_key is not None else []) + excluded_keys
        if len(assigned) != len(set(assigned)) or set(assigned) != set(occurrences):
            raise ValueError(f"Display/exclusion variants do not exactly partition {original_id}")
        if is_mixed:
            if evidence.get("canonical_status") != "UNTRANSLATED/NOT_REVIEWED":
                raise ValueError(f"Audit canonical status is not unresolved: {original_id}")
            if evidence.get("english") != original.get("english"):
                raise ValueError(f"Audit English mismatch: {original_id}")
            if evidence.get("canonical_occurrences") != occurrences:
                raise ValueError(f"Audit canonical occurrence order/scope mismatch: {original_id}")
            if not isinstance(display_key, str) or not display_key:
                raise ValueError(f"Display stable_key is invalid: {original_id}")
            display_evidence = evidence.get("display")
            internal_evidence = evidence.get("internal")
            if not isinstance(display_evidence, dict) or not isinstance(internal_evidence, dict):
                raise ValueError(f"Audit variant evidence is missing: {original_id}")
            if display_evidence.get("stable_key") != display_key:
                raise ValueError(f"Audit/display stable_key mismatch: {original_id}")
            if excluded_keys != [internal_evidence.get("stable_key")]:
                raise ValueError(f"Audit/internal stable_key scope mismatch: {original_id}")
            if display_evidence.get("japanese") != display.get("japanese"):
                raise ValueError(f"Audit/display Japanese mismatch: {original_id}")
            if excluded.get("reason") != internal_evidence.get("reason"):
                raise ValueError(f"Audit/internal exclusion reason mismatch: {original_id}")
            new_id = variant_id(original_id, [display_key])
            if evidence.get("dry_run_visible_variant_id") != new_id:
                raise ValueError(f"Audited deterministic display variant ID mismatch: {original_id}")
            if new_id in unit_index or new_id in output_ids:
                raise ValueError(f"Display variant translation_unit collision: {new_id}")
            output_ids.add(new_id)
            display_occurrence = occurrence_index.get(display_key)
            if display_occurrence is None:
                raise ValueError(f"Unknown display occurrence: {display_key}")
        else:
            display_evidence = None
            internal_evidence = None
            new_id = None
            display_occurrence = None

        excluded_occurrences: list[dict[str, Any]] = []
        for key in excluded_keys:
            occurrence = occurrence_index.get(key)
            if occurrence is None:
                raise ValueError(f"Unknown excluded occurrence: {key}")
            excluded_occurrences.append(occurrence)
        canonical_occurrences = (
            [display_occurrence, *excluded_occurrences]
            if display_occurrence is not None
            else excluded_occurrences
        )
        for occurrence in canonical_occurrences:
            key = occurrence["stable_key"]
            if occurrence.get("translation_unit") != original_id:
                raise ValueError(f"Canonical reverse-reference mismatch: {key}")
            if occurrence.get("english") != original.get("english"):
                raise ValueError(f"Canonical occurrence English mismatch: {key}")
            if occurrence.get("mode") != original.get("mode"):
                raise ValueError(f"Canonical occurrence mode mismatch: {key}")
            if occurrence.get("placeholder_signature") != original.get("placeholder_signature"):
                raise ValueError(f"Canonical occurrence placeholder signature mismatch: {key}")
            if occurrence.get("status") != "UNTRANSLATED" or occurrence.get("review_status") != "NOT_REVIEWED":
                raise ValueError(f"Canonical occurrence is not unresolved: {key}")
            if occurrence.get("japanese") != "":
                raise ValueError(f"Canonical occurrence already contains Japanese: {key}")

        if signature(original["english"]) != original.get("placeholder_signature"):
            raise ValueError(f"Canonical English placeholder signature is stale: {original_id}")
        if is_mixed:
            assert display is not None and display_occurrence is not None
            assert isinstance(display_evidence, dict)
            for field in ("english", "source", "context", "channel", "mode"):
                if display.get(field) != display_occurrence.get(field):
                    raise ValueError(f"Display {field} mismatch: {display_key}")
            for field in ("source", "context"):
                if display_evidence.get(field) != display.get(field):
                    raise ValueError(f"Audit/display {field} mismatch: {display_key}")
            if display.get("review_status") != "REVIEWED":
                raise ValueError(f"Display entry is not independently REVIEWED: {original_id}")
            japanese = display.get("japanese")
            if not isinstance(japanese, str) or not japanese.strip():
                raise ValueError(f"Display Japanese is empty: {original_id}")
            recorded_signature = display.get("placeholder_signature")
            if recorded_signature != original.get("placeholder_signature"):
                raise ValueError(f"Display recorded placeholder signature mismatch: {original_id}")
            if signature(japanese) != original.get("placeholder_signature"):
                raise ValueError(f"Display Japanese placeholder signature mismatch: {original_id}")
            review_evidence = display.get("review_evidence")
            if not isinstance(review_evidence, dict):
                raise ValueError(f"Display review_evidence is missing: {original_id}")
            required_review_evidence = {
                "exact_context_split": True,
                "internal_key_translation_count": 0,
                "generic_translation_unit_apply_compatible": False,
                "required_application_boundary": "EXACT_STABLE_KEY_ONLY",
                "exact_encoded_literal_match": True,
                "actual_user_environment_write_count": 0,
            }
            for field, expected in required_review_evidence.items():
                if review_evidence.get(field) != expected:
                    raise ValueError(f"Display review evidence {field} mismatch: {original_id}")
            if review_evidence.get("source_sha256") != display_evidence.get("source_sha256"):
                raise ValueError(f"Display source SHA-256 evidence mismatch: {original_id}")
            source_fact = source_audit_occurrence_index.get(display_key)
            if source_fact is None:
                raise ValueError(f"Source audit lacks display occurrence: {display_key}")
            if source_fact.get("translation_unit") != original_id:
                raise ValueError(f"Source audit display reverse-reference mismatch: {display_key}")
            if source_fact.get("english") != original.get("english"):
                raise ValueError(f"Source audit display English mismatch: {display_key}")
            for field in ("module", "source", "context", "channel", "mode"):
                if source_fact.get(field) != display_occurrence.get(field):
                    raise ValueError(
                        f"Source audit/canonical display {field} mismatch: {display_key}"
                    )
            for field in ("source", "context", "channel", "mode"):
                if display.get(field) != display_occurrence.get(field):
                    raise ValueError(f"Display/canonical {field} mismatch: {display_key}")
            if source_fact.get("source_sha256") != review_evidence.get("source_sha256"):
                raise ValueError(
                    f"Source audit/display source_sha256 mismatch: {display_key}"
                )
            if source_fact.get("source_file_exists") is not True:
                raise ValueError(f"Source audit display source file does not exist: {display_key}")
            if source_fact.get("exact_encoded_literal_match") is not True:
                raise ValueError(
                    f"Source audit display source literal was not exactly matched: {display_key}"
                )

        if excluded.get("english") != original.get("english"):
            raise ValueError(f"Exclusion English mismatch: {original_id}")
        if excluded.get("review_status") != "NOT_APPLICABLE":
            raise ValueError(f"Exclusion is not NOT_APPLICABLE: {original_id}")
        reason = excluded.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"Exclusion reason is empty: {original_id}")
        exclusion_occurrence_evidence = excluded.get("occurrences")
        evidence_index = unique_index(
            exclusion_occurrence_evidence,
            "stable_key",
            f"exclusion occurrence evidence for {original_id}",
        )
        if set(evidence_index) != set(excluded_keys):
            raise ValueError(f"Exclusion occurrence evidence scope mismatch: {original_id}")
        source_audit_entry = source_audit_unit_index[original_id]
        if source_audit_entry.get("english") != original.get("english"):
            raise ValueError(f"Source audit English mismatch: {original_id}")
        for occurrence in excluded_occurrences:
            key = occurrence["stable_key"]
            artifact = evidence_index[key]
            source_fact = source_audit_occurrence_index.get(key)
            if source_fact is None:
                raise ValueError(f"Source audit lacks excluded occurrence: {key}")
            if source_fact.get("translation_unit") != original_id:
                raise ValueError(f"Source audit reverse-reference mismatch: {key}")
            for field in ("source", "context"):
                if artifact.get(field) != occurrence.get(field):
                    raise ValueError(f"Exclusion {field} mismatch: {key}")
            for field in ("module", "source", "context", "channel", "mode"):
                if source_fact.get(field) != occurrence.get(field):
                    raise ValueError(f"Source audit/canonical {field} mismatch: {key}")
            if source_fact.get("source") != artifact.get("source"):
                raise ValueError(f"Source audit/exclusion source mismatch: {key}")
            if source_fact.get("context") != artifact.get("context"):
                raise ValueError(f"Source audit/exclusion context mismatch: {key}")
            if source_fact.get("source_sha256") != artifact.get("source_sha256"):
                raise ValueError(f"Source audit/exclusion source_sha256 mismatch: {key}")
            if artifact.get("exact_encoded_literal_match") is not True:
                raise ValueError(f"Exclusion source literal was not exactly matched: {key}")
            if source_fact.get("source_file_exists") is not True:
                raise ValueError(f"Source audit source file does not exist: {key}")
            if source_fact.get("exact_encoded_literal_match") is not True:
                raise ValueError(f"Source audit source literal was not exactly matched: {key}")
            if is_mixed and key == internal_evidence.get("stable_key"):
                for field in ("source", "context", "source_sha256"):
                    if artifact.get(field) != internal_evidence.get(field):
                        raise ValueError(f"Audit/internal {field} mismatch: {key}")

        source_entry = source_index[original_id]
        if source_entry.get("stable_key") not in excluded_keys:
            raise ValueError(f"Source batch representative is not an excluded occurrence: {original_id}")
        representative = occurrence_index[source_entry["stable_key"]]
        for field in (
            "english",
            "source",
            "context",
            "channel",
            "mode",
            "placeholder_signature",
        ):
            if source_entry.get(field) != representative.get(field):
                raise ValueError(f"Source batch representative {field} mismatch: {original_id}")

        modules = sorted({occurrence["module"] for occurrence in canonical_occurrences})
        if original.get("modules") != modules:
            raise ValueError(f"Original unit modules mismatch: {original_id}")
        validated.append(
            {
                "original": original,
                "original_id": original_id,
                "display": display,
                "display_key": display_key,
                "display_occurrence": display_occurrence,
                "excluded": excluded,
                "excluded_keys": excluded_keys,
                "excluded_occurrences": excluded_occurrences,
                "new_id": new_id,
                "is_mixed": is_mixed,
            }
        )
    return validated


def apply_validated_splits(
    *,
    validated: list[dict[str, Any]],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
) -> dict[str, Any]:
    occurrence_index = {entry["stable_key"]: entry for entry in ledger["entries"]}
    remove_ids: set[str] = set()
    created: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    for split in validated:
        original = split["original"]
        original_id = split["original_id"]
        display = split["display"]
        display_key = split["display_key"]
        new_id = split["new_id"]
        if split["is_mixed"]:
            assert display is not None and display_key is not None and new_id is not None
            display_notes = normalize_notes(display.get("notes"), f"display {original_id}")
            visible = occurrence_index[display_key]
            visible["translation_unit"] = new_id
            visible["japanese"] = display["japanese"]
            visible["status"] = "TRANSLATED"
            visible["review_status"] = "REVIEWED"
            visible["notes"] = display_notes
            created.append(
                {
                    "translation_unit": new_id,
                    "english": original["english"],
                    "japanese": display["japanese"],
                    "mode": original["mode"],
                    "placeholder_signature": original["placeholder_signature"],
                    "status": "TRANSLATED",
                    "review_status": "REVIEWED",
                    "occurrence_count": 1,
                    "modules": [visible["module"]],
                    "occurrences": [display_key],
                    "notes": display_notes,
                    "split_from": original_id,
                }
            )

        excluded = split["excluded"]
        exclusion_notes = normalize_notes(excluded.get("notes"), f"exclusion {original_id}")
        reason = excluded["reason"].strip()
        for stable_key in split["excluded_keys"]:
            occurrence = occurrence_index[stable_key]
            occurrence.pop("translation_unit", None)
            occurrence["japanese"] = ""
            occurrence["status"] = "RESOLVED_EXCLUSION"
            occurrence["review_status"] = "NOT_APPLICABLE"
            occurrence["notes"] = list(
                dict.fromkeys([*occurrence.get("notes", []), reason, *exclusion_notes])
            )
            reason_counts[reason] += 1
        remove_ids.add(original_id)

    units_payload["units"] = sorted(
        [
            unit
            for unit in units_payload["units"]
            if unit["translation_unit"] not in remove_ids
        ]
        + created,
        key=lambda unit: (unit["modules"], unit["english"], unit["translation_unit"]),
    )
    classification = ledger.setdefault("classification", {})
    stored_reasons = Counter(classification.get("resolved_exclusion_reasons", {}))
    stored_reasons.update(reason_counts)
    classification["resolved_exclusion_reasons"] = dict(sorted(stored_reasons.items()))
    return {
        "removed_original_units": len(remove_ids),
        "created_reviewed_display_units": len(created),
        "translated_display_occurrences": len(created),
        "excluded_occurrences": sum(reason_counts.values()),
        "reason_counts": dict(sorted(reason_counts.items())),
    }


def update_coverage(
    coverage: dict[str, Any],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
    ledger_sha: str,
    units_sha: str,
    applied_at: str,
    metadata: dict[str, Any],
) -> None:
    entries = ledger["entries"]
    units = units_payload["units"]
    resolved = sum(entry["status"] == "RESOLVED_EXCLUSION" for entry in entries)
    coverage.update(
        {
            "status": "TRANSLATION_IN_PROGRESS",
            "detailed_ledger_sha256": ledger_sha,
            "translation_units_sha256": units_sha,
            "total_occurrences": len(entries),
            "resolved_exclusion_occurrences": resolved,
            "translatable_occurrences": len(entries) - resolved,
            "unique_translation_units": len(units),
            "untranslated_units": sum(unit["status"] == "UNTRANSLATED" for unit in units),
            "translated_needs_review_units": sum(
                unit["status"] == "TRANSLATED" and unit["review_status"] != "REVIEWED"
                for unit in units
            ),
            "reviewed_units": sum(
                unit["status"] == "TRANSLATED" and unit["review_status"] == "REVIEWED"
                for unit in units
            ),
            "resolved_exclusion_reasons": ledger.get("classification", {}).get(
                "resolved_exclusion_reasons", {}
            ),
            "last_context_split_batch": metadata,
            "updated_at_utc": applied_at,
        }
    )
    for module, values in coverage.get("per_module", {}).items():
        subset = [entry for entry in entries if entry["module"] == module]
        values.update(
            {
                "occurrences": len(subset),
                "resolved_exclusions": sum(
                    entry["status"] == "RESOLVED_EXCLUSION" for entry in subset
                ),
                "translatable_occurrences": sum(
                    entry["status"] != "RESOLVED_EXCLUSION" for entry in subset
                ),
                "translated_occurrences": sum(
                    entry["status"] == "TRANSLATED" for entry in subset
                ),
                "reviewed_occurrences": sum(
                    entry["status"] == "TRANSLATED" and entry["review_status"] == "REVIEWED"
                    for entry in subset
                ),
            }
        )
    coverage["release_gate"] = (
        "MET"
        if coverage["untranslated_units"] == 0
        and coverage["translated_needs_review_units"] == 0
        and not coverage.get("extraction_failures")
        else "NOT_MET"
    )


def prepare_projection(
    *,
    audit: dict[str, Any],
    display_batch: dict[str, Any],
    exclusion_batch: dict[str, Any],
    ledger: dict[str, Any],
    units_payload: dict[str, Any],
    coverage: dict[str, Any],
    validated: list[dict[str, Any]],
    input_hashes: dict[str, str],
    applied_at: str,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    projected_ledger = copy.deepcopy(ledger)
    projected_units = copy.deepcopy(units_payload)
    projected_coverage = copy.deepcopy(coverage)
    result = apply_validated_splits(
        validated=validated,
        ledger=projected_ledger,
        units_payload=projected_units,
    )
    metadata = {
        "audit_id": audit.get("audit_id"),
        "display_batch_id": display_batch.get("batch_id"),
        "exclusion_batch_id": exclusion_batch.get("batch_id"),
        "source_batch_sha256": display_batch.get("source_batch_sha256"),
        "input_sha256": {
            key: input_hashes[key]
            for key in (
                "audit",
                "source_audit",
                "display",
                "exclusion",
                "source",
                "implementation_review",
                "ledger",
                "units",
                "coverage",
            )
        },
        "applied_at_utc": applied_at,
    }
    projected_ledger["last_context_split_batch"] = metadata
    projected_units["last_context_split_batch"] = metadata
    ledger_blob = json_bytes(projected_ledger)
    ledger_sha = sha256_bytes(ledger_blob)
    projected_units["source_ledger_sha256"] = ledger_sha
    units_blob = json_bytes(projected_units)
    units_sha = sha256_bytes(units_blob)
    update_coverage(
        projected_coverage,
        projected_ledger,
        projected_units,
        ledger_sha,
        units_sha,
        applied_at,
        metadata,
    )
    coverage_blob = json_bytes(projected_coverage)
    result.update(
        {
            "ledger_sha256_before": input_hashes["ledger"],
            "units_sha256_before": input_hashes["units"],
            "ledger_sha256_after": ledger_sha,
            "units_sha256_after": units_sha,
            "coverage_sha256_after": sha256_bytes(coverage_blob),
        }
    )
    return {
        "ledger": ledger_blob,
        "units": units_blob,
        "coverage": coverage_blob,
    }, result


@contextmanager
def exclusive_commit_lock(lock_path: Path):
    """Fail closed when another context-split commit owns the exact target set."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError(f"Context-split commit lock already exists: {lock_path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()}\n")
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def same_file(left: Path, right: Path) -> bool:
    try:
        return os.path.samefile(left, right)
    except (FileNotFoundError, OSError):
        return False


def link_no_overwrite(source: Path, destination: Path) -> None:
    """Atomically create destination only when no path currently occupies it."""
    os.link(source, destination, follow_symlinks=False)


@contextmanager
def write_denying_preimage_guard(path: Path):
    """Hold a readable preimage handle that rejects writers for its lifetime.

    Windows share modes are the only portable mechanism available here that
    can both detect a writer which already owns the canonical file and prevent
    a new writer from obtaining that file object after validation.  Delete
    sharing remains enabled so the exact guarded object can be renamed to its
    private claim.  The handle stays open through install, global verification,
    rollback/success cleanup, and claim removal.

    POSIX has no equivalent mandatory share-deny contract.  There we retain an
    O_NOFOLLOW read descriptor for identity/hash checks and keep the existing
    post-claim/global fail-closed checks; Linux CI therefore remains portable
    without pretending to provide Windows share semantics.
    """
    if os.name == "nt":
        ctypes.set_last_error(0)
        raw_handle = _KERNEL32.CreateFileW(
            str(path),
            _GENERIC_READ,
            _FILE_SHARE_READ | _FILE_SHARE_DELETE,
            None,
            _OPEN_EXISTING,
            _FILE_ATTRIBUTE_NORMAL,
            None,
        )
        if raw_handle == _INVALID_HANDLE_VALUE:
            error = ctypes.get_last_error()
            raise ValueError(
                "Unable to acquire write-denying preimage guard for "
                f"{path}: WinError {error}"
            )
        try:
            descriptor = msvcrt.open_osfhandle(
                int(raw_handle), os.O_RDONLY | getattr(os, "O_BINARY", 0)
            )
        except Exception:
            _KERNEL32.CloseHandle(raw_handle)
            raise
    else:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
    handle: BinaryIO | None = None
    try:
        handle = os.fdopen(descriptor, "rb", buffering=0)
        with handle:
            yield handle
    except Exception:
        if handle is None:
            os.close(descriptor)
        raise


def sha256_open_file(handle: BinaryIO) -> str:
    """Hash the exact guarded object, independent of its current path."""
    position = handle.tell()
    digest = hashlib.sha256()
    try:
        handle.seek(0)
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        handle.seek(position)
    return digest.hexdigest().upper()


def guarded_object_matches_path(handle: BinaryIO, path: Path) -> bool:
    """Return whether path still names the object captured by handle."""
    try:
        return os.path.samestat(
            os.fstat(handle.fileno()), os.stat(path, follow_symlinks=False)
        )
    except (FileNotFoundError, OSError):
        return False


def atomic_write_group(
    payloads: dict[Path, bytes],
    expected_before: dict[Path, str],
    lock_path: Path | None = None,
) -> None:
    """Guard and claim current files, install without overwrite, then verify.

    On Windows, every canonical preimage is opened with write sharing denied
    before any target is claimed.  That detects already-open writers and blocks
    new writers to the exact file object while still allowing our claim rename.
    The guarded object, not merely its path, is hashed before and after claim
    and once more before success cleanup.  A competing destination create is
    rejected by the no-overwrite link instead of being overwritten.  Claims
    are restored only when the target still belongs to this operation;
    otherwise both the external target and captured preimage are preserved.
    """
    if not payloads or set(payloads) != set(expected_before):
        raise ValueError("Atomic write targets and expected prehash targets must match exactly")
    lock_path = lock_path or (next(iter(payloads)).parent / ".apply_context_split_batch.lock")
    staged: dict[Path, Path] = {}
    claims: dict[Path, Path] = {}
    captured_hashes: dict[Path, str] = {}
    installed: list[Path] = []
    preserved_claims: set[Path] = set()
    with exclusive_commit_lock(lock_path):
        with ExitStack() as preimage_stack:
            guards: dict[Path, BinaryIO] = {}
            try:
                # Acquire every guard before staging or claiming anything.  On
                # Windows this rejects any FILE_SHARE_DELETE-capable writer
                # already retained by another process and then denies writers
                # until success/rollback cleanup is complete.
                for target in payloads:
                    if target.is_symlink() or target.parent.is_symlink():
                        raise ValueError(f"Atomic target or its parent is a symlink: {target}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    guards[target] = preimage_stack.enter_context(
                        write_denying_preimage_guard(target)
                    )

                for target, expected in expected_before.items():
                    if not guarded_object_matches_path(guards[target], target):
                        raise ValueError(
                            f"Global guarded preimage identity mismatch: {target}"
                        )
                    require_sha(
                        sha256_open_file(guards[target]),
                        expected,
                        f"global pre-commit recheck (guarded handle) for {target.name}",
                    )
                    require_sha(
                        sha256(target), expected, f"global pre-commit recheck for {target.name}"
                    )

                for target, payload in payloads.items():
                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        prefix=f".{target.name}.",
                        suffix=".stage",
                        dir=target.parent,
                        delete=False,
                    ) as handle:
                        handle.write(payload)
                        handle.flush()
                        os.fsync(handle.fileno())
                        staged[target] = Path(handle.name)

                for target, payload in payloads.items():
                    if not guarded_object_matches_path(guards[target], target):
                        raise ValueError(
                            f"Immediate guarded pre-claim identity mismatch: {target}"
                        )
                    require_sha(
                        sha256_open_file(guards[target]),
                        expected_before[target],
                        f"immediate pre-claim recheck (guarded handle) for {target.name}",
                    )
                    require_sha(
                        sha256(target),
                        expected_before[target],
                        f"immediate pre-claim recheck for {target.name}",
                    )
                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        prefix=f".{target.name}.",
                        suffix=".claim",
                        dir=target.parent,
                        delete=False,
                    ) as handle:
                        handle.flush()
                        os.fsync(handle.fileno())
                        claim = Path(handle.name)
                    os.replace(target, claim)
                    claims[target] = claim
                    if claim.is_symlink():
                        raise ValueError(f"Captured target became a symlink during claim: {target}")
                    if not guarded_object_matches_path(guards[target], claim):
                        raise ValueError(
                            f"Claimed preimage identity mismatch for {target.name}"
                        )
                    captured_hashes[target] = sha256_open_file(guards[target])
                    require_sha(
                        captured_hashes[target],
                        expected_before[target],
                        f"claimed preimage (guarded handle) for {target.name}",
                    )
                    require_sha(
                        sha256(claim),
                        expected_before[target],
                        f"claimed preimage for {target.name}",
                    )
                    try:
                        link_no_overwrite(staged[target], target)
                    except FileExistsError as exc:
                        raise ValueError(
                            f"Concurrent path creation rejected before install: {target}"
                        ) from exc
                    installed.append(target)
                    if not same_file(target, staged[target]):
                        raise ValueError(f"Installed target identity mismatch: {target}")
                    require_sha(
                        sha256(target),
                        sha256_bytes(payload),
                        f"post-replace verification for {target.name}",
                    )

                # A target installed earlier can still be replaced or modified
                # while subsequent targets are claimed.  Success requires one
                # final identity/content verification over projected targets
                # and over every still-guarded canonical preimage.
                for target, payload in payloads.items():
                    if not same_file(target, staged[target]):
                        raise ValueError(f"Final global target identity mismatch: {target}")
                    require_sha(
                        sha256(target),
                        sha256_bytes(payload),
                        f"final global post-commit verification for {target.name}",
                    )
                    claim = claims[target]
                    if not guarded_object_matches_path(guards[target], claim):
                        raise ValueError(
                            f"Final guarded preimage identity mismatch for {target.name}"
                        )
                    require_sha(
                        sha256_open_file(guards[target]),
                        captured_hashes[target],
                        f"final guarded preimage verification for {target.name}",
                    )
                    require_sha(
                        sha256(claim),
                        captured_hashes[target],
                        f"final claimed preimage verification for {target.name}",
                    )
            except Exception as original_error:
                rollback_errors: list[str] = []
                for target in reversed(list(claims)):
                    claim = claims[target]
                    if not claim.exists() and not claim.is_symlink():
                        rollback_errors.append(f"missing captured preimage for {target}")
                        continue
                    try:
                        if target.exists() or target.is_symlink():
                            tool_owned = (
                                target in installed
                                and same_file(target, staged[target])
                                and not target.is_symlink()
                                and sha256(target) == sha256_bytes(payloads[target])
                            )
                            if not tool_owned:
                                preserved_claims.add(claim)
                                continue
                            target.unlink()
                        try:
                            link_no_overwrite(claim, target)
                        except FileExistsError:
                            preserved_claims.add(claim)
                            continue
                        if not same_file(target, claim) or not guarded_object_matches_path(
                            guards[target], target
                        ):
                            preserved_claims.add(claim)
                            rollback_errors.append(
                                f"restored target identity mismatch for {target}"
                            )
                            continue
                        require_sha(
                            sha256_open_file(guards[target]),
                            captured_hashes[target],
                            f"rollback guarded-content verification for {target.name}",
                        )
                        require_sha(
                            sha256(target),
                            captured_hashes[target],
                            f"rollback captured-content verification for {target.name}",
                        )
                        claim.unlink()
                    except Exception as rollback_error:  # pragma: no cover - exceptional I/O path
                        preserved_claims.add(claim)
                        rollback_errors.append(str(rollback_error))
                if preserved_claims:
                    recovery = ", ".join(str(path) for path in sorted(preserved_claims))
                    rollback_errors.append(f"captured preimages preserved at: {recovery}")
                if rollback_errors:
                    raise RuntimeError(
                        "Atomic context-split rollback was not fully safe: "
                        + "; ".join(rollback_errors)
                    ) from original_error
                raise
            else:
                for claim in claims.values():
                    claim.unlink(missing_ok=True)
            finally:
                for path in staged.values():
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass
                for path in claims.values():
                    if path in preserved_claims:
                        continue
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass


def execute(
    *,
    repo: Path,
    audit_path: Path,
    source_audit_path: Path,
    display_path: Path,
    exclusion_path: Path,
    implementation_review_path: Path,
    ledger_path: Path,
    units_path: Path,
    coverage_path: Path,
    dry_run: bool,
    applied_at: str | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    work = (repo / "work").resolve()
    reports = (repo / "reports").resolve()
    for label, path in (
        ("audit", audit_path),
        ("source audit", source_audit_path),
        ("display batch", display_path),
        ("exclusion batch", exclusion_path),
        ("implementation review", implementation_review_path),
        ("ledger", ledger_path),
        ("units", units_path),
    ):
        reject_symlink_components(path, repo, label)
        if not is_below(path.resolve(), work):
            raise ValueError(f"{label} must remain below ignored work/: {path}")
    reject_symlink_components(coverage_path, repo, "coverage")
    if not (is_below(coverage_path.resolve(), work) or is_below(coverage_path.resolve(), reports)):
        raise ValueError("Coverage path must remain below work/ or reports/")
    paths = {
        "audit": audit_path.resolve(),
        "source_audit": source_audit_path.resolve(),
        "display": display_path.resolve(),
        "exclusion": exclusion_path.resolve(),
        "implementation_review": implementation_review_path.resolve(),
        "ledger": ledger_path.resolve(),
        "units": units_path.resolve(),
        "coverage": coverage_path.resolve(),
    }
    raw = {key: path.read_bytes() for key, path in paths.items()}
    hashes = {key: sha256_bytes(value) for key, value in raw.items()}
    payload = {key: json.loads(value.decode("utf-8")) for key, value in raw.items()}
    source_path = resolve_declared_path(repo, payload["display"].get("source_batch"), "source batch")
    paths["source"] = source_path
    source_raw = source_path.read_bytes()
    hashes["source"] = sha256_bytes(source_raw)
    payload["source"] = json.loads(source_raw.decode("utf-8"))

    validate_top_level_contract(
        repo=repo,
        audit=payload["audit"],
        display_batch=payload["display"],
        exclusion_batch=payload["exclusion"],
        source_batch=payload["source"],
        source_audit=payload["source_audit"],
        coverage=payload["coverage"],
        paths=paths,
        hashes=hashes,
    )
    validate_implementation_review_contract(
        repo=repo,
        review=payload["implementation_review"],
        audit=payload["audit"],
        source_audit=payload["source_audit"],
        display_batch=payload["display"],
        exclusion_batch=payload["exclusion"],
        source_batch=payload["source"],
        paths=paths,
        hashes=hashes,
    )
    validated = validate_split_contract(
        audit=payload["audit"],
        display_batch=payload["display"],
        exclusion_batch=payload["exclusion"],
        source_batch=payload["source"],
        source_audit=payload["source_audit"],
        ledger=payload["ledger"],
        units_payload=payload["units"],
    )
    applied_at = applied_at or datetime.now(tz=timezone.utc).isoformat()
    projected, result = prepare_projection(
        audit=payload["audit"],
        display_batch=payload["display"],
        exclusion_batch=payload["exclusion"],
        ledger=payload["ledger"],
        units_payload=payload["units"],
        coverage=payload["coverage"],
        validated=validated,
        input_hashes=hashes,
        applied_at=applied_at,
    )
    validate_implementation_review_projection(payload["implementation_review"], result)
    result.update(
        {
            "audit_id": payload["audit"].get("audit_id"),
            "display_batch_id": payload["display"].get("batch_id"),
            "dry_run": dry_run,
        }
    )
    if dry_run:
        return result

    target_payloads = {
        paths["ledger"]: projected["ledger"],
        paths["units"]: projected["units"],
        paths["coverage"]: projected["coverage"],
    }
    expected_before = {
        paths["ledger"]: hashes["ledger"],
        paths["units"]: hashes["units"],
        paths["coverage"]: hashes["coverage"],
    }
    atomic_write_group(target_payloads, expected_before)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--source-audit", required=True)
    parser.add_argument("--display-batch", required=True)
    parser.add_argument("--exclusion-batch", required=True)
    parser.add_argument("--implementation-review", required=True)
    parser.add_argument("--ledger", default="work/ledger/translation-ledger.json")
    parser.add_argument("--units", default="work/ledger/translation-units.json")
    parser.add_argument("--coverage", default="reports/translation-coverage.json")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true", help="Fully project the operation without writes")
    action.add_argument("--apply", action="store_true", help="Commit the validated operation")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    result = execute(
        repo=repo,
        audit_path=(repo / args.audit).resolve(),
        source_audit_path=(repo / args.source_audit).resolve(),
        display_path=(repo / args.display_batch).resolve(),
        exclusion_path=(repo / args.exclusion_batch).resolve(),
        implementation_review_path=(repo / args.implementation_review).resolve(),
        ledger_path=(repo / args.ledger).resolve(),
        units_path=(repo / args.units).resolve(),
        coverage_path=(repo / args.coverage).resolve(),
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
