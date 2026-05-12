#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Guarded demo-send once wrapper for GOLD multi-strategy sidecar flow.

This wrapper is intentionally separate from the normal dry-run BAT/wrapper.

Purpose:
1. Run the existing independent GOLD multi-strategy sidecar dry-run flow.
2. Inspect the generated Mochipoyo-compatible order_payloads.csv.
3. Run the MT5 sender only through a second, explicit guarded stage.
4. Pass --send to the sender only when BOTH flags are present:

       --allow-demo-send
       --send

Safety defaults:
- Default is NO SEND.
- If --send is passed without --allow-demo-send, it is suppressed.
- If --allow-demo-send is passed without --send, it is suppressed.
- production position_registry.csv is never written by this wrapper.
- registry outputs remain preview-only.
- Uses GOLD integration defaults, not symbol-wide blocking:
  position-policy=allow_any_until_max, max-symbol-positions=20,
  max-symbol-lot=1.0, max-orders=1.
- The dry-run bridge is called with --use-adapter-lot so strategy lot is kept:
  BUY_C_ENV_RR2_72H => 0.01, SELL_H1H4_BEAR_AB B_ONLY => 0.01,
  SELL_H1H4_BEAR_AB CORE_AB => 0.02.

Important:
- The first stage uses run_gold_multi_strategy_mochipoyo_loop_dry_run_fast_m15_patch.py.
- That dry-run stage may run sender dry-run if payload rows exist, but it never
  passes --send.
- This guarded wrapper may then run the sender again for the final guarded stage.
- Duplicate prevention is by order_key/order ledger. Do not force block_any here,
  because separate GOLD signals may intentionally hold multiple or opposite
  positions.

Strict send-success rule:
- If final guarded sender receives --send and payload_rows_out > 0, the cycle is
  successful only when:
    * guarded sender returncode is 0
    * order_send_called_count >= 1
    * sent_rows == payload_rows_out
    * error_rows == 0
- Therefore a case such as order_send_called_count=1 / sent_rows=0 /
  error_rows=1 is FAILED, even if the child sender process itself returned 0.

Safe no-payload behavior:
- No signal / no payload is a normal operational state.
- If payload_rows_out=0, sender --send was not passed, order_send_called_count=0,
  and sent_rows=0, this wrapper returns success even if the dry-run stage itself
  returned 1 for a no-payload/no-signal path.
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
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_guarded_demo_send_once")

SUMMARY_FILENAME = "latest_gold_multi_strategy_guarded_demo_send_once_result.json"
LOG_COLUMNS = [
    "cycle_start_utc",
    "cycle_end_utc",
    "cycle_ok",
    "cycle_ok_classification",
    "reason",
    "allow_demo_send",
    "send_requested",
    "send_flag_passed_to_sender",
    "send_suppressed_reason",
    "strict_send_success_required",
    "guarded_sender_success_ok",
    "guarded_sender_success_reason",
    "payload_rows_out",
    "guarded_sender_returncode",
    "guarded_sender_rows_out",
    "guarded_sender_dry_run_check_ok_rows",
    "guarded_sender_sent_rows",
    "guarded_sender_error_rows",
    "guarded_sender_order_send_called_count",
    "dry_run_wrapper_returncode",
    "dry_run_wrapper_cycle_ok",
    "dry_run_wrapper_summary_json",
    "summary_json",
    "total_seconds",
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


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    df = pd.DataFrame([{col: row.get(col, "") for col in columns}])
    df.to_csv(
        windows_long_path(path),
        mode="a",
        header=not Path(windows_long_path(path)).exists(),
        index=False,
        encoding="utf-8-sig",
    )


def payload_rows_count(path: Path) -> int:
    if not Path(windows_long_path(path)).exists():
        return 0
    try:
        return int(len(pd.read_csv(windows_long_path(path), encoding="utf-8-sig")))
    except Exception:
        return 0


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def safe_int(obj: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key, default) or 0)
    except Exception:
        return default


def safe_bool(obj: dict[str, Any], key: str, default: bool = False) -> bool:
    val = obj.get(key, default)
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() in {"true", "1", "yes", "y"}


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
    p = argparse.ArgumentParser(description="Run guarded demo-send once wrapper for GOLD multi-strategy sidecar flow.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--magic", type=int, default=26050601)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=20)
    p.add_argument("--max-symbol-lot", type=float, default=1.0)
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--disable-same-m15-skip", action="store_true")
    p.add_argument("--disable-monitor-skip", action="store_true")
    return p.parse_args()


