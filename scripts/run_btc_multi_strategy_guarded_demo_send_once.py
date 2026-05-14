#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Guarded demo-send once wrapper for BTC multi-strategy sidecar flow.

Stage 1: run BTC multi-strategy dry-run cycle. This builds candidates and
         order_payloads.csv, but never calls MT5.
Stage 1.5: convert the selected BTC payload candidate rows into the existing
           Mochipoyo Discord signal-notification schema and call
           send_mochipoyo_discord_messages.py.
Stage 2: call send_mt5_order_from_payload.py only when all order-send guards
         pass AND the Discord signal notification was actually SENT in this
         same cycle.

Safety intent:
- No-payload cycles remain a normal safe waiting state.
- A BTC signal that can produce an order must first be surfaced as a Discord
  signal notification.
- If the signal notification is missing, dry-run-only, duplicate-skipped,
  errored, or otherwise not SENT, MT5 order sending is blocked.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/research_results/btc_multi_strategy_guarded_demo_send_once")
DEFAULT_DISCORD_SIGNAL_LEDGER = Path("data/runtime_state/btc/multi_strategy/discord_signal_send_ledger.csv")
SUMMARY_FILENAME = "latest_btc_multi_strategy_guarded_demo_send_once_result.json"

LOG_COLUMNS = [
    "cycle_start_utc", "cycle_end_utc", "cycle_ok", "cycle_ok_classification", "reason",
    "allow_demo_send", "send_requested", "send_flag_passed_to_sender", "send_suppressed_reason",
    "payload_rows_out", "discord_signal_status", "discord_signal_returncode", "discord_signal_rows",
    "discord_signal_sent_rows", "discord_signal_error_rows", "discord_signal_dry_run_would_send_rows",
    "discord_signal_duplicate_rows", "discord_signal_send_gate_passed", "discord_signal_suppressed_reason",
    "discord_signal_notify_payload_csv", "discord_signal_send_ledger_csv", "discord_signal_preview_txt",
    "discord_signal_preview_json", "guarded_sender_returncode", "guarded_sender_rows_out",
    "guarded_sender_dry_run_check_ok_rows", "guarded_sender_sent_rows", "guarded_sender_error_rows",
    "guarded_sender_order_send_called_count", "dry_run_cycle_returncode", "dry_run_cycle_ok",
    "dry_run_cycle_summary_json", "summary_json", "total_seconds",
]


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def mkdir_path(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def ensure_parent_dir(path: Path) -> None:
    mkdir_path(path.parent)


def path_exists(path: Path) -> bool:
    return Path(windows_long_path(path)).exists()


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_parent_dir(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    df = pd.DataFrame([{col: row.get(col, "") for col in columns}])
    df.to_csv(windows_long_path(path), mode="a", header=not path_exists(path), index=False, encoding="utf-8-sig")


def csv_rows_count(path: Path) -> int:
    if not path_exists(path):
        return 0
    try:
        return int(len(read_csv(path)))
    except Exception:
        return 0


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def safe_int_value(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def safe_float_value(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        x = float(value)
        if pd.isna(x):
            return default
        return x
    except Exception:
        return default


def safe_int(obj: dict[str, Any], key: str, default: int = 0) -> int:
    return safe_int_value(obj.get(key, default), default=default)


def safe_bool(obj: dict[str, Any], key: str, default: bool = False) -> bool:
    val = obj.get(key, default)
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() in {"true", "1", "yes", "y"}


def row_get(row: pd.Series, key: str, default: Any = "") -> Any:
    if key not in row.index:
        return default
    value = row.get(key)
    if pd.isna(value):
        return default
    return value


def run_cmd(label: str, cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, float]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run guarded demo-send once wrapper for BTC multi-strategy sidecar flow.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--btc-m15-csv")
    p.add_argument("--btc-h1-csv")
    p.add_argument("--btc-h4-csv")
    p.add_argument("--btc-d1-csv")
    p.add_argument("--broker-symbol", default="BTCUSD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--base-lot", type=float, default=0.01)
    p.add_argument("--spread-cost-usd", type=float, default=22.5)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--horizon-hours", type=int, default=72)
    p.add_argument("--magic", type=int, default=26050604)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=20)
    p.add_argument("--max-symbol-lot", type=float, default=1.0)
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--live-lookback-bars", type=int, default=1)
    p.add_argument("--cooldown-bars-m15", type=int, default=16)
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--enable-sell-early-low-break-trade", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--discord-signal-send-ledger-csv", type=Path, default=DEFAULT_DISCORD_SIGNAL_LEDGER)
    p.add_argument("--discord-signal-webhook-url", default=None)
    p.add_argument("--discord-signal-webhook-env", default="DISCORD_WEBHOOK_URL")
    p.add_argument("--discord-signal-username", default="Mochipoyo Signal")
    p.add_argument("--discord-signal-style", choices=["compact", "detailed"], default="compact")
    p.add_argument("--discord-signal-max-rows", type=int, default=1)
    return p.parse_args()


def build_dry_run_cmd(args: argparse.Namespace, dry_out_dir: Path) -> list[str]:
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "run_btc_multi_strategy_dry_run_cycle.py"),
        "--csv-dir", str(args.csv_dir), "--out-dir", str(dry_out_dir), "--csv-sep", str(args.csv_sep),
        "--broker-symbol", str(args.broker_symbol), "--base-lot", str(args.base_lot),
        "--spread-cost-usd", str(args.spread_cost_usd), "--rr", str(args.rr),
        "--horizon-hours", str(args.horizon_hours), "--magic", str(args.magic),
        "--latest-confirmed-policy", str(args.latest_confirmed_policy), "--live-lookback-bars", str(args.live_lookback_bars),
        "--max-payload-rows", str(args.max_orders), "--cooldown-bars-m15", str(args.cooldown_bars_m15),
    ]
    for arg_name, flag in [("btc_m15_csv", "--btc-m15-csv"), ("btc_h1_csv", "--btc-h1-csv"), ("btc_h4_csv", "--btc-h4-csv"), ("btc_d1_csv", "--btc-d1-csv")]:
        value = getattr(args, arg_name, None)
        if value:
            cmd.extend([flag, str(value)])
    cmd.append("--enable-sell-early-low-break-trade" if args.enable_sell_early_low_break_trade else "--no-enable-sell-early-low-break-trade")
    return cmd


