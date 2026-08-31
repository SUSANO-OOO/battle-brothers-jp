from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "create_context_split_plan.py"
SPEC = importlib.util.spec_from_file_location("create_context_split_plan", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CreateContextSplitPlanTests(unittest.TestCase):
    def test_legacy_candidate_classification_is_used_when_prior_note_is_absent(self) -> None:
        self.assertEqual(
            MODULE.reason_code({"candidate_classification": "template_variable_key"}),
            "template_variable_key",
        )

    def test_builds_exact_excluded_and_player_facing_variants(self) -> None:
        audit = {"audit_id": "audit:mixed", "findings": [
            {
                "translation_unit": "unit:mixed", "stable_key": "vanilla:key",
                "classification": "RESOLVED_EXCLUSION", "prior_note_classification": "INTERNAL_KEY",
                "reason": "Machine key.", "source_evidence": {"verified": True},
            },
            {
                "translation_unit": "unit:mixed", "stable_key": "legends:visible",
                "classification": "PLAYER_FACING_REVIEW_REQUIRED", "prior_note_classification": "PLAYER_FACING_NAME",
                "reason": "Displayed name.", "source_evidence": {"verified": True},
            },
        ]}
        units = {"units": [{
            "translation_unit": "unit:mixed", "english": "Shared", "status": "UNTRANSLATED",
            "review_status": "NOT_REVIEWED", "occurrences": ["vanilla:key", "legends:visible"],
        }]}
        plan = MODULE.build_plan(audit, units, "plan:mixed")
        self.assertEqual(len(plan["splits"]), 1)
        self.assertEqual(plan["splits"][0]["variants"][0]["stable_keys"], ["vanilla:key"])
        self.assertEqual(plan["splits"][0]["variants"][1]["stable_keys"], ["legends:visible"])

    def test_rejects_incomplete_mixed_audit(self) -> None:
        audit = {"findings": [
            {
                "translation_unit": "unit:mixed", "stable_key": "vanilla:key",
                "classification": "RESOLVED_EXCLUSION", "prior_note_classification": "INTERNAL_KEY",
                "reason": "Machine key.", "source_evidence": {"verified": True},
            },
            {
                "translation_unit": "unit:mixed", "stable_key": "legends:visible",
                "classification": "PLAYER_FACING_REVIEW_REQUIRED", "prior_note_classification": "PLAYER_FACING_NAME",
                "reason": "Displayed name.", "source_evidence": {"verified": True},
            },
        ]}
        units = {"units": [{
            "translation_unit": "unit:mixed", "english": "Shared", "status": "UNTRANSLATED",
            "review_status": "NOT_REVIEWED", "occurrences": ["vanilla:key", "legends:visible", "extra"],
        }]}
        with self.assertRaisesRegex(ValueError, "exactly cover"):
            MODULE.build_plan(audit, units, "plan:mixed")

    def test_role_gated_split_requires_verified_proven_internal_partition(self) -> None:
        evidence = {
            "evidence_fingerprint": "A" * 64,
            "literal_role": MODULE.ROLE_BINDING_KEY,
            "role_confidence": MODULE.PARSER_PROVEN,
        }
        audit = {"findings": [
            {"translation_unit": "unit:mixed", "stable_key": "key",
             "classification": "RESOLVED_EXCLUSION", "candidate_classification": "INTERNAL_KEY",
             "reason": "Machine key.", "source_evidence": {"verified": True},
             "unit_role_gate": MODULE.GATE_REVIEW_REQUIRED,
             "role_metadata_verified": True, "occurrence_evidence": evidence},
            {"translation_unit": "unit:mixed", "stable_key": "visible",
             "classification": "PLAYER_FACING_REVIEW_REQUIRED", "reason": "Displayed.",
             "source_evidence": {"verified": True},
             "unit_role_gate": MODULE.GATE_REVIEW_REQUIRED,
             "role_metadata_verified": True,
             "occurrence_evidence": {**evidence, "evidence_fingerprint": "B" * 64,
                                     "literal_role": "LOCALIZATION_CANDIDATE"}},
        ]}
        units = {"units": [{
            "translation_unit": "unit:mixed", "english": "Shared", "status": "UNTRANSLATED",
            "review_status": "NOT_REVIEWED", "occurrences": ["key", "visible"],
            "role_gate": MODULE.GATE_REVIEW_REQUIRED,
        }]}
        plan = MODULE.build_plan(audit, units, "plan:strict")
        self.assertEqual(
            plan["splits"][0]["variants"][1]["role_gate_after_review"],
            MODULE.GATE_MANUAL_REVIEW,
        )
        audit["findings"][0]["role_metadata_verified"] = False
        with self.assertRaisesRegex(ValueError, "unverified role"):
            MODULE.build_plan(audit, units, "plan:strict")


if __name__ == "__main__":
    unittest.main()
