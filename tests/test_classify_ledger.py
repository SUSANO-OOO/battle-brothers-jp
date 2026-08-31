from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "classify_ledger.py"
SPEC = importlib.util.spec_from_file_location("classify_ledger", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

ROLES_PATH = Path(__file__).resolve().parents[1] / "tools" / "squirrel_literal_roles.py"
ROLES_SPEC = importlib.util.spec_from_file_location("squirrel_literal_roles_test", ROLES_PATH)
assert ROLES_SPEC and ROLES_SPEC.loader
ROLES = importlib.util.module_from_spec(ROLES_SPEC)
ROLES_SPEC.loader.exec_module(ROLES)


def occurrence(
    stable_key: str, english: str, source: str, metadata: dict | None = None
) -> dict:
    value = {
        "stable_key": stable_key,
        "module": "sample",
        "source": source,
        "context": "event.onPrepareVariables._vars.push()",
        "channel": "squirrel",
        "english": english,
        "japanese": "",
        "status": "UNTRANSLATED",
        "review_status": "NOT_REVIEWED",
        "mode": "literal",
        "placeholder_signature": {},
        "source_code": [],
        "notes": [],
    }
    if metadata:
        value.update(metadata)
    return value


class ClassifyLedgerTests(unittest.TestCase):
    def test_all_parser_proven_keys_autoexclude_only_after_source_reparse(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            code = 'function f(_vars) { _vars.push(["key", value]); }'
            (root / "event.nut").write_text(code, encoding="utf-8")
            analysis = ROLES.analyze_squirrel_literals(code)
            metadata = {
                field: analysis["records"][0][field]
                for field in ROLES.REQUIRED_ROLE_FIELDS
            }
            entries = [occurrence("sample:a", "key", "event.nut", metadata)]
            units, reasons = MODULE.classify_entries(entries, {"sample": str(root)})
        self.assertEqual(units, [])
        self.assertEqual(reasons["INTERNAL_TEMPLATE_VARIABLE_KEY"], 1)
        self.assertEqual(entries[0]["status"], "RESOLVED_EXCLUSION")

    def test_mixed_key_and_value_unit_is_review_required_not_representative_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            code = ('function f(_vars) { _vars.push(["same", "same"]); }')
            (root / "event.nut").write_text(code, encoding="utf-8")
            records = ROLES.analyze_squirrel_literals(code)["records"]
            entries = [
                occurrence(
                    f"sample:{index}",
                    "same",
                    "event.nut",
                    {field: record[field] for field in ROLES.REQUIRED_ROLE_FIELDS},
                )
                for index, record in enumerate(records)
            ]
            units, reasons = MODULE.classify_entries(entries, {"sample": str(root)})
        self.assertEqual(reasons, {})
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["role_gate"], ROLES.GATE_REVIEW_REQUIRED)
        self.assertTrue(all(item["status"] == "UNTRANSLATED" for item in entries))

    def test_source_drift_blocks_autoexclude(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = 'function f(_vars) { _vars.push(["key", value]); }'
            analysis = ROLES.analyze_squirrel_literals(original)
            metadata = {
                field: analysis["records"][0][field]
                for field in ROLES.REQUIRED_ROLE_FIELDS
            }
            (root / "event.nut").write_text(original.replace("value", "other"), encoding="utf-8")
            entries = [occurrence("sample:a", "key", "event.nut", metadata)]
            units, reasons = MODULE.classify_entries(entries, {"sample": str(root)})
        self.assertEqual(reasons, {})
        self.assertEqual(units[0]["role_gate"], ROLES.GATE_REVIEW_REQUIRED)

    def test_path_shaped_parser_value_is_never_heuristically_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            code = ('function f(_vars) { _vars.push(["image", '
                    '"ui/icons/example.png"]); }')
            (root / "event.nut").write_text(code, encoding="utf-8")
            record = ROLES.analyze_squirrel_literals(code)["records"][1]
            entries = [occurrence(
                "sample:value", "ui/icons/example.png", "event.nut",
                {field: record[field] for field in ROLES.REQUIRED_ROLE_FIELDS},
            )]
            units, reasons = MODULE.classify_entries(entries, {"sample": str(root)})
        self.assertEqual(reasons, {})
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["role_gate"], ROLES.GATE_MANUAL_REVIEW)
        self.assertEqual(entries[0]["status"], "UNTRANSLATED")

    def test_mixed_heuristic_context_remains_unresolved(self) -> None:
        entries = [
            occurrence("sample:path", "internalkey", "a.nut"),
            occurrence("sample:visible", "internalkey", "b.nut"),
        ]
        entries[0]["context"] = "Item.Icon"
        entries[1]["context"] = "Text"
        units, reasons = MODULE.classify_entries(entries, {})
        self.assertEqual(reasons, {})
        self.assertEqual(units[0]["role_gate"], ROLES.GATE_REVIEW_REQUIRED)

    def test_stateful_canonical_rebuild_is_refused(self) -> None:
        entry = occurrence("sample:a", "Visible", "a.nut")
        entry["status"] = "TRANSLATED"
        entry["review_status"] = "REVIEWED"
        entry["japanese"] = "表示"
        with self.assertRaisesRegex(ValueError, "refuses"):
            MODULE.require_fresh_extraction({"entries": [entry]})
        with self.assertRaisesRegex(ValueError, "fresh"):
            MODULE.require_fresh_extraction({"entries": [], "classification": {}})


if __name__ == "__main__":
    unittest.main()