def selected_candidates_csv(dry_summary: dict[str, Any], dry_out_dir: Path) -> Path:
    paths = dry_summary.get("paths", {}) if isinstance(dry_summary.get("paths"), dict) else {}
    raw = paths.get("selected_payload_candidates_csv") or paths.get("live_candidates_csv")
    if raw:
        return Path(str(raw))
    return dry_out_dir / "payload" / "btc_multi_strategy_selected_payload_candidates.csv"


def convert_selected_candidates_to_discord_payload(src_csv: Path, dst_csv: Path, *, fallback_spread_cost_usd: float) -> int:
    df = read_csv(src_csv)
    out_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        direction = str(row_get(row, "direction", "")).upper()
        entry = safe_float_value(row_get(row, "entry_price", row_get(row, "entry_price_reference", 0.0)))
        sl = safe_float_value(row_get(row, "sl_price", 0.0))
        tp = safe_float_value(row_get(row, "tp_price", 0.0))
        spread = safe_float_value(row_get(row, "spread_cost_usd", fallback_spread_cost_usd), fallback_spread_cost_usd)
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp - entry)
        spread_to_sl = spread / sl_dist if sl_dist > 0 else 0.0
        effective_rr = (tp_dist - spread) / (sl_dist + spread) if (sl_dist + spread) > 0 else 0.0
        signal_time = row_get(row, "signal_close_time", row_get(row, "signal_time", row_get(row, "entry_time", "")))
        entry_time = row_get(row, "entry_time", signal_time)
        strategy_slot = row_get(row, "strategy_slot", row_get(row, "pair_name", "BTC_MULTI"))
        strategy_id = row_get(row, "strategy_id", row_get(row, "candidate_name", strategy_slot))
        reason = row_get(row, "reason_text", row_get(row, "reason", "BTC multi-strategy signal"))
        payload_key = row_get(row, "payload_key", "")
        if not payload_key:
            stamp = str(signal_time).replace("-", "").replace(":", "").replace(" ", "_")[:13]
            payload_key = f"BTC_MULTI_{strategy_slot}_{direction}_{stamp}"
        out_rows.append({
            "payload_id": row_get(row, "payload_id", payload_key),
            "payload_key": payload_key,
            "symbol": "BTC",
            "broker_symbol": row_get(row, "broker_symbol", "BTCUSD#"),
            "direction": direction,
            "signal_close_time": signal_time,
            "entry_time": entry_time,
            "entry_price": entry,
            "sl_price": sl,
            "tp_price": tp,
            "rr": row_get(row, "rr", 2.0),
            "pair_name": strategy_slot,
            "candidate_name": strategy_id,
            "candidate_rank": row_get(row, "candidate_rank", "AUTO"),
            "selected_slice": row_get(row, "selected_slice", "LIVE"),
            "reason_text": reason,
            "caution_labels": row_get(row, "caution_labels", "NONE"),
            "mode_spread_price": spread,
            "mode_spread_points": spread,
            "spread_to_sl_ratio": spread_to_sl,
            "effective_rr_after_spread": effective_rr,
            "strategy_id": strategy_id,
            "strategy_slot": strategy_slot,
        })
    out = pd.DataFrame(out_rows)
    write_csv(out, dst_csv)
    return int(len(out))