def build_dry_run_cmd(args: argparse.Namespace, dry_out_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_mochipoyo_loop_dry_run_fast_m15_patch.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(dry_out_dir),
        "--broker-symbol", str(args.broker_symbol),
        "--expected-login", str(args.expected_login),
        "--require-demo-account" if args.require_demo_account else "--no-require-demo-account",
        "--select-symbol",
        "--fixed-lot", str(args.fixed_lot),
        "--magic", str(args.magic),
        "--max-orders", str(args.max_orders),
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--use-adapter-lot",
    ]
    if not args.disable_monitor_skip:
        cmd.append("--skip-monitor-when-no-open-signals")
    if not args.disable_same_m15_skip:
        cmd.append("--skip-same-m15-no-signal")
    return cmd


def build_guarded_sender_cmd(args: argparse.Namespace, paths: dict[str, Path], *, pass_send: bool) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(paths["payload_csv"]),
        "--order-ledger-csv", str(paths["guarded_order_ledger_csv"]),
        "--out-dir", str(paths["guarded_sender_out_dir"]),
        "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders),
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--select-symbol",
        "--expected-login", str(args.expected_login),
        "--registry-preview-out-csv", str(paths["registry_preview_csv"]),
        "--registry-preview-out-json", str(paths["registry_preview_json"]),
    ]
    if args.require_demo_account:
        cmd.append("--require-demo-account")
    if pass_send:
        cmd.append("--send")
    return cmd


def decide_send_suppression(args: argparse.Namespace, payload_rows: int) -> tuple[bool, str]:
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
    return True, ""


def is_safe_no_payload_cycle(*, args: argparse.Namespace, dry_rc: int, dry_cycle_ok: bool, payload_rows: int, pass_send: bool, guarded_report: dict[str, Any]) -> bool:
    return bool(
        payload_rows == 0
        and not pass_send
        and safe_int(guarded_report, "rows_out", 0) == 0
        and safe_int(guarded_report, "order_send_called_count", 0) == 0
        and safe_int(guarded_report, "sent_rows", 0) == 0
        and str(args.position_policy) == "allow_any_until_max"
        and dry_rc in {0, 1}
        and not dry_cycle_ok
    )


def evaluate_guarded_sender_success(
    *,
    pass_send: bool,
    payload_rows: int,
    guarded_sender_rc: int | str,
    guarded_report: dict[str, Any],
) -> tuple[bool, str, bool]:
    """Return (ok, reason, strict_send_success_required)."""
    rows_out = safe_int(guarded_report, "rows_out", 0)
    sent_rows = safe_int(guarded_report, "sent_rows", 0)
    error_rows = safe_int(guarded_report, "error_rows", 0)
    called = safe_int(guarded_report, "order_send_called_count", 0)

    if payload_rows <= 0:
        if guarded_sender_rc == "SKIPPED_NO_PAYLOAD_ROWS" and rows_out == 0 and sent_rows == 0 and called == 0:
            return True, "NO_PAYLOAD_ROWS_SAFE_SKIP", False
        return False, "NO_PAYLOAD_ROWS_BUT_SENDER_STATE_UNEXPECTED", False

    if pass_send:
        if guarded_sender_rc != 0:
            return False, f"SEND_REQUESTED_BUT_SENDER_RETURNCODE_NOT_ZERO: {guarded_sender_rc}", True
        if called <= 0:
            return False, "SEND_REQUESTED_BUT_ORDER_SEND_NOT_CALLED", True
        if sent_rows != int(payload_rows):
            return False, f"SEND_REQUESTED_BUT_SENT_ROWS_MISMATCH: sent_rows={sent_rows}; payload_rows={payload_rows}", True
        if error_rows != 0:
            return False, f"SEND_REQUESTED_BUT_ERROR_ROWS_NONZERO: error_rows={error_rows}", True
        if rows_out < int(payload_rows):
            return False, f"SEND_REQUESTED_BUT_ROWS_OUT_LT_PAYLOAD_ROWS: rows_out={rows_out}; payload_rows={payload_rows}", True
        return True, "SEND_REQUESTED_AND_ALL_PAYLOAD_ROWS_SENT", True

    # No-send/dry-run path: sender may validate, but must never call order_send.
    if guarded_sender_rc not in [0, "SKIPPED_NO_PAYLOAD_ROWS"]:
        return False, f"NO_SEND_BUT_SENDER_RETURNCODE_NOT_OK: {guarded_sender_rc}", False
    if called != 0 or sent_rows != 0:
        return False, f"NO_SEND_BUT_ORDER_SEND_OCCURRED: called={called}; sent_rows={sent_rows}", False
    return True, "NO_SEND_PATH_OK", False


