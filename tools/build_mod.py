#!/usr/bin/env python3
"""Build a deterministic Battle Brothers MOD ZIP from repository-owned src/."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath


ALLOWED_ROOTS = {"scripts", "battle_brothers_jp", "ui", "gfx"}
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)
REQUIRED_DISTRIBUTION_FILES = {
    "scripts/!mods_preload/mod_battle_brothers_jp.nut",
    "battle_brothers_jp/runtime/core.nut",
    "battle_brothers_jp/translations/reviewed_literals.nut",
    "battle_brothers_jp/README_INSTALL_JA.txt",
    "battle_brothers_jp/compatibility.json",
    "battle_brothers_jp/licenses/THIRD_PARTY_NOTICES.md",
    "battle_brothers_jp/licenses/rosetta-BSD-2-Clause.txt",
    "gfx/fonts/battle_brothers_jp/NotoSansCJKjp-Regular.otf",
    "gfx/fonts/battle_brothers_jp/OFL.txt",
}
KNOWN_LICENSE_HASHES = {
    "battle_brothers_jp/licenses/rosetta-BSD-2-Clause.txt": "4EEFDB99E20B7A53493FE81AD23E4B239C1B80AFBBBAFF86D10A7676C79A6F26",
    "battle_brothers_jp/licenses/THIRD_PARTY_NOTICES.md": "BBDBCD6D0A3EE28D35C8C130BFFE43B2501AC463D1C4641AC9F4731D68DDFC6B",
    "gfx/fonts/battle_brothers_jp/OFL.txt": "BABCFE66C8A098B2FA279BC724A3A342F8124F77CE18941FBCC1BBB39823CDED",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _is_link_or_junction(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )


def _reject_linked_components(repo: Path, path: Path, label: str) -> None:
    """Reject any existing symlink/junction from repo through path itself."""
    repo = repo.resolve()
    raw_path = path.absolute()
    try:
        relative = raw_path.relative_to(repo)
    except ValueError as error:
        raise ValueError(f"{label} lexical path must stay below {repo}") from error
    current = repo
    for part in relative.parts:
        current = current / part
        try:
            if _is_link_or_junction(current):
                raise ValueError(f"{label} contains a symlink or junction: {current}")
        except OSError as error:
            raise ValueError(f"{label} component could not be inspected: {current}") from error


def _validated_approved_root(repo: Path, parts: tuple[str, ...], label: str) -> tuple[Path, Path]:
    repo = repo.resolve()
    lexical = repo.joinpath(*parts)
    _reject_linked_components(repo, lexical, label)
    resolved = lexical.resolve()
    if resolved != repo and repo not in resolved.parents:
        raise ValueError(f"{label} resolves outside repository: {resolved}")
    return lexical, resolved


def validate_artifact_destination(
    repo: Path, output: Path, allow_incomplete: bool, internal_staging: bool = False
) -> Path:
    repo = repo.resolve()
    raw_output = output.absolute()
    if raw_output.is_symlink():
        raise ValueError("Artifact destination must be a regular non-symlink file")
    output = raw_output.resolve()
    if output.suffix.lower() != ".zip":
        raise ValueError("Artifact destination must be a .zip file")
    if output.exists():
        if not output.is_file() or output.stat().st_nlink != 1:
            raise ValueError("Artifact destination must be a regular non-aliased file")
    kind = "internal staging" if internal_staging else "development" if allow_incomplete else "release"
    root_parts = ("work", "build-staging") if internal_staging else ("work", "qa") if allow_incomplete else ("dist",)
    approved_lexical, approved = _validated_approved_root(
        repo, root_parts, f"{kind} artifact root"
    )
    if approved_lexical not in raw_output.parents or approved not in output.parents:
        raise ValueError(f"{kind} artifact destination must stay below {approved_lexical}")
    _reject_linked_components(repo, raw_output.parent, f"{kind} artifact destination")
    return output


def validate_qa_report_destination(repo: Path, qa_report: Path, output: Path) -> Path:
    repo = repo.resolve()
    raw_report = qa_report.absolute()
    if raw_report.is_symlink():
        raise ValueError("Release QA report must be a regular non-symlink file")
    qa_report = raw_report.resolve()
    output = output.resolve()
    approved_lexical, approved = _validated_approved_root(
        repo, ("reports", "local"), "Release QA report root"
    )
    if qa_report.suffix.lower() != ".json" \
        or approved_lexical not in raw_report.parents \
        or approved not in qa_report.parents:
        raise ValueError(f"Release QA report must be a .json below {approved_lexical}")
    _reject_linked_components(repo, raw_report.parent, "Release QA report destination")
    if qa_report == output:
        raise ValueError("Release QA report must not alias the artifact output")
    if qa_report.exists() and (not qa_report.is_file() or qa_report.stat().st_nlink != 1):
        raise ValueError("Release QA report must be a regular non-aliased file")
    if qa_report.exists() and output.exists() and qa_report.samefile(output):
        raise ValueError("Release QA report must not alias the artifact output")
    return qa_report


def source_inventory(repo: Path) -> dict[str, dict[str, object]]:
    src = repo / "src"
    return {
        path.relative_to(src).as_posix(): {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(src.rglob("*"))
        if path.is_file() and path.relative_to(src).parts[0] in ALLOWED_ROOTS
    }


def verify_distribution_contract(repo: Path) -> dict[str, object]:
    manifest_path = repo / "reports" / "package-source-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Package source manifest missing; run tools/generate_package_manifest.py")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_files = source_inventory(repo)
    if manifest.get("schema_version") != 1 \
        or manifest.get("generator") != "tools/generate_package_manifest.py":
        raise ValueError("Package source manifest generator identity is invalid")
    if manifest.get("files") != actual_files or manifest.get("file_count") != len(actual_files):
        raise ValueError("Package source manifest is stale; regenerate and review it")
    missing = sorted(REQUIRED_DISTRIBUTION_FILES - set(actual_files))
    if missing:
        raise ValueError(f"Required distribution files missing: {missing}")
    license_mismatches = [
        relative for relative, expected in KNOWN_LICENSE_HASHES.items()
        if relative not in actual_files or actual_files[relative]["sha256"] != expected
    ]
    if license_mismatches:
        raise ValueError(f"Third-party license/provenance bytes changed: {license_mismatches}")

    runtime_manifest = json.loads(
        (repo / "reports" / "runtime-translation-manifest.json").read_text(encoding="utf-8")
    )
    stale_runtime_outputs = [
        relative for relative, expected in runtime_manifest.get("outputs", {}).items()
        if not (repo / relative).is_file() or sha256(repo / relative) != expected
    ]
    if stale_runtime_outputs:
        raise ValueError(f"Generated runtime outputs are stale: {stale_runtime_outputs}")
    if runtime_manifest.get("external_rosetta_required") is not False \
        or runtime_manifest.get("external_stdlib_required") is not False:
        raise ValueError("Runtime manifest reintroduced an external Rosetta/stdlib requirement")

    compatibility = json.loads(
        (repo / "src" / "battle_brothers_jp" / "compatibility.json").read_text(encoding="utf-8")
    )
    snapshot_lock = json.loads(
        (repo / "reports" / "supported-snapshot-lock.json").read_text(encoding="utf-8")
    )
    version = (repo / "VERSION").read_text(encoding="utf-8").strip()
    if compatibility.get("mod_id") != "mod_battle_brothers_jp" or compatibility.get("version") != version:
        raise ValueError("VERSION and packaged compatibility metadata disagree")
    if compatibility.get("hard_dependencies") != [
        {"id": "mod_modern_hooks", "condition": ">=0.6.0"}
    ]:
        raise ValueError("Packaged hard dependency metadata is not the audited Modern Hooks-only contract")
    if compatibility.get("normal_runtime_network_required") is not False:
        raise ValueError("Packaged compatibility metadata requires a network at runtime")
    expected_release_state = (
        "DEVELOPMENT_NOT_RELEASE_CANDIDATE" if "dev" in version.lower() else None
    )
    if expected_release_state and compatibility.get("release_state") != expected_release_state:
        raise ValueError("Development VERSION and packaged release_state disagree")
    if compatibility.get("runtime_game_qa") not in {"NOT_TESTED", "PASS"}:
        raise ValueError("Packaged runtime_game_qa state is invalid")

    snapshot_id = snapshot_lock.get("installed_snapshot_id")
    snapshot_bindings = {
        "package_manifest": manifest.get("installed_snapshot_id"),
        "runtime_manifest": runtime_manifest.get("installed_snapshot_id"),
        "compatibility": compatibility.get("installed_snapshot_id"),
    }
    if not snapshot_id or any(value != snapshot_id for value in snapshot_bindings.values()):
        raise ValueError(f"Packaged metadata snapshot IDs disagree: {snapshot_bindings}")
    if runtime_manifest.get("runtime_qa") != compatibility.get("runtime_game_qa"):
        raise ValueError("Runtime manifest and packaged runtime_game_qa state disagree")

    install_readme = (
        repo / "src" / "battle_brothers_jp" / "README_INSTALL_JA.txt"
    ).read_text(encoding="utf-8")
    expected_readme_title = f"Battle Brothers 統合日本語化MOD {version}"
    expected_runtime_line = f"実ゲーム起動QAは現在 {compatibility['runtime_game_qa']} です。"
    if not install_readme.startswith(expected_readme_title + "\n") \
        or expected_runtime_line not in install_readme \
        or (("dev" in version.lower()) != ("これは開発ビルドです" in install_readme)):
        raise ValueError("Packaged install README version/build/runtime-QA state disagrees")

    preload = (repo / "src" / "scripts" / "!mods_preload" / "mod_battle_brothers_jp.nut").read_text(encoding="utf-8")
    if f'Version = "{version}"' not in preload \
        or f'Snapshot = "{snapshot_id}"' not in preload \
        or 'mod.require("mod_modern_hooks >= 0.6.0")' not in preload:
        raise ValueError("Preload version/snapshot/dependency metadata disagrees with the package contract")
    graph = json.loads((repo / "reports" / "mod-dependency-graph.json").read_text(encoding="utf-8"))
    jp_nodes = [node for node in graph.get("nodes", []) if node.get("id") == "mod_battle_brothers_jp"]
    expected_graph_classification = (
        "DEVELOPMENT_ARTIFACT_STATIC_QA_PASS_NOT_RELEASE"
        if "dev" in version.lower()
        else "RUNTIME_VERIFIED_BUILD_APPROVED"
        if compatibility.get("release_state") == "RUNTIME_VERIFIED_BUILD_APPROVED"
        else "RC_BUILD_APPROVED"
    )
    if len(jp_nodes) != 1 \
        or jp_nodes[0].get("version") != version \
        or jp_nodes[0].get("classification") != expected_graph_classification:
        raise ValueError("Dependency graph JP version/classification disagrees with package metadata")
    return {
        "installed_snapshot_id": snapshot_id,
        "package_manifest_sha256": sha256(manifest_path),
        "runtime_manifest_sha256": sha256(repo / "reports" / "runtime-translation-manifest.json"),
        "source_entries": len(actual_files),
    }


def verify_built_archive(repo: Path, output: Path) -> dict[str, object]:
    expected = source_inventory(repo)
    errors: list[str] = []
    with zipfile.ZipFile(output) as archive:
        if archive.comment != b"":
            errors.append("archive comment is not empty")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            errors.append("duplicate archive entry names")
        folded = [name.casefold() for name in names]
        if len(folded) != len(set(folded)):
            errors.append("case-colliding archive entry names")
        for info in infos:
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                errors.append(f"symlink archive entry: {info.filename}")
            if info.flag_bits & 0x1:
                errors.append(f"encrypted archive entry: {info.filename}")
            if info.date_time != FIXED_ZIP_TIME:
                errors.append(f"non-deterministic archive timestamp: {info.filename}")
            if info.compress_type != zipfile.ZIP_DEFLATED:
                errors.append(f"unexpected archive compression: {info.filename}")
            if ((info.external_attr >> 16) & 0o177777) != 0o100644:
                errors.append(f"unexpected archive mode: {info.filename}")
            if info.filename not in expected:
                errors.append(f"unexpected archive entry: {info.filename}")
                continue
            data = archive.read(info)
            if hashlib.sha256(data).hexdigest().upper() != expected[info.filename]["sha256"]:
                errors.append(f"archive content mismatch: {info.filename}")
        omitted = sorted(set(expected) - set(names))
        errors.extend(f"source omitted from archive: {name}" for name in omitted)
    if errors:
        raise ValueError(f"Built archive failed self-verification: {errors}")
    return {"entries": len(expected), "archive_sha256": sha256(output)}


def verify_semantic_limitations(repo: Path) -> None:
    path = repo / "reports" / "upstream-source-limitations.json"
    if not path.is_file():
        raise ValueError("Release build requires upstream-source limitation audit")
    payload = json.loads(path.read_text(encoding="utf-8"))
    allowed_statuses = {
        "RESOLVED",
        "RESOLVED_FOR_LOCALIZATION_WITH_KNOWN_UPSTREAM_LIMITATIONS",
    }
    if payload.get("status") not in allowed_statuses:
        raise ValueError(
            f"Release build refuses open upstream semantic limitations: {payload.get('status')}"
        )


def verify_release_metadata(repo: Path) -> None:
    compatibility = json.loads(
        (repo / "src" / "battle_brothers_jp" / "compatibility.json").read_text(encoding="utf-8")
    )
    allowed = {
        "RC_BUILD_APPROVED_MANUAL_INSTALL_VERIFICATION_REQUIRED": "NOT_TESTED",
        "RUNTIME_VERIFIED_BUILD_APPROVED": "PASS",
    }
    state = compatibility.get("release_state")
    if state not in allowed or compatibility.get("runtime_game_qa") != allowed[state]:
        raise ValueError("Release metadata is not in an approved runtime-verification state")


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


def _assemble_candidate(
    repo: Path,
    output: Path,
    allow_incomplete: bool,
    snapshot_report_path: Path | None = None,
    max_snapshot_age_hours: float = 24.0,
    internal_staging: bool = False,
) -> dict[str, object]:
    output = validate_artifact_destination(repo, output, allow_incomplete, internal_staging)
    src = repo / "src"
    version = (repo / "VERSION").read_text(encoding="utf-8").strip()
    coverage_path = repo / "reports" / "translation-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8")) if coverage_path.exists() else {}
    release_inputs: dict[str, object] | None = None
    distribution_contract = verify_distribution_contract(repo)
    if not allow_incomplete:
        if "dev" in version.lower():
            raise ValueError(f"Release build refuses development version: {version}")
        if coverage.get("release_gate") != "MET":
            raise ValueError("Release build refuses unmet translation coverage gate")
        verify_semantic_limitations(repo)
        verify_release_metadata(repo)
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
    archive_verification = verify_built_archive(repo, output)

    return {
        "schema_version": 1,
        "built_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "version": version,
        "development_artifact": allow_incomplete,
        "release_inputs": release_inputs,
        "distribution_contract": distribution_contract,
        "archive_verification": archive_verification,
        "artifact": str(output.resolve()),
        "artifact_sha256": sha256(output),
        "entries": len(files),
        "uncompressed_bytes": sum(path.stat().st_size for _, path in files),
    }


def build(
    repo: Path,
    output: Path,
    allow_incomplete: bool,
    snapshot_report_path: Path | None = None,
    max_snapshot_age_hours: float = 24.0,
    sq: Path | None = None,
    node: Path | None = None,
    qa_report: Path | None = None,
) -> dict[str, object]:
    output = validate_artifact_destination(repo, output, allow_incomplete)
    if allow_incomplete:
        return _assemble_candidate(
            repo, output, True, snapshot_report_path, max_snapshot_age_hours
        )

    if sq is None or node is None or not sq.is_file() or not node.is_file():
        raise ValueError("Release build requires existing --sq and --node executables")
    if qa_report is None:
        raise ValueError("Release build requires a bound QA report path")
    qa_report = validate_qa_report_destination(repo, qa_report, output)

    staging_dir, _ = _validated_approved_root(
        repo, ("work", "build-staging"), "internal staging artifact root"
    )
    staging_dir.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        dir=staging_dir, prefix="mod_battle_brothers_jp_", suffix=".candidate.zip", delete=False
    )
    temporary.close()
    candidate = Path(temporary.name)
    candidate.unlink()
    try:
        assembled = _assemble_candidate(
            repo, candidate, False, snapshot_report_path, max_snapshot_age_hours, True
        )
        qa_report.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run([
            sys.executable,
            str(repo / "tools" / "qa_mod.py"),
            "--archive", str(candidate),
            "--sq", str(sq.resolve()),
            "--node", str(node.resolve()),
            "--report", str(qa_report),
        ], capture_output=True, text=True)
        if completed.returncode != 0:
            raise ValueError("Release artifact QA failed; see " + str(qa_report))
        qa_payload = json.loads(qa_report.read_text(encoding="utf-8"))
        if qa_payload.get("status") != "PASS":
            raise ValueError(f"Release artifact QA is not fully PASS: {qa_payload.get('status')}")
        archive_checks = [
            check for check in qa_payload.get("checks", [])
            if check.get("name") == "archive_structure_and_content"
        ]
        candidate_sha = sha256(candidate)
        if len(archive_checks) != 1 \
            or archive_checks[0].get("status") != "PASS" \
            or archive_checks[0].get("detail", {}).get("artifact_sha256") != candidate_sha:
            raise ValueError("Release QA report is not bound to the assembled candidate SHA-256")

        output.parent.mkdir(parents=True, exist_ok=True)
        candidate.replace(output)
        assembled["artifact"] = str(output.resolve())
        assembled["artifact_sha256"] = sha256(output)
        assembled["archive_verification"]["archive_sha256"] = assembled["artifact_sha256"]
        assembled["qa_report"] = str(qa_report.resolve())
        assembled["qa_report_sha256"] = sha256(qa_report)
        assembled["qa_status"] = "PASS"
        return assembled
    finally:
        if candidate.exists():
            candidate.unlink()


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
    parser.add_argument("--sq", help="Squirrel executable; required for release build QA")
    parser.add_argument("--node", help="Node executable; required for release build QA")
    parser.add_argument("--qa-report", default="reports/local/release-build-qa.json")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = Path(args.output)
    if not output.is_absolute():
        output = repo / output
    if repo not in output.resolve().parents:
        raise SystemExit("ERROR: output must stay inside the repository")
    try:
        snapshot_report = Path(args.snapshot_report).resolve() if args.snapshot_report else None
        qa_report = Path(args.qa_report)
        if not qa_report.is_absolute():
            qa_report = repo / qa_report
        result = build(
            repo,
            output,
            args.allow_incomplete,
            snapshot_report,
            args.max_snapshot_age_hours,
            Path(args.sq).resolve() if args.sq else None,
            Path(args.node).resolve() if args.node else None,
            qa_report,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
