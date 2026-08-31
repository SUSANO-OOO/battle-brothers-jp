#!/usr/bin/env python3
"""Conservative structural roles for Squirrel localization literals.

This is deliberately a small fail-closed tokenizer, not a general Squirrel
parser. It recognizes only reviewed template-variable shapes. Anything
dynamic, malformed, non-unique, or outside those shapes remains review-only.
"""

from __future__ import annotations

import re
import hashlib
import json
from bisect import bisect_right
from pathlib import Path
from collections import Counter, defaultdict
from typing import Any, Callable


PARSER_PROVEN = "PARSER_PROVEN_EXACT"
ANALYZER_VERSION = "bbjp-squirrel-role-v2"
ROLE_BINDING_KEY = "TEMPLATE_BINDING_KEY"
ROLE_SUBSTITUTION_VALUE = "TEMPLATE_SUBSTITUTION_VALUE"
ROLE_LOCALIZATION_CANDIDATE = "LOCALIZATION_CANDIDATE"
ROLE_UNKNOWN_STRUCTURED = "UNKNOWN_STRUCTURED_TEMPLATE_ROLE"

GATE_AUTO_EXCLUDE = "AUTO_EXCLUDE_INTERNAL"
GATE_MANUAL_REVIEW = "MANUAL_TRANSLATION_REVIEW_REQUIRED"
GATE_REVIEW_REQUIRED = "REVIEW_REQUIRED"

REQUIRED_ROLE_FIELDS = (
    "role_analyzer_version",
    "literal_role",
    "role_confidence",
    "role_match_count",
    "role_failure_code",
    "consumer_family",
    "callee",
    "argument_index",
    "container_index",
    "source_span_start",
    "source_span_end",
    "source_line",
    "source_sha256",
)

HELPER_KEY_ARGUMENTS = {
    "::Const.LegendMod.extendVarsWithPronouns": 2,
}
BUILD_TEXT_CALLEES = {"::buildTextFromTemplate", "this.buildTextFromTemplate"}


def source_sha256(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest().upper()


def _decode_string(quote: str, body: str) -> str:
    result: list[str] = []
    index = 0
    escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}
    while index < len(body):
        if body[index] != "\\" or index + 1 >= len(body):
            result.append(body[index])
            index += 1
            continue
        nxt = body[index + 1]
        if nxt in (quote, "\\", "/"):
            result.append(nxt)
            index += 2
        elif nxt in escapes:
            result.append(escapes[nxt])
            index += 2
        elif nxt == "u" and re.fullmatch(r"[0-9A-Fa-f]{4}", body[index + 2 : index + 6]):
            result.append(chr(int(body[index + 2 : index + 6], 16)))
            index += 6
        elif nxt == "x" and re.fullmatch(r"[0-9A-Fa-f]{2}", body[index + 2 : index + 4]):
            result.append(chr(int(body[index + 2 : index + 4], 16)))
            index += 4
        else:
            result.extend(("\\", nxt))
            index += 2
    return "".join(result)


def tokenize_squirrel(code: str) -> list[dict[str, Any]]:
    """Tokenize enough Squirrel syntax to prove exact literal container roles."""
    tokens: list[dict[str, Any]] = []
    byte_offsets = [0]
    total_bytes = 0
    for character in code:
        total_bytes += len(character.encode("utf-8"))
        byte_offsets.append(total_bytes)
    newline_offsets = [index for index, character in enumerate(code) if character == "\n"]

    def line_at(offset: int) -> int:
        return bisect_right(newline_offsets, offset - 1) + 1

    index = 0
    length = len(code)
    while index < length:
        char = code[index]
        nxt = code[index + 1] if index + 1 < length else ""
        if char.isspace():
            index += 1
            continue
        if char == "/" and nxt == "/":
            newline = code.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if char == "/" and nxt == "*":
            end = code.find("*/", index + 2)
            if end < 0:
                tokens.append(
                    {"kind": "error", "text": "UNTERMINATED_BLOCK_COMMENT", "start": index}
                )
                index = length
            else:
                index = end + 2
            continue
        if char == "`":
            start = index
            index += 1
            terminated = False
            while index < length:
                if code[index] == "\\":
                    index += 2
                elif code[index] == "`":
                    index += 1
                    terminated = True
                    break
                else:
                    index += 1
            if not terminated:
                tokens.append(
                    {"kind": "error", "text": "UNTERMINATED_TEMPLATE", "start": start}
                )
            continue
        if char in ("'", '"'):
            quote = char
            start = index
            index += 1
            body_start = index
            terminated = False
            while index < length:
                if code[index] == "\\":
                    index += 2
                elif code[index] == quote:
                    end = index + 1
                    tokens.append(
                        {
                            "kind": "string",
                            "text": code[start:end],
                            "value": _decode_string(quote, code[body_start:index]),
                            "start": start,
                            "end": end,
                            "byte_start": byte_offsets[start],
                            "byte_end": byte_offsets[end],
                            "line": line_at(start),
                        }
                    )
                    index = end
                    terminated = True
                    break
                elif code[index] in "\r\n":
                    index += 1
                    break
                else:
                    index += 1
            if not terminated:
                tokens.append(
                    {"kind": "error", "text": "UNTERMINATED_STRING", "start": start}
                )
            continue
        if char.isalpha() or char in "_$":
            start = index
            index += 1
            while index < length and (code[index].isalnum() or code[index] in "_$"):
                index += 1
            tokens.append(
                {
                    "kind": "ident",
                    "text": code[start:index],
                    "start": start,
                    "end": index,
                    "line": line_at(start),
                }
            )
            continue
        two = code[index : index + 2]
        text = two if two in {"::", "<-", "==", "!=", "<=", ">="} else char
        end = index + len(text)
        tokens.append(
            {
                "kind": "punct",
                "text": text,
                "start": index,
                "end": end,
                "line": line_at(index),
            }
        )
        index = end
    return tokens