def main() -> int:
    args = parse_args()
    started_perf = time.perf_counter()
    cycle_start = utc_now_text()
    mkdir_path(args.out_dir)

    paths = {
        "dry_out_dir": args.out_dir / "dry_run_stage",
        "payload_csv": args.out_dir / "dry_run_stage" / "payload" / "order_payloads.csv",
        "guarded_sender_out_dir": args.out_dir / "guarded_sender",
        "guarded_order_ledger_csv": args.out_dir / "guarded_demo_order_ledger.csv",
        "registry_preview_csv": args.out_dir / "registry_preview" / "registry_preview.csv",
        "registry_preview_json": args.out_dir / "registry_preview" / "registry_preview.json",
        "summary_json": args.out_dir / SUMMARY_FILENAME,
        "cycle_log_csv": args.out_dir / "gold_multi_strategy_guarded_demo_send_once_log.csv",
    }

    print("=" * 80, flush=True)
    print("GOLD multi-strategy guarded demo-send ONCE wrapper", flush=True)
    print("Default is no-send. Sender receives --send only with BOTH --allow-demo-send and --send.", flush=True)
    print("Integration policy: use adapter lot, allow_any_until_max, duplicate order_key guard.", flush=True)
    print("Strict send success: when --send is passed, sent_rows must equal payload_rows_out and error_rows must be 0.", flush=True)
    print(f"csv_dir={args.csv_dir}", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"allow_demo_send={args.allow_demo_send} send_requested={args.send}", flush=True)
    print("=" * 80, flush=True)

    dry_rc, dry_seconds = run_cmd("dry_run_stage", build_dry_run_cmd(args, paths["dry_out_dir"]))
    dry_summary = read_json_or_empty(paths["dry_out_dir"] / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_result.json")
    payload_rows = payload_rows_count(paths["payload_csv"])

    pass_send, suppressed_reason = decide_send_suppression(args, payload_rows)
    guarded_sender_rc: int | str = "SKIPPED"
    guarded_seconds = 0.0
    guarded_report: dict[str, Any] = {}

    if payload_rows <= 0:
        guarded_sender_rc = "SKIPPED_NO_PAYLOAD_ROWS"
        print("[INFO] guarded sender skipped because payload rows are 0", flush=True)
    else:
        guarded_sender_rc, guarded_seconds = run_cmd(
            "guarded_sender",
            build_guarded_sender_cmd(args, paths, pass_send=pass_send),
        )
        guarded_report = read_json_or_empty(paths["guarded_sender_out_dir"] / "mt5_order_send_report.json")

    if not guarded_report:
        guarded_report = {
            "rows_out": 0,
            "dry_run_check_ok_rows": 0,
            "sent_rows": 0,
            "error_rows": 0,
            "order_send_called_count": 0,
            "reason": "GUARDED_SENDER_NOT_RUN",
        }

    cycle_end = utc_now_text()
    sender_order_send_called_count = safe_int(guarded_report, "order_send_called_count", 0)
    sender_sent_rows = safe_int(guarded_report, "sent_rows", 0)
    sender_error_rows = safe_int(guarded_report, "error_rows", 0)
    sender_rows_out = safe_int(guarded_report, "rows_out", 0)
    dry_cycle_ok = safe_bool(dry_summary, "cycle_ok", dry_rc == 0)
    guarded_sender_ok, guarded_sender_success_reason, strict_send_success_required = evaluate_guarded_sender_success(
        pass_send=bool(pass_send),
        payload_rows=int(payload_rows),
        guarded_sender_rc=guarded_sender_rc,
        guarded_report=guarded_report,
    )
    natural_ok = bool(dry_rc == 0 and dry_cycle_ok and guarded_sender_ok)
    safe_no_payload_ok = is_safe_no_payload_cycle(
        args=args,
        dry_rc=dry_rc,
        dry_cycle_ok=dry_cycle_ok,
        payload_rows=payload_rows,
        pass_send=pass_send,
        guarded_report=guarded_report,
    )
    cycle_ok = bool(natural_ok or safe_no_payload_ok)
    cycle_ok_classification = "NATURAL_PASS" if natural_ok else ("SAFE_NO_PAYLOAD_PASS" if safe_no_payload_ok else "FAILED")

    reason = "GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_PASS"
    if safe_no_payload_ok:
        reason = "GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_SAFE_NO_PAYLOAD_PASS"
    elif not cycle_ok:
        reason = "GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_FAILED"

    summary = {
        "schema_version": "gold_multi_strategy_guarded_demo_send_once_v4_strict_send_success",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "cycle_ok": cycle_ok,
        "cycle_ok_classification": cycle_ok_classification,
        "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send),
        "send_suppressed_reason": suppressed_reason,
        "strict_send_success_required": bool(strict_send_success_required),
        "guarded_sender_success_ok": bool(guarded_sender_ok),
        "guarded_sender_success_reason": guarded_sender_success_reason,
        "guards": {
            "expected_login": int(args.expected_login),
            "require_demo_account": bool(args.require_demo_account),
            "broker_symbol": str(args.broker_symbol),
            "fixed_lot_fallback": float(args.fixed_lot),
            "use_adapter_lot": True,
            "max_orders": int(args.max_orders),
            "position_policy": str(args.position_policy),
            "max_symbol_positions": int(args.max_symbol_positions),
            "max_symbol_lot": float(args.max_symbol_lot),
            "strict_send_success_rule": "if --send is passed and payload_rows_out>0, require sent_rows==payload_rows_out and error_rows==0",
        },
        "returncodes": {
            "dry_run_stage": dry_rc,
            "guarded_sender": guarded_sender_rc,
        },
        "key_metrics": {
            "dry_run_wrapper_cycle_ok": dry_cycle_ok,
            "payload_rows_out": int(payload_rows),
            "guarded_sender_rows_out": sender_rows_out,
            "guarded_sender_dry_run_check_ok_rows": safe_int(guarded_report, "dry_run_check_ok_rows", 0),
            "guarded_sender_sent_rows": sender_sent_rows,
            "guarded_sender_error_rows": sender_error_rows,
            "guarded_sender_order_send_called_count": sender_order_send_called_count,
        },
        "safety": {
            "normal_dry_run_wrapper_send_flag_passed": False,
            "guarded_sender_send_flag_passed": bool(pass_send),
            "strict_send_success_required": bool(strict_send_success_required),
            "production_registry_mutated": False,
            "existing_mochipoyo_bat_modified": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
            "position_policy_block_any_used": str(args.position_policy) == "block_any",
        },
        "timing": {
            "dry_run_stage_seconds": dry_seconds,
            "guarded_sender_seconds": guarded_seconds,
            "total_seconds": round(time.perf_counter() - started_perf, 3),
        },
        "paths": {k: str(v) for k, v in paths.items()},
        "dry_run_summary": dry_summary,
        "guarded_sender_report": guarded_report,
    }
    write_json(paths["summary_json"], summary)
    row = {
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "cycle_ok": cycle_ok,
        "cycle_ok_classification": cycle_ok_classification,
        "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send),
        "send_suppressed_reason": suppressed_reason,
        "strict_send_success_required": bool(strict_send_success_required),
        "guarded_sender_success_ok": bool(guarded_sender_ok),
        "guarded_sender_success_reason": guarded_sender_success_reason,
        "payload_rows_out": int(payload_rows),
        "guarded_sender_returncode": guarded_sender_rc,
        "guarded_sender_rows_out": sender_rows_out,
        "guarded_sender_dry_run_check_ok_rows": safe_int(guarded_report, "dry_run_check_ok_rows", 0),
        "guarded_sender_sent_rows": sender_sent_rows,
        "guarded_sender_error_rows": sender_error_rows,
        "guarded_sender_order_send_called_count": sender_order_send_called_count,
        "dry_run_wrapper_returncode": dry_rc,
        "dry_run_wrapper_cycle_ok": dry_cycle_ok,
        "dry_run_wrapper_summary_json": str(paths["dry_out_dir"] / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_result.json"),
        "summary_json": str(paths["summary_json"]),
        "total_seconds": summary["timing"]["total_seconds"],
    }
    append_csv_row(paths["cycle_log_csv"], row, LOG_COLUMNS)

    print("=" * 80, flush=True)
    print("GOLD multi-strategy guarded demo-send once summary", flush=True)
    print(json.dumps({
        "cycle_ok": cycle_ok,
        "cycle_ok_classification": cycle_ok_classification,
        "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send),
        "send_suppressed_reason": suppressed_reason,
        "strict_send_success_required": bool(strict_send_success_required),
        "guarded_sender_success_ok": bool(guarded_sender_ok),
        "guarded_sender_success_reason": guarded_sender_success_reason,
        "key_metrics": summary["key_metrics"],
        "guards": summary["guards"],
        "safety": summary["safety"],
        "timing": summary["timing"],
        "summary_json": str(paths["summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
