from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "ledger_integrity.py"
SPEC = importlib.util.spec_from_file_location("ledger_integrity_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LedgerIntegrityTests(unittest.TestCase):
    def test_duplicate_canonical_stable_key_is_rejected(self) -> None:
        entry = {"stable_key": "same", "translation_unit": "unit:test"}
        with self.assertRaisesRegex(ValueError, "Duplicate canonical stable_key"):
            MODULE.unique_occurrence_index([entry, dict(entry)])

    def test_duplicate_occurrence_in_unit_is_rejected(self) -> None:
        unit = {"translation_unit": "unit:test", "occurrences": ["same", "same"]}
        with self.assertRaisesRegex(ValueError, "Duplicate occurrence ID"):
            MODULE.unique_unit_index([unit])

    def test_occurrence_membership_drift_is_rejected(self) -> None:
        ledger = {
            "entries": [{"stable_key": "same", "translation_unit": "unit:other"}]
        }
        units = {
            "units": [{"translation_unit": "unit:test", "occurrences": ["same"]}]
        }
        with self.assertRaisesRegex(ValueError, "translation-unit mismatch"):
            MODULE.canonical_indexes(ledger, units)


if __name__ == "__main__":
    unittest.main()