def _matching(
    tokens: list[dict[str, Any]],
    opener: int,
    matching_pairs: dict[int, int] | None = None,
) -> int | None:
    if matching_pairs is not None:
        return matching_pairs.get(opener)
    pairs = {"(": ")", "[": "]", "{": "}"}
    opening = tokens[opener]["text"]
    closing = pairs.get(opening)
    if closing is None:
        return None
    depth = 0
    for index in range(opener, len(tokens)):
        text = tokens[index]["text"]
        if text == opening:
            depth += 1
        elif text == closing:
            depth -= 1
            if depth == 0:
                return index
    return None


def _matching_pairs(tokens: list[dict[str, Any]]) -> dict[int, int] | None:
    expected = {"(": ")", "[": "]", "{": "}"}
    reverse = {value: key for key, value in expected.items()}
    stack: list[tuple[str, int]] = []
    result: dict[int, int] = {}
    for index, token in enumerate(tokens):
        text = token["text"]
        if text in expected:
            stack.append((text, index))
        elif text in reverse:
            if not stack or stack[-1][0] != reverse[text]:
                return None
            _, opener = stack.pop()
            result[opener] = index
    return None if stack else result


def _split_top_level(
    tokens: list[dict[str, Any]], start: int, end: int
) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    segment_start = start
    stack: list[str] = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    for index in range(start, end):
        text = tokens[index]["text"]
        if text in pairs:
            stack.append(pairs[text])
        elif stack and text == stack[-1]:
            stack.pop()
        elif text == "," and not stack:
            segments.append((segment_start, index))
            segment_start = index + 1
    segments.append((segment_start, end))
    return [segment for segment in segments if segment[0] < segment[1]]


def _single_string(
    tokens: list[dict[str, Any]], segment: tuple[int, int]
) -> dict[str, Any] | None:
    start, end = segment
    if end - start == 1 and tokens[start]["kind"] == "string":
        return tokens[start]
    return None


def _single_ident(tokens: list[dict[str, Any]], segment: tuple[int, int]) -> str | None:
    start, end = segment
    if end - start == 1 and tokens[start]["kind"] == "ident":
        return str(tokens[start]["text"])
    return None


def _callee_before(tokens: list[dict[str, Any]], paren: int) -> str | None:
    if paren <= 0 or tokens[paren - 1]["kind"] != "ident":
        return None
    parts = [tokens[paren - 1]["text"]]
    index = paren - 2
    while (
        index >= 1
        and tokens[index]["text"] in {".", "::"}
        and tokens[index - 1]["kind"] == "ident"
        and (
            tokens[index]["text"] != "::"
            or tokens[index - 1]["end"] == tokens[index]["start"]
        )
    ):
        parts[:0] = [tokens[index - 1]["text"], tokens[index]["text"]]
        index -= 2
    if index >= 0 and tokens[index]["text"] == "::":
        parts.insert(0, "::")
    return "".join(parts)


def _calls(
    tokens: list[dict[str, Any]], matching_pairs: dict[int, int]
) -> list[dict[str, Any]]:
    calls = []
    for index, token in enumerate(tokens):
        if token["text"] != "(":
            continue
        callee = _callee_before(tokens, index)
        close = _matching(tokens, index, matching_pairs)
        if callee is None or close is None:
            continue
        calls.append(
            {
                "callee": callee,
                "open": index,
                "close": close,
                "args": _split_top_level(tokens, index + 1, close),
            }
        )
    return calls


