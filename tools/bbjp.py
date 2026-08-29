#!/usr/bin/env python3
"""Battle Brothers Japanese localization project utility.

All installed game and user-data inputs are opened read-only.  Extraction is
allowed only below the repository's ignored work/ directory.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA_VERSION = 1
TEXT_CODE_EXTENSIONS = {
    ".nut",
    ".cnut",
    ".js",
    ".css",
    ".html",
    ".txt",
    ".fnt",
    ".brush",
    ".json",
    ".xml",
    ".csv",
    ".tsv",
}
PRELOAD_FRAGMENT = "scripts/!mods_preload/"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def utc_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def file_record(path: Path, base: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "relative_path": path.relative_to(base).as_posix(),
        "size": stat.st_size,
        "mtime_utc": utc_iso(stat.st_mtime),
        "sha256": sha256_file(path),
    }


def tree_state(root: Path) -> dict[str, Any]:
    """Return a content-free tree state used to detect project-side writes."""
    records: list[dict[str, Any]] = []
    if not root.exists():
        return {"exists": False, "digest": None, "files": 0}
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=str):
        stat = path.stat()
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    return {
        "exists": True,
        "digest": canonical_sha256(records),
        "files": len(records),
    }


def parse_acf(text: str) -> dict[str, Any]:
    """Extract only stable fields needed from Steam's VDF-like ACF."""
    simple_fields: dict[str, Any] = {}
    for key in ("appid", "name", "installdir", "buildid", "TargetBuildID"):
        match = re.search(rf'"{re.escape(key)}"\s+"([^"]*)"', text)
        simple_fields[key] = match.group(1) if match else None

    depots: list[dict[str, str | None]] = []
    installed = re.search(
        r'"InstalledDepots"\s*\{(?P<body>.*?)\n\s*\}\s*\n\s*"SharedDepots"',
        text,
        flags=re.S,
    )
    if installed:
        for match in re.finditer(
            r'"(?P<depot>\d+)"\s*\{(?P<body>.*?)\n\s*\}',
            installed.group("body"),
            flags=re.S,
        ):
            body = match.group("body")
            manifest = re.search(r'"manifest"\s+"([^"]+)"', body)
            size = re.search(r'"size"\s+"([^"]+)"', body)
            dlc_appid = re.search(r'"dlcappid"\s+"([^"]+)"', body)
            depots.append(
                {
                    "depot_id": match.group("depot"),
                    "manifest_id": manifest.group(1) if manifest else None,
                    "size": size.group(1) if size else None,
                    "dlc_appid": dlc_appid.group(1) if dlc_appid else None,
                }
            )
    simple_fields["installed_depots"] = depots
    return simple_fields


