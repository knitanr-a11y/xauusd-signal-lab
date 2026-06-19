#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
TF_LIST = ["m1", "m5", "m15", "h1", "h4", "d1"]
STAGE = "GOLD_V3_243_SNAPSHOT_THEN_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_AUDIT_ONLY"
READY = "STAGE243_SNAPSHOT_THEN_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_READY_AUDIT_ONLY"
BLOCKED = "STAGE243_SNAPSHOT_THEN_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_BLOCKED_AUDIT_ONLY"

OFF_FLAGS = {
    "discord_webhook_called": False,
    "mt5_order_send_called": False,
    "order_placed": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
    "no_signal_order_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def progress(msg: str, current: int | None = None, total: int | None = None) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    if current is not None and total:
        pct = 100.0 * current / total
        print(f"[Stage243 snapshot progress {current}/{total} {pct:5.1f}% {ts}] {msg}", flush=True)
    else:
        print(f"[Stage243 snapshot progress {ts}] {msg}", flush=True)


def default_files_dir() -> Path:
    env = os.environ.get("GOLD_V3_MQL5_FILES", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    app = os.environ.get("APPDATA", "").strip()
    if app:
        return Path(app, "MetaQuotes", "Terminal", TERMINAL_HASH, "MQL5", "Files").resolve()
    return Path.cwd().resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def quick_line_count(path: Path) -> int:
    count = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            count += chunk.count(b"\n")
    return max(0, count - 1)


def copy_with_manifest(src: Path, dst: Path, role: str, tf: str) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return {"role": role, "tf": tf, "src": str(src), "dst": str(dst), "exists": False, "copied": False, "rows_approx": 0, "sha256": None}
    shutil.copy2(src, dst)
    return {
        "role": role,
        "tf": tf,
        "src": str(src),
        "dst": str(dst),
        "exists": True,
        "copied": True,
        "size_bytes": dst.stat().st_size,
        "rows_approx": quick_line_count(dst),
        "sha256": sha256_file(dst),
    }


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def write_paste(path: Path, summary: dict[str, Any]) -> None:
    lines = ["GOLD V3 243 PASTE_ME_SNAPSHOT_THEN_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_AUDIT_ONLY"]
    for key in ["step", "status", "ready", "decision", "created_at_utc", "elapsed_sec", "live_dir", "hist_2025_dir", "snapshot_root", "stage243_exit_code", "blocker_count"]:
        lines.append(f"{key}: {summary.get(key)}")
    lines += ["", "WHY_SNAPSHOT", "2026 live CSV can update while the search is running.", "This wrapper freezes all input CSVs first and runs Stage243 only against the snapshot copy.", "", "OFF_FLAGS"]
    for key in OFF_FLAGS:
        lines.append(f"{key}: {summary.get(key)}")
    lines += ["", "OUTPUT_FILES"]
    for k, v in summary.get("output_files", {}).items():
        lines.append(f"{k}: {v}")
    lines += ["", "BLOCKERS"]
    lines += summary.get("blockers", []) or ["NO_BLOCKERS"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    t0 = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-dir", default="", help="MQL5 Files dir containing live goldsharp_*.csv")
    parser.add_argument("--hist-2025-dir", default="", help="Directory containing 2025 gold#_*.csv")
    parser.add_argument("--snapshot-name", default="latest")
    parser.add_argument("--pass-through", nargs=argparse.REMAINDER, default=[])
    args = parser.parse_args()

    progress("resolve dirs", 1, 5)
    live_dir = Path(args.live_dir).expanduser().resolve() if args.live_dir else default_files_dir()
    hist_2025_dir = Path(args.hist_2025_dir).expanduser().resolve() if args.hist_2025_dir else live_dir / "FX_OUTPUTS" / "mt5_candles" / "gold_2025"
    stage_root = live_dir / "FX_OUTPUTS" / "gold_v3" / "243"
    snapshot_root = stage_root / "input_snapshot" / args.snapshot_name
    snapshot_hist = snapshot_root / "FX_OUTPUTS" / "mt5_candles" / "gold_2025"
    blockers: list[str] = []

    progress(f"freeze live/hist CSVs into {snapshot_root}", 2, 5)
    manifest_rows: list[dict[str, Any]] = []
    for tf in TF_LIST:
        manifest_rows.append(copy_with_manifest(live_dir / f"goldsharp_{tf}.csv", snapshot_root / f"goldsharp_{tf}.csv", "live_2026_goldsharp", tf))
        manifest_rows.append(copy_with_manifest(hist_2025_dir / f"gold#_{tf}.csv", snapshot_hist / f"gold#_{tf}.csv", "hist_2025_gold_hash", tf))

    for row in manifest_rows:
        if row["role"] == "hist_2025_gold_hash" and not row["copied"]:
            blockers.append(f"missing_hist_2025_{row['tf']}: {row['src']}")
        if row["role"] == "live_2026_goldsharp" and not row["copied"]:
            blockers.append(f"missing_live_goldsharp_{row['tf']}: {row['src']}")
        print(f"[Stage243 snapshot] {row['role']} {row['tf']} copied={row['copied']} rows_approx={row['rows_approx']} src={row['src']}", flush=True)

    manifest = {
        "step": STAGE,
        "created_at_utc": now_utc(),
        "live_dir": str(live_dir),
        "hist_2025_dir": str(hist_2025_dir),
        "snapshot_root": str(snapshot_root),
        "snapshot_hist_2025_dir": str(snapshot_hist),
        "files": manifest_rows,
        "blockers_before_stage243": blockers,
    }
    manifest_path = stage_root / "input_snapshot" / f"manifest_{args.snapshot_name}.json"
    save_json(manifest_path, manifest)

    stage243_exit = 2
    if not blockers:
        progress("run Stage243 against snapshot copy", 3, 5)
        script = Path(__file__).with_name("gold_v3_243_scalp_rebuild_no_lookahead_search_audit.py")
        cmd = [sys.executable, str(script), "--live-dir", str(snapshot_root), "--hist-2025-dir", str(snapshot_hist)] + list(args.pass_through or [])
        print("[Stage243 snapshot cmd] " + " ".join(cmd), flush=True)
        stage243_exit = subprocess.call(cmd)
        if stage243_exit != 0:
            blockers.append(f"stage243_exit_code_{stage243_exit}")

    progress("copy Stage243 outputs back to real FX_OUTPUTS/gold_v3/243", 4, 5)
    snapshot_stage_out = snapshot_root / "FX_OUTPUTS" / "gold_v3" / "243"
    real_work = stage_root / "scalp_rebuild_no_lookahead_search"
    snap_work = snapshot_stage_out / "scalp_rebuild_no_lookahead_search"
    if snap_work.exists():
        if real_work.exists():
            shutil.rmtree(real_work)
        shutil.copytree(snap_work, real_work)
    snap_paste = snapshot_stage_out / "paste_me.txt"
    if snap_paste.exists():
        shutil.copy2(snap_paste, stage_root / "paste_me_stage243_inner.txt")

    status = "READY" if not blockers else "BLOCKED"
    summary = {
        "step": STAGE,
        "status": status,
        "ready": status == "READY",
        "decision": READY if status == "READY" else BLOCKED,
        "created_at_utc": now_utc(),
        "elapsed_sec": round(time.time() - t0, 3),
        "live_dir": str(live_dir),
        "hist_2025_dir": str(hist_2025_dir),
        "snapshot_root": str(snapshot_root),
        "snapshot_manifest": str(manifest_path),
        "stage243_exit_code": stage243_exit,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "output_files": {
            "snapshot_manifest": str(manifest_path),
            "inner_stage243_paste": str(stage_root / "paste_me_stage243_inner.txt"),
            "wrapper_paste": str(stage_root / "paste_me.txt"),
            "candidate_results_csv": str(real_work / "stage243_candidate_results.csv"),
            "top_candidates_csv": str(real_work / "stage243_top_candidates.csv"),
            "no_lookahead_audit_csv": str(real_work / "stage243_no_lookahead_audit.csv"),
            "source_diagnostics_csv": str(real_work / "stage243_source_diagnostics.csv"),
            "summary_json": str(real_work / "stage243_summary.json"),
        },
    }
    summary.update(OFF_FLAGS)
    save_json(stage_root / "stage243_snapshot_wrapper_summary.json", summary)
    write_paste(stage_root / "paste_me.txt", summary)

    progress("done", 5, 5)
    print(f"Stage243 snapshot wrapper status: {status}", flush=True)
    print(f"decision: {summary['decision']}", flush=True)
    print(f"paste_me: {stage_root / 'paste_me.txt'}", flush=True)
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
