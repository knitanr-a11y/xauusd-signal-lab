#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Independent GOLD multi-strategy Mochipoyo-loop dry-run wrapper.

This script is the safe bridge between:

    BUY/SELL multi-strategy signal generation
        -> router
        -> autotrade adapter preview
        -> Mochipoyo-compatible order_payloads.csv
        -> guarded MT5 sender dry-run
        -> optional sender-native registry preview

It intentionally does NOT touch the existing Mochipoyo production/demo loop BAT.

Safety boundaries:
- Never passes --send to send_mt5_order_from_payload.py.
- Does not call or modify scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat.
- Does not write existing Mochipoyo notification ledgers.
- Does not write existing Mochipoyo trigger-state files.
- Does not write production position_registry.csv.
- Writes only under --out-dir by default.

This is intended to validate that the H4/H1 BUY/SELL signal work can flow toward
Mochipoyo-compatible payloads and sender dry-run without merging into the old loop.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_mochipoyo_loop_dry_run")

CYCLE_LOG_COLUMNS = [
    "cycle_start_utc",
    "cycle_end_utc",
    "cycle_ok",
    "csv_dir",
    "out_dir",
    "router_returncode",
    "adapter_returncode",
    "payload_bridge_returncode",
    "sender_returncode",
    "router_ok",
    "adapter_ok",
    "bridge_ok",
    "sender_stage_status",
    "signals_found_count",
    "open_order_intent_count",
    "close_intent_count",
    "order_previews_created",
    "close_previews_created",
    "payload_rows_out",
    "valid_order_payloads",
    "sender_rows_out",
    "sender_dry_run_check_ok_rows",
    "sender_sent_rows",
    "sender_error_rows",
    "sender_order_send_called_count",
    "registry_preview_enabled",
    "registry_preview_rows",
    "latest_summary_json",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run independent GOLD multi-strategy Mochipoyo-loop dry-run wrapper. Never passes --send.")
    p.add_argument("--csv-dir", type=Path, required=True, help="Directory containing MT5-exported GOLD CSV files.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--select-symbol", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--magic", type=int, default=26050601)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=5)
    p.add_argument("--max-symbol-lot", type=float, default=0.05)
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m5-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m1-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--skip-router", action="store_true", help="Use existing router outputs under this wrapper out-dir.")
    p.add_argument("--reset-adapter-ledger", action="store_true")
    p.add_argument("--use-adapter-lot", action="store_true", help="Use adapter effective_lot in payload bridge. Default is fixed lot 0.01.")
    p.add_argument("--disable-registry-preview", action="store_true", help="Do not request sender-native registry preview outputs.")
    p.add_argument("--continue-on-stage-error", action="store_true")
    return p.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


def run_cmd(label: str, cmd: list[str]) -> int:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    print(f"[STEP] {label} returncode={completed.returncode}", flush=True)
    return int(completed.returncode)


def safe_int(obj: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key, default) or 0)
    except Exception:
        return default


def safe_bool(obj: dict[str, Any], key: str, default: bool = False) -> bool:
    val = obj.get(key, default)
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in {"true", "1", "yes", "y"}


def payload_rows_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return int(len(pd.read_csv(path, encoding="utf-8-sig")))
    except Exception:
        return 0


def build_paths(out_dir: Path) -> dict[str, Path]:
    return {
        "router_out_dir": out_dir / "router",
        "buy_out_dir": out_dir / "buy_c_env_rr2_72h",
        "sell_out_dir": out_dir / "sell_h1h4_bear_ab",
        "adapter_out_dir": out_dir / "adapter",
        "payload_out_dir": out_dir / "payload",
        "sender_out_dir": out_dir / "sender",
        "registry_preview_csv": out_dir / "registry_preview" / "registry_preview.csv",
        "registry_preview_json": out_dir / "registry_preview" / "registry_preview.json",
        "order_ledger_csv": out_dir / "dry_run_order_ledger.csv",
        "summary_json": out_dir / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_result.json",
        "cycle_log_csv": out_dir / "gold_multi_strategy_mochipoyo_loop_dry_run_log.csv",
    }


def build_router_cmd(args: argparse.Namespace, paths: dict[str, Path]) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_dry_run_cycle.py"),
        "--csv-dir", str(args.csv_dir),
        "--router-out-dir", str(paths["router_out_dir"]),
        "--buy-out-dir", str(paths["buy_out_dir"]),
        "--sell-out-dir", str(paths["sell_out_dir"]),
        "--latest-confirmed-policy", str(args.latest_confirmed_policy),
        "--latest-confirmed-m5-policy", str(args.latest_confirmed_m5_policy),
        "--latest-confirmed-m1-policy", str(args.latest_confirmed_m1_policy),
        "--continue-on-strategy-error",
    ]


