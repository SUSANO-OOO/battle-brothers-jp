from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "apply_exclusion_batch.py"
SPEC = importlib.util.spec_from_file_location("apply_exclusion_batch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExclusionBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit = {
            "translation_unit": "unit:test",
            "english": "InternalKey",
            "status": "UNTRANSLATED",
            "review_status": "NOT_REVIEWED",
            "occurrence_count": 1,
            "occurrences": ["vanilla:test"],
        }
        self.entry = {
            "translation_unit": "unit:test",
            "english": "InternalKey",
            "review_status": "NOT_APPLICABLE",
            "reason": "INTERNAL_MACHINE_KEY",
            "stable_keys": ["vanilla:test"],
            "notes": ["Call site does not render this value."],
        }

    def validate_batch(self, batch, units):
        return MODULE.validate_batch(
            batch, units, enforce_role_evidence=False
        )

    def test_valid_exclusion_is_accepted(self) -> None:
        validated = self.validate_batch({"entries": [self.entry]}, {"unit:test": self.unit})
        self.assertEqual(validated[0]["reason"], "INTERNAL_MACHINE_KEY")

    def test_source_mismatch_is_rejected(self) -> None:
        entry = dict(self.entry, english="Different")
        with self.assertRaisesRegex(ValueError, "English/source mismatch"):
            self.validate_batch({"entries": [entry]}, {"unit:test": self.unit})

    def test_reviewed_translation_cannot_be_excluded(self) -> None:
        unit = dict(self.unit, status="TRANSLATED", review_status="REVIEWED")
        with self.assertRaisesRegex(ValueError, "not an unresolved unit"):
            self.validate_batch({"entries": [self.entry]}, {"unit:test": unit})

    def test_partial_unit_exclusion_is_rejected(self) -> None:
        unit = dict(self.unit, occurrence_count=2, occurrences=["vanilla:test", "legends:test"])
        with self.assertRaisesRegex(ValueError, "split contexts first"):
            self.validate_batch({"entries": [self.entry]}, {"unit:test": unit})

    def test_apply_removes_unit_and_resolves_occurrence(self) -> None:
        ledger = {
            "entries": [
                {
                    "stable_key": "vanilla:test",
                    "translation_unit": "unit:test",
                    "japanese": "",
                    "status": "UNTRANSLATED",
                    "review_status": "NOT_REVIEWED",
                    "notes": [],
                }
            ],
            "classification": {"resolved_exclusion_reasons": {}},
        }
        units = {"units": [dict(self.unit)]}
        validated = self.validate_batch({"entries": [dict(self.entry)]}, {"unit:test": self.unit})
        counts = MODULE.apply_entries(validated, ledger, units)
        self.assertEqual(units["units"], [])
        self.assertEqual(ledger["entries"][0]["status"], "RESOLVED_EXCLUSION")
        self.assertEqual(ledger["entries"][0]["review_status"], "NOT_APPLICABLE")
        self.assertNotIn("translation_unit", ledger["entries"][0])
        self.assertEqual(counts["INTERNAL_MACHINE_KEY"], 1)

    def test_source_bound_parser_key_exclusion_rejects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "event.nut"
            code = 'function f(_vars) { _vars.push(["InternalKey", value]); }'
            source.write_text(code, encoding="utf-8")
            occurrence = {
                "stable_key": "vanilla:test", "module": "vanilla", "source": "event.nut",
                "context": "onPrepareVariables._vars.push()", "channel": "squirrel",
                "mode": "literal", "english": "InternalKey",
                "translation_unit": "unit:test",
            }
            roots = {"vanilla": str(root)}
            evidence = MODULE.occurrence_evidence(
                MODULE.enrich_occurrence_role(occurrence, roots)
            )
            entry = dict(
                self.entry,
                occurrence_evidence=[evidence],
                requires_parser_proven_binding=True,
            )
            batch = {"schema_version": 2, "role_evidence_required": True, "entries": [entry]}
            validated = MODULE.validate_batch(
                batch, {"unit:test": self.unit},
                {"vanilla:test": occurrence}, roots,
            )
            self.assertEqual(len(validated), 1)
            source.write_text(code.replace("value", "other"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evidence drift"):
                MODULE.validate_batch(
                    batch, {"unit:test": self.unit},
                    {"vanilla:test": occurrence}, roots,
                )

    def test_parser_key_flag_without_evidence_is_rejected(self) -> None:
        entry = dict(self.entry, requires_parser_proven_binding=True)
        batch = {"schema_version": 2, "role_evidence_required": True, "entries": [entry]}
        with self.assertRaisesRegex(ValueError, "mandatory exclusion evidence"):
            MODULE.validate_batch(batch, {"unit:test": self.unit}, {}, {"vanilla": "unused"})

    def test_legacy_exclusion_batch_is_rejected_by_default(self) -> None:
        with self.assertRaisesRegex(ValueError, "schema-v2"):
            MODULE.validate_batch({"entries": [self.entry]}, {"unit:test": self.unit})


if __name__ == "__main__":
    unittest.main()