def build_discord_signal_cmd(args: argparse.Namespace, paths: dict[str, Path], *, pass_send: bool) -> list[str]:
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "send_mochipoyo_discord_messages.py"),
        "--input-csv", str(paths["discord_signal_notify_payload_csv"]),
        "--send-ledger-csv", str(args.discord_signal_send_ledger_csv),
        "--preview-txt", str(paths["discord_signal_preview_txt"]),
        "--preview-json", str(paths["discord_signal_preview_json"]),
        "--symbol", "BTC",
        "--max-rows", str(args.discord_signal_max_rows),
        "--style", str(args.discord_signal_style),
        "--webhook-env", str(args.discord_signal_webhook_env),
        "--username", str(args.discord_signal_username),
    ]
    if args.discord_signal_webhook_url:
        cmd.extend(["--webhook-url", str(args.discord_signal_webhook_url)])
    if pass_send:
        cmd.append("--send")
    return cmd


def summarize_discord_signal(paths: dict[str, Path], *, returncode: int | str, converted_rows: int, pass_send: bool, suppressed_reason: str) -> dict[str, Any]:
    preview = read_json_or_empty(paths["discord_signal_preview_json"])
    records = preview.get("records", []) if isinstance(preview.get("records"), list) else []
    total = len(records)
    sent = sum(1 for r in records if isinstance(r, dict) and bool(r.get("sent")))
    errors = sum(1 for r in records if isinstance(r, dict) and str(r.get("send_status", "")).startswith("ERROR"))
    dry_would_send = sum(1 for r in records if isinstance(r, dict) and str(r.get("send_status", "")) == "DRY_RUN_WOULD_SEND")
    duplicate_rows = sum(1 for r in records if isinstance(r, dict) and bool(r.get("duplicate_existing")))
    statuses = sorted({str(r.get("send_status", "")) for r in records if isinstance(r, dict)})
    if converted_rows <= 0:
        status = "NO_SIGNAL_ROWS"
    elif pass_send and sent > 0 and errors == 0 and sent == total:
        status = "SENT"
    elif not pass_send and dry_would_send > 0 and errors == 0:
        status = "DRY_RUN_WOULD_SEND"
    elif total > 0 and duplicate_rows == total and not pass_send:
        status = "DRY_RUN_DUPLICATE_WOULD_SKIP"
    elif total > 0 and duplicate_rows == total and pass_send:
        status = "DUPLICATE_SKIPPED"
    elif errors > 0:
        status = statuses[0] if statuses else "ERROR"
    else:
        status = statuses[0] if statuses else "UNKNOWN"
    return {
        "enabled": True,
        "status": status,
        "returncode": returncode,
        "rows": total,
        "converted_rows": converted_rows,
        "sent_rows": sent,
        "error_rows": errors,
        "dry_run_would_send_rows": dry_would_send,
        "duplicate_rows": duplicate_rows,
        "send_requested": bool(pass_send),
        "send_gate_passed": bool(pass_send and status == "SENT" and sent > 0 and errors == 0),
        "suppressed_reason": suppressed_reason,
        "input_candidates_csv": str(paths["selected_payload_candidates_csv"]),
        "notify_payload_csv": str(paths["discord_signal_notify_payload_csv"]),
        "preview_txt": str(paths["discord_signal_preview_txt"]),
        "preview_json": str(paths["discord_signal_preview_json"]),
        "send_statuses": statuses,
    }


