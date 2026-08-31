from __future__ import annotations

import importlib.util
import tempfile
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

    def validate_batch(self, batch, units):
        return MODULE.validate_batch(
            batch, units, enforce_role_evidence=False
        )

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
        self.assertEqual(len(self.validate_batch(batch, {"unit:test": self.unit})), 1)

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
            self.validate_batch(batch, {"unit:test": self.unit})

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
        validated = self.validate_batch(batch, {"unit:test": self.unit})
        self.assertEqual(validated[0]["notes"], ["mechanics checked"])

    def test_invalid_note_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "notes must be"):
            MODULE.normalize_notes({"unexpected": "mapping"})

    def test_resolved_boundary_hook_contract_is_accepted(self) -> None:
        batch = {
            "entries": [
                {
                    "translation_unit": "unit:test",
                    "english": "Welcome, %name%.",
                    "japanese": "%name%、ようこそ。",
                    "placeholder_signature": self.unit["placeholder_signature"],
                    "review_status": "REVIEWED",
                    "runtime_strategy": "BOUNDARY_HOOK",
                    "runtime_contract": {
                        "strategy": "BOUNDARY_HOOK",
                        "resolution_status": "RESOLVED",
                        "hook_target": "global::buildTextFromTemplate",
                    },
                }
            ]
        }
        validated = self.validate_batch(batch, {"unit:test": self.unit})
        self.assertEqual(validated[0]["runtime_strategy"], "BOUNDARY_HOOK")

    def test_boundary_hook_without_contract_is_rejected(self) -> None:
        batch = {
            "entries": [
                {
                    "translation_unit": "unit:test",
                    "english": "Welcome, %name%.",
                    "japanese": "%name%、ようこそ。",
                    "placeholder_signature": self.unit["placeholder_signature"],
                    "review_status": "REVIEWED",
                    "runtime_strategy": "BOUNDARY_HOOK",
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "requires runtime_contract"):
            self.validate_batch(batch, {"unit:test": self.unit})

    def test_actor_title_display_fragment_contract_is_accepted(self) -> None:
        batch = {
            "entries": [
                {
                    "translation_unit": "unit:test",
                    "english": "Welcome, %name%.",
                    "japanese": "%name%、ようこそ。",
                    "placeholder_signature": self.unit["placeholder_signature"],
                    "review_status": "REVIEWED",
                    "runtime_strategy": "ACTOR_TITLE_DISPLAY_FRAGMENT",
                    "runtime_contract": {
                        "strategy": "ACTOR_TITLE_DISPLAY_FRAGMENT",
                        "resolution_status": "RESOLVED",
                        "targets": ["generated Squirrel actor-title display registry", "generated JavaScript actor-title display registry"],
                        "operation": "Emit only through final display registries.",
                        "raw_state": "Keep actor identity and saves source-language.",
                        "acceptance": "Both registries contain the reviewed pair and raw state stays unchanged.",
                    },
                }
            ]
        }
        validated = self.validate_batch(batch, {"unit:test": self.unit})
        self.assertEqual(validated[0]["runtime_strategy"], "ACTOR_TITLE_DISPLAY_FRAGMENT")

    def test_actor_title_display_fragment_strategy_mismatch_is_rejected(self) -> None:
        batch = {
            "entries": [
                {
                    "translation_unit": "unit:test",
                    "english": "Welcome, %name%.",
                    "japanese": "%name%、ようこそ。",
                    "placeholder_signature": self.unit["placeholder_signature"],
                    "review_status": "REVIEWED",
                    "runtime_strategy": "ACTOR_TITLE_DISPLAY_FRAGMENT",
                    "runtime_contract": {
                        "strategy": "BOUNDARY_HOOK",
                        "resolution_status": "RESOLVED",
                        "targets": ["registry"],
                        "operation": "display only",
                        "raw_state": "raw",
                        "acceptance": "green",
                    },
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "strategy mismatch"):
            self.validate_batch(batch, {"unit:test": self.unit})

    def test_unknown_runtime_strategy_is_rejected(self) -> None:
        batch = {
            "entries": [
                {
                    "translation_unit": "unit:test",
                    "english": "Welcome, %name%.",
                    "japanese": "%name%、ようこそ。",
                    "placeholder_signature": self.unit["placeholder_signature"],
                    "review_status": "REVIEWED",
                    "runtime_strategy": "UNKNOWN_DISPLAY_MODE",
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "invalid runtime_strategy"):
            self.validate_batch(batch, {"unit:test": self.unit})

    def test_explicit_review_required_unit_gate_blocks_generic_apply(self) -> None:
        unit = dict(self.unit)
        unit["role_gate"] = MODULE.GATE_REVIEW_REQUIRED
        batch = {"entries": [{
            "translation_unit": "unit:test", "english": "Welcome, %name%.",
            "japanese": "%name%、ようこそ。",
            "placeholder_signature": self.unit["placeholder_signature"],
            "review_status": "REVIEWED",
        }]}
        with self.assertRaisesRegex(ValueError, "role gate blocks"):
            self.validate_batch(batch, {"unit:test": unit})

    def test_source_bound_value_evidence_is_accepted_and_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "event.nut"
            code = ('function f(_vars) { _vars.push(["name", '
                    '"Welcome, %name%."]); }')
            source.write_text(code, encoding="utf-8")
            occurrence = {
                "stable_key": "sample:value", "module": "sample", "source": "event.nut",
                "context": "onPrepareVariables._vars.push()", "channel": "squirrel",
                "mode": "literal", "english": "Welcome, %name%.",
                "translation_unit": "unit:test",
            }
            roots = {"sample": str(root)}
            enriched = MODULE.enrich_occurrence_role(occurrence, roots)
            evidence = MODULE.occurrence_evidence(enriched)
            unit = dict(self.unit)
            unit["occurrences"] = ["sample:value"]
            batch = {"schema_version": 2, "role_evidence_required": True, "entries": [{
                "translation_unit": "unit:test", "english": "Welcome, %name%.",
                "japanese": "%name%、ようこそ。",
                "placeholder_signature": self.unit["placeholder_signature"],
                "review_status": "REVIEWED",
                "unit_role_gate": MODULE.GATE_MANUAL_REVIEW,
                "occurrence_evidence": [evidence],
            }]}
            validated = MODULE.validate_batch(
                batch, {"unit:test": unit}, {"sample:value": occurrence}, roots
            )
            self.assertEqual(len(validated), 1)
            source.write_text(code.replace("name\",", "actor\","), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evidence drift"):
                MODULE.validate_batch(
                    batch, {"unit:test": unit}, {"sample:value": occurrence}, roots
                )

    def test_occurrence_set_drift_is_rejected(self) -> None:
        unit = dict(self.unit)
        unit["occurrences"] = ["a", "b"]
        batch = {"schema_version": 2, "role_evidence_required": True, "entries": [{
            "translation_unit": "unit:test", "english": "Welcome, %name%.",
            "japanese": "%name%、ようこそ。",
            "placeholder_signature": self.unit["placeholder_signature"],
            "review_status": "REVIEWED", "unit_role_gate": MODULE.GATE_MANUAL_REVIEW,
            "occurrence_evidence": [{"stable_key": "a"}],
        }]}
        with self.assertRaisesRegex(ValueError, "exactly cover"):
            MODULE.validate_batch(batch, {"unit:test": unit}, {}, {"sample": "unused"})

    def test_general_literal_source_drift_is_reparsed_and_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "screen.nut"
            code = 'function f() { local label = "Welcome, %name%."; return label; }'
            source.write_text(code, encoding="utf-8")
            occurrence = {
                "stable_key": "sample:general", "module": "sample", "source": "screen.nut",
                "context": "label", "channel": "squirrel", "mode": "literal",
                "english": "Welcome, %name%.", "translation_unit": "unit:test",
            }
            roots = {"sample": str(root)}
            evidence = MODULE.occurrence_evidence(
                MODULE.enrich_occurrence_role(occurrence, roots)
            )
            unit = dict(self.unit, occurrences=["sample:general"])
            batch = {"schema_version": 2, "role_evidence_required": True, "entries": [{
                "translation_unit": "unit:test", "english": "Welcome, %name%.",
                "japanese": "%name%、ようこそ。",
                "placeholder_signature": self.unit["placeholder_signature"],
                "review_status": "REVIEWED", "unit_role_gate": MODULE.GATE_MANUAL_REVIEW,
                "occurrence_evidence": [evidence],
            }]}
            MODULE.validate_batch(
                batch, {"unit:test": unit}, {"sample:general": occurrence}, roots
            )
            source.write_text(code.replace("return label", "return label + suffix"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evidence drift"):
                MODULE.validate_batch(
                    batch, {"unit:test": unit}, {"sample:general": occurrence}, roots
                )

    def test_canonical_occurrence_placeholder_signature_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "screen.nut").write_text(
                'function f() { return "Welcome, %name%."; }', encoding="utf-8"
            )
            occurrence = {
                "stable_key": "sample:general", "module": "sample", "source": "screen.nut",
                "context": "return", "channel": "squirrel", "mode": "literal",
                "english": "Welcome, %name%.",
                "placeholder_signature": self.unit["placeholder_signature"],
                "translation_unit": "unit:test",
            }
            roots = {"sample": str(root)}
            evidence = MODULE.occurrence_evidence(
                MODULE.enrich_occurrence_role(occurrence, roots)
            )
            unit = dict(self.unit, occurrences=["sample:general"])
            batch = {"schema_version": 2, "role_evidence_required": True, "entries": [{
                "translation_unit": "unit:test", "english": "Welcome, %name%.",
                "japanese": "%name%、ようこそ。",
                "placeholder_signature": self.unit["placeholder_signature"],
                "review_status": "REVIEWED", "unit_role_gate": MODULE.GATE_MANUAL_REVIEW,
                "occurrence_evidence": [evidence],
            }]}
            drifted = dict(occurrence, placeholder_signature={"percent_vars": []})
            with self.assertRaisesRegex(ValueError, "evidence drift"):
                MODULE.validate_batch(
                    batch, {"unit:test": unit}, {"sample:general": drifted}, roots
                )

    def test_canonical_occurrence_translation_unit_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "screen.nut").write_text(
                'function f() { return "Welcome, %name%."; }', encoding="utf-8"
            )
            occurrence = {
                "stable_key": "sample:general", "module": "sample", "source": "screen.nut",
                "context": "return", "channel": "squirrel", "mode": "literal",
                "english": "Welcome, %name%.", "translation_unit": "unit:test",
            }
            roots = {"sample": str(root)}
            evidence = MODULE.occurrence_evidence(
                MODULE.enrich_occurrence_role(occurrence, roots)
            )
            unit = dict(self.unit, occurrences=["sample:general"])
            batch = {"schema_version": 2, "role_evidence_required": True, "entries": [{
                "translation_unit": "unit:test", "english": "Welcome, %name%.",
                "japanese": "%name%、ようこそ。",
                "placeholder_signature": self.unit["placeholder_signature"],
                "review_status": "REVIEWED", "unit_role_gate": MODULE.GATE_MANUAL_REVIEW,
                "occurrence_evidence": [evidence],
            }]}
            drifted = dict(occurrence, translation_unit="unit:other")
            with self.assertRaisesRegex(ValueError, "translation-unit mismatch"):
                MODULE.validate_batch(
                    batch, {"unit:test": unit}, {"sample:general": drifted}, roots
                )

    def test_legacy_batch_without_role_evidence_is_rejected_by_default(self) -> None:
        batch = {"entries": [{
            "translation_unit": "unit:test", "english": "Welcome, %name%.",
            "japanese": "%name%、ようこそ。",
            "placeholder_signature": self.unit["placeholder_signature"],
            "review_status": "REVIEWED",
        }]}
        with self.assertRaisesRegex(ValueError, "schema-v2"):
            MODULE.validate_batch(batch, {"unit:test": self.unit})


if __name__ == "__main__":
    unittest.main()
