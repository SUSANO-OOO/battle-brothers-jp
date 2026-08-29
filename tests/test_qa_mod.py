from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "qa_mod.py"
SPEC = importlib.util.spec_from_file_location("qa_mod", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LedgerPartitionTests(unittest.TestCase):
    def test_exact_partition_is_accepted(self) -> None:
        ledger = {
            "entries": [
                {
                    "stable_key": "visible",
                    "translation_unit": "unit:visible",
                    "module": "vanilla",
                    "status": "UNTRANSLATED",
                    "review_status": "NOT_REVIEWED",
                    "japanese": "",
                },
                {
                    "stable_key": "internal",
                    "module": "vanilla",
                    "status": "RESOLVED_EXCLUSION",
                    "review_status": "NOT_APPLICABLE",
                    "japanese": "",
                },
            ]
        }
        units = {
            "units": [
                {
                    "translation_unit": "unit:visible",
                    "modules": ["vanilla"],
                    "occurrence_count": 1,
                    "occurrences": ["visible"],
                    "status": "UNTRANSLATED",
                    "review_status": "NOT_REVIEWED",
                }
            ]
        }
        coverage = {
            "total_occurrences": 2,
            "resolved_exclusion_occurrences": 1,
            "translatable_occurrences": 1,
            "unique_translation_units": 1,
            "untranslated_units": 1,
            "translated_needs_review_units": 0,
            "reviewed_units": 0,
        }
        errors = MODULE.ledger_partition_errors(ledger, units, coverage)
        self.assertFalse(any(errors[name] for name in errors if name != "canonical_counts"))

    def test_exclusion_inside_a_unit_is_rejected(self) -> None:
        ledger = {
            "entries": [
                {
                    "stable_key": "internal",
                    "translation_unit": "unit:mixed",
                    "module": "vanilla",
                    "status": "RESOLVED_EXCLUSION",
                    "review_status": "NOT_APPLICABLE",
                    "japanese": "",
                }
            ]
        }
        units = {
            "units": [
                {
                    "translation_unit": "unit:mixed",
                    "modules": ["vanilla"],
                    "occurrence_count": 1,
                    "occurrences": ["internal"],
                    "status": "UNTRANSLATED",
                    "review_status": "NOT_REVIEWED",
                }
            ]
        }
        coverage = {
            "total_occurrences": 1,
            "resolved_exclusion_occurrences": 1,
            "translatable_occurrences": 0,
            "unique_translation_units": 1,
            "untranslated_units": 1,
            "translated_needs_review_units": 0,
            "reviewed_units": 0,
        }
        errors = MODULE.ledger_partition_errors(ledger, units, coverage)
        self.assertTrue(errors["unit_errors"])
        self.assertTrue(errors["entry_errors"])


if __name__ == "__main__":
    unittest.main()
