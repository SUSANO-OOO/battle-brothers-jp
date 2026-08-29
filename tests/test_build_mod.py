from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
