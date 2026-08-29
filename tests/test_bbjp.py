from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "bbjp.py"
SPEC = importlib.util.spec_from_file_location("bbjp", MODULE_PATH)
assert SPEC and SPEC.loader
bbjp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bbjp)


class UtilityTests(unittest.TestCase):
    def test_canonical_hash_is_order_independent_for_mappings(self) -> None:
        self.assertEqual(
            bbjp.canonical_sha256({"b": 2, "a": 1}),
            bbjp.canonical_sha256({"a": 1, "b": 2}),
        )

    def test_archive_summary_finds_nested_preload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "mod_test.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("mod_test/scripts/!mods_preload/mod_test.nut", "::Hooks.register(\"x\");")
                archive.writestr("mod_test/ui/test.js", "const label = 'Test';")
            summary = bbjp.archive_summary(archive_path)
            self.assertEqual(summary["entry_count"], 2)
            self.assertEqual(
                summary["preload_entries"],
                ["mod_test/scripts/!mods_preload/mod_test.nut"],
            )

    def test_safe_member_rejects_parent_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                bbjp.safe_member_path(Path(temp_dir), "../outside.txt")

    def test_data_file_classification_does_not_imply_active(self) -> None:
        self.assertEqual(
            bbjp.classify_data_file("mod_example.zip"),
            ("mod_archive", "LOAD_CANDIDATE"),
        )
        self.assertEqual(
            bbjp.classify_data_file("mod_modern_hooks.zip"),
            ("mod_archive", "FRAMEWORK"),
        )

    def test_runtime_registration_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "log.html"
            log_path.write_text(
                '<div class="row info"><div class="text">'
                'Modern Hooks registered <span class="valueVar">Legends Mod</span> '
                '(<span class="valueVar">mod_legends</span>) version '
                '<span class="valueVar">19.4.20</span>'
                '</div></div>',
                encoding="utf-8",
            )
            parsed = bbjp.parse_runtime_log(log_path)
            self.assertEqual(
                parsed["registrations"],
                [{"name": "Legends Mod", "id": "mod_legends", "version": "19.4.20"}],
            )

    def test_snapshot_diff_reports_added_removed_and_changed_files(self) -> None:
        before = {
            "installed_snapshot_id": "old",
            "data_files": [
                {"relative_path": "same.zip", "sha256": "A"},
                {"relative_path": "changed.zip", "sha256": "B"},
                {"relative_path": "removed.zip", "sha256": "C"},
            ],
        }
        after = {
            "installed_snapshot_id": "new",
            "data_files": [
                {"relative_path": "same.zip", "sha256": "A"},
                {"relative_path": "changed.zip", "sha256": "D"},
                {"relative_path": "added.zip", "sha256": "E"},
            ],
        }
        result = bbjp.snapshot_diff_payload(before, after)
        self.assertTrue(result["snapshot_changed"])
        self.assertEqual(result["added_data_files"], ["added.zip"])
        self.assertEqual(result["removed_data_files"], ["removed.zip"])
        self.assertEqual(result["changed_data_files"], ["changed.zip"])
        self.assertEqual(result["unchanged_data_files"], ["same.zip"])


if __name__ == "__main__":
    unittest.main()