def _function_scopes(
    tokens: list[dict[str, Any]], matching_pairs: dict[int, int]
) -> list[dict[str, Any]]:
    """Return function bodies and exact parameter identifiers."""
    scopes = []
    for function_index, token in enumerate(tokens):
        if token.get("kind") != "ident" or token.get("text") != "function":
            continue
        paren = function_index + 1
        if paren < len(tokens) and tokens[paren].get("kind") == "ident":
            paren += 1
        if paren >= len(tokens) or tokens[paren]["text"] != "(":
            continue
        close_paren = _matching(tokens, paren, matching_pairs)
        if close_paren is None or close_paren + 1 >= len(tokens):
            continue
        body_open = close_paren + 1
        if tokens[body_open]["text"] != "{":
            continue
        body_close = _matching(tokens, body_open, matching_pairs)
        if body_close is None:
            continue
        parameter_segments = _split_top_level(tokens, paren + 1, close_paren)
        parameters = {
            str(tokens[start]["text"])
            for start, end in parameter_segments
            if end - start == 1 and tokens[start].get("kind") == "ident"
        }
        scopes.append(
            {
                "function": function_index,
                "body_open": body_open,
                "body_close": body_close,
                "parameters": parameters,
            }
        )
    return scopes


def _innermost_scope(scopes: list[dict[str, Any]], token_index: int) -> dict[str, Any] | None:
    candidates = [
        scope
        for scope in scopes
        if scope["body_open"] < token_index < scope["body_close"]
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda scope: scope["body_close"] - scope["body_open"])


def _parameter_unmodified(
    tokens: list[dict[str, Any]],
    matching_pairs: dict[int, int],
    scope: dict[str, Any],
    name: str,
) -> bool:
    for index in range(scope["body_open"] + 1, scope["body_close"]):
        if tokens[index].get("kind") != "ident" or tokens[index].get("text") != name:
            continue
        previous = tokens[index - 1]["text"] if index > scope["body_open"] + 1 else ""
        following = tokens[index + 1]["text"] if index + 1 < scope["body_close"] else ""
        following_two = (
            tokens[index + 2]["text"] if index + 2 < scope["body_close"] else ""
        )
        if previous == "local" or following in {"=", "<-", "++", "--"}:
            return False
        if following in {"+", "-", "*", "/", "%"} and following_two == "=":
            return False
        for opener, closer in matching_pairs.items():
            if (
                tokens[opener]["text"] != "("
                or not opener < index < closer
                or opener == 0
            ):
                continue
            binder = tokens[opener - 1].get("text")
            if binder == "catch":
                return False
            if binder == "foreach":
                in_indices = [
                    candidate
                    for candidate in range(opener + 1, closer)
                    if tokens[candidate].get("text") == "in"
                ]
                if in_indices and index < in_indices[0]:
                    return False
    return True


def _innermost_lexical_block(
    tokens: list[dict[str, Any]],
    matching_pairs: dict[int, int],
    scope: dict[str, Any],
    token_index: int,
) -> int | None:
    candidates = [
        opener
        for opener, closer in matching_pairs.items()
        if tokens[opener]["text"] == "{"
        and scope["body_open"] <= opener < token_index < closer <= scope["body_close"]
    ]
    return max(candidates) if candidates else None


def _is_direct_braced_statement(
    tokens: list[dict[str, Any]], declaration_index: int, block_open: int | None
) -> bool:
    """Accept only declarations that are direct statements in a brace block.

    A declaration immediately following ``)``, ``else``, ``do`` or a label can
    be controlled by an unbraced branch/loop even though its nearest brace is
    the surrounding function.  Those shapes require a real control-flow graph
    and therefore fail closed here.
    """
    if block_open is None or declaration_index <= block_open:
        return False
    return tokens[declaration_index - 1].get("text") in {"{", ";", "}"}


def _block_has_switch_labels(
    tokens: list[dict[str, Any]],
    matching_pairs: dict[int, int],
    scope: dict[str, Any],
    block_open: int | None,
) -> bool:
    """Reject same-block case/default paths unless a CFG proves dominance."""
    if block_open is None:
        return True
    block_close = matching_pairs.get(block_open)
    if block_close is None:
        return True
    for index in range(block_open + 1, block_close):
        if tokens[index].get("text") not in {"case", "default"}:
            continue
        if (
            _innermost_lexical_block(tokens, matching_pairs, scope, index)
            == block_open
        ):
            return True
    return False


