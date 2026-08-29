from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "create_category_batch.py"
SPEC = importlib.util.spec_from_file_location("create_category_batch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CategoryBatchTests(unittest.TestCase):
    def test_collects_assigned_units_from_batch_audit_and_review_metadata(self) -> None:
        payload = {
            "entries": [{"translation_unit": "translated"}],
            "findings": [{"translation_unit": "audited"}],
            "review_metadata": {
                "excluded_entries": [{"translation_unit": "candidate"}]
            },
        }
        self.assertEqual(
            MODULE.assigned_unit_ids(payload),
            {"translated", "audited", "candidate"},
        )

    def test_selects_only_untranslated_matching_occurrence(self) -> None:
        ledger = {"entries": [
            {"stable_key": "a", "module": "vanilla", "source": "scripts/items/sword.nut", "context": "Name", "channel": "squirrel", "mode": "literal", "source_code": []},
            {"stable_key": "b", "module": "legends", "source": "scripts/items/axe.nut", "context": "Name", "channel": "squirrel", "mode": "literal", "source_code": []},
        ]}
        units = {"units": [
            {"translation_unit": "u1", "english": "Sword", "status": "UNTRANSLATED", "occurrences": ["a"], "placeholder_signature": {}},
            {"translation_unit": "u2", "english": "Axe", "status": "TRANSLATED", "occurrences": ["b"], "placeholder_signature": {}},
        ]}
        result = MODULE.select_entries(units, ledger, module="vanilla", source_pattern=re.compile(r"scripts/items/"), channel="squirrel", mode="literal", limit=10)
        self.assertEqual([entry["translation_unit"] for entry in result], ["u1"])

    def test_excludes_units_already_assigned_to_an_active_batch(self) -> None:
        ledger = {"entries": [
            {"stable_key": "a", "module": "vanilla", "source": "scripts/events/a.nut", "context": "Text", "channel": "squirrel", "mode": "literal", "source_code": []},
            {"stable_key": "b", "module": "vanilla", "source": "scripts/events/b.nut", "context": "Text", "channel": "squirrel", "mode": "literal", "source_code": []},
        ]}
        units = {"units": [
            {"translation_unit": "active", "english": "Shared", "status": "UNTRANSLATED", "occurrences": ["a"], "placeholder_signature": {}},
            {"translation_unit": "new", "english": "New", "status": "UNTRANSLATED", "occurrences": ["b"], "placeholder_signature": {}},
        ]}
        result = MODULE.select_entries(
            units,
            ledger,
            module="vanilla",
            source_pattern=re.compile(r"scripts/events/"),
            channel="squirrel",
            mode="literal",
            limit=10,
            excluded_unit_ids={"active"},
        )
        self.assertEqual([entry["translation_unit"] for entry in result], ["new"])


if __name__ == "__main__":
    unittest.main()
