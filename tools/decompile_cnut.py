#!/usr/bin/env python3
"""Decompile copied Battle Brothers .cnut files strictly inside work/.

The original installed archive and extracted .cnut copy are never modified.
Each input is copied to a unique temporary file, decrypted there with bbsq,
and passed to nutcracker.  Only generated .nut files are written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_within(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    resolved_root = root.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"{label} must be inside {resolved_root}: {resolved}")
    return resolved


def run_hidden(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        creationflags=creationflags,
    )


def decompile_one(
    source: Path,
    source_root: Path,
    output_root: Path,
    temp_root: Path,
    bbsq: Path,
    nutcracker: Path,
) -> dict[str, Any]:
    relative = source.relative_to(source_root)
    target = output_root / relative.with_suffix(".nut")
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cnut-", dir=temp_root) as temp_dir:
        temp_cnut = Path(temp_dir) / "input.cnut"
        shutil.copyfile(source, temp_cnut)
        decrypt = run_hidden([str(bbsq), "-d", str(temp_cnut)])
        if decrypt.returncode != 0:
            return {
                "source": relative.as_posix(),
                "status": "decrypt_failed",
                "returncode": decrypt.returncode,
                "stderr": decrypt.stderr.decode("utf-8", errors="replace")[-2000:],
            }
        sanitized_sequences: dict[str, int] = {}
        # NutCracker has a documented conversion failure on the vanilla
        # cultist-origin event's CP1252 curly apostrophe. Replace only in the
        # disposable decrypted copy before NutCracker sees it. UTF-8 sequences
        # use equal-length sentinels and are restored in generated output;
        # CP1252 punctuation is normalized to its ASCII semantic equivalent.
        substitutions = [
            (b"\xe2\x80\x99", b"~AP", True),  # UTF-8 right single quotation mark
            (b"\xe2\x80\x9c", b"~LQ", True),  # UTF-8 left double quotation mark
            (b"\xe2\x80\x9d", b"~RQ", True),  # UTF-8 right double quotation mark
            (b"\xe2\x80\x93", b"~EN", True),  # UTF-8 en dash
            (b"\xe2\x80\x94", b"~EM", True),  # UTF-8 em dash
            (b"\x92", b"'", False),  # CP1252 right single quotation mark
        ]
        decrypted = temp_cnut.read_bytes()
        for original, sentinel, _restore in substitutions:
            count = decrypted.count(original)
            if count:
                sanitized_sequences[original.hex().upper()] = count
                decrypted = decrypted.replace(original, sentinel)
        if sanitized_sequences:
            temp_cnut.write_bytes(decrypted)

        decompile = run_hidden([str(nutcracker), str(temp_cnut)])
        if decompile.returncode == 0 and decompile.stdout.strip():
            restored = decompile.stdout
            for original, sentinel, restore in substitutions:
                if restore:
                    restored = restored.replace(sentinel, original)
            decompile = subprocess.CompletedProcess(
                decompile.args,
                decompile.returncode,
                stdout=restored,
                stderr=decompile.stderr,
            )
        if decompile.returncode != 0 or not decompile.stdout.strip():
            return {
                "source": relative.as_posix(),
                "status": "decompile_failed",
                "returncode": decompile.returncode,
                "stderr": decompile.stderr.decode("utf-8", errors="replace")[-2000:],
                "sanitized_utf8_sequences": sanitized_sequences,
            }
        target.write_bytes(decompile.stdout)
        return {
            "source": relative.as_posix(),
            "target": target.relative_to(output_root).as_posix(),
            "status": "ok_sanitized" if sanitized_sequences else "ok",
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
            "sanitized_utf8_sequences": sanitized_sequences,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--bbsq", required=True)
    parser.add_argument("--nutcracker", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--report")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    work_root = (repo_root / "work").resolve()
    source_root = require_within(Path(args.source), work_root, "source")
    output_root = require_within(Path(args.output), work_root, "output")
    bbsq = require_within(Path(args.bbsq), work_root, "bbsq")
    nutcracker = require_within(Path(args.nutcracker), work_root, "nutcracker")

    for tool in (bbsq, nutcracker):
        if not tool.is_file():
            raise FileNotFoundError(tool)
    if source_root.is_file():
        if source_root.suffix.lower() != ".cnut":
            raise ValueError(f"Single-file source must be a .cnut: {source_root}")
        inputs = [source_root]
        relative_root = source_root.parent
    elif source_root.is_dir():
        inputs = sorted(source_root.rglob("*.cnut"), key=str)
        relative_root = source_root
    else:
        raise FileNotFoundError(source_root)
    if args.limit is not None:
        inputs = inputs[: args.limit]
    output_root.mkdir(parents=True, exist_ok=True)
    temp_root = work_root / "temp"
    temp_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    lock = threading.Lock()
    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                decompile_one,
                source,
                relative_root,
                output_root,
                temp_root,
                bbsq,
                nutcracker,
            ): source
            for source in inputs
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            with lock:
                completed += 1
                if completed % 250 == 0 or completed == len(inputs):
                    print(f"decompiled {completed}/{len(inputs)}", file=sys.stderr)

    results.sort(key=lambda result: result["source"])
    report = {
        "source": str(source_root),
        "output": str(output_root),
        "tools": {
            "bbsq": {"path": str(bbsq), "sha256": sha256_file(bbsq)},
            "nutcracker": {"path": str(nutcracker), "sha256": sha256_file(nutcracker)},
        },
        "inputs": len(inputs),
        "ok": sum(result["status"].startswith("ok") for result in results),
        "failed": sum(not result["status"].startswith("ok") for result in results),
        "results": results,
    }
    if args.report:
        report_path = require_within(Path(args.report), work_root, "report")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("inputs", "ok", "failed")}, indent=2))
    return 0 if report["failed"] == 0 else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