def archive_summary(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        extensions = Counter(PurePosixPath(entry.filename).suffix.lower() for entry in entries)
        preloads = sorted(
            entry.filename.replace("\\", "/")
            for entry in entries
            if PRELOAD_FRAGMENT in entry.filename.replace("\\", "/").lower()
        )
        registration_candidates = sorted(
            entry.filename.replace("\\", "/")
            for entry in entries
            if (
                PurePosixPath(entry.filename).suffix.lower() in {".nut", ".json"}
                and re.search(
                    r"(?i)(preload|manifest|metadata|mod[_-]?info|compatibility|queue)",
                    entry.filename,
                )
            )
        )
        return {
            "entry_count": len(entries),
            "uncompressed_size": sum(entry.file_size for entry in entries),
            "extension_counts": dict(sorted(extensions.items())),
            "preload_entries": preloads,
            "registration_candidates": registration_candidates,
        }


def classify_data_file(name: str) -> tuple[str, str]:
    lower = name.lower()
    if re.fullmatch(r"data_\d+\.dat", lower):
        return "official_archive", "GAME_OR_DLC"
    if lower.startswith("mod_") and lower.endswith((".zip", ".dat")):
        if "modern_hooks" in lower:
            return "mod_archive", "FRAMEWORK"
        if re.search(r"(?:^|[ _-])msu(?:[ _-]|$)", lower):
            return "mod_archive", "FRAMEWORK"
        return "mod_archive", "LOAD_CANDIDATE"
    return "unknown_file", "LOAD_STATE_UNKNOWN"


def parse_runtime_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "registrations": [], "queue": []}
    raw = path.read_text(encoding="utf-8", errors="replace")
    text_blocks = re.findall(r'<div class="text">(.*?)</div>', raw, flags=re.S)
    lines = [
        re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", block))).strip()
        for block in text_blocks
    ]
    lines = [line for line in lines if line]

    registrations: list[dict[str, str]] = []
    registration_pattern = re.compile(
        r"Modern Hooks registered (?P<name>.*?) \((?P<id>[^)]+)\) version (?P<version>[^\s<]+)"
    )
    for line in lines:
        match = registration_pattern.search(line)
        if match:
            registration = match.groupdict()
            registration["version"] = registration["version"].rstrip(".")
            registrations.append(registration)

    queue_lines = [
        line
        for line in lines
        if "Executing queued function" in line or "Running queue bucket" in line
    ]
    error_counts = {
        "error": len(re.findall(r'<div class="row error">', raw)),
        "warning": len(re.findall(r'<div class="row warning">', raw)),
        "critical": len(re.findall(r'<div class="row critical">', raw)),
    }
    write_path_line = next((line for line in lines if line.startswith("Using write path:")), None)
    return {
        "path": str(path),
        "exists": True,
        "size": path.stat().st_size,
        "mtime_utc": utc_iso(path.stat().st_mtime),
        "sha256": sha256_file(path),
        "engine_write_path": write_path_line.split(":", 1)[1].strip() if write_path_line else None,
        "registrations": registrations,
        "queue": queue_lines,
        "log_severity_counts": error_counts,
    }


def scan(args: argparse.Namespace) -> int:
    game_root = Path(args.game_root).resolve()
    data_root = game_root / "data"
    user_data = Path(args.user_data).resolve()
    manifest = Path(args.steam_manifest).resolve()
    output = Path(args.output).resolve()

    for required in (game_root, data_root, manifest):
        if not required.exists():
            raise FileNotFoundError(f"Required installed input does not exist: {required}")

    before = {
        "game_root": tree_state(game_root),
        "user_data": tree_state(user_data),
    }

    data_files: list[dict[str, Any]] = []
    for path in sorted((p for p in data_root.iterdir() if p.is_file()), key=lambda p: p.name.lower()):
        kind, presence_class = classify_data_file(path.name)
        record = file_record(path, data_root)
        record.update({"kind": kind, "presence_classification": presence_class})
        if zipfile.is_zipfile(path):
            record["archive"] = archive_summary(path)
        data_files.append(record)

    loose_files: list[dict[str, Any]] = []
    for path in sorted((p for p in data_root.rglob("*") if p.is_file()), key=str):
        if path.parent == data_root:
            continue
        loose_files.append(file_record(path, data_root))

    exe = game_root / "win32" / "BattleBrothers.exe"
    executable = file_record(exe, game_root) if exe.exists() else None
    steam = parse_acf(manifest.read_text(encoding="utf-8", errors="replace"))
    runtime = parse_runtime_log(user_data / "log.html")

    snapshot_basis = {
        "steam": steam,
        "executable": executable,
        "data_files": [
            {key: record[key] for key in ("relative_path", "size", "sha256", "kind")}
            for record in data_files
        ],
        "loose_files": [
            {key: record[key] for key in ("relative_path", "size", "sha256")}
            for record in loose_files
        ],
    }
    installed_snapshot_id = f"BBJP-{canonical_sha256(snapshot_basis)[:20]}"

    after = {
        "game_root": tree_state(game_root),
        "user_data": tree_state(user_data),
    }
    changed_roots = [name for name in before if before[name] != after[name]]

    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "captured",
        "captured_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "installed_snapshot_id": installed_snapshot_id,
        "source_of_truth": "actual installed files",
        "paths": {
            "game_root": str(game_root),
            "data_root": str(data_root),
            "user_data": str(user_data),
            "steam_manifest": str(manifest),
        },
        "steam": steam,
        "executable": executable,
        "data_files": data_files,
        "loose_files": loose_files,
        "runtime_evidence": runtime,
        "write_audit": {
            "before": before,
            "after": after,
            "changed_roots": changed_roots,
            "write_count_to_user_environment": 0 if not changed_roots else None,
            "scope": "mtime/size/path tree comparison; file access times are intentionally excluded",
        },
        "snapshot_basis_sha256": canonical_sha256(snapshot_basis),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(installed_snapshot_id)
    if changed_roots:
        print(
            "ERROR: installed tree metadata changed while scanning: " + ", ".join(changed_roots),
            file=sys.stderr,
        )
        return 2
    return 0


