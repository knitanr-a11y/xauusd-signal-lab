#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_115A_QUEUE_LOOP_STORAGE_ONLY"
READY = "GOLD_V3_115A_QUEUE_LOOP_STORAGE_ONLY_READY"
BLOCKED = "GOLD_V3_115A_QUEUE_LOOP_STORAGE_ONLY_BLOCKED"

def jst():
    return datetime.now(timezone(timedelta(hours=9)))

def load_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

def append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")

def sleep_until_second(sec: int) -> float:
    now = datetime.now()
    target = now.replace(second=sec, microsecond=0)
    if target <= now:
        target += timedelta(minutes=1)
    return max(0.0, (target - now).total_seconds())

def month_dir(base: Path, dt: datetime) -> Path:
    return base / dt.strftime("%Y-%m")

def prune_old(root: Path, days: int) -> int:
    if not root.exists():
        return 0
    cutoff = jst() - timedelta(days=days)
    removed = 0
    for p in root.rglob("*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, timezone(timedelta(hours=9)))
            if mtime < cutoff:
                p.unlink()
                removed += 1
        except Exception:
            pass
    return removed

def read_input(inbox: Path):
    p = inbox / "latest_signal.json"
    if not p.exists():
        return {"side": "NO_SIGNAL", "signal_id": "NO_SIGNAL_INPUT_MISSING", "reason": "input_missing"}, False
    obj = load_json(p, {})
    if not obj:
        return {"side": "NO_SIGNAL", "signal_id": "NO_SIGNAL_INPUT_INVALID", "reason": "input_invalid"}, False
    if not obj.get("signal_id"):
        obj["signal_id"] = f"{obj.get('side','UNKNOWN')}|{obj.get('entry_dt','')}|{obj.get('symbol','XAUUSD')}"
    return obj, True

def candle_key(sig: dict, side: str, monitor_state: str) -> str:
    """One signal per candle per symbol/side/monitor-state, independent of volatile signal_id."""
    symbol = str(sig.get("symbol", "XAUUSD"))
    entry_dt = str(sig.get("entry_dt", ""))
    if not entry_dt:
        entry_dt = str(sig.get("bar_dt", "")) or str(sig.get("signal_dt", "")) or str(sig.get("signal_id", ""))
    return f"{symbol}|{side}|{entry_dt}|{monitor_state}"

def append_csv(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = ["queue_id", "candle_key", "signal_id", "entry_dt", "symbol", "side", "entry_price", "tp", "sl", "status", "outcome", "created_at_jst"]
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig") as f:
        if not exists:
            f.write(",".join(keys) + "\n")
        vals = [str(row.get(k, "")).replace(",", " ") for k in keys]
        f.write(",".join(vals) + "\n")

def run_once(root: Path, args, state: dict):
    base = root / "115a"
    inbox = base / "inbox"
    queue = base / "queue"
    current = base / "current"
    state_dir = base / "state"
    eval_root = base / "journal" / "evaluations"
    notice_root = base / "journal" / "notices"
    history = base / "trade_history"
    for d in [inbox, queue, current, state_dir, eval_root, notice_root, history]:
        d.mkdir(parents=True, exist_ok=True)
    freeze = load_json(root / "112c" / "gold_v3_112_selected_policy_freeze_manifest.json", {})
    monitor_state = freeze.get("virtual_monitor_latest_state", "UNKNOWN")
    sig, present = read_input(inbox)
    dt = jst()
    ymd = dt.strftime("%Y-%m-%d")
    side = str(sig.get("side", "NO_SIGNAL"))
    ck = candle_key(sig, side, monitor_state)
    queue_id = f"{ck}|{sig.get('signal_id')}"
    event = {
        "evaluated_at_jst": dt.isoformat(),
        "input_present": present,
        "side": side,
        "signal_id": sig.get("signal_id"),
        "candle_key": ck,
        "monitor_state": monitor_state,
        "action": "NO_QUEUE",
        "reason": sig.get("reason", ""),
    }
    if side not in ["", "NO_SIGNAL", "NONE"]:
        if state.get("last_candle_key") == ck:
            event["action"] = "SUPPRESSED_DUPLICATE_CANDLE"
        else:
            item = dict(event)
            item.update({"queue_id": queue_id, "symbol": sig.get("symbol", "XAUUSD"), "entry_dt": sig.get("entry_dt"), "entry_price": sig.get("entry_price"), "tp": sig.get("tp"), "sl": sig.get("sl")})
            append_jsonl(month_dir(queue, dt) / f"gold_v3_115a_queue_{ymd}.jsonl", item)
            append_jsonl(month_dir(notice_root, dt) / f"gold_v3_115a_notices_{ymd}.jsonl", item)
            state["last_candle_key"] = ck
            state["last_queue_id"] = queue_id
            state["last_queue_at_jst"] = dt.isoformat()
            event["action"] = "QUEUED"
            if side in ["LONG", "SHORT"]:
                append_csv(history / "gold_v3_115a_virtual_signal_ledger.csv", {"queue_id": queue_id, "candle_key": ck, "signal_id": sig.get("signal_id"), "entry_dt": sig.get("entry_dt"), "symbol": sig.get("symbol", "XAUUSD"), "side": side, "entry_price": sig.get("entry_price"), "tp": sig.get("tp"), "sl": sig.get("sl"), "status": "OPEN_TRACKING_ONLY", "outcome": "PENDING", "created_at_jst": dt.isoformat()})
    append_jsonl(month_dir(eval_root, dt) / f"gold_v3_115a_evaluations_{ymd}.jsonl", event)
    removed = prune_old(notice_root, args.retention_days)
    event["pruned_notice_files"] = removed
    write_json(current / "latest_evaluation.json", event)
    write_json(state_dir / "loop_state.json", state)
    return event, state

def write_outputs(root: Path, args, blockers, summary):
    base = root / "115a"
    rows = [
        "path,purpose",
        "inbox/latest_signal.json,input",
        "queue/YYYY-MM/*.jsonl,queued items",
        "current/latest_evaluation.json,latest evaluation",
        "state/loop_state.json,duplicate state",
        "journal/evaluations/YYYY-MM/*.jsonl,evaluation journal",
        "journal/notices/YYYY-MM/*.jsonl,pruned notice history",
        "trade_history/gold_v3_115a_virtual_signal_ledger.csv,win loss tracking",
    ]
    (base / "gold_v3_115a_folder_layout_matrix.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (base / "gold_v3_115a_retention_policy.csv").write_text("target,retention_days,prune\njournal/notices,%s,true\ntrade_history,not_pruned,false\njournal/evaluations,not_pruned_by_default,false\n" % args.retention_days, encoding="utf-8")
    write_json(base / "gold_v3_115a_summary.json", summary | {"blockers": blockers})
    (base / "GOLD_V3_115A_QUEUE_LOOP_STORAGE_ONLY_REPORT.md").write_text("# GOLD V3 115A report\n\n" + json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "GOLD V3 115A PASTE_ME_QUEUE_LOOP_STORAGE_ONLY",
        f"status: {summary['status']}",
        f"ready: {str(summary['ready']).lower()}",
        f"target_second: {summary['target_second']}",
        f"retention_days: {summary['retention_days']}",
        "duplicate_scope: candle_key",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "blocker_count: " + str(len(blockers)),
        "",
        "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()] + ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False)]
    (base / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--target-second", type=int, default=5)
    ap.add_argument("--retention-days", type=int, default=31)
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    base = root / "115a"
    base.mkdir(parents=True, exist_ok=True)
    print(STEP + " START", flush=True)
    blockers = []
    if not (root / "114c" / "gold_v3_114_summary.json").exists():
        blockers.append({"blocker_id": "missing_114_summary"})
    state = load_json(base / "state" / "loop_state.json", {})
    if not blockers:
        while True:
            event, state = run_once(root, args, state)
            print(f"action={event.get('action')} side={event.get('side')} signal_id={event.get('signal_id')} candle_key={event.get('candle_key')}", flush=True)
            if not args.loop:
                break
            time.sleep(sleep_until_second(args.target_second))
    summary = {
        "step": STEP,
        "status": READY if not blockers else BLOCKED,
        "ready": not blockers,
        "decision": "QUEUE_LOOP_STORAGE_ONLY_READY" if not blockers else "QUEUE_LOOP_STORAGE_ONLY_BLOCKED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(base),
        "target_second": args.target_second,
        "retention_days": args.retention_days,
        "loop_mode": args.loop,
        "duplicate_scope": "candle_key",
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    write_outputs(root, args, blockers, summary)
    print(json.dumps({"status": summary["status"], "ready": summary["ready"], "paste_me": str(base / "paste_me.txt")}, ensure_ascii=False, indent=2), flush=True)
    return 0 if not blockers else 2

if __name__ == "__main__":
    raise SystemExit(main())
