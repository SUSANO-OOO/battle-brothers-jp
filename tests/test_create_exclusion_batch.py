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
