#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STEP = "GOLD_V3_38_LIVE_MINUTE_LOOP"
OUT = "38_live_minute_loop"
READY_STATUS = "GOLD_V3_38_LIVE_MINUTE_LOOP_READY"
EXCEPTION_STATUS = "GOLD_V3_38_LIVE_MINUTE_LOOP_EXCEPTION"

LOOP_FIELDS = [
    "run_id",
    "scheduled_at_utc",
    "started_at_utc",
    "finished_at_utc",
    "elapsed_seconds",
    "return_code",
    "within_target_seconds",
    "stdout_tail",
    "stderr_tail",
]


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(dt: datetime | None = None) -> str:
    d = dt or utc_now_dt()
    return d.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_root_default() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root(repo_root: Path) -> Path:
    return repo_root.parents[1] if len(repo_root.parents) >= 2 else repo_root.parent


def v3_root(repo_root: Path) -> Path:
    return files_root(repo_root) / "FX_OUTPUTS" / "gold_v3"


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def append_csv(path: Path, row: dict[str, Any], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})


def tail_text(s: str, limit: int = 1200) -> str:
    s = s.replace("\r", " ").replace("\n", " | ")
    return s[-limit:]


def next_tick_epoch(delay_seconds: int) -> float:
    now = time.time()
    current_minute = int(now // 60) * 60
    target = current_minute + delay_seconds
    if now >= target:
        target = current_minute + 60 + delay_seconds
    return float(target)


def sleep_until(target_epoch: float) -> None:
    while True:
        left = target_epoch - time.time()
        if left <= 0:
            return
        time.sleep(min(left, 0.25))


def build_stage37_command(args: argparse.Namespace, repo_root: Path) -> list[str]:
    script = repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_37_ranked_live_discord_notify.py"
    cmd = [sys.executable, str(script), "--repo-root", str(repo_root), "--symbol", args.symbol]
    if args.live_snapshot:
        cmd += ["--live-snapshot", args.live_snapshot]
    if args.entry_time_column:
        cmd += ["--entry-time-column", args.entry_time_column]
    if args.enable_discord:
        cmd.append("--enable-discord")
    if args.discord_webhook_env:
        cmd += ["--discord-webhook-env", args.discord_webhook_env]
    if args.discord_webhook_url:
        cmd += ["--discord-webhook-url", args.discord_webhook_url]
    if args.notify_all_hits:
        cmd.append("--notify-all-hits")
    return cmd


def run_once(args: argparse.Namespace, repo_root: Path, out_dir: Path, run_id: int, scheduled_epoch: float) -> dict[str, Any]:
    scheduled_at = datetime.fromtimestamp(scheduled_epoch, tz=timezone.utc)
    started = utc_now_dt()
    cmd = build_stage37_command(args, repo_root)
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=args.stage37_timeout_seconds)
    finished = utc_now_dt()
    elapsed = (finished - started).total_seconds()
    row = {
        "run_id": run_id,
        "scheduled_at_utc": utc_text(scheduled_at),
        "started_at_utc": utc_text(started),
        "finished_at_utc": utc_text(finished),
        "elapsed_seconds": round(elapsed, 6),
        "return_code": proc.returncode,
        "within_target_seconds": elapsed <= args.target_seconds,
        "stdout_tail": tail_text(proc.stdout),
        "stderr_tail": tail_text(proc.stderr),
    }
    append_csv(out_dir / "gold_v3_38_loop_runs.csv", row, LOOP_FIELDS)
    write_json(
        out_dir / "gold_v3_38_summary.json",
        {
            "created_at_utc": utc_text(),
            "step": STEP,
            "status": READY_STATUS if proc.returncode == 0 else EXCEPTION_STATUS,
            "loop_delay_seconds_after_minute": args.delay_seconds,
            "target_seconds": args.target_seconds,
            "last_run": row,
            "loop_mode": "continuous" if args.loop else "once",
            "stage37_script": "scripts/gold_v3_runtime/gold_v3_37_ranked_live_discord_notify.py",
            "discord_enabled": bool(args.enable_discord),
            "mt5_direct_send_enabled": False,
        },
    )
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default="")
    ap.add_argument("--delay-seconds", type=int, default=5)
    ap.add_argument("--target-seconds", type=float, default=5.0)
    ap.add_argument("--stage37-timeout-seconds", type=float, default=15.0)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--run-once", action="store_true")
    ap.add_argument("--live-snapshot", default="")
    ap.add_argument("--entry-time-column", default="entry_time_utc")
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--enable-discord", action="store_true")
    ap.add_argument("--discord-webhook-env", default="GOLD_V3_DISCORD_WEBHOOK_URL")
    ap.add_argument("--discord-webhook-url", default="")
    ap.add_argument("--notify-all-hits", action="store_true")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else repo_root_default()
    out_dir = v3_root(repo_root) / OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.loop and not args.run_once:
        args.run_once = True

    run_id = 0
    try:
        while True:
            scheduled = next_tick_epoch(args.delay_seconds)
            sleep_until(scheduled)
            run_id += 1
            run_once(args, repo_root, out_dir, run_id, scheduled)
            if args.run_once and not args.loop:
                return 0
    except KeyboardInterrupt:
        write_json(out_dir / "gold_v3_38_summary.json", {"created_at_utc": utc_text(), "step": STEP, "status": "STOPPED_BY_USER"})
        return 0
    except Exception as exc:
        write_json(out_dir / "gold_v3_38_summary.json", {"created_at_utc": utc_text(), "step": STEP, "status": EXCEPTION_STATUS, "blocked_reason": f"{exc.__class__.__name__}: {exc}"})
        (out_dir / "gold_v3_38_exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
