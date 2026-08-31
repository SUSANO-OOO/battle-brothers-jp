from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "build_mod.py"
SPEC = importlib.util.spec_from_file_location("build_mod", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReleaseSemanticLimitationTests(unittest.TestCase):
    def test_open_semantic_limitation_blocks_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            reports = repo / "reports"
            reports.mkdir()
            (reports / "upstream-source-limitations.json").write_text(
                json.dumps({"status": "OPEN_SEMANTIC_LIMITATION", "entries": [{}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "refuses open"):
                MODULE.verify_semantic_limitations(repo)

    def test_resolved_semantic_audit_allows_release_gate_to_continue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            reports = repo / "reports"
            reports.mkdir()
            (reports / "upstream-source-limitations.json").write_text(
                json.dumps({"status": "RESOLVED", "entries": []}),
                encoding="utf-8",
            )
            MODULE.verify_semantic_limitations(repo)


class AtomicReleaseBuildTests(unittest.TestCase):
    @staticmethod
    def assembled(_repo: Path, candidate: Path, *_args: object) -> dict[str, object]:
        candidate.write_bytes(b"candidate")
        digest = MODULE.sha256(candidate)
        return {
            "artifact": str(candidate),
            "artifact_sha256": digest,
            "archive_verification": {"archive_sha256": digest},
        }

    def test_missing_qa_tools_do_not_touch_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            output = repo / "dist" / "mod.zip"
            output.parent.mkdir()
            output.write_bytes(b"existing")
            with self.assertRaisesRegex(ValueError, "requires existing"):
                MODULE.build(repo, output, False)
            self.assertEqual(output.read_bytes(), b"existing")

    def test_failed_qa_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            output = repo / "dist" / "mod.zip"
            output.parent.mkdir()
            output.write_bytes(b"existing")
            sq = repo / "sq.exe"
            node = repo / "node.exe"
            sq.write_bytes(b"tool")
            node.write_bytes(b"tool")
            qa_report = repo / "reports" / "local" / "qa.json"
            with mock.patch.object(MODULE, "_assemble_candidate", side_effect=self.assembled), \
                 mock.patch.object(MODULE.subprocess, "run", return_value=MODULE.subprocess.CompletedProcess([], 1)):
                with self.assertRaisesRegex(ValueError, "QA failed"):
                    MODULE.build(repo, output, False, sq=sq, node=node, qa_report=qa_report)
            self.assertEqual(output.read_bytes(), b"existing")

    def test_qa_sha_mismatch_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            output = repo / "dist" / "mod.zip"
            output.parent.mkdir()
            output.write_bytes(b"existing")
            sq = repo / "sq.exe"
            node = repo / "node.exe"
            sq.write_bytes(b"tool")
            node.write_bytes(b"tool")
            qa_report = repo / "reports" / "local" / "qa.json"

            def fake_run(_command: list[str], **_kwargs: object) -> object:
                qa_report.parent.mkdir(parents=True, exist_ok=True)
                qa_report.write_text(json.dumps({
                    "status": "PASS",
                    "checks": [{
                        "name": "archive_structure_and_content",
                        "status": "PASS",
                        "detail": {"artifact_sha256": "WRONG"},
                    }],
                }), encoding="utf-8")
                return MODULE.subprocess.CompletedProcess([], 0)

            with mock.patch.object(MODULE, "_assemble_candidate", side_effect=self.assembled), \
                 mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "not bound"):
                    MODULE.build(repo, output, False, sq=sq, node=node, qa_report=qa_report)
            self.assertEqual(output.read_bytes(), b"existing")

    def test_passed_bound_qa_atomically_publishes_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            output = repo / "dist" / "mod.zip"
            output.parent.mkdir()
            output.write_bytes(b"existing")
            sq = repo / "sq.exe"
            node = repo / "node.exe"
            sq.write_bytes(b"tool")
            node.write_bytes(b"tool")
            qa_report = repo / "reports" / "local" / "qa.json"

            def fake_run(command: list[str], **_kwargs: object) -> object:
                candidate = Path(command[command.index("--archive") + 1])
                qa_report.parent.mkdir(parents=True, exist_ok=True)
                qa_report.write_text(json.dumps({
                    "status": "PASS",
                    "checks": [{
                        "name": "archive_structure_and_content",
                        "status": "PASS",
                        "detail": {"artifact_sha256": MODULE.sha256(candidate)},
                    }],
                }), encoding="utf-8")
                return MODULE.subprocess.CompletedProcess([], 0)

            with mock.patch.object(MODULE, "_assemble_candidate", side_effect=self.assembled), \
                 mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run):
                result = MODULE.build(repo, output, False, sq=sq, node=node, qa_report=qa_report)
            self.assertEqual(output.read_bytes(), b"candidate")
            self.assertEqual(result["qa_status"], "PASS")
            self.assertEqual(result["artifact_sha256"], MODULE.sha256(output))


class DestinationSafetyTests(unittest.TestCase):
    @staticmethod
    def make_junction(link: Path, target: Path) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise OSError(completed.stderr or completed.stdout)

    def test_development_build_rejects_output_outside_work_qa_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "repo"
            repo.mkdir()
            output = root / "outside.zip"
            output.write_bytes(b"preserve")
            with self.assertRaisesRegex(ValueError, "development artifact destination"):
                MODULE.build(repo, output, True)
            self.assertEqual(output.read_bytes(), b"preserve")

    def test_development_build_rejects_source_tree_output_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            output = repo / "src" / "canonical.zip"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"preserve")
            with self.assertRaisesRegex(ValueError, "development artifact destination"):
                MODULE.build(repo, output, True)
            self.assertEqual(output.read_bytes(), b"preserve")

    def test_release_build_rejects_output_outside_dist_before_tool_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            output = repo / "work" / "qa" / "release.zip"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"preserve")
            with self.assertRaisesRegex(ValueError, "release artifact destination"):
                MODULE.build(repo, output, False)
            self.assertEqual(output.read_bytes(), b"preserve")

    def test_artifact_symlink_is_rejected_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            approved = repo / "work" / "qa"
            approved.mkdir(parents=True)
            target = repo / "canonical.zip"
            target.write_bytes(b"preserve")
            output = approved / "mod.zip"
            try:
                output.symlink_to(target)
            except OSError as error:
                self.skipTest(f"file symlink unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                MODULE.build(repo, output, True)
            self.assertEqual(target.read_bytes(), b"preserve")

    def test_artifact_hardlink_is_rejected_without_touching_canonical_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            approved = repo / "work" / "qa"
            approved.mkdir(parents=True)
            canonical = repo / "src" / "canonical.zip"
            canonical.parent.mkdir(parents=True)
            canonical.write_bytes(b"preserve")
            output = approved / "mod.zip"
            try:
                os.link(canonical, output)
            except OSError as error:
                self.skipTest(f"hardlink unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "non-aliased"):
                MODULE.build(repo, output, True)
            self.assertEqual(canonical.read_bytes(), b"preserve")

    def test_qa_report_hardlink_alias_is_rejected_without_touching_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            output = repo / "dist" / "mod.zip"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"preserve")
            qa_report = repo / "reports" / "local" / "qa.json"
            qa_report.parent.mkdir(parents=True)
            try:
                os.link(output, qa_report)
            except OSError as error:
                self.skipTest(f"hardlink unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "non-aliased|alias"):
                MODULE.validate_qa_report_destination(repo, qa_report, output)
            self.assertEqual(output.read_bytes(), b"preserve")

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_all_artifact_roots_reject_junction_escape_before_write(self) -> None:
        cases = (
            (("work", "qa"), True, False),
            (("dist",), False, False),
            (("work", "build-staging"), False, True),
        )
        for parts, allow_incomplete, internal_staging in cases:
            with self.subTest(parts=parts), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                repo = root / "repo"
                repo.mkdir()
                outside = root / "outside"
                outside.mkdir()
                link = repo.joinpath(*parts)
                try:
                    self.make_junction(link, outside)
                except OSError as error:
                    self.skipTest(f"junction creation unavailable: {error}")
                try:
                    with self.assertRaisesRegex(ValueError, "symlink or junction"):
                        MODULE.validate_artifact_destination(
                            repo, link / "escaped.zip", allow_incomplete, internal_staging
                        )
                    self.assertEqual(list(outside.iterdir()), [])
                finally:
                    os.rmdir(link)

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_qa_report_root_rejects_junction_escape_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "repo"
            repo.mkdir()
            outside = root / "outside"
            outside.mkdir()
            link = repo / "reports" / "local"
            try:
                self.make_junction(link, outside)
            except OSError as error:
                self.skipTest(f"junction creation unavailable: {error}")
            try:
                output = repo / "dist" / "mod.zip"
                with self.assertRaisesRegex(ValueError, "symlink or junction"):
                    MODULE.validate_qa_report_destination(repo, link / "qa.json", output)
                self.assertEqual(list(outside.iterdir()), [])
            finally:
                os.rmdir(link)

    def test_archive_self_check_rejects_noncanonical_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            source = repo / "src" / "scripts" / "file.nut"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            archive_path = repo / "bad.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.comment = b"unexpected"
                info = zipfile.ZipInfo("scripts/file.nut", (2025, 1, 1, 0, 0, 0))
                info.external_attr = 0o100600 << 16
                archive.writestr(info, b"source", compress_type=zipfile.ZIP_STORED)
            with self.assertRaisesRegex(ValueError, "self-verification"):
                MODULE.verify_built_archive(repo, archive_path)

    def test_localization_resolved_with_known_upstream_limitations_allows_release_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            reports = repo / "reports"
            reports.mkdir()
            (reports / "upstream-source-limitations.json").write_text(
                json.dumps(
                    {
                        "status": "RESOLVED_FOR_LOCALIZATION_WITH_KNOWN_UPSTREAM_LIMITATIONS",
                        "entries": [{"gameplay_change": "NONE", "runtime_qa": "NOT_TESTED"}],
                    }
                ),
                encoding="utf-8",
            )
            MODULE.verify_semantic_limitations(repo)


if __name__ == "__main__":
    unittest.main()
