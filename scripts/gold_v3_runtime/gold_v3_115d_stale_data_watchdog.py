#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, csv, json, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_115D_STALE_DATA_WATCHDOG"
READY = "GOLD_V3_115D_STALE_DATA_WATCHDOG_READY"
BLOCKED = "GOLD_V3_115D_STALE_DATA_WATCHDOG_BLOCKED"

CANDIDATES = ["candles_history_M15.csv", "candles_history_M5.csv", "candles_history_H1.csv"]
TIME_COL_HINTS = ["time", "datetime", "date", "dt", "timestamp"]

def jst():
    return datetime.now(timezone(timedelta(hours=9)))

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

def load_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")

def month_dir(base: Path, dt: datetime) -> Path:
    return base / dt.strftime("%Y-%m")

def detect_delimiter(sample: str) -> str:
    if sample.count(";") >= sample.count(","):
        return ";"
    return ","

def parse_dt(s: str):
    if s is None:
        return None
    t = str(s).strip().replace("T", " ")
    if not t:
        return None
    if t.endswith("Z"):
        t = t[:-1]
    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(t[:len(datetime.now().strftime(fmt))], fmt).replace(tzinfo=timezone(timedelta(hours=9)))
        except Exception:
            pass
    try:
        return datetime.fromisoformat(t).replace(tzinfo=timezone(timedelta(hours=9)))
    except Exception:
        return None

def latest_csv_time(path: Path):
    if not path.exists():
        return None, "missing"
    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        lines = [x for x in text.splitlines() if x.strip()]
        if len(lines) < 2:
            return None, "too_few_rows"
        delim = detect_delimiter("\n".join(lines[:5]))
        header = next(csv.reader([lines[0]], delimiter=delim))
        last = next(csv.reader([lines[-1]], delimiter=delim))
        idx = 0
        lower = [h.strip().lower() for h in header]
        for i, h in enumerate(lower):
            if any(k == h or k in h for k in TIME_COL_HINTS):
                idx = i
                break
        if idx >= len(last):
            idx = 0
        dt = parse_dt(last[idx])
        if dt is None:
            return None, f"parse_failed:{last[idx] if idx < len(last) else ''}"
        return dt, "ok"
    except Exception as e:
        return None, "error:" + str(e)

def expected_market_closed(now: datetime):
    wd = now.weekday()  # Mon=0 Sun=6
    hm = now.hour * 60 + now.minute
    if wd == 5:
        return True, "SATURDAY_JST"
    if wd == 6 and hm < 8 * 60:
        return True, "SUNDAY_PRE_OPEN_JST"
    if wd == 0 and hm < 7 * 60:
        return True, "MONDAY_STARTUP_QUIET_JST"
    if 6 * 60 + 55 <= hm <= 7 * 60 + 10:
        return True, "DAILY_ROLLOVER_QUIET_JST"
    return False, "EXPECTED_ACTIVE"

def find_csvs(mt5: Path):
    found = []
    for name in CANDIDATES:
        p = mt5 / name
        if p.exists():
            found.append(p)
    if found:
        return found
    # fallback shallow search only to avoid heavy scans
    for name in CANDIDATES:
        found += list(mt5.glob(f"*/{name}"))[:3]
    return found

def queue_watchdog(root: Path, status: dict, state: dict):
    side = "STOP_REVIEW"
    key = f"WATCHDOG|{status.get('state')}|{status.get('primary_latest_dt')}"
    if state.get("last_watchdog_queue_key") == key:
        return False, key
    now = jst()
    item = {
        "created_at_jst": now.isoformat(),
        "queue_id": key,
        "signal_id": key,
        "side": side,
        "symbol": "XAUUSD",
        "entry_dt": status.get("primary_latest_dt"),
        "monitor_state": status.get("state"),
        "reason": status.get("reason"),
        "stale_minutes": status.get("primary_stale_minutes"),
    }
    q = root / "115a" / "queue" / now.strftime("%Y-%m") / f"gold_v3_115d_watchdog_{now.strftime('%Y-%m-%d')}.jsonl"
    append_jsonl(q, item)
    state["last_watchdog_queue_key"] = key
    state["last_watchdog_queue_at_jst"] = now.isoformat()
    return True, key

