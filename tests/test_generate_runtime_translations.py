from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_runtime_translations.py"
SPEC = importlib.util.spec_from_file_location("generate_runtime_translations", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimeGenerationTests(unittest.TestCase):
    def test_only_reviewed_literals_are_emitted(self) -> None:
        ledger = {
            "entries": [
                {"stable_key": "v", "module": "vanilla", "channel": "squirrel"},
                {"stable_key": "j", "module": "vanilla_ui", "channel": "javascript"},
                {"stable_key": "p", "module": "vanilla", "channel": "squirrel"},
            ]
        }
        units = {
            "units": [
                {"translation_unit": "literal", "english": "Save", "japanese": "保存", "mode": "literal", "status": "TRANSLATED", "review_status": "REVIEWED", "occurrences": ["v", "j"]},
                {"translation_unit": "pattern", "english": "<raw.Expression> hits", "japanese": "<raw.Expression>が命中", "mode": "pattern", "status": "TRANSLATED", "review_status": "REVIEWED", "occurrences": ["p"]},
                {"translation_unit": "draft", "english": "Draft", "japanese": "草稿", "mode": "literal", "status": "TRANSLATED", "review_status": "DRAFT_INDEPENDENT_REVIEW_REQUIRED", "occurrences": ["v"]},
            ]
        }
        squirrel, javascript, emitted, pending, boundary = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel["vanilla"], [{"en": "Save", "ja": "保存"}])
        self.assertEqual(javascript, {"Save": "保存"})
        self.assertEqual(emitted, ["literal"])
        self.assertEqual(pending, ["pattern"])
        self.assertEqual(boundary, [])

    def test_boundary_hook_strategy_is_not_emitted_as_global_literal(self) -> None:
        ledger = {"entries": [{"stable_key": "g", "module": "vanilla", "channel": "squirrel"}]}
        units = {"units": [{"translation_unit": "general-title", "english": "General", "japanese": "将軍", "mode": "literal", "status": "TRANSLATED", "review_status": "REVIEWED", "occurrences": ["g"], "runtime_strategy": "BOUNDARY_HOOK"}]}
        squirrel, javascript, emitted, pending, boundary = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel, {})
        self.assertEqual(javascript, {})
        self.assertEqual(emitted, [])
        self.assertEqual(pending, [])
        self.assertEqual(boundary, ["general-title"])

    def test_literal_source_can_emit_only_an_anchored_final_display_pattern(self) -> None:
        ledger = {"entries": [{"stable_key": "d", "module": "legends", "channel": "squirrel"}]}
        units = {"units": [{
            "translation_unit": "dame-title",
            "english": "Dame",
            "japanese": "デイム",
            "mode": "literal",
            "status": "TRANSLATED",
            "review_status": "REVIEWED",
            "occurrences": ["d"],
            "runtime_strategy": "ROSETTA_PATTERN",
            "runtime_contract": {
                "strategy": "ROSETTA_PATTERN",
                "resolution_status": "RESOLVED",
                "runtime_en": "Dame <first:word><rest:str>",
                "runtime_ja": "デイム・<first><rest>",
                "samples": [{"english": "Dame Roderick", "japanese": "デイム・Roderick"}],
            },
        }]}
        squirrel, javascript, emitted, pending, boundary = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel, {})
        self.assertEqual(javascript, {})
        self.assertEqual(emitted, [])
        self.assertEqual(pending, [])
        self.assertEqual(boundary, [])
        patterns, emitted, pending, boundary, samples = MODULE.reviewed_pattern_units(units, ledger)
        self.assertEqual(patterns["legends"], [{"en": "Dame <first:word><rest:str>", "ja": "デイム・<first><rest>", "mode": "pattern"}])
        self.assertEqual(emitted, ["dame-title"])
        self.assertEqual(pending, [])
        self.assertEqual(boundary, [])
        self.assertEqual(samples, [{"translation_unit": "dame-title", "english": "Dame Roderick", "japanese": "デイム・Roderick"}])

    def test_literal_source_captureless_runtime_rule_is_rejected(self) -> None:
        ledger = {"entries": [{"stable_key": "d", "module": "legends", "channel": "squirrel"}]}
        units = {"units": [{
            "translation_unit": "dame-title",
            "english": "Dame",
            "japanese": "デイム",
            "mode": "literal",
            "status": "TRANSLATED",
            "review_status": "REVIEWED",
            "occurrences": ["d"],
            "runtime_strategy": "ROSETTA_PATTERN",
            "runtime_contract": {
                "strategy": "ROSETTA_PATTERN",
                "resolution_status": "RESOLVED",
                "runtime_en": "Dame",
                "runtime_ja": "デイム",
                "samples": [{"english": "Dame", "japanese": "デイム"}],
            },
        }]}
        with self.assertRaisesRegex(ValueError, "at least one capture"):
            MODULE.reviewed_pattern_units(units, ledger)

    def test_cross_module_squirrel_literal_is_registered_once(self) -> None:
        ledger = {"entries": [
            {"stable_key": "v", "module": "vanilla", "channel": "squirrel"},
            {"stable_key": "l", "module": "legends", "channel": "squirrel"},
        ]}
        units = {"units": [{"translation_unit": "shared", "english": "Retreat", "japanese": "撤退", "mode": "literal", "status": "TRANSLATED", "review_status": "REVIEWED", "occurrences": ["v", "l"]}]}
        squirrel, _, emitted, _, _ = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel, {"vanilla": [{"en": "Retreat", "ja": "撤退"}]})
        self.assertEqual(emitted, ["shared"])

    def test_squirrel_quoting_is_json_compatible(self) -> None:
        self.assertEqual(MODULE.quoted('A "quoted" line\n'), '"A \\"quoted\\" line\\n"')

    def test_regex_equivalent_capture_names_are_rejected(self) -> None:
        ledger = {"entries": [
            {"stable_key": "a", "module": "vanilla", "channel": "squirrel"},
            {"stable_key": "b", "module": "legends", "channel": "squirrel"},
        ]}
        base = {"mode": "pattern", "status": "TRANSLATED", "review_status": "REVIEWED"}
        units = {"units": [
            {**base, "translation_unit": "a", "occurrences": ["a"], "runtime_contract": {
                "resolution_status": "RESOLVED", "strategy": "ROSETTA_PATTERN",
                "runtime_en": "<value:val_tag> Resolve", "runtime_ja": "精神力 <value>", "samples": []}},
            {**base, "translation_unit": "b", "occurrences": ["b"], "runtime_contract": {
                "resolution_status": "RESOLVED", "strategy": "ROSETTA_PATTERN",
                "runtime_en": "<bonus:val_tag> Resolve", "runtime_ja": "精神力 <bonus>", "samples": []}},
        ]}
        with self.assertRaisesRegex(ValueError, "Regex-equivalent"):
            MODULE.reviewed_pattern_units(units, ledger)


if __name__ == "__main__":
    unittest.main()
