#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Copy new image_gen outputs to a target directory and delete safe originals.

This wrapper intentionally reuses the shared cache extractor, then deletes only
files created under ~/.codex/generated_images after hash verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE_DIR", SKILL_DIR.parent.parent)).expanduser().resolve()
EXTRACTOR = Path(
    os.environ.get(
        "LOCAL_GPT_IMAGE_SNAPSHOTTER",
        str(WORKSPACE_DIR / "scripts" / "imagegen_cache_extractor.py"),
    )
).expanduser().resolve()
GENERATED_ROOT = Path(
    os.environ.get("LOCAL_GPT_IMAGE_GENERATED_ROOT", str(Path.home() / ".codex/generated_images"))
).expanduser().resolve()


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def run_extractor(args: argparse.Namespace, json_out: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(EXTRACTOR),
        "extract",
        "--before",
        str(args.before),
        "--out-dir",
        str(args.out_dir),
        "--json-out",
        str(json_out),
        "--max-size",
        str(args.max_size),
        "--min-bytes",
        str(args.min_bytes),
    ]
    if args.since_epoch is not None:
        command.extend(["--since-epoch", str(args.since_epoch)])
    for root in args.root or []:
        command.extend(["--root", root])

    subprocess.run(command, check=True)
    return json.loads(json_out.read_text(encoding="utf-8"))


def delete_originals(saved: list[dict[str, Any]], keep_originals: bool) -> tuple[list[str], list[dict[str, str]]]:
    deleted: list[str] = []
    skipped: list[dict[str, str]] = []
    seen_sources: set[str] = set()

    if keep_originals:
        for item in saved:
            source = item.get("source")
            if source:
                skipped.append({"source": source, "reason": "keep-originals"})
        return deleted, skipped

    for item in saved:
        source_text = item.get("source")
        expected_sha1 = item.get("sha1")
        if not source_text or source_text in seen_sources:
            continue
        seen_sources.add(source_text)

        source = Path(source_text)
        try:
            resolved = source.resolve()
        except OSError:
            skipped.append({"source": source_text, "reason": "resolve-failed"})
            continue

        if not is_under(resolved, GENERATED_ROOT):
            skipped.append({"source": str(resolved), "reason": "outside-generated-images"})
            continue
        if not resolved.exists():
            skipped.append({"source": str(resolved), "reason": "missing"})
            continue
        if not resolved.is_file():
            skipped.append({"source": str(resolved), "reason": "not-file"})
            continue
        if expected_sha1 and sha1_file(resolved) != expected_sha1:
            skipped.append({"source": str(resolved), "reason": "sha1-mismatch"})
            continue

        resolved.unlink()
        deleted.append(str(resolved))

    return deleted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Save built-in image_gen outputs to a directory and delete safe originals."
    )
    parser.add_argument("--before", required=True, type=Path, help="Snapshot JSON created before image_gen.")
    parser.add_argument("--out-dir", required=True, type=Path, help="Target directory for copied images.")
    parser.add_argument("--json-out", type=Path, help="Optional result JSON output path.")
    parser.add_argument("--root", action="append", help="Override extractor root. Usually not needed.")
    parser.add_argument("--max-size", type=int, default=50 * 1024 * 1024)
    parser.add_argument("--min-bytes", type=int, default=20 * 1024)
    parser.add_argument("--since-epoch", type=float)
    parser.add_argument("--keep-originals", action="store_true", help="Copy files but do not delete originals.")
    args = parser.parse_args()

    if not EXTRACTOR.exists():
        raise SystemExit(f"extractor not found: {EXTRACTOR}")
    if not args.before.exists():
        raise SystemExit(f"snapshot not found: {args.before}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    temp_json: Path | None = None
    json_path = args.json_out
    if json_path is None:
        handle = tempfile.NamedTemporaryFile(prefix="local-gpt-image-", suffix=".json", delete=False)
        handle.close()
        temp_json = Path(handle.name)
        json_path = temp_json
    else:
        json_path.parent.mkdir(parents=True, exist_ok=True)

    result = run_extractor(args, json_path)
    deleted, skipped = delete_originals(result.get("saved", []), args.keep_originals)

    result["deleted_original_count"] = len(deleted)
    result["deleted_originals"] = deleted
    result["skipped_delete"] = skipped

    if args.json_out:
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    elif temp_json:
        temp_json.unlink(missing_ok=True)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