def run_once(root: Path, mt5: Path, args, state: dict):
    now = jst()
    closed, reason = expected_market_closed(now)
    csvs = find_csvs(mt5)
    rows = []
    for p in csvs:
        dt, parse_status = latest_csv_time(p)
        stale = None
        if dt is not None:
            stale = max(0.0, (now - dt).total_seconds() / 60.0)
        rows.append({"path": str(p), "latest_dt": dt.isoformat() if dt else "", "parse_status": parse_status, "stale_minutes": stale})
    primary = None
    for r in rows:
        if r["path"].endswith("candles_history_M15.csv"):
            primary = r
            break
    if primary is None and rows:
        primary = rows[0]
    status_state = "INPUT_MISSING"
    detail = "no_candidate_csv_found"
    if closed:
        status_state = "MARKET_CLOSED_EXPECTED" if "ROLLOVER" not in reason else "ROLLOVER_QUIET_EXPECTED"
        detail = reason
    elif not primary:
        status_state = "INPUT_MISSING"
        detail = "no_primary_csv"
    elif primary.get("parse_status") != "ok":
        status_state = "INPUT_PARSE_ERROR"
        detail = primary.get("parse_status")
    else:
        stale = float(primary.get("stale_minutes") or 0.0)
        if stale >= args.stop_stale_minutes:
            status_state = "STOP_REVIEW_STALE"
            detail = f"primary_stale_minutes_ge_{args.stop_stale_minutes}"
        elif stale >= args.watch_stale_minutes:
            status_state = "WATCH_STALE"
            detail = f"primary_stale_minutes_ge_{args.watch_stale_minutes}"
        else:
            status_state = "OK"
            detail = "fresh_enough"
    result = {
        "checked_at_jst": now.isoformat(),
        "state": status_state,
        "reason": detail,
        "market_closed_expected": closed,
        "market_reason": reason,
        "primary_path": primary.get("path") if primary else "",
        "primary_latest_dt": primary.get("latest_dt") if primary else "",
        "primary_stale_minutes": primary.get("stale_minutes") if primary else None,
        "watch_stale_minutes": args.watch_stale_minutes,
        "stop_stale_minutes": args.stop_stale_minutes,
        "csv_rows": rows,
        "queued": False,
    }
    if status_state in ["WATCH_STALE", "STOP_REVIEW_STALE", "INPUT_PARSE_ERROR", "INPUT_MISSING"] and not closed:
        queued, key = queue_watchdog(root, result, state)
        result["queued"] = queued
        result["queue_key"] = key
    out = root / "115d"
    append_jsonl(out / "journal" / now.strftime("%Y-%m") / f"gold_v3_115d_watchdog_{now.strftime('%Y-%m-%d')}.jsonl", result)
    write_json(out / "current" / "latest_watchdog_status.json", result)
    write_json(out / "state" / "watchdog_state.json", state)
    return result, state

def write_paste(root: Path, summary: dict):
    out = root / "115d"
    lines = [
        "GOLD V3 115D PASTE_ME_STALE_DATA_WATCHDOG",
        f"status: {summary['status']}",
        f"ready: {str(summary['ready']).lower()}",
        f"watchdog_state: {summary.get('watchdog_state')}",
        f"market_closed_expected: {summary.get('market_closed_expected')}",
        f"queued: {summary.get('queued')}",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "",
        "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--watch-stale-minutes", type=float, default=45.0)
    ap.add_argument("--stop-stale-minutes", type=float, default=90.0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--target-second", type=int, default=5)
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "115d"
    out.mkdir(parents=True, exist_ok=True)
    state = load_json(out / "state" / "watchdog_state.json", {})
    print(f"{STEP} START mt5={mt5}", flush=True)
    last = {}
    while True:
        last, state = run_once(root, mt5, args, state)
        print(f"watchdog_state={last.get('state')} stale={last.get('primary_stale_minutes')} queued={last.get('queued')}", flush=True)
        summary = {
            "step": STEP,
            "status": READY,
            "ready": True,
            "decision": "STALE_DATA_WATCHDOG_READY",
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "output_dir": str(out),
            "watchdog_state": last.get("state"),
            "market_closed_expected": last.get("market_closed_expected"),
            "market_reason": last.get("market_reason"),
            "primary_path": last.get("primary_path"),
            "primary_latest_dt": last.get("primary_latest_dt"),
            "primary_stale_minutes": last.get("primary_stale_minutes"),
            "queued": last.get("queued"),
            "watch_stale_minutes": args.watch_stale_minutes,
            "stop_stale_minutes": args.stop_stale_minutes,
            "source_csv_mutated": False,
            "contract_mutated": False,
            "open_asof_allowed": False,
            "elapsed_seconds": round(time.time() - t0, 2),
        }
        write_json(out / "gold_v3_115d_summary.json", summary)
        write_paste(root, summary)
        if args.once or not args.loop:
            break
        now = datetime.now()
        target = now.replace(second=args.target_second, microsecond=0)
        if target <= now:
            target += timedelta(minutes=1)
        time.sleep(max(0.0, (target - now).total_seconds()))
    print(json.dumps({"status": READY, "ready": True, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
