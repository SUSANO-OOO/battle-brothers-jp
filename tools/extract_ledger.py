#!/usr/bin/env python3
"""Extract localization candidates from copied/decompiled Squirrel and JS.

The detailed ledger contains copyrighted English source material and therefore
must remain under ignored work/. A content-free aggregate report may be
committed under reports/.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from squirrel_literal_roles import (  # noqa: E402 - local tool import after path guard
    ANALYZER_VERSION,
    REQUIRED_ROLE_FIELDS,
    ROLE_LOCALIZATION_CANDIDATE,
    analyze_squirrel_literals,
    role_metadata_for_entry,
)


ROSETTA_COMMIT = "dde98e99fd95ed0e7474a4328555144b4e913678"
PLACEHOLDER_PATTERNS = {
    "percent_vars": re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%"),
    "printf": re.compile(r"%(?:\d+\$)?[sdif](?![A-Za-z0-9_]*%)"),
    "bbcode_tags": re.compile(r"\[[^\]\r\n]+\]"),
    "captures": re.compile(r"<[^>\r\n]+>"),
}
INTERNAL_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:/\\#-]+$")
PATHISH_RE = re.compile(
    r"(?i)(?:^|[/\\])(?:ui|gfx|scripts|mods?|screens?|assets?)(?:[/\\]|$)|"
    r"\.(?:png|jpg|jpeg|gif|js|css|nut|cnut|wav|ogg|brush|html)$"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def require_within(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    root = root.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"{label} must be inside {root}: {resolved}")
    return resolved


def load_rosetta(rosetta_root: Path):
    module_path = rosetta_root / "rosetta.py"
    spec = importlib.util.spec_from_file_location("bbjp_rosetta_extractor", module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load Rosetta extractor: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OPTS.update(
        {
            "lang": "ja",
            "engine": None,
            "ref": None,
            "check": None,
            "debug": False,
            "failfast": False,
            "context": True,
            "quiet": True,
        }
    )
    return module


def placeholder_signature(text: str) -> dict[str, Any]:
    signature: dict[str, Any] = {
        name: pattern.findall(text) for name, pattern in PLACEHOLDER_PATTERNS.items()
    }
    signature.update(
        {
            "newlines": text.count("\n"),
            "brace_open": text.count("{"),
            "brace_close": text.count("}"),
            "template_pipes": text.count("|") if "{" in text or "}" in text else 0,
        }
    )
    return signature


def stable_key(module: str, source: str, context: str, english: str, channel: str) -> str:
    basis = "\x1f".join((module, source, context, english, channel))
    return f"{module}:{sha256_text(basis)[:24]}"


def make_entry(
    *,
    module: str,
    source: str,
    context: str,
    english: str,
    channel: str,
    source_code: list[str] | None = None,
    mode: str = "literal",
    role_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "stable_key": stable_key(module, source, context, english, channel),
        "module": module,
        "source": source,
        "context": context,
        "channel": channel,
        "english": english,
        "japanese": "",
        "status": "UNTRANSLATED",
        "review_status": "NOT_REVIEWED",
        "mode": mode,
        "placeholder_signature": placeholder_signature(english),
        "source_code": source_code or [],
        "notes": [],
    }
    if role_metadata is not None:
        missing = [field for field in REQUIRED_ROLE_FIELDS if field not in role_metadata]
        if missing:
            raise ValueError(f"role metadata is incomplete: {missing}")
        entry.update({field: role_metadata[field] for field in REQUIRED_ROLE_FIELDS})
    return entry


def lexical_role_metadata(
    *, source_sha256: str, start: int, end: int, line: int
) -> dict[str, Any]:
    """Record an exact lexical location without claiming a structural role."""
    return {
        "role_analyzer_version": ANALYZER_VERSION,
        "literal_role": ROLE_LOCALIZATION_CANDIDATE,
        "role_confidence": "EXACT_LITERAL_MANUAL_REVIEW_REQUIRED",
        "role_match_count": 1,
        "role_failure_code": "NON_SQUIRREL_CHANNEL",
        "consumer_family": None,
        "callee": None,
        "argument_index": None,
        "container_index": None,
        "source_span_start": start,
        "source_span_end": end,
        "source_line": line,
        "source_sha256": source_sha256,
    }


def extract_squirrel(
    module: str, root: Path, rosetta: Any
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    warnings: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.nut"), key=str):
        relative = path.relative_to(root).as_posix()
        if rosetta.FILES_SKIP_RE.search(str(path)):
            continue
        try:
            code = path.read_bytes().decode("utf-8")
            source_sha256 = sha256_text(code)
            role_analysis = analyze_squirrel_literals(code, source_sha256)
            rosetta.SEEN.clear()
            file_entries = []
            for pair in rosetta.extract(code, filename=str(path)):
                if not isinstance(pair, dict) or not pair.get("en"):
                    continue
                english = str(pair["en"])
                context = str(pair.get("_context", ""))
                mode = str(pair.get("mode", "literal"))
                file_entries.append(
                    make_entry(
                        module=module,
                        source=relative,
                        context=context,
                        english=english,
                        channel="squirrel",
                        source_code=[str(line) for line in pair.get("_code", [])],
                        mode=mode,
                        role_metadata=role_metadata_for_entry(
                            role_analysis,
                            english=english,
                            context=context,
                            mode=mode,
                            source_sha256=source_sha256,
                        ),
                    )
                )
            entries.extend(file_entries)
        except Exception as error:  # use a broad lexical fallback and preserve evidence
            fallback = fallback_squirrel_strings(module, root, path, code, error)
            if fallback:
                entries.extend(fallback)
                warnings.append(
                    {
                        "module": module,
                        "source": relative,
                        "warning": "ROSETTA_PARSER_FALLBACK",
                        "error": repr(error),
                        "fallback_candidates": len(fallback),
                    }
                )
            else:
                failures.append({"module": module, "source": relative, "error": repr(error)})
    return entries, failures, warnings


def decode_js_string(quote: str, body: str) -> str:
    # Decode only common JS escapes; retain unknown escapes rather than losing data.
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


def iter_code_strings(code: str) -> Iterable[tuple[str, str, int, int]]:
    """Yield single/double-quoted literals while ignoring comments/templates.

    A regex-only extractor can treat apostrophes in comments as opening quotes
    and consume arbitrary code until the next apostrophe. This small lexical
    scanner deliberately skips line comments, block comments, and backtick
    templates before identifying ordinary Squirrel/JavaScript literals.
    """
    index = 0
    length = len(code)
    while index < length:
        char = code[index]
        nxt = code[index + 1] if index + 1 < length else ""
        if char == "/" and nxt == "/":
            newline = code.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if char == "/" and nxt == "*":
            end = code.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if char == "`":
            index += 1
            while index < length:
                if code[index] == "\\":
                    index += 2
                elif code[index] == "`":
                    index += 1
                    break
                else:
                    index += 1
            continue
        if char not in ("'", '"'):
            index += 1
            continue
        quote = char
        start = index
        index += 1
        body_start = index
        while index < length:
            if code[index] == "\\":
                index += 2
            elif code[index] == quote:
                yield quote, code[body_start:index], start, index + 1
                index += 1
                break
            elif code[index] in "\r\n":
                # Ordinary JS/Squirrel quoted strings cannot cross an
                # unescaped physical line. Drop the malformed candidate.
                index += 1
                break
            else:
                index += 1


def fallback_squirrel_strings(
    module: str, root: Path, path: Path, code: str, error: Exception
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    relative = path.relative_to(root).as_posix()
    source_sha256 = sha256_text(code)
    role_analysis = analyze_squirrel_literals(code, source_sha256)
    lines = code.splitlines()
    previous_offset = 0
    line = 1
    for quote, body, start, end in iter_code_strings(code):
        english = decode_js_string(quote, body)
        prefix = code[max(0, start - 160) : start]
        suffix = code[end : end + 100]
        if not js_candidate(english, prefix, suffix):
            continue
        line += code.count("\n", previous_offset, start)
        previous_offset = start
        column = start - code.rfind("\n", 0, start)
        context_line = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        entry = make_entry(
            module=module,
            source=relative,
            context=f"fallback:line:{line}:column:{column}",
            english=english,
            channel="squirrel_fallback",
            source_code=[context_line],
            role_metadata={
                **lexical_role_metadata(
                    source_sha256=source_sha256,
                    start=len(code[:start].encode("utf-8")),
                    end=len(code[:end].encode("utf-8")),
                    line=line,
                ),
                "literal_role": "UNKNOWN_STRUCTURED_TEMPLATE_ROLE",
                "role_confidence": "PARSER_FALLBACK_REVIEW_REQUIRED",
                "role_match_count": 0,
                "role_failure_code": "PARSER_FALLBACK",
            },
        )
        entry["notes"] = ["ROSETTA_PARSER_FALLBACK", repr(error)]
        entries.append(entry)
    return entries


def js_candidate(text: str, prefix: str, suffix: str) -> bool:
    stripped = text.strip()
    nearby = prefix[-120:] + suffix[:100]
    if len(stripped) < 2 or not re.search(r"[A-Za-z]", stripped):
        return False
    if stripped.lower() == "use strict":
        return False
    if stripped.startswith("<") and stripped.endswith(">"):
        visible = html.unescape(re.sub(r"<[^>]*>", "", stripped)).strip()
        if not re.search(r"[A-Za-z]", visible):
            return False
    if PATHISH_RE.search(stripped) or stripped.startswith((".", "#", "[", "data-")):
        return False
    if INTERNAL_TOKEN_RE.fullmatch(stripped) and not re.search(r"\s", stripped):
        # Keep common visible one-word UI labels; reject most identifiers/property values.
        visible_call_site = re.search(
            r"(?i)(?:createTextButton|createDialog|createPopupDialog|addPopupDialog(?:Ok|Cancel)Button|"
            r"\.html|\.text|\.append)\s*\(\s*$",
            prefix,
        )
        if stripped.lower() not in {
            "back", "cancel", "close", "continue", "done", "load", "new", "no", "off",
            "ok", "on", "options", "quit", "save", "start", "yes", "random", "reset",
            "craft", "repair", "rest", "training", "locked", "unlocked",
        } and not visible_call_site:
            return False
    nearby = nearby.lower()
    if re.search(
        r"(?:font-family|background|display|position|width|height|opacity|classlist|"
        r"console\.(?:log|error|warn)|typeof|sq\.call)",
        nearby,
    ):
        return False
    return True


def extract_javascript(module: str, root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.js"), key=str):
        relative = path.relative_to(root).as_posix()
        relative_parts = {part.lower() for part in Path(relative).parts}
        if "extern" in relative_parts or path.name.lower().endswith(".min.js"):
            # Bundled UI libraries are runtime dependencies, not game copy.
            continue
        code = path.read_bytes().decode("utf-8")
        source_sha256 = sha256_text(code)
        lines = code.splitlines()
        previous_offset = 0
        line = 1
        for quote, body, start, end in iter_code_strings(code):
            english = decode_js_string(quote, body)
            prefix = code[max(0, start - 160) : start]
            suffix = code[end : end + 100]
            if not js_candidate(english, prefix, suffix):
                continue
            line += code.count("\n", previous_offset, start)
            previous_offset = start
            context_line = lines[line - 1].strip() if 0 < line <= len(lines) else ""
            entries.append(
                make_entry(
                    module=module,
                    source=relative,
                    context=f"line:{line}:column:{start - code.rfind(chr(10), 0, start)}",
                    english=english,
                    channel="javascript",
                    source_code=[context_line],
                    role_metadata=lexical_role_metadata(
                        source_sha256=source_sha256,
                        start=len(code[:start].encode("utf-8")),
                        end=len(code[:end].encode("utf-8")),
                        line=line,
                    ),
                )
            )
    return entries


def parse_module(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("module must be NAME=PATH")
    name, path = value.split("=", 1)
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise argparse.ArgumentTypeError(f"invalid module name: {name}")
    return name, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rosetta-root", required=True)
    parser.add_argument("--module", action="append", type=parse_module, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--coverage-output", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    work_root = (repo_root / "work").resolve()
    rosetta_root = require_within(Path(args.rosetta_root), work_root, "Rosetta root")
    output = require_within(Path(args.output), work_root, "detailed ledger output")
    coverage_output = Path(args.coverage_output).resolve()
    if repo_root not in coverage_output.parents:
        raise ValueError("coverage output must be inside the repository")

    actual_commit = subprocess.run(
        ["git", "-C", str(rosetta_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual_commit != ROSETTA_COMMIT:
        raise ValueError(f"Rosetta source drift: expected {ROSETTA_COMMIT}, got {actual_commit}")
    rosetta = load_rosetta(rosetta_root)

    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    warnings: list[dict[str, Any]] = []
    module_roots: dict[str, str] = {}
    for module, raw_root in args.module:
        root = require_within(raw_root, work_root, f"module {module}")
        module_roots[module] = str(root)
        squirrel, squirrel_failures, squirrel_warnings = extract_squirrel(module, root, rosetta)
        entries.extend(squirrel)
        failures.extend(squirrel_failures)
        warnings.extend(squirrel_warnings)
        entries.extend(extract_javascript(module, root))

    entries.sort(key=lambda entry: (entry["module"], entry["source"], entry["context"], entry["english"]))
    key_counts = Counter(entry["stable_key"] for entry in entries)
    duplicate_keys = sorted(key for key, count in key_counts.items() if count > 1)
    detailed = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "rosetta": {"version": "0.5.0", "commit": actual_commit},
        "module_roots": module_roots,
        "entries": entries,
        "extraction_failures": failures,
        "extraction_warnings": warnings,
        "duplicate_stable_keys": duplicate_keys,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(detailed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    per_module = {}
    for module in sorted(module_roots):
        subset = [entry for entry in entries if entry["module"] == module]
        per_module[module] = {
            "candidates": len(subset),
            "squirrel": sum(entry["channel"].startswith("squirrel") for entry in subset),
            "squirrel_fallback": sum(entry["channel"] == "squirrel_fallback" for entry in subset),
            "javascript": sum(entry["channel"] == "javascript" for entry in subset),
            "untranslated": sum(entry["status"] == "UNTRANSLATED" for entry in subset),
            "translated_needs_review": 0,
            "reviewed": 0,
            "resolved_exclusions": 0,
        }
    coverage = {
        "schema_version": 1,
        "status": "candidate_extraction",
        "detailed_ledger_location": "work/ledger/translation-ledger.json (gitignored)",
        "detailed_ledger_sha256": hashlib.sha256(output.read_bytes()).hexdigest().upper(),
        "rosetta_extractor": {"version": "0.5.0", "commit": actual_commit},
        "total_candidates": len(entries),
        "untranslated": len(entries),
        "translated_needs_review": 0,
        "reviewed": 0,
        "resolved_exclusions": 0,
        "extraction_failures": failures,
        "extraction_warnings": warnings,
        "duplicate_stable_keys": duplicate_keys,
        "per_module": per_module,
        "release_gate": "NOT_MET",
    }
    coverage_output.parent.mkdir(parents=True, exist_ok=True)
    coverage_output.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "total_candidates": len(entries),
                "failures": len(failures),
                "warnings": len(warnings),
                "per_module": per_module,
            },
            indent=2,
        )
    )
    return 0 if not failures and not duplicate_keys else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
