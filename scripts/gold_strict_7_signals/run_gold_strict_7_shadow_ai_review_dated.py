#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dated-run wrapper for GOLD strict7 shadow AI review.

This wrapper keeps verification artifacts under:
  data/verification/gold_strict7_shadow_review/YYYY/MM/YYYYMMDD_HHMMSS/

It delegates the actual review work to run_gold_strict_7_shadow_ai_review_pipeline.py
and writes latest pointers in the verification root for easy discovery.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE = REPO_ROOT / "scripts" / "gold_strict_7_signals" / "run_gold_strict_7_shadow_ai_review_pipeline.py"
DEFAULT_OUT_ROOT = Path("data/verification/gold_strict7_shadow_review")
SUMMARY_NAME = "gold_strict_7_shadow_ai_review_pipeline_summary.json"
WRAPPER_SCHEMA_VERSION = "gold_strict_7_shadow_ai_review_dated_wrapper_v1"


def wpath(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def mkdirp(path: str | Path) -> None:
    Path(wpath(path)).mkdir(parents=True, exist_ok=True)


def write_text(path: str | Path, text: str) -> None:
    mkdirp(Path(path).parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json(path: str | Path) -> dict[str, Any]:
    try:
        with open(wpath(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(add_help=True, description="Run GOLD strict7 shadow AI review into dated verification folders.")
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument("--run-stamp", default="", help="Optional fixed run stamp YYYYMMDD_HHMMSS for reproducible reruns.")
    args, unknown = p.parse_known_args()
    return args, unknown


def main() -> int:
    args, unknown = parse_args()
    now = datetime.now()
    run_stamp = args.run_stamp.strip() or now.strftime("%Y%m%d_%H%M%S")
    yyyy = run_stamp[:4] if len(run_stamp) >= 4 else now.strftime("%Y")
    mm = run_stamp[4:6] if len(run_stamp) >= 6 else now.strftime("%m")
    out_root = args.out_root
    run_dir = out_root / yyyy / mm / run_stamp
    mkdirp(run_dir)

    cmd = [sys.executable, str(PIPELINE), "--out-dir", str(run_dir), *unknown]
    print("=" * 80, flush=True)
    print("GOLD strict7 shadow AI review dated wrapper", flush=True)
    print(f"out_root={out_root}", flush=True)
    print(f"run_dir={run_dir}", flush=True)
    print("CMD: " + " ".join(cmd), flush=True)
    print("=" * 80, flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")

    summary_path = run_dir / SUMMARY_NAME
    latest_summary_path = out_root / f"latest_{SUMMARY_NAME}"
    latest_run_dir_path = out_root / "latest_run_dir.txt"
    wrapper_summary_path = run_dir / "gold_strict_7_shadow_ai_review_dated_wrapper_summary.json"
    latest_wrapper_summary_path = out_root / "latest_gold_strict_7_shadow_ai_review_dated_wrapper_summary.json"

    pipeline_summary = read_json(summary_path)
    wrapper_summary = {
        "schema_version": WRAPPER_SCHEMA_VERSION,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cycle_ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "out_root": str(out_root),
        "run_dir": str(run_dir),
        "pipeline_summary_json": str(summary_path),
        "latest_pipeline_summary_json": str(latest_summary_path),
        "latest_run_dir_txt": str(latest_run_dir_path),
        "pipeline_reason": pipeline_summary.get("reason", ""),
        "pipeline_key_metrics": pipeline_summary.get("key_metrics", {}),
        "safety": {
            "shadow_only": True,
            "mt5_order_send": False,
            "verification_output_dated": True,
            "strategy_rules_modified": False,
        },
    }
    write_json(wrapper_summary_path, wrapper_summary)
    write_json(latest_wrapper_summary_path, wrapper_summary)
    write_text(latest_run_dir_path, str(run_dir))
    if summary_path.exists():
        mkdirp(latest_summary_path.parent)
        shutil.copyfile(wpath(summary_path), wpath(latest_summary_path))

    print("=" * 80, flush=True)
    print("dated wrapper summary", flush=True)
    print(json.dumps({
        "cycle_ok": wrapper_summary["cycle_ok"],
        "returncode": wrapper_summary["returncode"],
        "run_dir": str(run_dir),
        "latest_summary": str(latest_summary_path),
    }, ensure_ascii=False, indent=2), flush=True)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
