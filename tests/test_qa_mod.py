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


class TranslationReviewTrancheTests(unittest.TestCase):
    def test_exact_tranche_accounting_is_accepted(self) -> None:
        units = {
            "units": [
                {"status": "TRANSLATED", "review_status": "REVIEWED"},
                {"status": "TRANSLATED", "review_status": "REVIEWED"},
                {"status": "UNTRANSLATED", "review_status": "NOT_REVIEWED"},
            ]
        }
        tranches = {
            "canonical_reviewed_units": 2,
            "translated_needs_review_units": 0,
            "tranches": [
                {"name": "first", "reviewed_units": 1},
                {"name": "second", "reviewed_units": 9, "canonical_count_delta": 1},
            ],
        }
        errors = MODULE.translation_review_tranche_errors(units, tranches)
        self.assertFalse(errors["malformed_tranche_indexes"])
        self.assertFalse(errors["duplicate_tranche_names"])
        self.assertFalse(errors["count_mismatches"])

    def test_stale_or_duplicate_tranche_report_is_rejected(self) -> None:
        units = {"units": [{"status": "TRANSLATED", "review_status": "REVIEWED"}]}
        tranches = {
            "canonical_reviewed_units": 2,
            "translated_needs_review_units": 1,
            "tranches": [
                {"name": "same", "reviewed_units": 1},
                {"name": "same", "reviewed_units": 1},
            ],
        }
        errors = MODULE.translation_review_tranche_errors(units, tranches)
        self.assertEqual(errors["duplicate_tranche_names"], ["same"])
        self.assertEqual(len(errors["count_mismatches"]), 3)


class BoundManifestCheckTests(unittest.TestCase):
    def test_manifest_checks_always_return_a_qa_result(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        checks = (
            MODULE.check_runtime_reachability_map(repo),
            MODULE.check_package_source_manifest(repo, repo / "src"),
            MODULE.check_external_composition_contract(repo),
        )
        for check in checks:
            self.assertIsInstance(check, dict)
            self.assertEqual(check.get("status"), "PASS", check)
            self.assertIsInstance(check.get("detail"), dict)


class ActorTitleRegistryTests(unittest.TestCase):
    def test_cross_layer_longest_first_registry_is_accepted(self) -> None:
        squirrel = '''
::BattleBrothersJP.ActorTitleDisplayFragments <- [
    { english = "the Old Guard" japanese = "古参兵" }
    { english = "the Old" japanese = "老人" }
];
::BattleBrothersJP.ActorTitleGenericDisplayFragments <- [
    { english = "the Old Guard" japanese = "古参兵" }
];
'''
        javascript = '''
window.BattleBrothersJPActorTitleFragments = {
    "the Old Guard": "古参兵",
    "the Old": "老人"
};
window.BattleBrothersJPGenericActorTitleFragments = {
    "the Old Guard": "古参兵"
};
'''
        errors = MODULE.actor_title_registry_errors(
            squirrel,
            javascript,
            {
                "reviewed_actor_title_display_fragments": 2,
                "reviewed_generic_actor_title_display_fragments": 1,
            },
        )
        self.assertEqual(errors["squirrel_block_count"], 1)
        self.assertEqual(errors["javascript_block_count"], 1)
        self.assertFalse(any(
            value for key, value in errors.items()
            if key not in {
                "squirrel_block_count",
                "javascript_block_count",
                "generic_squirrel_block_count",
                "generic_javascript_block_count",
            }
        ))

    def test_short_prefix_first_and_cross_layer_drift_are_rejected(self) -> None:
        squirrel = '''
::BattleBrothersJP.ActorTitleDisplayFragments <- [
    { english = "the Old" japanese = "老人" }
    { english = "the Old Guard" japanese = "古参兵" }
];
::BattleBrothersJP.ActorTitleGenericDisplayFragments <- [
    { english = "the Stranger" japanese = "よそ者" }
];
'''
        javascript = '''
window.BattleBrothersJPActorTitleFragments = {
    "the Old Guard": "古参兵",
    "the Old": "古老"
};
window.BattleBrothersJPGenericActorTitleFragments = {
    "the Stranger": "よそ者"
};
'''
        errors = MODULE.actor_title_registry_errors(
            squirrel,
            javascript,
            {
                "reviewed_actor_title_display_fragments": 3,
                "reviewed_generic_actor_title_display_fragments": 1,
            },
        )
        self.assertTrue(errors["order_mismatch"])
        self.assertTrue(errors["cross_layer_mismatch"])
        self.assertTrue(errors["manifest_count_mismatch"])
        self.assertTrue(errors["generic_not_subset"])


if __name__ == "__main__":
    unittest.main()
