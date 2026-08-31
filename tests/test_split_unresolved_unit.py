from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "split_unresolved_unit.py"
SPEC = importlib.util.spec_from_file_location("split_unresolved_unit", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SplitUnresolvedUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = {
            "entries": [
                {
                    "stable_key": "vanilla:internal",
                    "module": "vanilla",
                    "translation_unit": "unit:mixed",
                    "japanese": "",
                    "status": "UNTRANSLATED",
                    "review_status": "NOT_REVIEWED",
                    "notes": [],
                },
                {
                    "stable_key": "legends:visible",
                    "module": "legends",
                    "translation_unit": "unit:mixed",
                    "japanese": "",
                    "status": "UNTRANSLATED",
                    "review_status": "NOT_REVIEWED",
                    "notes": [],
                },
            ],
            "classification": {"resolved_exclusion_reasons": {}},
        }
        self.units = {
            "units": [
                {
                    "translation_unit": "unit:mixed",
                    "english": "Mixed",
                    "japanese": "",
                    "mode": "literal",
                    "placeholder_signature": {},
                    "status": "UNTRANSLATED",
                    "review_status": "NOT_REVIEWED",
                    "occurrence_count": 2,
                    "modules": ["legends", "vanilla"],
                    "occurrences": ["vanilla:internal", "legends:visible"],
                    "notes": [],
                }
            ]
        }
        self.plan = {
            "splits": [
                {
                    "original_unit": "unit:mixed",
                    "variants": [
                        {
                            "stable_keys": ["vanilla:internal"],
                            "resolution": "RESOLVED_EXCLUSION",
                            "review_status": "NOT_APPLICABLE",
                            "reason": "INTERNAL_KEY",
                        },
                        {
                            "stable_keys": ["legends:visible"],
                            "resolution": "UNTRANSLATED",
                            "review_status": "NOT_REVIEWED",
                        },
                    ],
                }
            ]
        }

    def test_mixed_unit_is_partitioned_without_false_translation(self) -> None:
        result = MODULE.apply_splits(
            self.plan, self.ledger, self.units, enforce_role_evidence=False
        )
        self.assertEqual(result["excluded_occurrences"], 1)
        self.assertEqual(len(self.units["units"]), 1)
        self.assertEqual(self.units["units"][0]["status"], "UNTRANSLATED")
        self.assertEqual(self.ledger["entries"][0]["status"], "RESOLVED_EXCLUSION")
        self.assertNotIn("translation_unit", self.ledger["entries"][0])
        self.assertEqual(self.ledger["entries"][1]["status"], "UNTRANSLATED")

    def test_incomplete_partition_is_rejected(self) -> None:
        self.plan["splits"][0]["variants"].pop()
        with self.assertRaisesRegex(ValueError, "at least two variants"):
            MODULE.apply_splits(
                self.plan, self.ledger, self.units, enforce_role_evidence=False
            )

    def test_source_bound_split_rejects_role_evidence_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "event.nut"
            code = ('function f(_vars) { local label = "shared"; '
                    '_vars.push(["shared", value]); }')
            source.write_text(code, encoding="utf-8")
            self.ledger["module_roots"] = {"vanilla": str(root), "legends": str(root)}
            for occurrence, context in zip(
                self.ledger["entries"], ["onPrepareVariables._vars.push()", "Text"]
            ):
                occurrence.update(
                    source="event.nut", context=context, channel="squirrel",
                    mode="literal", english="shared",
                )
            enriched = [
                MODULE.enrich_occurrence_role(item, self.ledger["module_roots"])
                for item in self.ledger["entries"]
            ]
            self.plan["splits"][0]["variants"][0]["occurrence_evidence"] = [
                MODULE.occurrence_evidence(enriched[0])
            ]
            self.plan["splits"][0]["variants"][1].update(
                occurrence_evidence=[MODULE.occurrence_evidence(enriched[1])],
                role_gate_after_review=MODULE.GATE_MANUAL_REVIEW,
            )
            self.plan.update(schema_version=2, role_evidence_required=True)
            source.write_text(code.replace("value", "other"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evidence drift"):
                MODULE.apply_splits(self.plan, self.ledger, self.units)

    def test_role_gated_plan_without_evidence_is_rejected_by_default(self) -> None:
        self.plan.update(schema_version=2, role_evidence_required=True)
        with self.assertRaisesRegex(ValueError, "mandatory role evidence"):
            MODULE.apply_splits(self.plan, self.ledger, self.units)


if __name__ == "__main__":
    unittest.main()
