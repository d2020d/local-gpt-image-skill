#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""State helper for the local-gpt-image skill.

This script cannot call the Codex image_gen tool. It prepares and finalizes a
job so the assistant can call image_gen between the two deterministic steps.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


BASE_DIR = Path("/tmp/local-gpt-image-jobs")
SKILL_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE_DIR", SKILL_DIR.parent.parent)).expanduser().resolve()
SNAPSHOTTER = Path(
    os.environ.get(
        "LOCAL_GPT_IMAGE_SNAPSHOTTER",
        str(WORKSPACE_DIR / "scripts" / "imagegen_cache_extractor.py"),
    )
).expanduser().resolve()
FINISHER = Path(
    os.environ.get(
        "LOCAL_GPT_IMAGE_FINISHER",
        str(SKILL_DIR / "scripts" / "extract_and_delete.py"),
    )
).expanduser().resolve()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        override = "LOCAL_GPT_IMAGE_SNAPSHOTTER" if label == "snapshotter" else "LOCAL_GPT_IMAGE_FINISHER"
        raise SystemExit(
            f"{label} not found: {path}\n"
            f"Set OPENCLAW_WORKSPACE_DIR or {override} to the correct path."
        )


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def make_job_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time_ns() % 1_000_000):06d}"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def start(args: argparse.Namespace) -> None:
    require_file(SNAPSHOTTER, "snapshotter")
    job_id = args.job_id or make_job_id()
    job_dir = BASE_DIR / job_id
    state_path = Path(args.state_out).expanduser() if args.state_out else job_dir / "state.json"
    snapshot_path = job_dir / "before.json"
    result_path = job_dir / "result.json"
    out_dir = Path(args.out_dir).expanduser().resolve()

    out_dir.mkdir(parents=True, exist_ok=True)
    job_dir.mkdir(parents=True, exist_ok=True)

    run([sys.executable, str(SNAPSHOTTER), "snapshot", "--out", str(snapshot_path)])

    state = {
        "ok": True,
        "job_id": job_id,
        "created_at": time.time(),
        "prompt": args.prompt,
        "count": args.count,
        "out_dir": str(out_dir),
        "snapshot": str(snapshot_path),
        "result": str(result_path),
        "delete_originals": not args.keep_originals,
        "next_action": "CALL_IMAGE_GEN_WITH_PROMPT_THEN_RUN_FINISH",
    }
    write_json(state_path, state)
    print(json.dumps({"ok": True, "state": str(state_path), **state}, ensure_ascii=False, indent=2))


def finish(args: argparse.Namespace) -> None:
    require_file(FINISHER, "finisher")
    state_path = Path(args.state).expanduser()
    state = read_json(state_path)
    command = [
        sys.executable,
        str(FINISHER),
        "--before",
        state["snapshot"],
        "--out-dir",
        state["out_dir"],
        "--json-out",
        state["result"],
    ]
    if args.keep_originals or not state.get("delete_originals", True):
        command.append("--keep-originals")
    run(command)

    result = read_json(Path(state["result"]))
    state["finished_at"] = time.time()
    state["finish_result"] = result
    write_json(state_path, state)
    print(json.dumps({"ok": True, "state": str(state_path), **result}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare/finalize one local-gpt-image job.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Snapshot current generated-image cache before calling image_gen.")
    p_start.add_argument("--out-dir", required=True, help="Target directory for saved images.")
    p_start.add_argument("--prompt", required=True, help="Prompt that the assistant will pass to image_gen.")
    p_start.add_argument("--count", type=int, default=1, help="Expected number of image_gen calls or outputs.")
    p_start.add_argument("--job-id", help="Optional stable job id.")
    p_start.add_argument("--state-out", help="Optional explicit state JSON path.")
    p_start.add_argument("--keep-originals", action="store_true", help="Do not delete original generated files.")
    p_start.set_defaults(func=start)

    p_finish = sub.add_parser("finish", help="Copy generated outputs and delete safe originals.")
    p_finish.add_argument("--state", required=True, help="State JSON emitted by start.")
    p_finish.add_argument("--keep-originals", action="store_true", help="Override state and keep originals.")
    p_finish.set_defaults(func=finish)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