def _record(
    token: dict[str, Any],
    *,
    role: str,
    family: str,
    callee: str,
    argument_index: int,
    container_index: int | None,
    source_sha256: str,
) -> dict[str, Any]:
    return {
        "value": token["value"],
        "role_analyzer_version": ANALYZER_VERSION,
        "literal_role": role,
        "role_confidence": PARSER_PROVEN,
        "role_match_count": 1,
        "role_failure_code": None,
        "consumer_family": family,
        "callee": callee,
        "argument_index": argument_index,
        "container_index": container_index,
        "source_span_start": token["byte_start"],
        "source_span_end": token["byte_end"],
        "source_line": token["line"],
        "source_sha256": source_sha256,
    }


def _array_pairs(
    tokens: list[dict[str, Any]],
    opener: int,
    closer: int,
    matching_pairs: dict[int, int],
) -> list[tuple[dict[str, Any] | None, dict[str, Any] | None]]:
    result = []
    for segment in _split_top_level(tokens, opener + 1, closer):
        start, end = segment
        if end - start < 2 or tokens[start]["text"] != "[":
            continue
        pair_close = _matching(tokens, start, matching_pairs)
        if pair_close is None or pair_close != end - 1:
            continue
        elements = _split_top_level(tokens, start + 1, pair_close)
        if len(elements) != 2:
            continue
        result.append((_single_string(tokens, elements[0]), _single_string(tokens, elements[1])))
    return result