def decide_order_send(args: argparse.Namespace, payload_rows: int, discord_signal: dict[str, Any]) -> tuple[bool, str]:
    if not args.send:
        return False, "SEND_NOT_REQUESTED"
    if not args.allow_demo_send:
        return False, "ALLOW_DEMO_SEND_NOT_SET"
    if payload_rows <= 0:
        return False, "NO_PAYLOAD_ROWS"
    if payload_rows > int(args.max_orders):
        return False, f"PAYLOAD_ROWS_EXCEED_MAX_ORDERS payload_rows={payload_rows}; max_orders={args.max_orders}"
    if payload_rows > 1:
        return False, "INITIAL_GUARD_BLOCKS_MORE_THAN_ONE_PAYLOAD_ROW"
    if not bool(discord_signal.get("send_gate_passed", False)):
        return False, f"DISCORD_SIGNAL_NOTIFY_NOT_SENT status={discord_signal.get('status', 'UNKNOWN')}"
    return True, ""


def build_guarded_sender_cmd(args: argparse.Namespace, paths: dict[str, Path], *, pass_send: bool) -> list[str]:
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(paths["payload_csv"]), "--order-ledger-csv", str(paths["guarded_order_ledger_csv"]),
        "--out-dir", str(paths["guarded_sender_out_dir"]), "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders), "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy), "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot), "--select-symbol", "--expected-login", str(args.expected_login),
        "--registry-preview-out-csv", str(paths["registry_preview_csv"]),
        "--registry-preview-out-json", str(paths["registry_preview_json"]),
    ]
    if args.require_demo_account:
        cmd.append("--require-demo-account")
    if pass_send:
        cmd.append("--send")
    return cmd


