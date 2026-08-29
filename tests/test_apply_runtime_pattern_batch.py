from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "apply_runtime_pattern_batch.py"
SPEC = importlib.util.spec_from_file_location("apply_runtime_pattern_batch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimePatternValidationTests(unittest.TestCase):
    def test_valid_rosetta_pattern(self) -> None:
        MODULE.validate_rosetta_contract({
            "translation_unit": "unit:test",
            "runtime_en": "Gain <value:int> Resolve",
            "runtime_ja": "決意が<value>増加する",
            "samples": [{"english": "Gain 5 Resolve", "japanese": "決意が5増加する"}],
        })

    def test_raw_extractor_hint_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Raw or invalid"):
            MODULE.validate_rosetta_contract({
                "translation_unit": "unit:test",
                "runtime_en": "Gain <this.m.Value> Resolve",
                "runtime_ja": "決意が<this.m.Value>増加する",
                "samples": [{"english": "Gain 5 Resolve", "japanese": "決意が5増加する"}],
            })

    def test_duplicate_capture_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate capture"):
            MODULE.validate_rosetta_contract({
                "translation_unit": "unit:test",
                "runtime_en": "<x:int> and <x:int>",
                "runtime_ja": "<x>と<x>",
                "samples": [{"english": "1 and 2", "japanese": "1と2"}],
            })

    def test_bounded_correction_preserves_prior_evidence(self) -> None:
        unit = {"runtime_contract": {"source": "scripts/example.nut", "runtime_en": "<old:int>"}}
        entry = {
            "translation_unit": "unit:test",
            "english": "<raw>",
            "runtime_en": "<value:int>",
            "runtime_ja": "<value>",
        }
        merged = MODULE.merge_runtime_contract(unit, entry)
        self.assertEqual(merged["source"], "scripts/example.nut")
        self.assertEqual(merged["runtime_en"], "<value:int>")
        self.assertNotIn("translation_unit", merged)


if __name__ == "__main__":
    unittest.main()