def analyze_squirrel_literals(
    code: str, expected_source_sha256: str | None = None
) -> dict[str, Any]:
    """Return exact structural records plus every lexical string token."""
    actual_source_sha256 = source_sha256(code)
    if (
        expected_source_sha256 is not None
        and expected_source_sha256.upper() != actual_source_sha256
    ):
        raise ValueError("caller-supplied source SHA-256 does not match source text")
    tokens = tokenize_squirrel(code)
    if any(token.get("kind") == "error" for token in tokens):
        return {
            "tokens": tokens,
            "string_tokens": [token for token in tokens if token["kind"] == "string"],
            "records": [],
            "source_sha256": actual_source_sha256,
            "parse_failure_code": "LEXICAL_ERROR",
        }
    matching_pairs = _matching_pairs(tokens)
    if matching_pairs is None:
        return {
            "tokens": tokens,
            "string_tokens": [token for token in tokens if token["kind"] == "string"],
            "records": [],
            "source_sha256": actual_source_sha256,
            "parse_failure_code": "UNBALANCED_DELIMITERS",
        }
    calls = _calls(tokens, matching_pairs)
    scopes = _function_scopes(tokens, matching_pairs)
    records: list[dict[str, Any]] = []

    for call in calls:
        callee = call["callee"]
        args = call["args"]
        scope = _innermost_scope(scopes, call["open"])
        has_vars_parameter = (
            scope is not None
            and "_vars" in scope["parameters"]
            and _parameter_unmodified(tokens, matching_pairs, scope, "_vars")
        )
        if callee == "_vars.push" and len(args) == 1 and has_vars_parameter:
            start, end = args[0]
            if end - start >= 2 and tokens[start]["text"] == "[":
                close = _matching(tokens, start, matching_pairs)
                if close == end - 1:
                    elements = _split_top_level(tokens, start + 1, close)
                    if len(elements) == 2:
                        key = _single_string(tokens, elements[0])
                        value = _single_string(tokens, elements[1])
                        if key is not None:
                            records.append(
                                _record(
                                    key,
                                    role=ROLE_BINDING_KEY,
                                    family="_vars.push([key,value])",
                                    callee=callee,
                                    argument_index=0,
                                    container_index=0,
                                    source_sha256=actual_source_sha256,
                                )
                            )
                        if value is not None:
                            records.append(
                                _record(
                                    value,
                                    role=ROLE_SUBSTITUTION_VALUE,
                                    family="_vars.push([key,value])",
                                    callee=callee,
                                    argument_index=0,
                                    container_index=1,
                                    source_sha256=actual_source_sha256,
                                )
                            )

        helper_index = HELPER_KEY_ARGUMENTS.get(callee)
        if (
            helper_index is not None
            and len(args) == 3
            and helper_index < len(args)
            and has_vars_parameter
            and _single_ident(tokens, args[0]) == "_vars"
        ):
            helper_key = _single_string(tokens, args[helper_index])
            if helper_key is not None:
                records.append(
                    _record(
                        helper_key,
                        role=ROLE_BINDING_KEY,
                        family="extendVarsWithPronouns keyPrefix",
                        callee=callee,
                        argument_index=helper_index,
                        container_index=None,
                        source_sha256=actual_source_sha256,
                    )
                )

    build_calls = [call for call in calls if call["callee"] in BUILD_TEXT_CALLEES]
    for scope in scopes:
        assignments: dict[str, list[tuple[int, int, int, int | None]]] = defaultdict(list)
        for index in range(scope["body_open"] + 1, scope["body_close"] - 2):
            if (
                tokens[index]["kind"] == "ident"
                and tokens[index + 1]["kind"] == "ident"
                and tokens[index]["text"] == "local"
                and tokens[index + 2]["text"] in {"=", "<-"}
                and index + 3 < len(tokens)
                and tokens[index + 3]["text"] == "["
            ):
                close = _matching(tokens, index + 3, matching_pairs)
                if close is not None and close < scope["body_close"]:
                    assignments[str(tokens[index + 1]["text"])].append(
                        (
                            index + 3,
                            close,
                            index + 1,
                            _innermost_lexical_block(
                                tokens, matching_pairs, scope, index
                            ),
                        )
                    )

        for variable, definitions in assignments.items():
            consumers = [
                call
                for call in build_calls
                if _innermost_scope(scopes, call["open"]) is scope
                and len(call["args"]) == 2
                and _single_ident(tokens, call["args"][1]) == variable
            ]
            if len(definitions) != 1 or len(consumers) != 1:
                continue
            opener, closer, declaration_index, declaration_block = definitions[0]
            call = consumers[0]
            consumer_segment = call["args"][1]
            identifier_uses = [
                index
                for index in range(scope["body_open"] + 1, scope["body_close"])
                if tokens[index].get("kind") == "ident" and tokens[index].get("text") == variable
            ]
            if (
                identifier_uses != [declaration_index, consumer_segment[0]]
                or closer >= call["open"]
                or not _is_direct_braced_statement(
                    tokens, declaration_index - 1, declaration_block
                )
                or _block_has_switch_labels(
                    tokens, matching_pairs, scope, declaration_block
                )
                or declaration_block
                != _innermost_lexical_block(
                    tokens, matching_pairs, scope, call["open"]
                )
            ):
                continue
            argument_index = 1
            callee = call["callee"]
            for key, value in _array_pairs(tokens, opener, closer, matching_pairs):
                if key is not None:
                    records.append(
                        _record(
                            key,
                            role=ROLE_BINDING_KEY,
                            family="buildTextFromTemplate vars pair",
                            callee=callee,
                            argument_index=argument_index,
                            container_index=0,
                            source_sha256=actual_source_sha256,
                        )
                    )
                if value is not None:
                    records.append(
                        _record(
                            value,
                            role=ROLE_SUBSTITUTION_VALUE,
                            family="buildTextFromTemplate vars pair",
                            callee=callee,
                            argument_index=argument_index,
                            container_index=1,
                            source_sha256=actual_source_sha256,
                        )
                    )

    for call in build_calls:
        if len(call["args"]) != 2:
            continue
        for argument_index, segment in enumerate(call["args"]):
            if argument_index != 1:
                continue
            start, end = segment
            if end - start < 2 or tokens[start]["text"] != "[":
                continue
            close = _matching(tokens, start, matching_pairs)
            if close != end - 1:
                continue
            for key, value in _array_pairs(tokens, start, close, matching_pairs):
                if key is not None:
                    records.append(
                        _record(
                            key,
                            role=ROLE_BINDING_KEY,
                            family="buildTextFromTemplate inline vars pair",
                            callee=call["callee"],
                            argument_index=argument_index,
                            container_index=0,
                            source_sha256=actual_source_sha256,
                        )
                    )
                if value is not None:
                    records.append(
                        _record(
                            value,
                            role=ROLE_SUBSTITUTION_VALUE,
                            family="buildTextFromTemplate inline vars pair",
                            callee=call["callee"],
                            argument_index=argument_index,
                            container_index=1,
                            source_sha256=actual_source_sha256,
                        )
                    )

    unique_records = {
        (record["source_span_start"], record["source_span_end"], record["literal_role"], record["callee"]): record
        for record in records
    }
    return {
        "tokens": tokens,
        "string_tokens": [token for token in tokens if token["kind"] == "string"],
        "records": sorted(unique_records.values(), key=lambda item: item["source_span_start"]),
        "source_sha256": actual_source_sha256,
    }


def _default_metadata(source_sha256: str) -> dict[str, Any]:
    return {
        "role_analyzer_version": ANALYZER_VERSION,
        "literal_role": ROLE_LOCALIZATION_CANDIDATE,
        "role_confidence": "MANUAL_REVIEW_REQUIRED",
        "role_match_count": 0,
        "role_failure_code": "UNCLASSIFIED_CANDIDATE",
        "consumer_family": None,
        "callee": None,
        "argument_index": None,
        "container_index": None,
        "source_span_start": None,
        "source_span_end": None,
        "source_line": None,
        "source_sha256": source_sha256,
    }


