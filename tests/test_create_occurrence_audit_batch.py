from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "create_occurrence_audit_batch.py"
SPEC = importlib.util.spec_from_file_location("create_occurrence_audit_batch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OccurrenceAuditBatchTests(unittest.TestCase):
    def test_expands_candidate_to_all_cross_module_occurrences(self) -> None:
        review = {
            "batch_id": "review:test",
            "review_metadata": {
                "excluded_entries": [
                    {
                        "translation_unit": "unit:test",
                        "classification": "INTERNAL_KEY",
                        "reason": "Representative call site is internal.",
                    }
                ]
            },
        }
        ledger = {
            "entries": [
                {"stable_key": "v", "module": "vanilla", "source": "v.nut", "context": "v", "channel": "squirrel", "mode": "literal"},
                {"stable_key": "l", "module": "legends", "source": "l.nut", "context": "l", "channel": "squirrel", "mode": "literal"},
            ]
        }
        units = {
            "units": [
                {
                    "translation_unit": "unit:test",
                    "english": "Key",
                    "status": "UNTRANSLATED",
                    "occurrences": ["v", "l"],
                }
            ]
        }
        payload = MODULE.build_audit_batch(review, ledger, units)
        self.assertEqual(payload["candidate_units"], 1)
        self.assertEqual(payload["occurrence_count"], 2)
        self.assertEqual({item["stable_key"] for item in payload["findings"]}, {"v", "l"})
        self.assertTrue(all(item["classification"] == "AUDIT_REQUIRED" for item in payload["findings"]))

    def test_translated_candidate_is_rejected(self) -> None:
        review = {
            "review_metadata": {
                "excluded_entries": [{"translation_unit": "unit:test"}]
            }
        }
        units = {
            "units": [
                {
                    "translation_unit": "unit:test",
                    "english": "Key",
                    "status": "TRANSLATED",
                    "occurrences": [],
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "no longer unresolved"):
            MODULE.build_audit_batch(review, {"entries": []}, units)

    def test_already_resolved_candidate_is_recorded_without_reaudit(self) -> None:
        review = {
            "review_metadata": {
                "excluded_entries": [
                    {"translation_unit": "unit:old", "stable_key": "internal"}
                ]
            }
        }
        ledger = {
            "entries": [
                {
                    "stable_key": "internal",
                    "status": "RESOLVED_EXCLUSION",
                    "notes": ["INTERNAL_KEY"],
                }
            ]
        }
        payload = MODULE.build_audit_batch(review, ledger, {"units": []})
        self.assertEqual(payload["candidate_units"], 0)
        self.assertEqual(payload["occurrence_count"], 0)
        self.assertEqual(payload["already_resolved_candidates"][0]["stable_key"], "internal")


if __name__ == "__main__":
    unittest.main()
