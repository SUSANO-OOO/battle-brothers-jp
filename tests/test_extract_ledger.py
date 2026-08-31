import importlib.util
import tempfile
import hashlib
import re
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "extract_ledger.py"
SPEC = importlib.util.spec_from_file_location("extract_ledger", MODULE_PATH)
assert SPEC and SPEC.loader
EXTRACT_LEDGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACT_LEDGER)


class JavascriptExtractionTests(unittest.TestCase):
    def test_external_and_minified_javascript_are_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "extern").mkdir()
            (root / "extern" / "library.js").write_text("'External label';", encoding="utf-8")
            (root / "vendor.min.js").write_text("'Minified label';", encoding="utf-8")
            (root / "screen.js").write_text("var label = 'Visible label';", encoding="utf-8")

            entries = EXTRACT_LEDGER.extract_javascript("sample", root)

        self.assertEqual([entry["english"] for entry in entries], ["Visible label"])

    def test_line_context_tracks_candidates_after_rejected_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "screen.js"
            source.write_text(
                "var internal = 'someIdentifier';\n"
                "var label = 'First visible label';\n"
                "var other = 'anotherIdentifier';\n"
                "var second = 'Second visible label';\n",
                encoding="utf-8",
            )

            entries = EXTRACT_LEDGER.extract_javascript("sample", root)

        self.assertEqual(
            [entry["context"].split(":column:")[0] for entry in entries],
            ["line:2", "line:4"],
        )

    def test_html_scaffold_without_visible_text_is_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "screen.js").write_text(
                "var scaffold = '<div class=\"row\"></div>';\n"
                "var visible = '<div class=\"hint\">No one is assigned.</div>';\n",
                encoding="utf-8",
            )

            entries = EXTRACT_LEDGER.extract_javascript("sample", root)

        self.assertEqual([entry["english"] for entry in entries], ['<div class="hint">No one is assigned.</div>'])

    def test_apostrophes_inside_comments_do_not_consume_javascript_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "screen.js").write_text(
                "// the div's helper must not start a string\n"
                "var label = 'Visible label';\n"
                "/* another developer's comment */\n"
                "var second = \"Second visible label\";\n",
                encoding="utf-8",
            )

            entries = EXTRACT_LEDGER.extract_javascript("sample", root)

        self.assertEqual(
            [entry["english"] for entry in entries],
            ["Visible label", "Second visible label"],
        )

    def test_one_word_label_is_kept_at_visible_control_call_site(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "screen.js").write_text(
                "button.createTextButton('Scenarios', callback);\n"
                "var internal = 'InternalIdentifier';\n",
                encoding="utf-8",
            )

            entries = EXTRACT_LEDGER.extract_javascript("sample", root)

        self.assertEqual([entry["english"] for entry in entries], ["Scenarios"])

    def test_squirrel_fallback_preserves_failure_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "broken.nut"
            code = 'local name = "Visible Name"; local id = "internal_id";'
            source.write_text(code, encoding="utf-8")

            entries = EXTRACT_LEDGER.fallback_squirrel_strings(
                "sample", root, source, code, SyntaxError("upstream parser failure")
            )

        self.assertEqual([entry["english"] for entry in entries], ["Visible Name"])
        self.assertIn("ROSETTA_PARSER_FALLBACK", entries[0]["notes"])
        self.assertEqual(entries[0]["role_failure_code"], "PARSER_FALLBACK")
        self.assertEqual(
            entries[0]["literal_role"], "UNKNOWN_STRUCTURED_TEMPLATE_ROLE"
        )

    def test_squirrel_extraction_hashes_raw_crlf_bytes(self):
        class FakeRosetta:
            FILES_SKIP_RE = re.compile(r"$^")
            SEEN = set()

            @staticmethod
            def extract(code, filename):
                yield {
                    "en": "key",
                    "_context": "onPrepareVariables._vars.push()",
                    "_code": [],
                    "mode": "literal",
                }

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = b'function f(_vars) {\r\n  _vars.push(["key", value]);\r\n}\r\n'
            (root / "event.nut").write_bytes(raw)
            entries, failures, warnings = EXTRACT_LEDGER.extract_squirrel(
                "sample", root, FakeRosetta()
            )
        self.assertFalse(failures)
        self.assertFalse(warnings)
        self.assertEqual(
            entries[0]["source_sha256"], hashlib.sha256(raw).hexdigest().upper()
        )


if __name__ == "__main__":
    unittest.main()
