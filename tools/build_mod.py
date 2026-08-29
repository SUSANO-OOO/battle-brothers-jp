#!/usr/bin/env python3
"""Build a deterministic Battle Brothers MOD ZIP from repository-owned src/."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath


ALLOWED_ROOTS = {"scripts", "battle_brothers_jp", "ui", "gfx"}
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verify_release_inputs(
    repo: Path, snapshot_report_path: Path | None, max_snapshot_age_hours: float
) -> dict[str, object]:
    if snapshot_report_path is None:
        raise ValueError("Release build requires --snapshot-report from a fresh read-only scan")
    lock = json.loads((repo / "reports" / "supported-snapshot-lock.json").read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_report_path.read_text(encoding="utf-8"))
    coverage = json.loads((repo / "reports" / "translation-coverage.json").read_text(encoding="utf-8"))

    captured = datetime.fromisoformat(snapshot["captured_at_utc"])
    if captured.tzinfo is None:
        raise ValueError("Fresh snapshot timestamp must include a timezone")
    age = datetime.now(tz=timezone.utc) - captured.astimezone(timezone.utc)
    if age < timedelta(0) or age > timedelta(hours=max_snapshot_age_hours):
        raise ValueError(
            f"Snapshot report is not fresh: age={age.total_seconds() / 3600:.2f}h, "
            f"limit={max_snapshot_age_hours:.2f}h"
        )

    expected_identity = (lock["installed_snapshot_id"], lock["snapshot_basis_sha256"])
    actual_identity = (snapshot.get("installed_snapshot_id"), snapshot.get("snapshot_basis_sha256"))
    if actual_identity != expected_identity:
        raise ValueError(f"Fresh snapshot identity does not match supported lock: {actual_identity}")
    if coverage.get("installed_snapshot_id") != lock["installed_snapshot_id"]:
        raise ValueError("Coverage is not bound to the supported installed snapshot ID")
    if coverage.get("snapshot_basis_sha256") != lock["snapshot_basis_sha256"]:
        raise ValueError("Coverage is not bound to the supported snapshot fingerprint")
    if snapshot.get("steam", {}).get("buildid") != lock["steam_build_id"]:
        raise ValueError("Steam build ID differs from the supported snapshot lock")
    if snapshot.get("executable", {}).get("sha256") != lock["executable_sha256"]:
        raise ValueError("BattleBrothers.exe fingerprint differs from the supported snapshot lock")

    actual_data_files = {item["relative_path"]: item["sha256"] for item in snapshot.get("data_files", [])}
    if actual_data_files != lock["data_files"]:
        missing = sorted(set(lock["data_files"]) - set(actual_data_files))
        unexpected = sorted(set(actual_data_files) - set(lock["data_files"]))
        changed = sorted(
            name for name in set(actual_data_files) & set(lock["data_files"])
            if actual_data_files[name] != lock["data_files"][name]
        )
        raise ValueError(
            f"Installed data fingerprints differ from supported lock: "
            f"missing={missing}, unexpected={unexpected}, changed={changed}"
        )

    write_audit = snapshot.get("write_audit", {})
    if write_audit.get("changed_roots") or write_audit.get("write_count_to_user_environment") != 0:
        raise ValueError("Fresh scan did not prove zero project writes to the user environment")

    ledger_hashes = {}
    for relative, expected_hash in lock["ledger_files"].items():
        path = repo / relative
        if not path.is_file():
            raise ValueError(f"Canonical ledger file missing: {relative}")
        actual_hash = sha256(path)
        ledger_hashes[relative] = actual_hash
        if actual_hash != expected_hash:
            raise ValueError(f"Canonical ledger fingerprint changed: {relative}")

    return {
        "installed_snapshot_id": lock["installed_snapshot_id"],
        "snapshot_basis_sha256": lock["snapshot_basis_sha256"],
        "fresh_snapshot_captured_at_utc": snapshot["captured_at_utc"],
        "fresh_snapshot_age_hours": round(age.total_seconds() / 3600, 4),
        "ledger_sha256": ledger_hashes,
    }


def build(
    repo: Path,
    output: Path,
    allow_incomplete: bool,
    snapshot_report_path: Path | None = None,
    max_snapshot_age_hours: float = 24.0,
) -> dict[str, object]:
    src = repo / "src"
    version = (repo / "VERSION").read_text(encoding="utf-8").strip()
    coverage_path = repo / "reports" / "translation-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8")) if coverage_path.exists() else {}
    release_inputs: dict[str, object] | None = None
    if not allow_incomplete:
        if "dev" in version.lower():
            raise ValueError(f"Release build refuses development version: {version}")
        if coverage.get("release_gate") != "MET":
            raise ValueError("Release build refuses unmet translation coverage gate")
        release_inputs = verify_release_inputs(repo, snapshot_report_path, max_snapshot_age_hours)

    files = []
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        relative = PurePosixPath(path.relative_to(src).as_posix())
        if relative.parts[0] not in ALLOWED_ROOTS:
            continue
        files.append((relative, path))
    files.sort(key=lambda item: str(item[0]))
    if not files:
        raise ValueError("No distributable files found below src/")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, path in files:
            info = zipfile.ZipInfo(str(relative), FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    return {
        "schema_version": 1,
        "built_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "version": version,
        "development_artifact": allow_incomplete,
        "release_inputs": release_inputs,
        "artifact": str(output.resolve()),
        "artifact_sha256": sha256(output),
        "entries": len(files),
        "uncompressed_bytes": sum(path.stat().st_size for _, path in files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dist/mod_battle_brothers_jp.zip")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Build a clearly development-only artifact despite unmet release gates.",
    )
    parser.add_argument(
        "--snapshot-report",
        help="Fresh reports/source-snapshot JSON produced by a read-only scan; required for release builds.",
    )
    parser.add_argument("--max-snapshot-age-hours", type=float, default=24.0)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = Path(args.output)
    if not output.is_absolute():
        output = repo / output
    if repo not in output.resolve().parents:
        raise SystemExit("ERROR: output must stay inside the repository")
    try:
        snapshot_report = Path(args.snapshot_report).resolve() if args.snapshot_report else None
        result = build(
            repo,
            output,
            args.allow_incomplete,
            snapshot_report,
            args.max_snapshot_age_hours,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
