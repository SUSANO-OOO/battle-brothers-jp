#!/usr/bin/env python3
"""Create a review batch from the implemented Vertical Slice source maps."""

from __future__ import annotations

import json
import re
from pathlib import Path


PAIR_RE = re.compile(
    r"\{(?P<body>[^{}]*?\ben\s*=\s*(?P<en>\"(?:\\.|[^\"\\])*\")"
    r"[^{}]*?\bja\s*=\s*(?P<ja>\"(?:\\.|[^\"\\])*\")[^{}]*?)\}",
    re.S,
)
JS_PAIR_RE = re.compile(
    r'^\s*(?P<en>\"(?:\\.|[^\"\\])*\")\s*:\s*'
    r'(?P<ja>\"(?:\\.|[^\"\\])*\")\s*,?\s*$',
    re.M,
)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    squirrel = (repo / "src" / "battle_brothers_jp" / "translations" / "vertical_slice.nut").read_text(encoding="utf-8")
    javascript = (repo / "src" / "ui" / "mods" / "mod_battle_brothers_jp" / "main.js").read_text(encoding="utf-8")
    translations = {
        json.loads(match.group("en")): json.loads(match.group("ja"))
        for match in PAIR_RE.finditer(squirrel)
    }
    translations.update(
        {
            json.loads(match.group("en")): json.loads(match.group("ja"))
            for match in JS_PAIR_RE.finditer(javascript)
        }
    )
    units_payload = json.loads((repo / "work" / "ledger" / "translation-units.json").read_text(encoding="utf-8"))
    units = {unit["english"]: unit for unit in units_payload["units"] if unit["english"] in translations}
    if set(units) != set(translations):
        raise SystemExit(f"ERROR: source/ledger mismatch: missing={sorted(set(translations) - set(units))}")
    entries = []
    for english in sorted(translations):
        unit = units[english]
        entries.append(
            {
                "translation_unit": unit["translation_unit"],
                "stable_key": unit["occurrences"][0],
                "english": english,
                "japanese": translations[english],
                "source": "src Vertical Slice maps",
                "context": "reports/vertical-slice-reachability.json",
                "placeholder_signature": unit["placeholder_signature"],
                "review_status": "DRAFT_INDEPENDENT_REVIEW_REQUIRED",
                "notes": ["STATICALLY_REACHABLE", "RUNTIME_NOT_TESTED"],
            }
        )
    payload = {
        "schema_version": 1,
        "batch_id": "vertical_slice_source_001",
        "installed_snapshot_id": "BBJP-CF88150E7B355ECD32D9",
        "entries": entries,
    }
    output = repo / "work" / "review_batches" / "vertical_slice_source_001.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "entries": len(entries)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