def build_adapter_cmd(args: argparse.Namespace, paths: dict[str, Path]) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_autotrade_adapter_dry_run.py"),
        "--router-out-dir", str(paths["router_out_dir"]),
        "--out-dir", str(paths["adapter_out_dir"]),
        "--broker-symbol", str(args.broker_symbol),
    ]
    if args.reset_adapter_ledger:
        cmd.append("--reset-ledger")
    return cmd


def build_payload_cmd(args: argparse.Namespace, paths: dict[str, Path]) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py"),
        "--adapter-out-dir", str(paths["adapter_out_dir"]),
        "--out-dir", str(paths["payload_out_dir"]),
        "--broker-symbol", str(args.broker_symbol),
        "--fixed-lot", str(args.fixed_lot),
        "--magic", str(args.magic),
        "--max-orders", str(args.max_orders),
    ]
    if args.use_adapter_lot:
        cmd.append("--use-adapter-lot")
    return cmd


def build_sender_cmd(args: argparse.Namespace, paths: dict[str, Path]) -> list[str] | None:
    input_csv = paths["payload_out_dir"] / "order_payloads.csv"
    if payload_rows_count(input_csv) <= 0:
        return None
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(input_csv),
        "--order-ledger-csv", str(paths["order_ledger_csv"]),
        "--out-dir", str(paths["sender_out_dir"]),
        "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders),
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
    ]
    if args.select_symbol:
        cmd.append("--select-symbol")
    if args.expected_login is not None:
        cmd.extend(["--expected-login", str(args.expected_login)])
    if args.require_demo_account:
        cmd.append("--require-demo-account")
    if not args.disable_registry_preview:
        cmd.extend([
            "--registry-preview-out-csv", str(paths["registry_preview_csv"]),
            "--registry-preview-out-json", str(paths["registry_preview_json"]),
        ])
    # Intentionally never append --send in this wrapper.
    return cmd