def role_metadata_for_entry(
    analysis: dict[str, Any],
    *,
    english: str,
    context: str,
    mode: str,
    source_sha256: str,
) -> dict[str, Any]:
    """Bind one extracted candidate to exactly one parser-proven literal role."""
    actual_source_sha256 = analysis.get("source_sha256")
    if source_sha256.upper() != actual_source_sha256:
        raise ValueError("role binding source SHA-256 does not match analyzer source")
    default = _default_metadata(actual_source_sha256)
    context_family: Callable[[dict[str, Any]], bool] | None = None
    if "_vars.push" in context:
        context_family = lambda record: record["consumer_family"] == "_vars.push([key,value])"
    elif "extendVarsWithPronouns" in context:
        context_family = lambda record: record["consumer_family"] == "extendVarsWithPronouns keyPrefix"
    elif context.endswith(".vars") or "buildTextFromTemplate" in context:
        context_family = lambda record: str(record["consumer_family"]).startswith("buildTextFromTemplate")

    matching_strings = [
        token for token in analysis["string_tokens"] if token.get("value") == english
    ]
    records = [record for record in analysis["records"] if record["value"] == english]
    if context_family is not None:
        records = [record for record in records if context_family(record)]
    elif len(matching_strings) > 1:
        # Rosetta has no stable source span.  With repeated same-text literals,
        # one structural record cannot identify which extracted occurrence it
        # represents; a visible literal must not inherit an internal-key role.
        default.update(
            {
                "literal_role": ROLE_UNKNOWN_STRUCTURED,
                "role_confidence": "NONUNIQUE_LITERAL_REVIEW_REQUIRED",
                "role_match_count": len(matching_strings),
                "role_failure_code": "NONUNIQUE_LITERAL_MATCH",
            }
        )
        return default
    if len(records) == 1:
        return {key: records[0][key] for key in REQUIRED_ROLE_FIELDS}
    if len(records) > 1:
        default.update(
            {
                "literal_role": ROLE_UNKNOWN_STRUCTURED,
                "role_confidence": "NONUNIQUE_STRUCTURAL_MATCH_REVIEW_REQUIRED",
                "role_match_count": len(records),
                "role_failure_code": "NONUNIQUE_STRUCTURAL_MATCH",
            }
        )
        return default

    if context_family is not None:
        default.update(
            {
                "literal_role": ROLE_UNKNOWN_STRUCTURED,
                "role_confidence": "NO_PARSER_PROVEN_STRUCTURAL_MATCH",
                "role_match_count": 0,
                "role_failure_code": analysis.get(
                    "parse_failure_code", "NO_PARSER_PROVEN_STRUCTURAL_MATCH"
                ),
            }
        )
        if len(matching_strings) == 1:
            default.update(
                {
                    "source_span_start": matching_strings[0]["byte_start"],
                    "source_span_end": matching_strings[0]["byte_end"],
                    "source_line": matching_strings[0]["line"],
                }
            )
        return default
    if mode == "literal" and len(matching_strings) == 1:
        default.update(
            {
                "role_confidence": "EXACT_LITERAL_MANUAL_REVIEW_REQUIRED",
                "role_match_count": 1,
                "role_failure_code": "NO_SUPPORTED_STRUCTURAL_CONSUMER",
                "source_span_start": matching_strings[0]["byte_start"],
                "source_span_end": matching_strings[0]["byte_end"],
                "source_line": matching_strings[0]["line"],
            }
        )
    elif len(matching_strings) > 1:
        default.update(
            {
                "literal_role": ROLE_UNKNOWN_STRUCTURED,
                "role_confidence": "NONUNIQUE_LITERAL_REVIEW_REQUIRED",
                "role_match_count": len(matching_strings),
                "role_failure_code": "NONUNIQUE_LITERAL_MATCH",
            }
        )
    else:
        default.update(
            {
                "role_confidence": "NO_EXACT_LITERAL_MANUAL_REVIEW_REQUIRED",
                "role_failure_code": analysis.get(
                    "parse_failure_code", "NO_EXACT_LITERAL_MATCH"
                ),
            }
        )
    return default