def main() -> int:
    args = parse_args()
    started_perf = time.perf_counter()
    cycle_start = utc_now_text()
    mkdir_path(args.out_dir)

    paths = {
        "dry_out_dir": args.out_dir / "dry_run_stage",
        "payload_csv": args.out_dir / "dry_run_stage" / "payload" / "order_payloads.csv",
        "selected_payload_candidates_csv": args.out_dir / "dry_run_stage" / "payload" / "btc_multi_strategy_selected_payload_candidates.csv",
        "discord_signal_dir": args.out_dir / "discord_signal",
        "discord_signal_notify_payload_csv": args.out_dir / "discord_signal" / "btc_signal_notify_payload.csv",
        "discord_signal_preview_txt": args.out_dir / "discord_signal" / "btc_signal_notify_preview.txt",
        "discord_signal_preview_json": args.out_dir / "discord_signal" / "btc_signal_notify_preview.json",
        "guarded_sender_out_dir": args.out_dir / "guarded_sender",
        "guarded_order_ledger_csv": args.out_dir / "guarded_demo_order_ledger.csv",
        "registry_preview_csv": args.out_dir / "registry_preview" / "registry_preview.csv",
        "registry_preview_json": args.out_dir / "registry_preview" / "registry_preview.json",
        "summary_json": args.out_dir / SUMMARY_FILENAME,
        "cycle_log_csv": args.out_dir / "btc_multi_strategy_guarded_demo_send_once_log.csv",
    }

    print("=" * 80, flush=True)
    print("BTC multi-strategy guarded demo-send ONCE wrapper", flush=True)
    print("Order sending is gated by successful Discord signal notification.", flush=True)
    print(f"csv_dir={args.csv_dir}", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"allow_demo_send={args.allow_demo_send} send_requested={args.send}", flush=True)
    print("=" * 80, flush=True)

    dry_rc, dry_seconds = run_cmd("btc_dry_run_cycle", build_dry_run_cmd(args, paths["dry_out_dir"]))
    dry_summary = read_json_or_empty(paths["dry_out_dir"] / "latest_btc_multi_strategy_dry_run_cycle_result.json")
    dry_cycle_ok = bool(dry_rc == 0 and safe_bool(dry_summary, "cycle_ok", False))
    payload_rows = csv_rows_count(paths["payload_csv"])

    selected_from_summary = selected_candidates_csv(dry_summary, paths["dry_out_dir"])
    paths["selected_payload_candidates_csv"] = selected_from_summary

    discord_signal_rc: int | str = "SKIPPED"
    discord_signal_seconds = 0.0
    discord_signal_notify: dict[str, Any] = {
        "enabled": True,
        "status": "SKIPPED",
        "returncode": discord_signal_rc,
        "rows": 0,
        "converted_rows": 0,
        "sent_rows": 0,
        "error_rows": 0,
        "dry_run_would_send_rows": 0,
        "duplicate_rows": 0,
        "send_requested": False,
        "send_gate_passed": False,
        "suppressed_reason": "NOT_ATTEMPTED",
        "input_candidates_csv": str(selected_from_summary),
        "notify_payload_csv": str(paths["discord_signal_notify_payload_csv"]),
        "preview_txt": str(paths["discord_signal_preview_txt"]),
        "preview_json": str(paths["discord_signal_preview_json"]),
    }

    if not dry_cycle_ok:
        discord_signal_notify["suppressed_reason"] = "DRY_RUN_CYCLE_FAILED"
    elif payload_rows <= 0:
        discord_signal_notify["status"] = "NO_PAYLOAD_ROWS"
        discord_signal_notify["suppressed_reason"] = "NO_PAYLOAD_ROWS"
    else:
        try:
            converted_rows = convert_selected_candidates_to_discord_payload(
                selected_from_summary,
                paths["discord_signal_notify_payload_csv"],
                fallback_spread_cost_usd=float(args.spread_cost_usd),
            )
            discord_signal_rc, discord_signal_seconds = run_cmd(
                "discord_signal_notify",
                build_discord_signal_cmd(args, paths, pass_send=bool(args.send)),
            )
            discord_signal_notify = summarize_discord_signal(
                paths,
                returncode=discord_signal_rc,
                converted_rows=converted_rows,
                pass_send=bool(args.send),
                suppressed_reason="",
            )
        except Exception as exc:
            discord_signal_notify = {
                **discord_signal_notify,
                "status": "ERROR_CONVERT_OR_NOTIFY_EXCEPTION",
                "returncode": discord_signal_rc,
                "error": repr(exc),
                "suppressed_reason": "DISCORD_SIGNAL_NOTIFY_EXCEPTION",
            }
            print(f"[SAFETY] Discord signal notification failed before order send: {exc!r}", flush=True)

    pass_send, suppressed_reason = decide_order_send(args, payload_rows, discord_signal_notify)
    guarded_sender_rc: int | str = "SKIPPED"
    guarded_seconds = 0.0
    guarded_report: dict[str, Any] = {}

    if not dry_cycle_ok:
        guarded_sender_rc = "SKIPPED_DRY_RUN_FAILED"
        guarded_report = {"rows_out": 0, "dry_run_check_ok_rows": 0, "sent_rows": 0, "error_rows": 0, "order_send_called_count": 0, "reason": "DRY_RUN_CYCLE_FAILED"}
        print("[SAFETY] dry run cycle failed; guarded sender skipped", flush=True)
    elif payload_rows <= 0:
        guarded_sender_rc = "SKIPPED_NO_PAYLOAD_ROWS"
        guarded_report = {"rows_out": 0, "dry_run_check_ok_rows": 0, "sent_rows": 0, "error_rows": 0, "order_send_called_count": 0, "reason": "NO_PAYLOAD_ROWS"}
        print("[INFO] guarded sender skipped because payload rows are 0", flush=True)
    elif not pass_send:
        guarded_sender_rc = "SKIPPED_SIGNAL_NOTIFY_GATE"
        guarded_report = {"rows_out": 0, "dry_run_check_ok_rows": 0, "sent_rows": 0, "error_rows": 0, "order_send_called_count": 0, "reason": suppressed_reason}
        print(f"[SAFETY] guarded sender skipped by signal-notify gate: {suppressed_reason}", flush=True)
    else:
        guarded_sender_rc, guarded_seconds = run_cmd("guarded_sender", build_guarded_sender_cmd(args, paths, pass_send=pass_send))
        guarded_report = read_json_or_empty(paths["guarded_sender_out_dir"] / "mt5_order_send_report.json")

    cycle_end = utc_now_text()
    sender_order_send_called_count = safe_int(guarded_report, "order_send_called_count", 0)
    sender_sent_rows = safe_int(guarded_report, "sent_rows", 0)
    sender_error_rows = safe_int(guarded_report, "error_rows", 0)
    sender_rows_out = safe_int(guarded_report, "rows_out", 0)
    sender_dry_run_ok = safe_int(guarded_report, "dry_run_check_ok_rows", 0)

    safe_no_payload_ok = bool(dry_cycle_ok and payload_rows == 0 and sender_order_send_called_count == 0 and sender_sent_rows == 0)
    notify_preview_block_ok = bool(dry_cycle_ok and payload_rows > 0 and not args.send and discord_signal_notify.get("status") in {"DRY_RUN_WOULD_SEND", "DRY_RUN_DUPLICATE_WOULD_SKIP"} and sender_order_send_called_count == 0 and sender_sent_rows == 0)
    notify_sent_send_suppressed_ok = bool(dry_cycle_ok and payload_rows > 0 and args.send and not args.allow_demo_send and discord_signal_notify.get("status") == "SENT" and sender_order_send_called_count == 0 and sender_sent_rows == 0)
    sent_ok = bool(dry_cycle_ok and payload_rows > 0 and pass_send and guarded_sender_rc == 0 and sender_order_send_called_count == 1 and sender_sent_rows == 1 and sender_error_rows == 0)

    cycle_ok = bool(safe_no_payload_ok or notify_preview_block_ok or notify_sent_send_suppressed_ok or sent_ok)
    if safe_no_payload_ok:
        cycle_ok_classification = "SAFE_NO_PAYLOAD_PASS"
        reason = "BTC_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_SAFE_NO_PAYLOAD_PASS"
    elif notify_preview_block_ok:
        cycle_ok_classification = "SIGNAL_NOTIFY_DRY_RUN_BLOCKED_SEND"
        reason = "BTC_MULTI_STRATEGY_SIGNAL_NOTIFY_DRY_RUN_BLOCKED_ORDER_SEND_PASS"
    elif notify_sent_send_suppressed_ok:
        cycle_ok_classification = "SIGNAL_NOTIFY_SENT_ORDER_SEND_SUPPRESSED_PASS"
        reason = "BTC_MULTI_STRATEGY_SIGNAL_NOTIFY_SENT_ORDER_SEND_SUPPRESSED_PASS"
    elif sent_ok:
        cycle_ok_classification = "SENT_PASS"
        reason = "BTC_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_PASS"
    else:
        cycle_ok_classification = "FAILED_SIGNAL_NOTIFY_BLOCKED_SEND" if payload_rows > 0 and sender_order_send_called_count == 0 else "FAILED"
        reason = "BTC_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_FAILED"

    summary = {
        "schema_version": "btc_multi_strategy_guarded_demo_send_once_v2_signal_notify_gate",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "cycle_ok": bool(cycle_ok),
        "cycle_ok_classification": cycle_ok_classification,
        "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send),
        "send_suppressed_reason": suppressed_reason,
        "guards": {
            "expected_login": int(args.expected_login), "require_demo_account": bool(args.require_demo_account),
            "broker_symbol": str(args.broker_symbol), "base_lot": float(args.base_lot),
            "spread_cost_usd": float(args.spread_cost_usd), "max_orders": int(args.max_orders),
            "position_policy": str(args.position_policy), "max_symbol_positions": int(args.max_symbol_positions),
            "max_symbol_lot": float(args.max_symbol_lot), "deviation": int(args.deviation),
            "early_low_break_trade_enabled": bool(args.enable_sell_early_low_break_trade),
            "cooldown_bars_m15": int(args.cooldown_bars_m15),
            "discord_signal_notify_required_before_order_send": True,
        },
        "returncodes": {"dry_run_cycle": dry_rc, "discord_signal_notify": discord_signal_rc, "guarded_sender": guarded_sender_rc},
        "key_metrics": {
            "dry_run_cycle_ok": dry_cycle_ok,
            "payload_rows_out": int(payload_rows),
            "discord_signal_rows": int(discord_signal_notify.get("rows", 0) or 0),
            "discord_signal_converted_rows": int(discord_signal_notify.get("converted_rows", 0) or 0),
            "discord_signal_sent_rows": int(discord_signal_notify.get("sent_rows", 0) or 0),
            "discord_signal_error_rows": int(discord_signal_notify.get("error_rows", 0) or 0),
            "discord_signal_dry_run_would_send_rows": int(discord_signal_notify.get("dry_run_would_send_rows", 0) or 0),
            "discord_signal_duplicate_rows": int(discord_signal_notify.get("duplicate_rows", 0) or 0),
            "guarded_sender_rows_out": sender_rows_out,
            "guarded_sender_dry_run_check_ok_rows": sender_dry_run_ok,
            "guarded_sender_sent_rows": sender_sent_rows,
            "guarded_sender_error_rows": sender_error_rows,
            "guarded_sender_order_send_called_count": sender_order_send_called_count,
        },
        "safety": {
            "dry_run_cycle_mt5_called": False,
            "discord_signal_notify_gate_required": True,
            "discord_signal_notify_send_gate_passed": bool(discord_signal_notify.get("send_gate_passed", False)),
            "guarded_sender_send_flag_passed": bool(pass_send),
            "production_registry_mutated": False, "existing_gold_bat_modified": False,
            "gold_ledgers_mutated": False, "trigger_state_mutated": False,
        },
        "timing": {"dry_run_cycle_seconds": dry_seconds, "discord_signal_notify_seconds": discord_signal_seconds, "guarded_sender_seconds": guarded_seconds, "total_seconds": round(time.perf_counter() - started_perf, 3)},
        "paths": {k: str(v) for k, v in paths.items()},
        "dry_run_summary": dry_summary,
        "discord_signal_notify": discord_signal_notify,
        "guarded_sender_report": guarded_report,
    }
    write_json(paths["summary_json"], summary)

    row = {
        "cycle_start_utc": cycle_start, "cycle_end_utc": cycle_end, "cycle_ok": cycle_ok,
        "cycle_ok_classification": cycle_ok_classification, "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send), "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send), "send_suppressed_reason": suppressed_reason,
        "payload_rows_out": int(payload_rows),
        "discord_signal_status": discord_signal_notify.get("status", ""),
        "discord_signal_returncode": discord_signal_notify.get("returncode", ""),
        "discord_signal_rows": discord_signal_notify.get("rows", 0),
        "discord_signal_sent_rows": discord_signal_notify.get("sent_rows", 0),
        "discord_signal_error_rows": discord_signal_notify.get("error_rows", 0),
        "discord_signal_dry_run_would_send_rows": discord_signal_notify.get("dry_run_would_send_rows", 0),
        "discord_signal_duplicate_rows": discord_signal_notify.get("duplicate_rows", 0),
        "discord_signal_send_gate_passed": discord_signal_notify.get("send_gate_passed", False),
        "discord_signal_suppressed_reason": discord_signal_notify.get("suppressed_reason", ""),
        "discord_signal_notify_payload_csv": str(paths["discord_signal_notify_payload_csv"]),
        "discord_signal_send_ledger_csv": str(args.discord_signal_send_ledger_csv),
        "discord_signal_preview_txt": str(paths["discord_signal_preview_txt"]),
        "discord_signal_preview_json": str(paths["discord_signal_preview_json"]),
        "guarded_sender_returncode": guarded_sender_rc,
        "guarded_sender_rows_out": sender_rows_out, "guarded_sender_dry_run_check_ok_rows": sender_dry_run_ok,
        "guarded_sender_sent_rows": sender_sent_rows, "guarded_sender_error_rows": sender_error_rows,
        "guarded_sender_order_send_called_count": sender_order_send_called_count,
        "dry_run_cycle_returncode": dry_rc, "dry_run_cycle_ok": dry_cycle_ok,
        "dry_run_cycle_summary_json": str(paths["dry_out_dir"] / "latest_btc_multi_strategy_dry_run_cycle_result.json"),
        "summary_json": str(paths["summary_json"]), "total_seconds": summary["timing"]["total_seconds"],
    }
    append_csv_row(paths["cycle_log_csv"], row, LOG_COLUMNS)

    print("=" * 80, flush=True)
    print("BTC multi-strategy guarded demo-send once summary", flush=True)
    print(json.dumps({
        "cycle_ok": cycle_ok,
        "cycle_ok_classification": cycle_ok_classification,
        "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send),
        "send_suppressed_reason": suppressed_reason,
        "discord_signal_notify": {
            "status": discord_signal_notify.get("status"),
            "rows": discord_signal_notify.get("rows"),
            "sent_rows": discord_signal_notify.get("sent_rows"),
            "error_rows": discord_signal_notify.get("error_rows"),
            "dry_run_would_send_rows": discord_signal_notify.get("dry_run_would_send_rows"),
            "send_gate_passed": discord_signal_notify.get("send_gate_passed"),
            "suppressed_reason": discord_signal_notify.get("suppressed_reason"),
            "preview_txt": str(paths["discord_signal_preview_txt"]),
        },
        "key_metrics": summary["key_metrics"],
        "guards": summary["guards"],
        "summary_json": str(paths["summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
