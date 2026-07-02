#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from btc_youtube_candidate_signals import BTC4_ID, BTC4_TP1_MAGIC, BTC4_TP2_MAGIC, validate_order_group  # noqa: E402

DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/research_results/btc_youtube_candidates_guarded_demo_send_once")
DEFAULT_STATE_DIR = Path("data/runtime_state/btc/youtube_candidates")
SUMMARY_NAME = "latest_btc_youtube_candidates_guarded_demo_send_once_result.json"


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def mkdirp(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    mkdirp(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    mkdirp(path.parent)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def run_cmd(label: str, cmd: list[str]) -> tuple[int, float]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} rc={completed.returncode} seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


def convert_notification_csv(src: Path, dst: Path) -> int:
    frame = read_csv(src)
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        entry = float(row.get("entry_price_reference", 0.0) or 0.0)
        sl = float(row.get("sl_price", 0.0) or 0.0)
        tp = float(row.get("tp_price", 0.0) or 0.0)
        spread = float(row.get("spread_cost_usd", 30.0) or 30.0)
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp - entry)
        rows.append({
            "payload_id": row.get("payload_key", ""),
            "payload_key": row.get("payload_key", ""),
            "symbol": "BTC",
            "broker_symbol": row.get("broker_symbol", "BTCUSD#"),
            "direction": row.get("direction", ""),
            "signal_close_time": row.get("signal_close_time", row.get("entry_time", "")),
            "entry_time": row.get("entry_time", ""),
            "entry_price": entry,
            "sl_price": sl,
            "tp_price": tp,
            "rr": row.get("rr", 0.0),
            "pair_name": row.get("strategy_slot", "BTC_YOUTUBE"),
            "candidate_name": row.get("candidate_name", row.get("strategy_id", "")),
            "candidate_rank": row.get("candidate_rank", "YOUTUBE"),
            "selected_slice": row.get("selected_slice", "DEMO_FORWARD"),
            "reason_text": row.get("reason_text", "YouTube BTC candidate"),
            "caution_labels": row.get("caution_labels", "DEMO_ONLY"),
            "mode_spread_price": spread,
            "mode_spread_points": spread,
            "spread_to_sl_ratio": spread / sl_dist if sl_dist > 0 else 0.0,
            "effective_rr_after_spread": (tp_dist - spread) / (sl_dist + spread) if sl_dist + spread > 0 else 0.0,
            "strategy_id": row.get("strategy_id", ""),
            "strategy_slot": row.get("strategy_slot", ""),
        })
    write_csv(pd.DataFrame(rows), dst)
    return len(rows)


def notification_command(args: argparse.Namespace, *, input_csv: Path, ledger: Path, preview_txt: Path, preview_json: Path) -> list[str]:
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "send_mochipoyo_discord_messages.py"),
        "--input-csv", str(input_csv),
        "--send-ledger-csv", str(ledger),
        "--preview-txt", str(preview_txt),
        "--preview-json", str(preview_json),
        "--symbol", "BTC",
        "--max-rows", "10",
        "--style", "detailed",
        "--webhook-env", str(args.discord_webhook_env),
        "--username", str(args.discord_username),
    ]
    if args.discord_webhook_url:
        cmd.extend(["--webhook-url", args.discord_webhook_url])
    if args.send:
        cmd.append("--send")
    return cmd


def summarize_notification(preview_json: Path, *, row_count: int, send_requested: bool, rc: int | str) -> dict[str, Any]:
    preview = read_json(preview_json)
    records = preview.get("records", []) if isinstance(preview.get("records"), list) else []
    sent = sum(1 for item in records if isinstance(item, dict) and bool(item.get("sent")))
    errors = sum(1 for item in records if isinstance(item, dict) and str(item.get("send_status", "")).startswith("ERROR"))
    duplicates = sum(1 for item in records if isinstance(item, dict) and bool(item.get("duplicate_existing")))
    dry = sum(1 for item in records if isinstance(item, dict) and str(item.get("send_status", "")) == "DRY_RUN_WOULD_SEND")
    if row_count == 0:
        status = "NO_ROWS"
    elif send_requested and sent == row_count and errors == 0:
        status = "SENT"
    elif not send_requested and dry > 0 and errors == 0:
        status = "DRY_RUN_WOULD_SEND"
    elif duplicates == row_count:
        status = "DUPLICATE_SKIPPED" if send_requested else "DRY_RUN_DUPLICATE_WOULD_SKIP"
    elif errors:
        status = "ERROR"
    else:
        status = "UNKNOWN"
    return {
        "status": status,
        "returncode": rc,
        "rows": row_count,
        "sent_rows": sent,
        "error_rows": errors,
        "duplicate_rows": duplicates,
        "dry_run_would_send_rows": dry,
        "send_gate_passed": bool(send_requested and status == "SENT" and sent == row_count),
        "preview_json": str(preview_json),
    }