def occurrence_role_gate(
    occurrences: list[dict[str, Any]],
    proof_validator: Callable[[dict[str, Any]], bool] | None = None,
) -> str:
    """Classify a complete global unit; never infer from one representative."""
    if not occurrences or any(
        any(field not in occurrence for field in REQUIRED_ROLE_FIELDS)
        for occurrence in occurrences
    ):
        return GATE_MANUAL_REVIEW
    roles = [occurrence["literal_role"] for occurrence in occurrences]
    confidences = [occurrence["role_confidence"] for occurrence in occurrences]
    valid_binding_proofs = [valid_binding_key_proof(occurrence) for occurrence in occurrences]
    if all(valid_binding_proofs) and proof_validator is not None and all(
        proof_validator(occurrence) for occurrence in occurrences
    ):
        return GATE_AUTO_EXCLUDE
    if any(role == ROLE_BINDING_KEY for role in roles):
        return GATE_REVIEW_REQUIRED
    if any(role == ROLE_UNKNOWN_STRUCTURED for role in roles) or any(
        "NONUNIQUE" in str(confidence) for confidence in confidences
    ):
        return GATE_REVIEW_REQUIRED
    is_value = [role == ROLE_SUBSTITUTION_VALUE for role in roles]
    if any(is_value):
        if not all(is_value):
            return GATE_REVIEW_REQUIRED
        if any(not valid_substitution_value_proof(item) for item in occurrences):
            return GATE_REVIEW_REQUIRED
        if proof_validator is None or any(
            not proof_validator(occurrence) for occurrence in occurrences
        ):
            return GATE_REVIEW_REQUIRED
    return GATE_MANUAL_REVIEW


def _load_source_analysis(
    occurrence: dict[str, Any],
    module_roots: dict[str, str],
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    root_value = module_roots.get(str(occurrence.get("module")))
    if not root_value:
        raise ValueError("module source root is unavailable")
    root = Path(root_value).resolve()
    path = (root / str(occurrence.get("source", ""))).resolve()
    if path != root and root not in path.parents:
        raise ValueError("source path escapes module root")
    cache_key = str(path)
    if analysis_cache is not None and cache_key in analysis_cache:
        return analysis_cache[cache_key]
    code = path.read_bytes().decode("utf-8")
    digest = source_sha256(code)
    value = (code, digest, analyze_squirrel_literals(code))
    if analysis_cache is not None:
        analysis_cache[cache_key] = value
    return value


def source_structural_proof(
    occurrence: dict[str, Any],
    module_roots: dict[str, str],
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] | None = None,
) -> bool:
    """Reparse the current copied source and match one exact recorded proof."""
    try:
        code, digest, analysis = _load_source_analysis(
            occurrence, module_roots, analysis_cache
        )
        if digest != occurrence.get("source_sha256"):
            return False
        matches = [
            record
            for record in analysis["records"]
            if record.get("value") == occurrence.get("english")
            and all(record.get(field) == occurrence.get(field) for field in REQUIRED_ROLE_FIELDS)
        ]
        return len(matches) == 1 and (
            valid_binding_key_proof(matches[0])
            or valid_substitution_value_proof(matches[0])
        )
    except (OSError, UnicodeError, ValueError, TypeError):
        return False


def valid_binding_key_proof(occurrence: dict[str, Any]) -> bool:
    """Validate all non-source structural invariants for one proven key."""
    if any(field not in occurrence for field in REQUIRED_ROLE_FIELDS):
        return False
    if (
        occurrence.get("role_analyzer_version") != ANALYZER_VERSION
        or occurrence.get("literal_role") != ROLE_BINDING_KEY
        or occurrence.get("role_confidence") != PARSER_PROVEN
        or occurrence.get("role_match_count") != 1
        or occurrence.get("role_failure_code") is not None
        or not re.fullmatch(r"[0-9A-F]{64}", str(occurrence.get("source_sha256", "")))
        or not isinstance(occurrence.get("source_span_start"), int)
        or not isinstance(occurrence.get("source_span_end"), int)
        or occurrence["source_span_start"] >= occurrence["source_span_end"]
        or not isinstance(occurrence.get("source_line"), int)
        or occurrence["source_line"] <= 0
    ):
        return False
    family = occurrence.get("consumer_family")
    contract = (
        ("_vars.push([key,value])", "_vars.push", 0, 0),
        ("buildTextFromTemplate vars pair", BUILD_TEXT_CALLEES, 1, 0),
        ("buildTextFromTemplate inline vars pair", BUILD_TEXT_CALLEES, 1, 0),
        (
            "extendVarsWithPronouns keyPrefix",
            "::Const.LegendMod.extendVarsWithPronouns",
            2,
            None,
        ),
    )
    for expected_family, callee, argument_index, container_index in contract:
        callees = callee if isinstance(callee, set) else {callee}
        if family == expected_family:
            return (
                occurrence.get("callee") in callees
                and occurrence.get("argument_index") == argument_index
                and occurrence.get("container_index") == container_index
            )
    return False