def safe_member_path(destination: Path, member_name: str) -> Path:
    normalized = PurePosixPath(member_name.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"Unsafe archive member: {member_name}")
    target = destination.joinpath(*normalized.parts).resolve()
    if destination.resolve() not in target.parents and target != destination.resolve():
        raise ValueError(f"Archive member escapes destination: {member_name}")
    return target


def extract(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    work_root = (repo_root / "work").resolve()
    destination = Path(args.destination).resolve()
    archive_path = Path(args.archive).resolve()

    if work_root not in destination.parents and destination != work_root:
        raise ValueError(f"Extraction destination must be below {work_root}")
    if not archive_path.is_file() or not zipfile.is_zipfile(archive_path):
        raise ValueError(f"Input is not a readable ZIP-compatible archive: {archive_path}")

    extracted = 0
    skipped = 0
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            extension = PurePosixPath(entry.filename).suffix.lower()
            if args.text_code_only and extension not in TEXT_CODE_EXTENSIONS:
                skipped += 1
                continue
            target = safe_member_path(destination, entry.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry, "r") as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            extracted += 1

    result = {
        "archive": str(archive_path),
        "archive_sha256": sha256_file(archive_path),
        "destination": str(destination),
        "text_code_only": args.text_code_only,
        "extracted": extracted,
        "skipped": skipped,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def snapshot_file_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["relative_path"]: item for item in payload.get("data_files", [])}


def snapshot_diff_payload(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    old = snapshot_file_map(before)
    new = snapshot_file_map(after)
    shared = set(old) & set(new)
    changed = sorted(name for name in shared if old[name].get("sha256") != new[name].get("sha256"))
    return {
        "schema_version": 1,
        "before_snapshot_id": before.get("installed_snapshot_id"),
        "after_snapshot_id": after.get("installed_snapshot_id"),
        "snapshot_changed": before.get("installed_snapshot_id") != after.get("installed_snapshot_id"),
        "added_data_files": sorted(set(new) - set(old)),
        "removed_data_files": sorted(set(old) - set(new)),
        "changed_data_files": changed,
        "unchanged_data_files": sorted(name for name in shared if name not in changed),
    }


def diff_snapshots(args: argparse.Namespace) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    payload = snapshot_diff_payload(before, after)
    if args.output:
        output = Path(args.output).resolve()
        repo = Path(__file__).resolve().parents[1]
        if repo not in output.parents:
            raise ValueError("Diff output must stay inside the repository")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def show_coverage(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.report).read_text(encoding="utf-8"))
    keys = (
        "installed_snapshot_id", "total_occurrences", "resolved_exclusion_occurrences",
        "translatable_occurrences", "unique_translation_units", "untranslated_units",
        "translated_needs_review_units", "reviewed_units", "release_gate",
    )
    print(json.dumps({key: payload.get(key) for key in keys}, ensure_ascii=False, indent=2))
    return 0


def run_project_script(script: str, arguments: list[str]) -> int:
    repo = Path(__file__).resolve().parents[1]
    completed = subprocess.run([sys.executable, str(repo / "tools" / script), *arguments])
    return completed.returncode


def validate_batch_command(args: argparse.Namespace) -> int:
    command = ["--batch", args.batch, "--dry-run"]
    if args.reviewed_only:
        command.append("--reviewed-only")
    return run_project_script("apply_translation_batch.py", command)


def build_command(args: argparse.Namespace) -> int:
    command = ["--output", args.output]
    if args.allow_incomplete:
        command.append("--allow-incomplete")
    if args.snapshot_report:
        command.extend(["--snapshot-report", args.snapshot_report])
    return run_project_script("build_mod.py", command)


def qa_command(args: argparse.Namespace) -> int:
    command = ["--report", args.report]
    for option, value in (("--archive", args.archive), ("--sq", args.sq), ("--node", args.node)):
        if value:
            command.extend([option, value])
    return run_project_script("qa_mod.py", command)


def update_plan(args: argparse.Namespace) -> int:
    repo = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    work = (repo / "work").resolve()
    if work not in output.parents:
        raise ValueError("Update plans must remain below ignored work/")
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    delta = snapshot_diff_payload(before, after)
    changed = delta["added_data_files"] + delta["removed_data_files"] + delta["changed_data_files"]
    payload = {
        **delta,
        "changed_inputs": changed,
        "dependency_graph_review_required": bool(changed),
        "translation_extraction_allowed": not changed,
        "next_action": (
            "Update inventory and dependency graph before extracting or translating changed MODs."
            if changed else "No installed data fingerprint change; run stale-source and coverage validation."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bbjp", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Capture the installed source snapshot")
    scan_parser.add_argument("--game-root", required=True)
    scan_parser.add_argument("--user-data", required=True)
    scan_parser.add_argument("--steam-manifest", required=True)
    scan_parser.add_argument("--output", default="reports/source-snapshot.json")
    scan_parser.set_defaults(handler=scan)

    extract_parser = subparsers.add_parser(
        "extract", help="Copy selected archive inputs into the ignored work directory"
    )
    extract_parser.add_argument("--archive", required=True)
    extract_parser.add_argument("--destination", required=True)
    extract_parser.add_argument(
        "--text-code-only",
        action="store_true",
        help="Copy only code/text formats relevant to localization and dependency analysis",
    )
    extract_parser.set_defaults(handler=extract)

    diff_parser = subparsers.add_parser("diff", help="Compare two installed snapshot reports")
    diff_parser.add_argument("--before", required=True)
    diff_parser.add_argument("--after", required=True)
    diff_parser.add_argument("--output")
    diff_parser.set_defaults(handler=diff_snapshots)

    coverage_parser = subparsers.add_parser("coverage", help="Show canonical coverage summary")
    coverage_parser.add_argument("--report", default="reports/translation-coverage.json")
    coverage_parser.set_defaults(handler=show_coverage)

    validate_parser = subparsers.add_parser("validate", help="Validate a translation batch without applying it")
    validate_parser.add_argument("--batch", required=True)
    validate_parser.add_argument("--reviewed-only", action="store_true")
    validate_parser.set_defaults(handler=validate_batch_command)

    build_command_parser = subparsers.add_parser("build", help="Build the MOD archive")
    build_command_parser.add_argument("--output", default="dist/mod_battle_brothers_jp.zip")
    build_command_parser.add_argument("--allow-incomplete", action="store_true")
    build_command_parser.add_argument("--snapshot-report")
    build_command_parser.set_defaults(handler=build_command)

    qa_parser = subparsers.add_parser("qa", help="Run static/local MOD QA")
    qa_parser.add_argument("--archive")
    qa_parser.add_argument("--sq")
    qa_parser.add_argument("--node")
    qa_parser.add_argument("--report", default="reports/qa-static.json")
    qa_parser.set_defaults(handler=qa_command)

    update_parser = subparsers.add_parser("update", help="Create a graph-first update plan from two snapshots")
    update_parser.add_argument("--before", required=True)
    update_parser.add_argument("--after", required=True)
    update_parser.add_argument("--output", default="work/update/update-plan.json")
    update_parser.set_defaults(handler=update_plan)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