def sender_command(args: argparse.Namespace, payload_csv: Path, order_ledger: Path, sender_out: Path) -> list[str]:
    cmd = [
        sys.executable, str(SCRIPT_DIR / "send_btc_youtube_mt5_orders.py"),
        "--input-csv", str(payload_csv),
        "--order-ledger-csv", str(order_ledger),
        "--out-dir", str(sender_out),
        "--symbol", str(args.broker_symbol),
        "--max-orders", "3",
        "--deviation", str(args.deviation),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--expected-login", str(args.expected_login),
    ]
    if args.send and args.allow_demo_send:
        cmd.append("--send")
    return cmd


def arm_btc4_state(state_json: Path, orders: pd.DataFrame, *, sender_sent_rows: int, sender_called_count: int) -> None:
    btc4 = orders[orders["strategy_id"].astype(str) == BTC4_ID].copy() if not orders.empty else pd.DataFrame()
    if btc4.empty or sender_called_count <= 0:
        return
    signal_key = str(btc4.iloc[0]["parent_signal_key"])
    state = read_json(state_json)
    pairs = state.get("pairs", []) if isinstance(state.get("pairs"), list) else []
    if any(str(pair.get("signal_key", "")) == signal_key for pair in pairs if isinstance(pair, dict)):
        return
    expected_total = len(orders)
    pairs.append({
        "signal_key": signal_key,
        "status": "ARMED" if sender_sent_rows == expected_total else "PARTIAL_SEND_ANOMALY",
        "armed_at_utc": datetime.now(UTC).isoformat(),
        "tp1_magic": BTC4_TP1_MAGIC,
        "tp2_magic": BTC4_TP2_MAGIC,
        "direction": str(btc4.iloc[0]["direction"]),
        "entry_time": str(btc4.iloc[0]["entry_time"]),
    })
    state = {"schema_version": "btc4_split_position_state_v1", "updated_at_utc": utc_text(), "pairs": pairs}
    write_json(state_json, state)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guarded Discord + MT5 demo flow for YouTube BTC4/5/6 candidates.")
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    parser.add_argument("--m5-csv", default="")
    parser.add_argument("--m15-csv", default="")
    parser.add_argument("--h4-csv", default="")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--broker-symbol", default="BTCUSD#")
    parser.add_argument("--expected-login", type=int, default=75539039)
    parser.add_argument("--deviation", type=int, default=100)
    parser.add_argument("--max-symbol-positions", type=int, default=6)
    parser.add_argument("--max-symbol-lot", type=float, default=0.10)
    parser.add_argument("--discord-webhook-url", default="")
    parser.add_argument("--discord-webhook-env", default="DISCORD_WEBHOOK_URL")
    parser.add_argument("--discord-username", default="Mochipoyo BTC YouTube")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--allow-demo-send", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.perf_counter()
    mkdirp(args.out_dir)
    mkdirp(args.state_dir)
    paths = {
        "dry_out": args.out_dir / "dry_run",
        "trade_notify_input": args.out_dir / "discord" / "trade_notify_payload.csv",
        "monitor_notify_input": args.out_dir / "discord" / "monitor_notify_payload.csv",
        "trade_preview_txt": args.out_dir / "discord" / "trade_preview.txt",
        "trade_preview_json": args.out_dir / "discord" / "trade_preview.json",
        "monitor_preview_txt": args.out_dir / "discord" / "monitor_preview.txt",
        "monitor_preview_json": args.out_dir / "discord" / "monitor_preview.json",
        "trade_notify_ledger": args.state_dir / "discord_trade_send_ledger.csv",
        "monitor_notify_ledger": args.state_dir / "discord_monitor_send_ledger.csv",
        "order_ledger": args.state_dir / "demo_order_ledger.csv",
        "btc4_state": args.state_dir / "btc4_split_position_state.json",
        "manager_report": args.out_dir / "position_manager_report.json",
        "sender_out": args.out_dir / "sender",
        "summary": args.out_dir / SUMMARY_NAME,
    }

    dry_cmd = [
        sys.executable, str(SCRIPT_DIR / "run_btc_youtube_candidates_dry_run_cycle.py"),
        "--csv-dir", str(args.csv_dir), "--out-dir", str(paths["dry_out"]),
    ]
    for value, flag in [(args.m5_csv, "--m5-csv"), (args.m15_csv, "--m15-csv"), (args.h4_csv, "--h4-csv")]:
        if value:
            dry_cmd.extend([flag, str(value)])
    dry_rc, dry_seconds = run_cmd("youtube_dry_run", dry_cmd)
    dry_summary = read_json(paths["dry_out"] / "latest_btc_youtube_candidates_dry_run_cycle_result.json")
    dry_ok = bool(dry_rc == 0 and dry_summary.get("cycle_ok"))

    trade_src = paths["dry_out"] / "candidates" / "btc_youtube_trade_notification_candidates.csv"
    monitor_src = paths["dry_out"] / "candidates" / "btc_youtube_monitor_notification_candidates.csv"
    order_csv = paths["dry_out"] / "payload" / "order_payloads.csv"
    orders = read_csv(order_csv)
    order_errors = validate_order_group(orders)

    manager = {"cycle_ok": True, "status": "SKIPPED_PREVIEW_MODE"}
    manager_rc: int | str = "SKIPPED"
    manager_seconds = 0.0
    if args.send and args.allow_demo_send:
        manager_cmd = [
            sys.executable, str(SCRIPT_DIR / "manage_btc_youtube_positions.py"),
            "--state-json", str(paths["btc4_state"]),
            "--report-json", str(paths["manager_report"]),
            "--symbol", str(args.broker_symbol),
            "--expected-login", str(args.expected_login),
            "--require-demo-account", "--require-hedging", "--send",
        ]
        manager_rc, manager_seconds = run_cmd("position_manager_and_preflight", manager_cmd)
        manager = read_json(paths["manager_report"])

    trade_rows = convert_notification_csv(trade_src, paths["trade_notify_input"]) if dry_ok else 0
    monitor_rows = convert_notification_csv(monitor_src, paths["monitor_notify_input"]) if dry_ok else 0

    trade_notify = {"status": "NO_ROWS", "rows": 0, "send_gate_passed": False}
    monitor_notify = {"status": "NO_ROWS", "rows": 0, "send_gate_passed": False}
    notify_seconds = 0.0
    if trade_rows:
        rc, sec = run_cmd("discord_trade_notifications", notification_command(
            args, input_csv=paths["trade_notify_input"], ledger=paths["trade_notify_ledger"],
            preview_txt=paths["trade_preview_txt"], preview_json=paths["trade_preview_json"],
        ))
        notify_seconds += sec
        trade_notify = summarize_notification(paths["trade_preview_json"], row_count=trade_rows, send_requested=args.send, rc=rc)
    if monitor_rows:
        rc, sec = run_cmd("discord_monitor_notifications", notification_command(
            args, input_csv=paths["monitor_notify_input"], ledger=paths["monitor_notify_ledger"],
            preview_txt=paths["monitor_preview_txt"], preview_json=paths["monitor_preview_json"],
        ))
        notify_seconds += sec
        monitor_notify = summarize_notification(paths["monitor_preview_json"], row_count=monitor_rows, send_requested=args.send, rc=rc)

    payload_rows = len(orders)
    sender_report: dict[str, Any] = {}
    sender_rc: int | str = "SKIPPED"
    sender_seconds = 0.0
    order_gate = bool(
        dry_ok
        and not order_errors
        and payload_rows > 0
        and args.send
        and args.allow_demo_send
        and bool(manager.get("cycle_ok"))
        and trade_notify.get("send_gate_passed")
    )
    if order_gate:
        sender_rc, sender_seconds = run_cmd("mt5_guarded_demo_sender", sender_command(
            args, order_csv, paths["order_ledger"], paths["sender_out"]
        ))
        sender_report = read_json(paths["sender_out"] / "mt5_order_send_report.json")
    elif payload_rows:
        sender_report = {
            "rows_out": 0,
            "sent_rows": 0,
            "error_rows": 0,
            "order_send_called_count": 0,
            "reason": "ORDER_GATE_BLOCKED",
        }

    sent_rows = int(sender_report.get("sent_rows", 0) or 0)
    called_count = int(sender_report.get("order_send_called_count", 0) or 0)
    error_rows = int(sender_report.get("error_rows", 0) or 0)
    if payload_rows and called_count:
        arm_btc4_state(paths["btc4_state"], orders, sender_sent_rows=sent_rows, sender_called_count=called_count)

    if not dry_ok:
        classification = "FAILED_DRY_RUN"
        cycle_ok = False
    elif payload_rows == 0 and trade_rows == 0 and monitor_rows == 0:
        classification = "SAFE_NO_SIGNAL"
        cycle_ok = True
    elif not args.send:
        classification = "DISCORD_PREVIEW_ONLY_ORDER_BLOCKED"
        cycle_ok = trade_notify.get("status") in {"NO_ROWS", "DRY_RUN_WOULD_SEND", "DRY_RUN_DUPLICATE_WOULD_SKIP"} and monitor_notify.get("status") in {"NO_ROWS", "DRY_RUN_WOULD_SEND", "DRY_RUN_DUPLICATE_WOULD_SKIP"}
    elif payload_rows == 0:
        classification = "DISCORD_MONITOR_SENT_NO_ORDER"
        cycle_ok = monitor_notify.get("status") in {"NO_ROWS", "SENT", "DUPLICATE_SKIPPED"}
    elif args.send and not args.allow_demo_send and trade_notify.get("status") == "SENT":
        classification = "DISCORD_SENT_DEMO_ORDER_NOT_ALLOWED"
        cycle_ok = True
    elif trade_notify.get("status") == "DUPLICATE_SKIPPED":
        classification = "SAFE_DUPLICATE_SIGNAL_SUPPRESSED"
        cycle_ok = True
    elif order_gate and sender_rc == 0 and sent_rows == payload_rows and error_rows == 0:
        classification = "DISCORD_SENT_AND_DEMO_ORDERS_SENT"
        cycle_ok = True
    else:
        classification = "FAILED_OR_ORDER_BLOCKED"
        cycle_ok = False

    summary = {
        "schema_version": "btc_youtube_guarded_demo_send_once_v1",
        "cycle_at_utc": utc_text(),
        "cycle_ok": bool(cycle_ok),
        "classification": classification,
        "scope": {
            "btc4": "Discord + MT5 demo, 0.02 split 0.01 TP1 / 0.01 TP2",
            "btc5": "Discord + MT5 demo, 0.01",
            "btc6": "Discord monitor only, no order payload",
        },
        "guards": {
            "demo_account_required": True,
            "expected_login": args.expected_login,
            "hedging_account_required": True,
            "discord_sent_same_cycle_required_before_order": True,
            "order_contract_errors": order_errors,
            "send_requested": args.send,
            "allow_demo_send": args.allow_demo_send,
            "order_gate_passed": order_gate,
        },
        "rows": {"trade_notifications": trade_rows, "monitor_notifications": monitor_rows, "order_payloads": payload_rows},
        "dry_run": dry_summary,
        "position_manager": manager,
        "trade_discord": trade_notify,
        "monitor_discord": monitor_notify,
        "sender_report": sender_report,
        "returncodes": {"dry": dry_rc, "manager": manager_rc, "sender": sender_rc},
        "timing": {"dry": dry_seconds, "manager": manager_seconds, "discord": notify_seconds, "sender": sender_seconds, "total": round(time.perf_counter() - started, 3)},
        "paths": {key: str(value) for key, value in paths.items()},
    }
    write_json(paths["summary"], summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
