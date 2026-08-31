from __future__ import annotations

import importlib.util
import tempfile
import hashlib
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "squirrel_literal_roles.py"
SPEC = importlib.util.spec_from_file_location("squirrel_literal_roles", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SquirrelLiteralRoleTests(unittest.TestCase):
    def analyze(self, code: str) -> dict:
        return MODULE.analyze_squirrel_literals(code)

    def records(self, code: str) -> list[dict]:
        return self.analyze(code)["records"]

    def test_push_pair_distinguishes_key_and_literal_value(self) -> None:
        records = self.records(
            'function onPrepareVariables(_vars) { _vars.push(["Town", "former beggar"]); }'
        )
        self.assertEqual(
            [(item["value"], item["literal_role"], item["container_index"]) for item in records],
            [
                ("Town", MODULE.ROLE_BINDING_KEY, 0),
                ("former beggar", MODULE.ROLE_SUBSTITUTION_VALUE, 1),
            ],
        )
        self.assertTrue(all(item["role_confidence"] == MODULE.PARSER_PROVEN for item in records))

    def test_push_key_preserves_spaces_and_capitalization(self) -> None:
        records = self.records(
            'function onPrepareVariables(_vars) { _vars.push(["a ", value]); _vars.push(["a few", other]); }'
        )
        self.assertEqual([item["value"] for item in records], ["a ", "a few"])
        self.assertTrue(all(item["literal_role"] == MODULE.ROLE_BINDING_KEY for item in records))

    def test_dynamic_and_malformed_push_keys_are_not_proven(self) -> None:
        dynamic = self.records('function onPrepareVariables(_vars) { _vars.push([prefix + "key", value]); }')
        malformed = self.records('function onPrepareVariables(_vars) { _vars.push(["key"]); }')
        self.assertEqual(dynamic, [])
        self.assertEqual(malformed, [])

    def test_direct_vars_pairs_require_build_text_consumer(self) -> None:
        consumed = self.records(
            'function render() { local vars = [["regionname", region], ["visible", "former beggar"]]; '
            'return this.buildTextFromTemplate(text, vars); }'
        )
        unconsumed = self.records(
            'function render() { local vars = [["regionname", region]]; return vars; }'
        )
        self.assertEqual(
            [(item["value"], item["literal_role"], item["argument_index"]) for item in consumed],
            [
                ("regionname", MODULE.ROLE_BINDING_KEY, 1),
                ("visible", MODULE.ROLE_BINDING_KEY, 1),
                ("former beggar", MODULE.ROLE_SUBSTITUTION_VALUE, 1),
            ],
        )
        self.assertEqual(unconsumed, [])

    def test_inline_build_text_pairs_are_proven(self) -> None:
        records = self.records(
            'function render() { return ::buildTextFromTemplate(text, '
            '[["name", actor.getName()], ["count", "five"]]); }'
        )
        self.assertEqual(
            [(item["value"], item["literal_role"]) for item in records],
            [
                ("name", MODULE.ROLE_BINDING_KEY),
                ("count", MODULE.ROLE_BINDING_KEY),
                ("five", MODULE.ROLE_SUBSTITUTION_VALUE),
            ],
        )

    def test_reviewed_helper_contract_uses_exact_third_argument(self) -> None:
        records = self.records(
            'function onPrepareVariables(_vars) { '
            '::Const.LegendMod.extendVarsWithPronouns(_vars, brother, "commander"); }'
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["callee"], "::Const.LegendMod.extendVarsWithPronouns")
        self.assertEqual(records[0]["argument_index"], 2)
        self.assertEqual(records[0]["literal_role"], MODULE.ROLE_BINDING_KEY)

    def test_comments_do_not_create_false_structural_records(self) -> None:
        records = self.records(
            'function onPrepareVariables(_vars) { '
            '// _vars.push(["fake", value]);\n_vars.push(["real", value]); }'
        )
        self.assertEqual([item["value"] for item in records], ["real"])

    def test_metadata_binds_exact_push_context_and_span(self) -> None:
        code = 'function onPrepareVariables(_vars) {\n  _vars.push(["brother", actor]);\n}'
        metadata = MODULE.role_metadata_for_entry(
            self.analyze(code),
            english="brother",
            context="event.onPrepareVariables._vars.push()",
            mode="literal",
            source_sha256=MODULE.source_sha256(code),
        )
        self.assertEqual(metadata["literal_role"], MODULE.ROLE_BINDING_KEY)
        self.assertEqual(metadata["source_line"], 2)
        self.assertEqual(
            code.encode("utf-8")[
                metadata["source_span_start"] : metadata["source_span_end"]
            ].decode("utf-8"),
            '"brother"',
        )

    def test_nonunique_structural_match_fails_closed(self) -> None:
        code = ('function onPrepareVariables(_vars) { _vars.push(["brother", one]); '
                '_vars.push(["brother", two]); }')
        metadata = MODULE.role_metadata_for_entry(
            self.analyze(code),
            english="brother",
            context="event.onPrepareVariables._vars.push()",
            mode="literal",
            source_sha256=MODULE.source_sha256(code),
        )
        self.assertEqual(metadata["literal_role"], MODULE.ROLE_UNKNOWN_STRUCTURED)
        self.assertIn("NONUNIQUE", metadata["role_confidence"])

    def test_structured_context_without_parser_proof_fails_closed(self) -> None:
        code = ('function onPrepareVariables(_vars) { '
                '_vars.push([prefix + "brother", actor]); }')
        metadata = MODULE.role_metadata_for_entry(
            self.analyze(code),
            english="brother",
            context="event.onPrepareVariables._vars.push()",
            mode="literal",
            source_sha256=MODULE.source_sha256(code),
        )
        self.assertEqual(metadata["literal_role"], MODULE.ROLE_UNKNOWN_STRUCTURED)
        self.assertEqual(metadata["role_confidence"], "NO_PARSER_PROVEN_STRUCTURAL_MATCH")

    def test_all_occurrence_gate_never_uses_one_representative(self) -> None:
        internal = self.records(
            'function f(_vars) { _vars.push(["key", value]); }'
        )[0]
        visible = dict(internal)
        visible.update(
            literal_role=MODULE.ROLE_LOCALIZATION_CANDIDATE,
            role_confidence="EXACT_LITERAL_MANUAL_REVIEW_REQUIRED",
        )
        value = dict(internal)
        value["literal_role"] = MODULE.ROLE_SUBSTITUTION_VALUE
        accept = lambda occurrence: True
        self.assertEqual(
            MODULE.occurrence_role_gate([internal, dict(internal)], accept),
            MODULE.GATE_AUTO_EXCLUDE,
        )
        self.assertEqual(
            MODULE.occurrence_role_gate([internal, dict(internal)]),
            MODULE.GATE_REVIEW_REQUIRED,
        )
        self.assertEqual(MODULE.occurrence_role_gate([internal, visible]), MODULE.GATE_REVIEW_REQUIRED)
        self.assertEqual(MODULE.occurrence_role_gate([value]), MODULE.GATE_REVIEW_REQUIRED)
        self.assertEqual(MODULE.occurrence_role_gate([visible]), MODULE.GATE_MANUAL_REVIEW)
        self.assertEqual(MODULE.occurrence_role_gate([{}]), MODULE.GATE_MANUAL_REVIEW)
        tampered = dict(internal)
        tampered["argument_index"] = 1
        self.assertEqual(
            MODULE.occurrence_role_gate([tampered]), MODULE.GATE_REVIEW_REQUIRED
        )

    def test_same_text_visible_and_internal_without_exact_context_fails_closed(self) -> None:
        code = ('function onPrepareVariables(_vars) { local visible = "five"; '
                '_vars.push(["five", actor]); }')
        metadata = MODULE.role_metadata_for_entry(
            self.analyze(code),
            english="five",
            context="onPrepareVariables",
            mode="literal",
            source_sha256=MODULE.source_sha256(code),
        )
        self.assertEqual(metadata["literal_role"], MODULE.ROLE_UNKNOWN_STRUCTURED)
        self.assertEqual(
            metadata["role_confidence"], "NONUNIQUE_LITERAL_REVIEW_REQUIRED"
        )

    def test_vars_receiver_must_be_current_function_parameter(self) -> None:
        outside = self.records('_vars.push(["outside", value]);')
        wrong_receiver = self.records(
            'function f(_vars) { holder._vars.push(["nested", value]); }'
        )
        local_only = self.records(
            'function f() { local _vars = []; _vars.push(["local", value]); }'
        )
        reassigned = self.records(
            'function f(_vars) { _vars = other; _vars.push(["changed", value]); }'
        )
        foreach_shadow = self.records(
            'function f(_vars) { foreach (_vars in collections) { '
            '_vars.push(["shadowkey", value]); } }'
        )
        catch_shadow = self.records(
            'function f(_vars) { try {} catch (_vars) { '
            '_vars.push(["catchkey", value]); } }'
        )
        self.assertEqual(outside, [])
        self.assertEqual(wrong_receiver, [])
        self.assertEqual(local_only, [])
        self.assertEqual(reassigned, [])
        self.assertEqual(foreach_shadow, [])
        self.assertEqual(catch_shadow, [])

    def test_build_text_requires_exact_arg_one_single_scope_def_use(self) -> None:
        wrong_arg = self.records(
            'function f() { local vars = [["key", value]]; '
            'return this.buildTextFromTemplate(vars, text); }'
        )
        reassigned = self.records(
            'function f() { local vars = [["key", value]]; vars = other; '
            'return this.buildTextFromTemplate(text, vars); }'
        )
        aliased = self.records(
            'function f() { local vars = [["key", value]]; local alias = vars; '
            'return this.buildTextFromTemplate(text, vars); }'
        )
        cross_scope = self.records(
            'function a() { local vars = [["key", value]]; } '
            'function b() { return this.buildTextFromTemplate(text, vars); }'
        )
        self.assertEqual(wrong_arg, [])
        self.assertEqual(reassigned, [])
        self.assertEqual(aliased, [])
        self.assertEqual(cross_scope, [])

    def test_helper_requires_exact_arity_and_vars_parameter(self) -> None:
        extra = self.records(
            'function f(_vars) { ::Const.LegendMod.extendVarsWithPronouns('
            '_vars, brother, "key", extra); }'
        )
        no_parameter = self.records(
            'function f() { ::Const.LegendMod.extendVarsWithPronouns('
            '_vars, brother, "key"); }'
        )
        self.assertEqual(extra, [])
        self.assertEqual(no_parameter, [])

    def test_analyzer_self_hashes_and_spans_are_utf8_bytes(self) -> None:
        code = 'function f(_vars) { local 日本語 = 1; _vars.push(["key", value]); }'
        analysis = self.analyze(code)
        record = analysis["records"][0]
        self.assertEqual(analysis["source_sha256"], MODULE.source_sha256(code))
        raw = code.encode("utf-8")
        self.assertEqual(
            raw[record["source_span_start"] : record["source_span_end"]].decode("utf-8"),
            '"key"',
        )
        with self.assertRaisesRegex(ValueError, "caller-supplied"):
            MODULE.analyze_squirrel_literals(code, "0" * 64)

    def test_unbalanced_source_never_produces_positive_proof(self) -> None:
        code = 'function f(_vars) { _vars.push(["key", value]);'
        analysis = self.analyze(code)
        self.assertEqual(analysis["records"], [])
        self.assertEqual(analysis["parse_failure_code"], "UNBALANCED_DELIMITERS")

    def test_shadowed_or_non_dominating_build_text_is_not_proven(self) -> None:
        shadowed = self.records(
            'function f(buildTextFromTemplate) { local vars = [["key", value]]; '
            'return buildTextFromTemplate(text, vars); }'
        )
        branched = self.records(
            'function f() { if (condition) { local vars = [["key", value]]; } '
            'return this.buildTextFromTemplate(text, vars); }'
        )
        unbraced_if = self.records(
            'function f() { if (condition) local vars = [["ifkey", value]]; '
            'return this.buildTextFromTemplate(text, vars); }'
        )
        unbraced_while = self.records(
            'function f() { while (condition) local vars = [["whilekey", value]]; '
            'return this.buildTextFromTemplate(text, vars); }'
        )
        cross_case = self.records(
            'function f() { switch (value) { case 1: '
            'local vars = [["casekey", value]]; case 2: '
            'return this.buildTextFromTemplate(text, vars); } }'
        )
        self.assertEqual(shadowed, [])
        self.assertEqual(branched, [])
        self.assertEqual(unbraced_if, [])
        self.assertEqual(unbraced_while, [])
        self.assertEqual(cross_case, [])

    def test_same_foreach_block_definition_and_consumer_are_proven(self) -> None:
        records = self.records(
            'function f() { foreach (region in regions) { '
            'local vars = [["regionname", region.getName()]]; '
            'result.push(this.buildTextFromTemplate(text, vars)); } }'
        )
        self.assertEqual(
            [(record["value"], record["literal_role"]) for record in records],
            [("regionname", MODULE.ROLE_BINDING_KEY)],
        )

    def test_lexical_error_before_candidate_blocks_all_proof(self) -> None:
        analysis = self.analyze(
            'function f(_vars) { local broken = "unterminated\n'
            '_vars.push(["key", value]); }'
        )
        self.assertEqual(analysis["records"], [])
        self.assertEqual(analysis["parse_failure_code"], "LEXICAL_ERROR")

    def test_operation_cache_parses_one_source_once_for_multiple_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "event.nut").write_text(
                'function f(_vars) { _vars.push(["key", "visible"]); }',
                encoding="utf-8",
            )
            roots = {"sample": str(root)}
            cache = {}
            common = {
                "module": "sample", "source": "event.nut",
                "context": "onPrepareVariables._vars.push()", "channel": "squirrel",
                "mode": "literal",
            }
            MODULE.enrich_occurrence_role(
                {**common, "stable_key": "key", "english": "key"}, roots, cache
            )
            MODULE.enrich_occurrence_role(
                {**common, "stable_key": "value", "english": "visible"}, roots, cache
            )
            self.assertEqual(len(cache), 1)

    def test_crlf_raw_hash_span_and_source_reproof_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = b'function f(_vars) {\r\n  _vars.push(["key", value]);\r\n}\r\n'
            (root / "event.nut").write_bytes(raw)
            occurrence = {
                "stable_key": "sample:key", "module": "sample", "source": "event.nut",
                "context": "onPrepareVariables._vars.push()", "channel": "squirrel",
                "mode": "literal", "english": "key",
            }
            roots = {"sample": str(root)}
            enriched = MODULE.enrich_occurrence_role(occurrence, roots)
            self.assertEqual(
                enriched["source_sha256"], hashlib.sha256(raw).hexdigest().upper()
            )
            self.assertEqual(
                raw[enriched["source_span_start"] : enriched["source_span_end"]].decode("utf-8"),
                '"key"',
            )
            self.assertTrue(MODULE.source_binding_key_proof(enriched, roots))


if __name__ == "__main__":
    unittest.main()
