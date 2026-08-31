#!/usr/bin/env python3
"""Generate a deterministic hash manifest for every distributable src file."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPECTED_DISTRIBUTABLE_FILES = {
    "battle_brothers_jp/compatibility.json",
    "battle_brothers_jp/hooks/event_variable_boundaries.nut",
    "battle_brothers_jp/hooks/msu_display_boundaries.nut",
    "battle_brothers_jp/hooks/runtime_display_boundaries.nut",
    "battle_brothers_jp/hooks/semantic_name_safety.nut",
    "battle_brothers_jp/hooks/source_defect_boundaries.nut",
    "battle_brothers_jp/hooks/ui_boundaries.nut",
    "battle_brothers_jp/licenses/rosetta-BSD-2-Clause.txt",
    "battle_brothers_jp/licenses/THIRD_PARTY_NOTICES.md",
    "battle_brothers_jp/README_INSTALL_JA.txt",
    "battle_brothers_jp/runtime/core.nut",
    "battle_brothers_jp/translations/reviewed_literals.nut",
    "gfx/fonts/battle_brothers_jp/NotoSansCJKjp-Regular.otf",
    "gfx/fonts/battle_brothers_jp/OFL.txt",
    "gfx/fonts/battle_brothers_jp/README.md",
    "scripts/!mods_preload/mod_battle_brothers_jp.nut",
    "ui/mods/mod_battle_brothers_jp/generated_strings.js",
    "ui/mods/mod_battle_brothers_jp/generated_strings_legends.js",
    "ui/mods/mod_battle_brothers_jp/generated_strings_modern_hooks.js",
    "ui/mods/mod_battle_brothers_jp/generated_strings_msu.js",
    "ui/mods/mod_battle_brothers_jp/main.css",
    "ui/mods/mod_battle_brothers_jp/main.js",
}
ALLOWED_ROOTS = {"scripts", "battle_brothers_jp", "ui", "gfx"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    src = repo / "src"
    discovered = {
        path.relative_to(src).as_posix(): {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(src.rglob("*"))
        if path.is_file() and path.relative_to(src).parts[0] in ALLOWED_ROOTS
    }
    unexpected = sorted(set(discovered) - EXPECTED_DISTRIBUTABLE_FILES)
    missing = sorted(EXPECTED_DISTRIBUTABLE_FILES - set(discovered))
    if unexpected or missing:
        raise SystemExit(
            f"ERROR: distributable inventory changed; review the explicit allowlist: "
            f"unexpected={unexpected}, missing={missing}"
        )
    files = {relative: discovered[relative] for relative in sorted(EXPECTED_DISTRIBUTABLE_FILES)}
    payload = {
        "schema_version": 1,
        "generator": "tools/generate_package_manifest.py",
        "installed_snapshot_id": "BBJP-CF88150E7B355ECD32D9",
        "file_count": len(files),
        "files": files,
    }
    output = repo / "reports" / "package-source-manifest.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"file_count": len(files)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
