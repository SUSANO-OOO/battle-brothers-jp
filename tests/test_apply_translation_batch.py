from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "apply_translation_batch.py"
SPEC = importlib.util.spec_from_file_location("apply_translation_batch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TranslationBatchValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit = {
            "translation_unit": "unit:test",
            "english": "Welcome, %name%.",
            "placeholder_signature": MODULE.signature("Welcome, %name%."),
        }

    def test_valid_batch_preserves_placeholder(self) -> None:
        batch = {
            "entries": [
                {
                    "translation_unit": "unit:test",
                    "english": "Welcome, %name%.",
                    "japanese": "%name%、ようこそ。",
                    "placeholder_signature": self.unit["placeholder_signature"],
                    "review_status": "REVIEWED",
                }
            ]
        }
        self.assertEqual(len(MODULE.validate_batch(batch, {"unit:test": self.unit})), 1)

    def test_missing_placeholder_is_rejected(self) -> None:
        batch = {
            "entries": [
                {
                    "translation_unit": "unit:test",
                    "english": "Welcome, %name%.",
                    "japanese": "ようこそ。",
                    "placeholder_signature": self.unit["placeholder_signature"],
                    "review_status": "REVIEWED",
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "signature mismatch"):
            MODULE.validate_batch(batch, {"unit:test": self.unit})

    def test_named_percent_variable_is_not_double_counted_as_printf(self) -> None:
        value = MODULE.signature("Welcome, %dragonslayer%. Value: %d")
        self.assertEqual(value["percent_vars"], ["%dragonslayer%"])
        self.assertEqual(value["printf"], ["%d"])

    def test_string_note_is_kept_as_one_note(self) -> None:
        batch = {
            "entries": [
                {
                    "translation_unit": "unit:test",
                    "english": "Welcome, %name%.",
                    "japanese": "%name%、ようこそ。",
                    "placeholder_signature": self.unit["placeholder_signature"],
                    "review_status": "REVIEWED",
                    "notes": "mechanics checked",
                }
            ]
        }
        validated = MODULE.validate_batch(batch, {"unit:test": self.unit})
        self.assertEqual(validated[0]["notes"], ["mechanics checked"])

    def test_invalid_note_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "notes must be"):
            MODULE.normalize_notes({"unexpected": "mapping"})


if __name__ == "__main__":
    unittest.main()
