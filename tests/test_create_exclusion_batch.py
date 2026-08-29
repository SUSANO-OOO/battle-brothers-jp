from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "create_exclusion_batch.py"
SPEC = importlib.util.spec_from_file_location("create_exclusion_batch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CreateExclusionBatchTests(unittest.TestCase):
    def test_schema_v2_reason_object_is_normalized(self) -> None:
        audit = {
            "audit_id": "audit:v2",
            "findings": [
                {
                    "translation_unit": "unit:v2",
                    "stable_key": "legends:v2",
                    "classification": "RESOLVED_EXCLUSION",
                    "prior_note_classification": {
                        "classification": "INTERNAL_GAMEPLAY_MATCH_TOKEN",
                        "reason": "Used by a matcher.",
                    },
                    "reason": "Not player-facing.",
                    "source_evidence": {"verified": True},
                }
            ],
        }
        units = {
            "units": [
                {
                    "translation_unit": "unit:v2",
                    "english": "Broad Head",
                    "occurrences": ["legends:v2"],
                }
            ]
        }
        batch, skipped = MODULE.build_batch(audit, units, "batch:v2")
        self.assertFalse(skipped)
        self.assertEqual(batch["entries"][0]["reason"], "INTERNAL_GAMEPLAY_MATCH_TOKEN")
        self.assertEqual(batch["entries"][0]["reason_codes"], ["INTERNAL_GAMEPLAY_MATCH_TOKEN"])

    def test_legacy_candidate_classification_is_used_when_prior_note_is_absent(self) -> None:
        finding = {"candidate_classification": "template_variable_key"}
        self.assertEqual(MODULE.exclusion_reason_code(finding), "template_variable_key")

    def test_whole_unit_with_multiple_internal_reason_codes_is_explicitly_aggregated(self) -> None:
        audit = {
            "findings": [
                {
                    "translation_unit": "unit:multi",
                    "stable_key": "vanilla:a",
                    "classification": "RESOLVED_EXCLUSION",
                    "prior_note_classification": "INTERNAL_KEY",
                    "reason": "Machine key.",
                    "source_evidence": {"verified": True},
                },
                {
                    "translation_unit": "unit:multi",
                    "stable_key": "vanilla:b",
                    "classification": "RESOLVED_EXCLUSION",
                    "prior_note_classification": "DEBUG_ONLY_SOURCE",
                    "reason": "Debug text.",
                    "source_evidence": {"verified": True},
                },
            ]
        }
        units = {
            "units": [
                {
                    "translation_unit": "unit:multi",
                    "english": "Internal",
                    "occurrences": ["vanilla:a", "vanilla:b"],
                }
            ]
        }
        batch, skipped = MODULE.build_batch(audit, units, "batch:multi")
        self.assertFalse(skipped)
        self.assertEqual(batch["entries"][0]["reason"], "MULTIPLE_RESOLVED_EXCLUSION_REASONS")
        self.assertEqual(batch["entries"][0]["reason_codes"], ["DEBUG_ONLY_SOURCE", "INTERNAL_KEY"])

    def test_partial_mixed_unit_is_skipped(self) -> None:
        audit = {
            "audit_id": "audit:test",
            "findings": [
                {
                    "translation_unit": "unit:mixed",
                    "stable_key": "vanilla:internal",
                    "classification": "RESOLVED_EXCLUSION",
                    "prior_note_classification": "INTERNAL_KEY",
                    "reason": "Not displayed.",
                    "source_evidence": {"verified": True},
                }
            ],
        }
        units = {
            "units": [
                {
                    "translation_unit": "unit:mixed",
                    "english": "Mixed",
                    "occurrences": ["vanilla:internal", "legends:visible"],
                },
                {
                    "translation_unit": "unit:internal",
                    "english": "Internal",
                    "occurrences": ["vanilla:key"],
                },
            ]
        }
        audit["findings"].append(
            {
                "translation_unit": "unit:internal",
                "stable_key": "vanilla:key",
                "classification": "RESOLVED_EXCLUSION",
                "prior_note_classification": "INTERNAL_KEY",
                "reason": "Not displayed.",
                "source_evidence": {"verified": True},
            }
        )
        batch, skipped = MODULE.build_batch(audit, units, "batch:test")
        self.assertEqual([entry["translation_unit"] for entry in batch["entries"]], ["unit:internal"])
        self.assertEqual(skipped[0]["translation_unit"], "unit:mixed")

    def test_unverified_evidence_is_rejected(self) -> None:
        audit = {
            "findings": [
                {
                    "translation_unit": "unit:test",
                    "stable_key": "vanilla:test",
                    "classification": "RESOLVED_EXCLUSION",
                    "prior_note_classification": "INTERNAL_KEY",
                    "reason": "Not displayed.",
                    "source_evidence": {"verified": False},
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "Unverified"):
            MODULE.build_batch(audit, {"units": []}, "batch:test")


if __name__ == "__main__":
    unittest.main()