def valid_substitution_value_proof(occurrence: dict[str, Any]) -> bool:
    if any(field not in occurrence for field in REQUIRED_ROLE_FIELDS):
        return False
    candidate = dict(occurrence)
    candidate["literal_role"] = ROLE_BINDING_KEY
    candidate["container_index"] = 0
    if not valid_binding_key_proof(candidate):
        return False
    return (
        occurrence.get("literal_role") == ROLE_SUBSTITUTION_VALUE
        and occurrence.get("role_confidence") == PARSER_PROVEN
        and occurrence.get("container_index") == 1
        and occurrence.get("consumer_family")
        in {
            "_vars.push([key,value])",
            "buildTextFromTemplate vars pair",
            "buildTextFromTemplate inline vars pair",
        }
    )


def source_binding_key_proof(
    occurrence: dict[str, Any],
    module_roots: dict[str, str],
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] | None = None,
) -> bool:
    return valid_binding_key_proof(occurrence) and source_structural_proof(
        occurrence, module_roots, analysis_cache
    )


def enrich_occurrence_role(
    occurrence: dict[str, Any],
    module_roots: dict[str, str],
    analysis_cache: dict[str, tuple[str, str, dict[str, Any]]] | None = None,
    *,
    force_reanalysis: bool = False,
) -> dict[str, Any]:
    """Return a parser-evidence sidecar without mutating legacy canonical data."""
    enriched = dict(occurrence)
    if not force_reanalysis and all(field in enriched for field in REQUIRED_ROLE_FIELDS):
        return enriched
    try:
        code, digest, analysis = _load_source_analysis(
            enriched, module_roots, analysis_cache
        )
        if enriched.get("channel") == "squirrel_fallback":
            metadata = _default_metadata(digest)
            matches = [
                token
                for token in analysis["string_tokens"]
                if token.get("value") == enriched.get("english")
            ]
            metadata.update(
                literal_role=ROLE_UNKNOWN_STRUCTURED,
                role_confidence="PARSER_FALLBACK_REVIEW_REQUIRED",
                role_match_count=0,
                role_failure_code="PARSER_FALLBACK",
            )
            if len(matches) == 1:
                metadata.update(
                    source_span_start=matches[0]["byte_start"],
                    source_span_end=matches[0]["byte_end"],
                    source_line=matches[0]["line"],
                )
        elif enriched.get("channel") == "squirrel":
            metadata = role_metadata_for_entry(
                analysis,
                english=str(enriched.get("english", "")),
                context=str(enriched.get("context", "")),
                mode=str(enriched.get("mode", "literal")),
                source_sha256=digest,
            )
        else:
            metadata = _default_metadata(digest)
            matches = [
                token
                for token in analysis["string_tokens"]
                if token.get("value") == enriched.get("english")
            ]
            if len(matches) == 1:
                metadata.update(
                    role_confidence="EXACT_LITERAL_MANUAL_REVIEW_REQUIRED",
                    role_match_count=1,
                    role_failure_code="NON_SQUIRREL_CHANNEL",
                    source_span_start=matches[0]["byte_start"],
                    source_span_end=matches[0]["byte_end"],
                    source_line=matches[0]["line"],
                )
            else:
                metadata.update(
                    literal_role=ROLE_UNKNOWN_STRUCTURED,
                    role_confidence="NONUNIQUE_LITERAL_REVIEW_REQUIRED",
                    role_match_count=len(matches),
                    role_failure_code="NONUNIQUE_LITERAL_MATCH",
                )
        enriched.update(metadata)
        return enriched
    except (OSError, UnicodeError, ValueError, TypeError):
        metadata = _default_metadata("0" * 64)
        metadata.update(
            literal_role=ROLE_UNKNOWN_STRUCTURED,
            role_confidence="SOURCE_ANALYSIS_FAILED_REVIEW_REQUIRED",
            role_failure_code="SOURCE_ANALYSIS_FAILED",
        )
        enriched.update(metadata)
        return enriched


def evidence_fingerprint(occurrence: dict[str, Any]) -> str:
    basis = {
        "stable_key": occurrence.get("stable_key"),
        "module": occurrence.get("module"),
        "source": occurrence.get("source"),
        "context": occurrence.get("context"),
        "channel": occurrence.get("channel"),
        "mode": occurrence.get("mode"),
        "english": occurrence.get("english"),
        "placeholder_signature": occurrence.get("placeholder_signature"),
        "role": {field: occurrence.get(field) for field in REQUIRED_ROLE_FIELDS},
    }
    encoded = json.dumps(basis, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def occurrence_evidence(occurrence: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: occurrence.get(key)
        for key in (
            "stable_key",
            "module",
            "source",
            "context",
            "channel",
            "mode",
            "english",
            "placeholder_signature",
            *REQUIRED_ROLE_FIELDS,
        )
    }
    result["evidence_fingerprint"] = evidence_fingerprint(occurrence)
    return result


def role_summary(occurrences: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(item.get("literal_role", "LEGACY_UNSPECIFIED")) for item in occurrences).items()))