def main() -> int:
    args = parse_args()
    paths = build_paths(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cycle_start = utc_now_text()

    print("=" * 80, flush=True)
    print("GOLD multi-strategy Mochipoyo-loop DRY-RUN wrapper", flush=True)
    print("NO --send / NO existing Mochipoyo BAT mutation / NO production registry write", flush=True)
    print(f"csv_dir={args.csv_dir}", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print("=" * 80, flush=True)

    router_rc: int | str = "SKIPPED"
    if not args.skip_router:
        router_rc = run_cmd("router", build_router_cmd(args, paths))
        if router_rc != 0 and not args.continue_on_stage_error:
            print("[ERROR] router failed; stopping", flush=True)
    else:
        print("[INFO] router skipped; using existing router outputs", flush=True)

    adapter_rc: int | str = "SKIPPED"
    if router_rc == 0 or router_rc == "SKIPPED" or args.continue_on_stage_error:
        adapter_rc = run_cmd("adapter", build_adapter_cmd(args, paths))
        if adapter_rc != 0 and not args.continue_on_stage_error:
            print("[ERROR] adapter failed; stopping", flush=True)

    payload_rc: int | str = "SKIPPED"
    if adapter_rc == 0 or args.continue_on_stage_error:
        payload_rc = run_cmd("payload_bridge", build_payload_cmd(args, paths))
        if payload_rc != 0 and not args.continue_on_stage_error:
            print("[ERROR] payload bridge failed; stopping", flush=True)

    sender_rc: int | str = "SKIPPED_NO_PAYLOAD_ROWS"
    sender_cmd = build_sender_cmd(args, paths)
    if sender_cmd is not None and (payload_rc == 0 or args.continue_on_stage_error):
        sender_rc = run_cmd("sender_dry_run", sender_cmd)
    elif sender_cmd is None:
        print("[INFO] sender skipped because order_payloads.csv has no rows", flush=True)

    router_result = read_json_or_empty(paths["router_out_dir"] / "latest_multi_strategy_cycle_result.json")
    adapter_result = read_json_or_empty(paths["adapter_out_dir"] / "latest_adapter_result.json")
    payload_result = read_json_or_empty(paths["payload_out_dir"] / "order_payloads.json")
    sender_report = read_json_or_empty(paths["sender_out_dir"] / "mt5_order_send_report.json")
    registry_preview = sender_report.get("registry_preview", {}) if isinstance(sender_report.get("registry_preview", {}), dict) else {}

    sender_rows_out = safe_int(sender_report, "rows_out", 0)
    sender_dry_ok = safe_int(sender_report, "dry_run_check_ok_rows", 0)
    sender_sent_rows = safe_int(sender_report, "sent_rows", 0)
    sender_error_rows = safe_int(sender_report, "error_rows", 0)
    sender_order_send_called = safe_int(sender_report, "order_send_called_count", 0)

    router_ok = safe_bool(router_result, "router_ok", router_rc in [0, "SKIPPED"])
    adapter_ok = safe_bool(adapter_result, "adapter_ok", adapter_rc == 0)
    bridge_ok = safe_bool(payload_result, "bridge_ok", payload_rc == 0)
    sender_stage_ok = sender_rc in [0, "SKIPPED_NO_PAYLOAD_ROWS"] and sender_sent_rows == 0 and sender_order_send_called == 0
    cycle_ok = bool(router_ok and adapter_ok and bridge_ok and sender_stage_ok)
    cycle_end = utc_now_text()

    summary = {
        "schema_version": "gold_multi_strategy_mochipoyo_loop_dry_run_v1",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "cycle_ok": cycle_ok,
        "reason": "GOLD_MULTI_STRATEGY_MOCHIPOYO_LOOP_DRY_RUN_PASS" if cycle_ok else "GOLD_MULTI_STRATEGY_MOCHIPOYO_LOOP_DRY_RUN_FAILED",
        "safety": {
            "send_flag_passed": False,
            "existing_mochipoyo_bat_modified": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
            "production_registry_mutated": False,
            "sender_order_send_called_count": sender_order_send_called,
            "sender_sent_rows": sender_sent_rows,
        },
        "paths": {k: str(v) for k, v in paths.items()},
        "returncodes": {
            "router": router_rc,
            "adapter": adapter_rc,
            "payload_bridge": payload_rc,
            "sender": sender_rc,
        },
        "key_metrics": {
            "router_ok": router_ok,
            "adapter_ok": adapter_ok,
            "bridge_ok": bridge_ok,
            "sender_stage_ok": sender_stage_ok,
            "signals_found_count": safe_int(router_result, "signals_found_count", 0),
            "open_order_intent_count": safe_int(router_result, "open_order_intent_count", 0),
            "close_intent_count": safe_int(router_result, "close_intent_count", 0),
            "order_previews_created": safe_int(adapter_result, "order_previews_created", 0),
            "close_previews_created": safe_int(adapter_result, "close_previews_created", 0),
            "payload_rows_out": safe_int(payload_result, "rows_out", 0),
            "valid_order_payloads": safe_int(payload_result, "valid_order_payloads", 0),
            "sender_rows_out": sender_rows_out,
            "sender_dry_run_check_ok_rows": sender_dry_ok,
            "sender_sent_rows": sender_sent_rows,
            "sender_error_rows": sender_error_rows,
            "sender_order_send_called_count": sender_order_send_called,
            "registry_preview_enabled": bool(registry_preview.get("preview_enabled", False)),
            "registry_preview_rows": safe_int(registry_preview, "registry_preview_rows", 0),
        },
        "router_result": router_result,
        "adapter_result": adapter_result,
        "payload_bridge_result": payload_result,
        "sender_report": sender_report,
    }
    write_json(paths["summary_json"], summary)
    metrics = summary["key_metrics"]
    append_csv_row(paths["cycle_log_csv"], {
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "cycle_ok": cycle_ok,
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "router_returncode": router_rc,
        "adapter_returncode": adapter_rc,
        "payload_bridge_returncode": payload_rc,
        "sender_returncode": sender_rc,
        "sender_stage_status": "OK" if sender_stage_ok else "FAILED",
        "latest_summary_json": str(paths["summary_json"]),
        **metrics,
    }, CYCLE_LOG_COLUMNS)

    print("=" * 80, flush=True)
    print("GOLD multi-strategy Mochipoyo-loop dry-run summary", flush=True)
    print(json.dumps({
        "cycle_ok": cycle_ok,
        "reason": summary["reason"],
        "returncodes": summary["returncodes"],
        "key_metrics": metrics,
        "summary_json": str(paths["summary_json"]),
        "cycle_log_csv": str(paths["cycle_log_csv"]),
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
