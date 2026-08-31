from __future__ import annotations

import json
import re
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "reports" / "public-ecosystem-profile.json"
SNAPSHOT_LOCK_PATH = ROOT / "reports" / "supported-snapshot-lock.json"
AUDIT_PATH = ROOT / "docs" / "PUBLIC_ECOSYSTEM_AUDIT.md"
ADR_PATH = ROOT / "docs" / "ARCHITECTURE_DECISIONS.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class PublicEcosystemProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_json(PROFILE_PATH)
        cls.snapshot = load_json(SNAPSHOT_LOCK_PATH)

    def test_current_verified_snapshot_is_bound_to_installed_lock(self) -> None:
        current = self.profile["current_verified_source_snapshot"]
        self.assertEqual(current["snapshot_id"], self.snapshot["installed_snapshot_id"])
        self.assertEqual(current["steam_build_id"], self.snapshot["steam_build_id"])
        self.assertEqual(current["legends"], "19.4.20")
        self.assertEqual(current["legends_assets"], "19.4.3")

    def test_public_latest_is_not_silently_claimed_verified(self) -> None:
        current = self.profile["current_verified_source_snapshot"]
        latest = self.profile["public_latest_observed"]
        target = self.profile["next_public_release_target"]
        self.assertNotEqual(current["legends"], latest["legends"])
        self.assertEqual(target["legends_public_delta_candidate"], latest["legends"])
        self.assertNotIn("VERIFIED", target["legends_public_delta_status"])
        self.assertEqual(
            target["legends_public_delta_evidence"]["runtime_qa"],
            "NOT_TESTED",
        )

    def test_vanilla_install_has_only_the_selected_framework_dependency(self) -> None:
        architecture = self.profile["selected_public_architecture"]
        install = self.profile["install_convention"]
        self.assertEqual(
            architecture["hard_dependencies"],
            ["mod_modern_hooks >= 0.6.0"],
        )
        self.assertEqual(
            set(architecture["not_required_or_bundled_by_jp"]),
            {"mod_rosetta", "stdlib"},
        )
        self.assertTrue(
            architecture["independently_installed_rosetta_stdlib_coexistence_allowed"]
        )
        self.assertFalse(install["vanilla_user_requires_legends"])
        self.assertFalse(install["vanilla_user_requires_msu"])
        self.assertFalse(install["vanilla_user_requires_rosetta"])
        self.assertFalse(install["vanilla_user_requires_stdlib"])
        self.assertFalse(install["unzip"])
        self.assertEqual(install["artifact_count"], 1)

    def test_runtime_policy_is_offline_and_fail_safe(self) -> None:
        architecture = self.profile["selected_public_architecture"]
        self.assertFalse(architecture["normal_gameplay_network_required"])
        self.assertEqual(
            architecture["unknown_text_policy"],
            "ORIGINAL_ENGLISH_PASS_THROUGH",
        )
        self.assertEqual(
            architecture["unknown_mod_policy"],
            "NO_SPECULATIVE_GLOBAL_TRANSLATION",
        )

    def test_queue_buckets_and_effective_pattern_inventory_are_explicit(self) -> None:
        queue = self.profile["queue_semantics"]
        inventory = self.profile["runtime_migration_inventory"]
        self.assertEqual(queue["default_registration_bucket"], "Normal")
        self.assertEqual(queue["audited_final_display_bucket"], "Late")
        self.assertEqual(queue["order_relations_scope"], "SAME_BUCKET_ONLY")
        self.assertEqual(inventory["generated_reviewed_pattern_rules"], 122)
        self.assertEqual(inventory["manual_reviewed_context_pattern_rules"], 1)
        self.assertEqual(inventory["effective_reviewed_pattern_rules"], 123)
        self.assertEqual(inventory["val_capture_rules"], 0)
        self.assertNotIn("val", inventory["effective_capture_types"])

    def assert_valid_legends_delta_evidence(self, evidence: dict[str, Any]) -> None:
        self.assertEqual(
            evidence["official_compare_url"],
            "https://github.com/Battle-Brothers-Legends/Legends-public/compare/19.4.20...19.4.21",
        )
        self.assertEqual(
            evidence["base_commit_sha"],
            "d0e0dc3c34ff87cd5a737038b1648ce135e66985",
        )
        self.assertEqual(
            evidence["head_commit_sha"],
            "3238e8a0dc326683e17f11777627ae971e6f2b29",
        )
        self.assertRegex(evidence["base_commit_sha"], r"\A[0-9a-f]{40}\Z")
        self.assertRegex(evidence["head_commit_sha"], r"\A[0-9a-f]{40}\Z")
        self.assertTrue(evidence["classifications_are_nonexclusive"])
        self.assertEqual(evidence["distinct_archive_files"], 37)
        expected_releases = {
            "19.4.20": {
                "url": "https://github.com/Battle-Brothers-Legends/Legends-public/releases/download/19.4.20/mod_legends-19.4.20.zip",
                "size": 5453255,
                "sha256": "6A1E1482BF909EEC2E0ECE70C3992BA80FAB5A948B9CD0625063B1729B002A71",
            },
            "19.4.21": {
                "url": "https://github.com/Battle-Brothers-Legends/Legends-public/releases/download/19.4.21/mod_legends-19.4.21.zip",
                "size": 5453780,
                "sha256": "A8468E36B43A8501A05900288308F2FEF629CB37B64F7126A001558A0CFD07FD",
            },
        }
        self.assertEqual(evidence["release_assets"], expected_releases)
        for release in evidence["release_assets"].values():
            self.assertIs(type(release["size"]), int)
            self.assertGreater(release["size"], 0)
            self.assertIsNotNone(re.fullmatch(r"[0-9A-F]{64}", release["sha256"]))

    def test_delta_evidence_is_reproducible_from_a_clean_clone(self) -> None:
        evidence = self.profile["next_public_release_target"][
            "legends_public_delta_evidence"
        ]
        self.assert_valid_legends_delta_evidence(evidence)

    def test_delta_fingerprint_contract_rejects_mutations(self) -> None:
        original = self.profile["next_public_release_target"][
            "legends_public_delta_evidence"
        ]
        mutations = {
            "compare_url": lambda value: value.__setitem__(
                "official_compare_url", "https://example.invalid/fake"
            ),
            "base_commit": lambda value: value.__setitem__(
                "base_commit_sha", "x" * 40
            ),
            "head_commit": lambda value: value.__setitem__(
                "head_commit_sha", "y" * 40
            ),
            "release_url": lambda value: value["release_assets"]["19.4.21"].__setitem__(
                "url", "https://example.invalid/mod_legends.zip"
            ),
            "release_size": lambda value: value["release_assets"]["19.4.21"].__setitem__(
                "size", -1
            ),
            "release_digest": lambda value: value["release_assets"]["19.4.21"].__setitem__(
                "sha256", "z" * 64
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                candidate = deepcopy(original)
                mutate(candidate)
                with self.assertRaises(AssertionError):
                    self.assert_valid_legends_delta_evidence(candidate)

    def test_known_incompatible_has_a_distinct_runtime_mapping(self) -> None:
        self.assertIn("KNOWN_INCOMPATIBLE", self.profile["compatibility_states"])
        mapping = self.profile["compatibility_state_mapping"]
        self.assertEqual(mapping["KNOWN_INCOMPATIBLE"], "UNSUPPORTED")
        self.assertNotEqual(
            mapping["KNOWN_INCOMPATIBLE_meaning"],
            mapping["KNOWN_CONFLICT_meaning"],
        )

    def test_all_evidence_links_are_https(self) -> None:
        urls = [
            url
            for component in self.profile["components"]
            for url in component.get("evidence", [])
        ]
        self.assertGreaterEqual(len(urls), 10)
        self.assertTrue(all(url.startswith("https://") for url in urls))

    def test_required_user_facing_documents_exist_and_name_all_version_states(self) -> None:
        audit = AUDIT_PATH.read_text(encoding="utf-8")
        adr = ADR_PATH.read_text(encoding="utf-8")
        for marker in (
            "CURRENT_VERIFIED_SOURCE_SNAPSHOT",
            "PUBLIC_LATEST",
            "NEXT_PUBLIC_RELEASE_TARGET",
        ):
            self.assertIn(marker, audit)
        self.assertIn("Single ZIP + safely conditional modules", adr)
        self.assertIn("mod_modern_hooks >= 0.6.0", adr)

    def test_write_audit_remains_zero(self) -> None:
        self.assertEqual(self.profile["actual_user_environment_writes"], 0)


if __name__ == "__main__":
    unittest.main()
