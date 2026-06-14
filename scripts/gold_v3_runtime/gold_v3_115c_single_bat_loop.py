#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, time, traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_115a_queue_loop as qloop
import gold_v3_115b_queue_sender as sender

STEP = "GOLD_V3_115C_SINGLE_BAT_LOOP"

class ArgsA:
    def __init__(self, target_second=5, retention_days=31):
        self.target_second = target_second
        self.retention_days = retention_days
        self.loop = False
        self.mt5_files_dir = ""

class ArgsB:
    def __init__(self, target_second=5, env_file="", no_send=False, timeout=10):
        self.target_second = target_second
        self.env_file = env_file
        self.no_send = no_send
        self.timeout = timeout
        self.loop = False
        self.mt5_files_dir = ""

def jst():
    return datetime.now(timezone(timedelta(hours=9)))

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

def load_json(p: Path, default=None):
    if default is None:
        default = {}
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def append_jsonl(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")

def sleep_to_second(sec: int) -> float:
    now = datetime.now()
    target = now.replace(second=sec, microsecond=0)
    if target <= now:
        target += timedelta(minutes=1)
    return max(0.0, (target - now).total_seconds())

def find_mt5_files_dir() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if p.name == "Files":
            return p
    return Path.cwd()

def error_notice(repo_root: Path, mt5: Path, msg: str) -> dict:
    key, url, _ = sender.find_endpoint(repo_root, mt5, "")
    result = {"env_key_found": bool(key), "env_key_name": key if key else "", "sent": False}
    if not url:
        result["reason"] = "endpoint_missing"
        return result
    try:
        status = sender.post(url, msg, 10)
        result["sent"] = True
        result["http_status"] = status
    except Exception as e:
        result["reason"] = str(e)
    return result

def run_cycle(root: Path, repo_root: Path, mt5: Path, args, state: dict) -> dict:
    base = root / "115c"
    state_dir = base / "state"
    journal = base / "journal"
    current = base / "current"
    for d in [state_dir, journal, current]:
        d.mkdir(parents=True, exist_ok=True)
    args_a = ArgsA(args.target_second, args.retention_days)
    args_b = ArgsB(args.target_second, args.env_file, args.no_send, args.timeout)
    state_a = load_json(root / "115a" / "state" / "loop_state.json", {})
    state_b = load_json(root / "115b" / "state" / "sender_state.json", {"sent_ids": []})
    ev_a, state_a = qloop.run_once(root, args_a, state_a)
    write_json(root / "115a" / "state" / "loop_state.json", state_a)
    ev_b, state_b = sender.run_once(root, repo_root, mt5, args_b, state_b)
    write_json(root / "115b" / "state" / "sender_state.json", state_b)
    now = jst()
    event = {
        "checked_at_jst": now.isoformat(),
        "action_115a": ev_a.get("action"),
        "side": ev_a.get("side"),
        "signal_id": ev_a.get("signal_id"),
        "monitor_state": ev_a.get("monitor_state"),
        "queue_rows": ev_b.get("queue_rows"),
        "sent": ev_b.get("sent"),
        "skipped": ev_b.get("skipped"),
        "errors": ev_b.get("errors"),
        "market_idle_normal": ev_a.get("action") in ["NO_QUEUE", "SUPPRESSED_DUPLICATE"],
        "runtime_error": False,
    }
    append_jsonl(journal / now.strftime("%Y-%m") / f"gold_v3_115c_loop_{now.strftime('%Y-%m-%d')}.jsonl", event)
    write_json(current / "latest_115c_status.json", event)
    return event

def write_paste(root: Path, summary: dict):
    out = root / "115c"
    lines = [
        "GOLD V3 115C PASTE_ME_SINGLE_BAT_LOOP",
        f"status: {summary['status']}",
        f"ready: {str(summary['ready']).lower()}",
        f"target_second: {summary['target_second']}",
        f"retention_days: {summary['retention_days']}",
        f"last_runtime_error: {summary.get('last_runtime_error')}",
        f"market_stop_treated_as_error: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "",
        "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--target-second", type=int, default=5)
    ap.add_argument("--retention-days", type=int, default=31)
    ap.add_argument("--env-file", default="")
    ap.add_argument("--no-send", action="store_true")
    ap.add_argument("--timeout", type=int, default=10)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    mt5 = Path(args.mt5_files_dir) if args.mt5_files_dir else find_mt5_files_dir()
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    repo_root = Path(__file__).resolve().parents[2]
    out = root / "115c"
    out.mkdir(parents=True, exist_ok=True)
    state = load_json(out / "state" / "single_loop_state.json", {})
    print(f"{STEP} START target_second={args.target_second} mt5={mt5}", flush=True)
    last = {}
    last_error = None
    while True:
        try:
            last = run_cycle(root, repo_root, mt5, args, state)
            state["last_ok_at_jst"] = jst().isoformat()
            state["last_event"] = last
            write_json(out / "state" / "single_loop_state.json", state)
            print(f"OK action={last.get('action_115a')} side={last.get('side')} queue={last.get('queue_rows')} sent={last.get('sent')} errors={last.get('errors')}", flush=True)
        except KeyboardInterrupt:
            print("STOP requested by user", flush=True)
            break
        except Exception as e:
            err = {
                "error_at_jst": jst().isoformat(),
                "error": str(e),
                "traceback_tail": traceback.format_exc()[-2000:],
            }
            append_jsonl(out / "journal" / jst().strftime("%Y-%m") / f"gold_v3_115c_errors_{jst().strftime('%Y-%m-%d')}.jsonl", err)
            write_json(out / "current" / "latest_115c_error.json", err)
            notice_result = error_notice(repo_root, mt5, "GOLD V3 115C loop error\n" + str(e))
            err["notice_result"] = notice_result
            last_error = err
            print(f"ERROR caught and recorded: {e}", flush=True)
        summary = {
            "step": STEP,
            "status": "GOLD_V3_115C_SINGLE_BAT_LOOP_RUNNING_OR_READY",
            "ready": True,
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "output_dir": str(out),
            "target_second": args.target_second,
            "retention_days": args.retention_days,
            "market_stop_treated_as_error": False,
            "last_runtime_error": bool(last_error),
            "source_csv_mutated": False,
            "contract_mutated": False,
            "open_asof_allowed": False,
            "last_event": last,
        }
        write_json(out / "gold_v3_115c_summary.json", summary)
        write_paste(root, summary)
        if args.once:
            break
        time.sleep(sleep_to_second(args.target_second))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
