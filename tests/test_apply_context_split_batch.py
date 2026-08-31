from __future__ import annotations

import copy
import ctypes
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

if os.name == "nt":
    from ctypes import wintypes

    KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    KERNEL32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    KERNEL32.CreateFileW.restype = wintypes.HANDLE
    KERNEL32.SetFilePointerEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_longlong,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    KERNEL32.SetFilePointerEx.restype = wintypes.BOOL
    KERNEL32.WriteFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    KERNEL32.WriteFile.restype = wintypes.BOOL
    KERNEL32.SetEndOfFile.argtypes = [wintypes.HANDLE]
    KERNEL32.SetEndOfFile.restype = wintypes.BOOL
    KERNEL32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    KERNEL32.FlushFileBuffers.restype = wintypes.BOOL
    KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    KERNEL32.CloseHandle.restype = wintypes.BOOL

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    FILE_SHARE_DELETE = 0x00000004
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    FILE_BEGIN = 0
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "apply_context_split_batch.py"
SPEC = importlib.util.spec_from_file_location("apply_context_split_batch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def open_windows_shared_delete_writer(path: Path):
    ctypes.set_last_error(0)
    handle = KERNEL32.CreateFileW(
        str(path),
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    return handle, ctypes.get_last_error()


def overwrite_windows_handle(handle, payload: bytes) -> None:
    if not KERNEL32.SetFilePointerEx(handle, 0, None, FILE_BEGIN):
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_string_buffer(payload)
    written = wintypes.DWORD()
    if not KERNEL32.WriteFile(handle, buffer, len(payload), ctypes.byref(written), None):
        raise ctypes.WinError(ctypes.get_last_error())
    if written.value != len(payload):
        raise AssertionError(f"partial retained-handle write: {written.value}/{len(payload)}")
    if not KERNEL32.SetEndOfFile(handle):
        raise ctypes.WinError(ctypes.get_last_error())
    if not KERNEL32.FlushFileBuffers(handle):
        raise ctypes.WinError(ctypes.get_last_error())


class ContextSplitBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        (self.repo / "work" / "review_batches").mkdir(parents=True)
        (self.repo / "work" / "ledger").mkdir(parents=True)
        (self.repo / "work" / "qa").mkdir(parents=True)
        (self.repo / "tools").mkdir(parents=True)
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "tools/apply_context_split_batch.py").write_bytes(MODULE_PATH.read_bytes())
        (self.repo / "tests/test_apply_context_split_batch.py").write_bytes(
            Path(__file__).read_bytes()
        )
        self.paths = {
            "source": self.repo / "work/review_batches/source.json",
            "source_audit": self.repo / "work/review_batches/source-audit.json",
            "display": self.repo / "work/review_batches/display.json",
            "exclusion": self.repo / "work/review_batches/exclusion.json",
            "audit": self.repo / "work/review_batches/audit.json",
            "implementation_review": self.repo / "work/review_batches/implementation-review.json",
            "ledger": self.repo / "work/ledger/translation-ledger.json",
            "units": self.repo / "work/ledger/translation-units.json",
            "coverage": self.repo / "work/qa/translation-coverage.json",
        }
        self.snapshot = "BBJP-TEST-SNAPSHOT"
        self.mixed_id = "unit:mixed"
        self.whole_id = "unit:whole"
        self.display_key = "vanilla:display"
        self.internal_key = "vanilla:internal"
        self.whole_keys = ["vanilla:whole-a", "vanilla:whole-b"]
        self.display_source_sha = "A" * 64
        self.internal_source_sha = "B" * 64
        self.whole_source_shas = ["C" * 64, "D" * 64]

        mixed_signature = MODULE.signature("five")
        whole_signature = MODULE.signature("internal_key")
        self.source = {
            "schema_version": 1,
            "batch_id": "source",
            "installed_snapshot_id": self.snapshot,
            "entry_count": 2,
            "actual_user_environment_write_count": 0,
            "entries": [
                self.source_entry(
                    self.mixed_id,
                    self.internal_key,
                    "five",
                    "scripts/events/test_event.nut",
                    "test_event.onPrepareVariables._vars.push()",
                    mixed_signature,
                ),
                self.source_entry(
                    self.whole_id,
                    self.whole_keys[0],
                    "internal_key",
                    "scripts/events/whole_a.nut",
                    "whole_a.onPrepareVariables._vars.push()",
                    whole_signature,
                ),
            ],
        }
        self.write("source", self.source)
        source_sha = MODULE.sha256(self.paths["source"])
        self.display = {
            "schema_version": 1,
            "batch_id": "display-reviewed",
            "installed_snapshot_id": self.snapshot,
            "source_batch": "work/review_batches/source.json",
            "source_batch_sha256": source_sha,
            "entry_count": 1,
            "reviewed_count": 1,
            "unresolved_count": 0,
            "internal_counterpart_batch": "work/review_batches/exclusion.json",
            "actual_user_environment_write_count": 0,
            "entries": [
                {
                    "translation_unit": self.mixed_id,
                    "stable_key": self.display_key,
                    "english": "five",
                    "japanese": "五",
                    "source": "scripts/config/strings.nut",
                    "context": "gt.Const.Strings.Amount",
                    "channel": "squirrel",
                    "mode": "literal",
                    "placeholder_signature": mixed_signature,
                    "review_status": "REVIEWED",
                    "notes": ["reviewed exact display context"],
                    "review_evidence": {
                        "exact_context_split": True,
                        "internal_key_translation_count": 0,
                        "generic_translation_unit_apply_compatible": False,
                        "required_application_boundary": "EXACT_STABLE_KEY_ONLY",
                        "source_sha256": self.display_source_sha,
                        "exact_encoded_literal_match": True,
                        "actual_user_environment_write_count": 0,
                    },
                }
            ],
        }
        self.exclusion = {
            "schema_version": 1,
            "batch_id": "exclusion-reviewed",
            "installed_snapshot_id": self.snapshot,
            "source_batch": "work/review_batches/source.json",
            "source_batch_sha256": source_sha,
            "entry_count": 2,
            "reviewed_exclusion_count": 2,
            "canonical_occurrence_count": 3,
            "substitution_key_translation_count": 0,
            "unresolved_count": 0,
            "actual_user_environment_write_count": 0,
            "source_audit_id": "source-audit",
            "entries": [
                self.exclusion_entry(
                    self.mixed_id,
                    "five",
                    [
                        (
                            self.internal_key,
                            "scripts/events/test_event.nut",
                            "test_event.onPrepareVariables._vars.push()",
                            self.internal_source_sha,
                        )
                    ],
                ),
                self.exclusion_entry(
                    self.whole_id,
                    "internal_key",
                    [
                        (
                            self.whole_keys[0],
                            "scripts/events/whole_a.nut",
                            "whole_a.onPrepareVariables._vars.push()",
                            self.whole_source_shas[0],
                        ),
                        (
                            self.whole_keys[1],
                            "scripts/events/whole_b.nut",
                            "whole_b.onPrepareVariables._vars.push()",
                            self.whole_source_shas[1],
                        ),
                    ],
                ),
            ],
        }
        self.ledger = {
            "schema_version": 1,
            "entries": [
                self.ledger_entry(
                    self.display_key,
                    self.mixed_id,
                    "five",
                    "scripts/config/strings.nut",
                    "gt.Const.Strings.Amount",
                    mixed_signature,
                ),
                self.ledger_entry(
                    self.internal_key,
                    self.mixed_id,
                    "five",
                    "scripts/events/test_event.nut",
                    "test_event.onPrepareVariables._vars.push()",
                    mixed_signature,
                ),
                self.ledger_entry(
                    self.whole_keys[0],
                    self.whole_id,
                    "internal_key",
                    "scripts/events/whole_a.nut",
                    "whole_a.onPrepareVariables._vars.push()",
                    whole_signature,
                ),
                self.ledger_entry(
                    self.whole_keys[1],
                    self.whole_id,
                    "internal_key",
                    "scripts/events/whole_b.nut",
                    "whole_b.onPrepareVariables._vars.push()",
                    whole_signature,
                ),
            ],
            "classification": {"resolved_exclusion_reasons": {"EXISTING": 3}},
        }
        self.units = {
            "schema_version": 1,
            "units": [
                self.unit(self.mixed_id, "five", [self.display_key, self.internal_key], mixed_signature),
                self.unit(self.whole_id, "internal_key", self.whole_keys, whole_signature),
            ],
        }
        self.write("display", self.display)
        self.write("exclusion", self.exclusion)
        self.write("ledger", self.ledger)
        self.write("units", self.units)
        self.coverage = {
            "schema_version": 1,
            "installed_snapshot_id": self.snapshot,
            "detailed_ledger_sha256": MODULE.sha256(self.paths["ledger"]),
            "translation_units_sha256": MODULE.sha256(self.paths["units"]),
            "extraction_failures": [],
            "per_module": {"vanilla": {}},
        }
        self.write("coverage", self.coverage)
        self.source_audit = self.make_source_audit()
        self.write("source_audit", self.source_audit)
        self.audit = self.make_audit()
        self.write("audit", self.audit)
        self.implementation_review = self.make_implementation_review()
        self.write("implementation_review", self.implementation_review)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def source_entry(unit_id, stable_key, english, source, context, placeholder_signature):
        return {
            "translation_unit": unit_id,
            "stable_key": stable_key,
            "english": english,
            "japanese": "",
            "source": source,
            "context": context,
            "channel": "squirrel",
            "mode": "literal",
            "placeholder_signature": placeholder_signature,
            "review_status": "DRAFT_INDEPENDENT_REVIEW_REQUIRED",
            "notes": [],
        }

    @staticmethod
    def exclusion_entry(unit_id, english, occurrence_values):
        occurrences = [
            {
                "stable_key": key,
                "source": source,
                "context": context,
                "source_sha256": source_sha,
                "exact_encoded_literal_match": True,
            }
            for key, source, context, source_sha in occurrence_values
        ]
        return {
            "translation_unit": unit_id,
            "english": english,
            "review_status": "NOT_APPLICABLE",
            "reason": "INTERNAL_TEMPLATE_VARIABLE_KEY",
            "stable_keys": [item["stable_key"] for item in occurrences],
            "occurrences": occurrences,
            "notes": ["reviewed internal substitution key"],
        }

    @staticmethod
    def ledger_entry(stable_key, unit_id, english, source, context, placeholder_signature):
        return {
            "stable_key": stable_key,
            "module": "vanilla",
            "english": english,
            "japanese": "",
            "source": source,
            "context": context,
            "channel": "squirrel",
            "mode": "literal",
            "placeholder_signature": placeholder_signature,
            "translation_unit": unit_id,
            "status": "UNTRANSLATED",
            "review_status": "NOT_REVIEWED",
            "notes": [],
        }

    @staticmethod
    def unit(unit_id, english, occurrences, placeholder_signature):
        return {
            "translation_unit": unit_id,
            "english": english,
            "japanese": "",
            "mode": "literal",
            "placeholder_signature": placeholder_signature,
            "status": "UNTRANSLATED",
            "review_status": "NOT_REVIEWED",
            "occurrence_count": len(occurrences),
            "modules": ["vanilla"],
            "occurrences": list(occurrences),
            "notes": [],
        }

    @staticmethod
    def source_audit_occurrence(stable_key, source, context, source_sha):
        return {
            "stable_key": stable_key,
            "module": "vanilla",
            "source": source,
            "context": context,
            "channel": "squirrel",
            "mode": "literal",
            "source_file_exists": True,
            "source_sha256": source_sha,
            "exact_encoded_literal_match": True,
            "matching_source_lines": [1],
        }

    @staticmethod
    def source_audit_entry(unit_id, stable_key, english, occurrences):
        return {
            "index": 1,
            "translation_unit": unit_id,
            "stable_key": stable_key,
            "english": english,
            "classification": "PLAYER_FACING_EVENT_CHOICE",
            "player_facing": True,
            "canonical_occurrence_count": len(occurrences),
            "audited_occurrence_count": len(occurrences),
            "all_occurrences_exact_match": True,
            "placeholder_signature_ok": True,
            "boundary_or_warning": None,
            "occurrences": occurrences,
        }

    def make_source_audit(self):
        mixed_occurrences = [
            self.source_audit_occurrence(
                self.display_key,
                "scripts/config/strings.nut",
                "gt.Const.Strings.Amount",
                self.display_source_sha,
            ),
            self.source_audit_occurrence(
                self.internal_key,
                "scripts/events/test_event.nut",
                "test_event.onPrepareVariables._vars.push()",
                self.internal_source_sha,
            ),
        ]
        whole_occurrences = [
            self.source_audit_occurrence(
                self.whole_keys[0],
                "scripts/events/whole_a.nut",
                "whole_a.onPrepareVariables._vars.push()",
                self.whole_source_shas[0],
            ),
            self.source_audit_occurrence(
                self.whole_keys[1],
                "scripts/events/whole_b.nut",
                "whole_b.onPrepareVariables._vars.push()",
                self.whole_source_shas[1],
            ),
        ]
        entries = [
            self.source_audit_entry(
                self.mixed_id, self.internal_key, "five", mixed_occurrences
            ),
            self.source_audit_entry(
                self.whole_id, self.whole_keys[0], "internal_key", whole_occurrences
            ),
        ]
        return {
            "schema_version": 1,
            "audit_id": "source-audit",
            "installed_snapshot_id": self.snapshot,
            "source_batch": "work/review_batches/source.json",
            "source_root": "work/decompiled/vanilla",
            "source_root_read_only_copy": True,
            "actual_user_environment_write_count": 0,
            "canonical_ledger_sha256": MODULE.sha256(self.paths["ledger"]),
            "canonical_units_sha256": MODULE.sha256(self.paths["units"]),
            "entry_count": len(entries),
            "canonical_occurrence_count": 4,
            "exact_occurrence_match_count": 4,
            "units_with_all_occurrences_exact_match": 2,
            "placeholder_signature_pass_count": 2,
            "validation_error_count": 0,
            "validation_errors": [],
            "entries": entries,
        }

    def make_implementation_review(self):
        def reviewed_input(label, path_key, input_id):
            return {
                "path": MODULE.repo_relative(self.repo, self.paths[path_key]),
                "id": input_id,
                "installed_snapshot_id": self.snapshot,
                "sha256": MODULE.sha256(self.paths[path_key]),
            }

        return {
            "schema_version": 1,
            "review_id": "implementation-review",
            "status": "PASS",
            "review_scope": "CONTEXT_SPLIT_BATCH_IMPLEMENTATION",
            "independent_review": True,
            "tests_status": "PASS",
            "installed_snapshot_id": self.snapshot,
            "canonical_application_authorized": True,
            "canonical_application_performed": False,
            "actual_user_environment_write_count": 0,
            "authorized_targets": {
                "ledger": MODULE.repo_relative(self.repo, self.paths["ledger"]),
                "units": MODULE.repo_relative(self.repo, self.paths["units"]),
                "coverage": MODULE.repo_relative(self.repo, self.paths["coverage"]),
            },
            "inputs": {
                "boundary_audit": reviewed_input(
                    "boundary_audit", "audit", self.audit["audit_id"]
                ),
                "source_audit": reviewed_input(
                    "source_audit", "source_audit", self.source_audit["audit_id"]
                ),
                "display_batch": reviewed_input(
                    "display_batch", "display", self.display["batch_id"]
                ),
                "exclusion_batch": reviewed_input(
                    "exclusion_batch", "exclusion", self.exclusion["batch_id"]
                ),
                "source_batch": reviewed_input(
                    "source_batch", "source", self.source["batch_id"]
                ),
                "tool": {
                    "path": "tools/apply_context_split_batch.py",
                    "sha256": MODULE.sha256(
                        self.repo / "tools/apply_context_split_batch.py"
                    ),
                },
                "tests": [
                    {
                        "path": "tests/test_apply_context_split_batch.py",
                        "sha256": MODULE.sha256(
                            self.repo / "tests/test_apply_context_split_batch.py"
                        ),
                    }
                ],
            },
            "canonical_prehash": {
                "ledger": MODULE.sha256(self.paths["ledger"]),
                "units": MODULE.sha256(self.paths["units"]),
                "coverage": MODULE.sha256(self.paths["coverage"]),
            },
            "production_dry_run": {
                "status": "PASS",
                "dry_run": True,
                "actual_user_environment_write_count": 0,
                "canonical_write_count": 0,
                "removed_original_units": 2,
                "created_reviewed_display_units": 1,
                "translated_display_occurrences": 1,
                "excluded_occurrences": 3,
                "reason_counts": {"INTERNAL_TEMPLATE_VARIABLE_KEY": 3},
                "ledger_sha256_before": MODULE.sha256(self.paths["ledger"]),
                "units_sha256_before": MODULE.sha256(self.paths["units"]),
            },
        }

    def make_audit(self):
        display_sha = MODULE.sha256(self.paths["display"])
        exclusion_sha = MODULE.sha256(self.paths["exclusion"])
        source_sha = MODULE.sha256(self.paths["source"])
        ledger_sha = MODULE.sha256(self.paths["ledger"])
        units_sha = MODULE.sha256(self.paths["units"])
        source_audit_sha = MODULE.sha256(self.paths["source_audit"])
        return {
            "schema_version": 1,
            "audit_id": "context-split-test-audit",
            "installed_snapshot_id": self.snapshot,
            "canonical_application_performed": False,
            "actual_user_environment_write_count": 0,
            "gate_b": {
                "generic_unit_applier_allowed": False,
                "affected_unit_count": 1,
                "mixed_units": [
                    {
                        "translation_unit": self.mixed_id,
                        "english": "five",
                        "canonical_status": "UNTRANSLATED/NOT_REVIEWED",
                        "canonical_occurrences": [self.display_key, self.internal_key],
                        "display": {
                            "stable_key": self.display_key,
                            "source": "scripts/config/strings.nut",
                            "context": "gt.Const.Strings.Amount",
                            "japanese": "五",
                            "source_sha256": self.display_source_sha,
                        },
                        "internal": {
                            "stable_key": self.internal_key,
                            "source": "scripts/events/test_event.nut",
                            "context": "test_event.onPrepareVariables._vars.push()",
                            "reason": "INTERNAL_TEMPLATE_VARIABLE_KEY",
                            "source_sha256": self.internal_source_sha,
                        },
                        "dry_run_visible_variant_id": MODULE.variant_id(
                            self.mixed_id, [self.display_key]
                        ),
                    }
                ],
                "dry_run_evidence": {
                    "canonical_file_sha_before": {
                        "translation-ledger.json": ledger_sha,
                        "translation-units.json": units_sha,
                    }
                },
            },
            "sha256_provenance": {
                "work/review_batches/display.json": display_sha,
                "work/review_batches/exclusion.json": exclusion_sha,
                "work/review_batches/source.json": source_sha,
                "work/review_batches/source-audit.json": source_audit_sha,
            },
        }

    def write(self, key, value) -> None:
        self.paths[key].write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def refresh_contract(self) -> None:
        self.write("source", self.source)
        source_sha = MODULE.sha256(self.paths["source"])
        self.display["source_batch_sha256"] = source_sha
        self.exclusion["source_batch_sha256"] = source_sha
        self.write("display", self.display)
        self.write("exclusion", self.exclusion)
        self.write("ledger", self.ledger)
        self.write("units", self.units)
        self.source_audit["canonical_ledger_sha256"] = MODULE.sha256(self.paths["ledger"])
        self.source_audit["canonical_units_sha256"] = MODULE.sha256(self.paths["units"])
        self.write("source_audit", self.source_audit)
        self.coverage["detailed_ledger_sha256"] = MODULE.sha256(self.paths["ledger"])
        self.coverage["translation_units_sha256"] = MODULE.sha256(self.paths["units"])
        self.write("coverage", self.coverage)
        self.audit["gate_b"]["dry_run_evidence"]["canonical_file_sha_before"] = {
            "translation-ledger.json": MODULE.sha256(self.paths["ledger"]),
            "translation-units.json": MODULE.sha256(self.paths["units"]),
        }
        self.audit["sha256_provenance"] = {
            "work/review_batches/display.json": MODULE.sha256(self.paths["display"]),
            "work/review_batches/exclusion.json": MODULE.sha256(self.paths["exclusion"]),
            "work/review_batches/source.json": MODULE.sha256(self.paths["source"]),
            "work/review_batches/source-audit.json": MODULE.sha256(
                self.paths["source_audit"]
            ),
        }
        self.write("audit", self.audit)
        self.implementation_review = self.make_implementation_review()
        self.write("implementation_review", self.implementation_review)

    def execute(self, dry_run=True):
        return MODULE.execute(
            repo=self.repo,
            audit_path=self.paths["audit"],
            source_audit_path=self.paths["source_audit"],
            display_path=self.paths["display"],
            exclusion_path=self.paths["exclusion"],
            implementation_review_path=self.paths["implementation_review"],
            ledger_path=self.paths["ledger"],
            units_path=self.paths["units"],
            coverage_path=self.paths["coverage"],
            dry_run=dry_run,
            applied_at="2026-08-31T00:00:00+00:00",
        )

    def test_dry_run_projects_full_batch_without_writing(self) -> None:
        before = {key: path.read_bytes() for key, path in self.paths.items()}
        result = self.execute(dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["removed_original_units"], 2)
        self.assertEqual(result["created_reviewed_display_units"], 1)
        self.assertEqual(result["excluded_occurrences"], 3)
        self.assertEqual(before, {key: path.read_bytes() for key, path in self.paths.items()})

    def test_apply_translates_only_display_and_excludes_every_reviewed_internal(self) -> None:
        result = self.execute(dry_run=False)
        self.assertFalse(result["dry_run"])
        ledger = json.loads(self.paths["ledger"].read_text(encoding="utf-8"))
        units = json.loads(self.paths["units"].read_text(encoding="utf-8"))
        coverage = json.loads(self.paths["coverage"].read_text(encoding="utf-8"))
        occurrences = {entry["stable_key"]: entry for entry in ledger["entries"]}
        visible = occurrences[self.display_key]
        self.assertEqual(visible["japanese"], "五")
        self.assertEqual(visible["status"], "TRANSLATED")
        self.assertEqual(
            visible["translation_unit"], MODULE.variant_id(self.mixed_id, [self.display_key])
        )
        for key in [self.internal_key, *self.whole_keys]:
            self.assertEqual(occurrences[key]["status"], "RESOLVED_EXCLUSION")
            self.assertNotIn("translation_unit", occurrences[key])
            self.assertEqual(occurrences[key]["japanese"], "")
        unit_ids = {unit["translation_unit"] for unit in units["units"]}
        self.assertNotIn(self.mixed_id, unit_ids)
        self.assertNotIn(self.whole_id, unit_ids)
        self.assertIn(MODULE.variant_id(self.mixed_id, [self.display_key]), unit_ids)
        self.assertEqual(coverage["reviewed_units"], 1)
        self.assertEqual(coverage["resolved_exclusion_occurrences"], 3)

    def test_stale_canonical_hash_is_rejected(self) -> None:
        self.paths["units"].write_bytes(self.paths["units"].read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "canonical units SHA-256 mismatch"):
            self.execute()

    def test_display_input_hash_drift_is_rejected(self) -> None:
        self.paths["display"].write_bytes(self.paths["display"].read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "audit provenance.*SHA-256 mismatch"):
            self.execute()

    def test_non_unresolved_original_state_is_rejected_after_hash_refresh(self) -> None:
        self.units["units"][0]["status"] = "TRANSLATED"
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "not UNTRANSLATED/NOT_REVIEWED"):
            self.execute()

    def test_incomplete_partition_is_rejected(self) -> None:
        signature = MODULE.signature("five")
        extra_key = "vanilla:unreviewed-extra"
        self.ledger["entries"].append(
            self.ledger_entry(
                extra_key,
                self.mixed_id,
                "five",
                "scripts/config/extra.nut",
                "extra",
                signature,
            )
        )
        mixed_unit = next(
            unit for unit in self.units["units"] if unit["translation_unit"] == self.mixed_id
        )
        mixed_unit["occurrences"].append(extra_key)
        mixed_unit["occurrence_count"] += 1
        self.audit["gate_b"]["mixed_units"][0]["canonical_occurrences"].append(extra_key)
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "do not exactly partition"):
            self.execute()

    def test_duplicate_display_unit_is_rejected(self) -> None:
        duplicate = copy.deepcopy(self.display["entries"][0])
        duplicate["stable_key"] = "vanilla:other"
        self.display["entries"].append(duplicate)
        self.display["entry_count"] = 2
        self.display["reviewed_count"] = 2
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "Duplicate translation_unit values in display batch"):
            self.execute()

    def test_display_context_drift_is_rejected(self) -> None:
        self.display["entries"][0]["context"] = "wrong.context"
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "Display context mismatch"):
            self.execute()

    def test_display_placeholder_signature_drift_is_rejected(self) -> None:
        self.display["entries"][0]["placeholder_signature"] = MODULE.signature("%name%")
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "recorded placeholder signature mismatch"):
            self.execute()

    def test_exclusion_occurrence_source_drift_is_rejected(self) -> None:
        self.exclusion["entries"][1]["occurrences"][0]["source"] = "scripts/events/wrong.nut"
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "Exclusion source mismatch"):
            self.execute()

    def test_extra_full_batch_entry_is_not_ignored(self) -> None:
        extra = self.exclusion_entry(
            "unit:extra",
            "extra",
            [("vanilla:extra", "scripts/extra.nut", "extra.context", "E" * 64)],
        )
        self.exclusion["entries"].append(extra)
        self.exclusion["entry_count"] += 1
        self.exclusion["reviewed_exclusion_count"] += 1
        self.exclusion["canonical_occurrence_count"] += 1
        self.source["entries"].append(
            self.source_entry(
                "unit:extra",
                "vanilla:extra",
                "extra",
                "scripts/extra.nut",
                "extra.context",
                MODULE.signature("extra"),
            )
        )
        self.source["entry_count"] += 1
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "Source audit lacks reviewed exclusion units"):
            self.execute()

    def test_source_batch_sha_drift_is_rejected(self) -> None:
        self.paths["source"].write_bytes(self.paths["source"].read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "source batch SHA-256 mismatch"):
            self.execute()

    def test_coverage_canonical_state_mismatch_is_rejected(self) -> None:
        self.coverage["detailed_ledger_sha256"] = "0" * 64
        self.write("coverage", self.coverage)
        with self.assertRaisesRegex(ValueError, "Coverage ledger SHA-256"):
            self.execute()

    def test_blocked_preimplementation_audit_cannot_apply_without_pass_review(self) -> None:
        self.implementation_review["status"] = "FAIL"
        self.implementation_review["canonical_application_authorized"] = False
        self.write("implementation_review", self.implementation_review)
        before = {
            key: self.paths[key].read_bytes() for key in ("ledger", "units", "coverage")
        }
        with self.assertRaisesRegex(ValueError, "status must be PASS"):
            self.execute(dry_run=False)
        self.assertEqual(
            before,
            {key: self.paths[key].read_bytes() for key in ("ledger", "units", "coverage")},
        )

    def test_implementation_review_tool_hash_is_pinned(self) -> None:
        self.implementation_review["inputs"]["tool"]["sha256"] = "0" * 64
        self.write("implementation_review", self.implementation_review)
        with self.assertRaisesRegex(ValueError, "implementation review tool SHA-256 mismatch"):
            self.execute()

    def test_implementation_review_projected_counts_are_pinned(self) -> None:
        self.implementation_review["production_dry_run"]["excluded_occurrences"] = 2
        self.write("implementation_review", self.implementation_review)
        with self.assertRaisesRegex(ValueError, "projected excluded_occurrences mismatch"):
            self.execute()

    def test_source_audit_direct_hash_drift_is_rejected(self) -> None:
        self.paths["source_audit"].write_bytes(
            self.paths["source_audit"].read_bytes() + b" "
        )
        with self.assertRaisesRegex(ValueError, "audit provenance.*source-audit.*SHA-256 mismatch"):
            self.execute()

    def test_nonrepresentative_source_sha_tamper_is_rejected(self) -> None:
        self.exclusion["entries"][1]["occurrences"][1]["source_sha256"] = "0" * 64
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "Source audit/exclusion source_sha256 mismatch"):
            self.execute()

    def test_nonrepresentative_channel_tamper_is_rejected(self) -> None:
        target = next(
            entry
            for entry in self.ledger["entries"]
            if entry["stable_key"] == self.whole_keys[1]
        )
        target["channel"] = "javascript"
        self.refresh_contract()
        with self.assertRaisesRegex(ValueError, "Source audit/canonical channel mismatch"):
            self.execute()

    def test_display_channel_tamper_still_must_match_source_audit(self) -> None:
        display_occurrence = next(
            entry
            for entry in self.ledger["entries"]
            if entry["stable_key"] == self.display_key
        )
        display_occurrence["channel"] = "javascript"
        self.display["entries"][0]["channel"] = "javascript"
        self.refresh_contract()
        with self.assertRaisesRegex(
            ValueError, "Source audit/canonical display channel mismatch"
        ):
            self.execute()

    def test_coverage_preimage_sha_is_recorded_in_metadata(self) -> None:
        coverage_before = MODULE.sha256(self.paths["coverage"])
        self.execute(dry_run=False)
        ledger = json.loads(self.paths["ledger"].read_text(encoding="utf-8"))
        provenance = ledger["last_context_split_batch"]["input_sha256"]
        self.assertEqual(provenance["coverage"], coverage_before)
        self.assertEqual(provenance["source_audit"], MODULE.sha256(self.paths["source_audit"]))
        self.assertEqual(
            provenance["implementation_review"],
            MODULE.sha256(self.paths["implementation_review"]),
        )

    def test_apply_cleanup_and_second_application_are_fail_closed(self) -> None:
        self.execute(dry_run=False)
        before_second = {
            key: self.paths[key].read_bytes() for key in ("ledger", "units", "coverage")
        }
        with self.assertRaisesRegex(ValueError, "canonical ledger SHA-256 mismatch"):
            self.execute(dry_run=False)
        self.assertEqual(
            before_second,
            {key: self.paths[key].read_bytes() for key in ("ledger", "units", "coverage")},
        )
        debris = [
            path
            for path in self.repo.rglob("*")
            if path.name.endswith((".stage", ".claim"))
            or path.name == ".apply_context_split_batch.lock"
        ]
        self.assertEqual(debris, [])

    def test_concurrent_update_after_global_recheck_is_rejected_and_rolled_back(self) -> None:
        targets = [self.repo / f"work/qa/race-{name}.json" for name in ("a", "b", "c")]
        for index, target in enumerate(targets):
            target.write_bytes(f"before-{index}".encode())
        payloads = {
            target: f"after-{index}".encode() for index, target in enumerate(targets)
        }
        expected = {target: MODULE.sha256(target) for target in targets}
        before = {target: target.read_bytes() for target in targets}
        real_replace = MODULE.os.replace
        injected = False
        write_blocked = False

        def inject_competing_write(source, destination):
            nonlocal injected, write_blocked
            if source == targets[0] and str(destination).endswith(".claim") and not injected:
                injected = True
                try:
                    targets[1].write_bytes(b"concurrent-update")
                except PermissionError:
                    write_blocked = True
            return real_replace(source, destination)

        with mock.patch.object(MODULE.os, "replace", side_effect=inject_competing_write):
            if os.name == "nt":
                MODULE.atomic_write_group(payloads, expected)
            else:
                with self.assertRaisesRegex(ValueError, "immediate pre-claim recheck"):
                    MODULE.atomic_write_group(payloads, expected)
        if os.name == "nt":
            self.assertTrue(write_blocked)
            self.assertEqual(
                {target: target.read_bytes() for target in targets}, payloads
            )
        else:
            self.assertEqual(targets[0].read_bytes(), before[targets[0]])
            self.assertEqual(targets[1].read_bytes(), b"concurrent-update")
            self.assertEqual(targets[2].read_bytes(), before[targets[2]])
        self.assertFalse((targets[0].parent / ".apply_context_split_batch.lock").exists())

    def test_external_write_between_check_and_claim_is_never_overwritten(self) -> None:
        targets = [self.repo / f"work/qa/claim-race-{name}.json" for name in ("a", "b")]
        for index, target in enumerate(targets):
            target.write_bytes(f"before-{index}".encode())
        payloads = {target: b"tool-output" for target in targets}
        expected = {target: MODULE.sha256(target) for target in targets}
        before = {target: target.read_bytes() for target in targets}
        real_replace = MODULE.os.replace
        injected = False
        write_blocked = False

        def inject_same_target_before_claim(source, destination):
            nonlocal injected, write_blocked
            if source == targets[0] and str(destination).endswith(".claim") and not injected:
                injected = True
                try:
                    targets[0].write_bytes(b"external-between-check-and-claim")
                except PermissionError:
                    write_blocked = True
            return real_replace(source, destination)

        with mock.patch.object(
            MODULE.os, "replace", side_effect=inject_same_target_before_claim
        ):
            if os.name == "nt":
                MODULE.atomic_write_group(payloads, expected)
            else:
                with self.assertRaisesRegex(ValueError, "claimed preimage"):
                    MODULE.atomic_write_group(payloads, expected)
        if os.name == "nt":
            self.assertTrue(write_blocked)
            self.assertEqual(
                {target: target.read_bytes() for target in targets}, payloads
            )
        else:
            self.assertEqual(targets[0].read_bytes(), b"external-between-check-and-claim")
            self.assertEqual(targets[1].read_bytes(), before[targets[1]])
        self.assertEqual(list(targets[0].parent.glob("*.claim")), [])

    @unittest.skipUnless(os.name == "nt", "requires Win32 file-share semantics")
    def test_retained_share_delete_writer_is_rejected_before_any_claim(self) -> None:
        targets = [
            self.repo / f"work/qa/retained-writer-{name}.json"
            for name in ("ledger", "units", "coverage")
        ]
        for index, target in enumerate(targets):
            target.write_bytes(f"before-{index}".encode())
        payloads = {
            target: f"projected-{index}".encode() for index, target in enumerate(targets)
        }
        expected = {target: MODULE.sha256(target) for target in targets}
        before = {target: target.read_bytes() for target in targets}
        retained, error = open_windows_shared_delete_writer(targets[0])
        self.assertNotEqual(retained, INVALID_HANDLE_VALUE, f"WinError {error}")
        external = b"external-write-through-retained-canonical-handle"
        try:
            with self.assertRaisesRegex(ValueError, "write-denying preimage guard"):
                MODULE.atomic_write_group(payloads, expected)
            overwrite_windows_handle(retained, external)
            self.assertEqual(targets[0].read_bytes(), external)
        finally:
            KERNEL32.CloseHandle(retained)
        self.assertEqual(targets[1].read_bytes(), before[targets[1]])
        self.assertEqual(targets[2].read_bytes(), before[targets[2]])
        self.assertEqual(list(targets[0].parent.glob("*.claim")), [])
        self.assertEqual(list(targets[0].parent.glob("*.stage")), [])
        self.assertFalse((targets[0].parent / ".apply_context_split_batch.lock").exists())

    @unittest.skipUnless(os.name == "nt", "requires Win32 file-share semantics")
    def test_guard_blocks_new_share_delete_writer_but_allows_claim_rename(self) -> None:
        targets = [
            self.repo / f"work/qa/new-writer-{name}.json"
            for name in ("ledger", "units", "coverage")
        ]
        for index, target in enumerate(targets):
            target.write_bytes(f"before-{index}".encode())
        payloads = {
            target: f"projected-{index}".encode() for index, target in enumerate(targets)
        }
        expected = {target: MODULE.sha256(target) for target in targets}
        real_replace = MODULE.os.replace
        attempted = False
        sharing_error = None

        def attempt_writer_then_rename(source, destination):
            nonlocal attempted, sharing_error
            if source == targets[0] and str(destination).endswith(".claim") and not attempted:
                attempted = True
                writer, sharing_error = open_windows_shared_delete_writer(targets[0])
                if writer != INVALID_HANDLE_VALUE:
                    KERNEL32.CloseHandle(writer)
                    self.fail("write-denying guard allowed a new share-delete writer")
            return real_replace(source, destination)

        with mock.patch.object(MODULE.os, "replace", side_effect=attempt_writer_then_rename):
            MODULE.atomic_write_group(payloads, expected)
        self.assertTrue(attempted)
        self.assertEqual(sharing_error, 32)  # ERROR_SHARING_VIOLATION
        self.assertEqual({target: target.read_bytes() for target in targets}, payloads)
        self.assertEqual(list(targets[0].parent.glob("*.claim")), [])
        self.assertEqual(list(targets[0].parent.glob("*.stage")), [])

    @unittest.skipUnless(os.name == "nt", "requires Win32 file-share semantics")
    def test_guard_follows_claim_and_blocks_writer_to_claimed_preimage(self) -> None:
        targets = [
            self.repo / f"work/qa/claimed-writer-{name}.json"
            for name in ("ledger", "units", "coverage")
        ]
        for index, target in enumerate(targets):
            target.write_bytes(f"before-{index}".encode())
        payloads = {
            target: f"projected-{index}".encode() for index, target in enumerate(targets)
        }
        expected = {target: MODULE.sha256(target) for target in targets}
        real_link = MODULE.link_no_overwrite
        attempted = False
        sharing_error = None

        def attempt_claim_writer_then_install(source, destination):
            nonlocal attempted, sharing_error
            if destination == targets[0] and not attempted:
                attempted = True
                claims = list(targets[0].parent.glob(f".{targets[0].name}.*.claim"))
                self.assertEqual(len(claims), 1)
                writer, sharing_error = open_windows_shared_delete_writer(claims[0])
                if writer != INVALID_HANDLE_VALUE:
                    KERNEL32.CloseHandle(writer)
                    self.fail("preimage guard did not follow the renamed claim object")
            return real_link(source, destination)

        with mock.patch.object(
            MODULE, "link_no_overwrite", side_effect=attempt_claim_writer_then_install
        ):
            MODULE.atomic_write_group(payloads, expected)
        self.assertTrue(attempted)
        self.assertEqual(sharing_error, 32)  # ERROR_SHARING_VIOLATION
        self.assertEqual({target: target.read_bytes() for target in targets}, payloads)
        self.assertEqual(list(targets[0].parent.glob("*.claim")), [])
        self.assertEqual(list(targets[0].parent.glob("*.stage")), [])

    def test_final_global_verification_rejects_external_postinstall_write(self) -> None:
        targets = [
            self.repo / f"work/qa/postcommit-{name}.json"
            for name in ("ledger", "units", "coverage")
        ]
        for index, target in enumerate(targets):
            target.write_bytes(f"before-{index}".encode())
        payloads = {
            target: f"tool-after-{index}".encode() for index, target in enumerate(targets)
        }
        expected = {target: MODULE.sha256(target) for target in targets}
        real_link = MODULE.link_no_overwrite
        link_calls = 0

        def inject_after_first_target_postcheck(source, destination):
            nonlocal link_calls
            link_calls += 1
            if link_calls == 2:
                targets[0].write_bytes(b"external-after-ledger-install")
            return real_link(source, destination)

        with mock.patch.object(
            MODULE, "link_no_overwrite", side_effect=inject_after_first_target_postcheck
        ):
            with self.assertRaisesRegex(RuntimeError, "captured preimages preserved"):
                MODULE.atomic_write_group(payloads, expected)
        self.assertEqual(targets[0].read_bytes(), b"external-after-ledger-install")
        self.assertEqual(targets[1].read_bytes(), b"before-1")
        self.assertEqual(targets[2].read_bytes(), b"before-2")
        recovery = list(targets[0].parent.glob(".postcommit-ledger.json.*.claim"))
        self.assertEqual(len(recovery), 1)
        self.assertEqual(recovery[0].read_bytes(), b"before-0")
        self.assertFalse((targets[0].parent / ".apply_context_split_batch.lock").exists())

    def test_symlink_target_is_rejected_without_touching_referent(self) -> None:
        referent = self.repo / "work/qa/referent.json"
        target = self.repo / "work/qa/symlink.json"
        referent.write_bytes(b"referent")
        try:
            target.symlink_to(referent)
        except OSError as exc:  # Windows may not grant symlink creation to this test process.
            self.skipTest(f"symlink creation unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "symlink"):
            MODULE.atomic_write_group(
                {target: b"tool-output"}, {target: MODULE.sha256(target)}
            )
        self.assertEqual(referent.read_bytes(), b"referent")

    def test_existing_exclusive_lock_rejects_commit_without_target_writes(self) -> None:
        targets = [self.repo / f"work/qa/locked-{name}.json" for name in ("a", "b")]
        for index, target in enumerate(targets):
            target.write_bytes(f"before-{index}".encode())
        payloads = {target: b"after" for target in targets}
        expected = {target: MODULE.sha256(target) for target in targets}
        before = {target: target.read_bytes() for target in targets}
        lock_path = targets[0].parent / ".apply_context_split_batch.lock"
        lock_path.write_text("held\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "commit lock already exists"):
            MODULE.atomic_write_group(payloads, expected, lock_path=lock_path)
        self.assertEqual(before, {target: target.read_bytes() for target in targets})

    def test_atomic_group_rechecks_before_any_replace(self) -> None:
        targets = [self.repo / "work/qa/a.json", self.repo / "work/qa/b.json"]
        for index, target in enumerate(targets):
            target.write_bytes(f"before-{index}".encode())
        before = {target: target.read_bytes() for target in targets}
        payloads = {target: f"after-{index}".encode() for index, target in enumerate(targets)}
        expected = {target: MODULE.sha256(target) for target in targets}
        expected[targets[1]] = "0" * 64
        with self.assertRaisesRegex(ValueError, "global pre-commit recheck"):
            MODULE.atomic_write_group(payloads, expected)
        self.assertEqual(before, {target: target.read_bytes() for target in targets})


if __name__ == "__main__":
    unittest.main()
