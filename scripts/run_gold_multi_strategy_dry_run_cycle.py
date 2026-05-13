#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Isolated GOLD multi-strategy dry-run router.

Runs isolated GOLD strategy sidecars and aggregates order/close intents into
router-level files consumed by the existing adapter/payload/guarded-sender flow.

Current strategy slots:
- BUY_C_ENV_RR2_72H
- SELL_H1H4_BEAR_AB
- GOLD_ALT_PF_SIGNAL_PACK

Safety boundaries:
- No Discord send.
- No MT5 order placement.
- No existing Mochipoyo state/ledger mutation.
- Strategy outputs remain in strategy-specific out directories.
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

BUY_STRATEGY_ID = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H"
SELL_STRATEGY_ID = "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H"
ALT_STRATEGY_ID = "GOLD_ALT_PF_SIGNAL_PACK_V1"

DEFAULT_ROUTER_OUT_DIR = Path("data/research_results/gold_multi_strategy_dry_run")
DEFAULT_BUY_OUT_DIR = Path("data/research_results/gold_c_env_rr2_72h_live_scan")
DEFAULT_SELL_OUT_DIR = Path("data/research_results/gold_h1h4_bear_ab_live_loop")
DEFAULT_ALT_OUT_DIR = Path("data/research_results/gold_alt_pf_signal_pack")

STRATEGY_STATUS_COLUMNS = [
    "router_cycle_start_utc", "strategy_slot", "strategy_id", "direction", "strategy_out_dir", "runner_returncode",
    "cycle_ok", "signal_found", "rank", "trade_enabled", "duplicate", "signal_key", "scan_reason",
    "latest_m15_close_time", "candidate_count", "latest_candidate_entry_time", "signals_monitored", "resolved_skipped",
    "position_results_created", "tp_touched", "sl_touched", "time_exit_required", "close_intent_created",
    "open_unresolved", "no_path", "monitor_reason", "order_intent_path", "close_intent_path", "latest_cycle_result_path",
]

ROUTER_CYCLE_LOG_COLUMNS = [
    "router_cycle_start_utc", "router_cycle_end_utc", "router_ok", "router_mode", "csv_dir", "router_out_dir",
    "buy_enabled", "sell_enabled", "alt_enabled", "skip_monitor_when_no_open_signals", "buy_returncode",
    "sell_returncode", "alt_returncode", "strategies_ok", "signals_found_count", "open_order_intent_count",
    "observe_only_intent_count", "duplicate_skip_count", "close_intent_count", "strategy_status_latest",
    "combined_order_intents_jsonl", "combined_close_intents_jsonl", "latest_multi_strategy_cycle_result",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run isolated GOLD multi-strategy dry-run router cycle.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--router-out-dir", type=Path, default=DEFAULT_ROUTER_OUT_DIR)
    p.add_argument("--buy-out-dir", type=Path, default=DEFAULT_BUY_OUT_DIR)
    p.add_argument("--sell-out-dir", type=Path, default=DEFAULT_SELL_OUT_DIR)
    p.add_argument("--alt-out-dir", type=Path, default=DEFAULT_ALT_OUT_DIR)
    p.add_argument("--disable-buy", action="store_true")
    p.add_argument("--disable-sell", action="store_true")
    p.add_argument("--disable-alt", action="store_true")
    p.add_argument("--aggregate-only", action="store_true")
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m5-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m1-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--skip-monitor-when-no-open-signals", action="store_true")
    p.add_argument("--continue-on-strategy-error", action="store_true")
    return p.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns} for row in rows]).to_csv(path, index=False, encoding="utf-8-sig")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig"
    )


def run_cmd(cmd: list[str]) -> int:
    print("[CMD] " + " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    return int(completed.returncode)


def build_buy_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "run_gold_c_env_rr2_72h_dry_run_cycle.py"),
           "--csv-dir", str(args.csv_dir), "--out-dir", str(args.buy_out_dir), "--cycles", "1", "--sleep-seconds", "0",
           "--latest-confirmed-policy", str(args.latest_confirmed_policy), "--latest-confirmed-m5-policy", str(args.latest_confirmed_m5_policy)]
    if args.skip_monitor_when_no_open_signals:
        cmd.append("--skip-monitor-when-no-open-signals")
    return cmd


def build_sell_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "run_gold_h1h4_bear_ab_dry_run_loop.py"),
           "--csv-dir", str(args.csv_dir), "--out-dir", str(args.sell_out_dir), "--iterations", "1", "--interval-seconds", "0",
           "--base-lot", "0.01", "--latest-confirmed-policy", str(args.latest_confirmed_policy),
           "--latest-confirmed-m1-policy", str(args.latest_confirmed_m1_policy)]
    if args.skip_monitor_when_no_open_signals:
        cmd.append("--skip-monitor-when-no-open-signals")
    return cmd


def build_alt_cmd(args: argparse.Namespace) -> list[str]:
    return [sys.executable, str(REPO_ROOT / "scripts" / "run_gold_alt_pf_signal_pack_dry_run_cycle.py"),
            "--csv-dir", str(args.csv_dir), "--out-dir", str(args.alt_out_dir),
            "--latest-confirmed-policy", str(args.latest_confirmed_policy), "--base-lot", "0.01", "--max-lot-per-trade", "0.01"]


def load_strategy_outputs(strategy_out_dir: Path) -> dict[str, Any]:
    return {
        "latest_scan_result": read_json_or_empty(strategy_out_dir / "latest_scan_result.json"),
        "latest_position_monitor_result": read_json_or_empty(strategy_out_dir / "latest_position_monitor_result.json"),
        "latest_dry_run_cycle_result": read_json_or_empty(strategy_out_dir / "latest_dry_run_cycle_result.json"),
        "latest_dry_run_loop_cycle_result": read_json_or_empty(strategy_out_dir / "latest_dry_run_loop_cycle_result.json"),
        "order_intent_path": strategy_out_dir / "order_intent_dry_run.json",
        "close_intent_path": strategy_out_dir / "close_intent_dry_run.json",
    }


def aggregate_only_cycle_ok(strategy_out_dir: Path) -> bool:
    outputs = load_strategy_outputs(strategy_out_dir)
    if outputs["latest_dry_run_cycle_result"]:
        return bool(outputs["latest_dry_run_cycle_result"].get("cycle_ok", False))
    if outputs["latest_dry_run_loop_cycle_result"]:
        return bool(outputs["latest_dry_run_loop_cycle_result"].get("cycle", {}).get("cycle_ok", False))
    return bool(outputs["latest_scan_result"] or outputs["latest_position_monitor_result"])


def normalize_status(router_cycle_start: str, out_dir: Path, returncode: int | str, *, slot: str, strategy_id: str, direction: str, cycle_kind: str) -> dict[str, Any]:
    outputs = load_strategy_outputs(out_dir)
    scan = outputs["latest_scan_result"]
    monitor = outputs["latest_position_monitor_result"]
    if cycle_kind == "loop":
        cycle_ok = outputs["latest_dry_run_loop_cycle_result"].get("cycle", {}).get("cycle_ok", aggregate_only_cycle_ok(out_dir) if returncode == "AGGREGATE_ONLY" else returncode == 0)
        cycle_path = out_dir / "latest_dry_run_loop_cycle_result.json"
    else:
        cycle_ok = outputs["latest_dry_run_cycle_result"].get("cycle_ok", aggregate_only_cycle_ok(out_dir) if returncode == "AGGREGATE_ONLY" else returncode == 0)
        cycle_path = out_dir / "latest_dry_run_cycle_result.json"
    order_intent_path = outputs["order_intent_path"]
    close_intent_path = outputs["close_intent_path"]
    return {
        "router_cycle_start_utc": router_cycle_start, "strategy_slot": slot, "strategy_id": strategy_id, "direction": direction,
        "strategy_out_dir": str(out_dir), "runner_returncode": returncode, "cycle_ok": cycle_ok,
        "signal_found": scan.get("signal_found", ""), "rank": scan.get("rank", ""), "trade_enabled": scan.get("trade_enabled", ""),
        "duplicate": scan.get("duplicate", ""), "signal_key": scan.get("signal_key", ""), "scan_reason": scan.get("reason", ""),
        "latest_m15_close_time": scan.get("latest_m15_close_time", ""), "candidate_count": scan.get("candidate_count", ""),
        "latest_candidate_entry_time": scan.get("latest_candidate_entry_time", ""), "signals_monitored": monitor.get("signals_monitored", ""),
        "resolved_skipped": monitor.get("resolved_skipped", ""), "position_results_created": monitor.get("position_results_created", ""),
        "tp_touched": monitor.get("tp_touched", ""), "sl_touched": monitor.get("sl_touched", ""),
        "time_exit_required": monitor.get("time_exit_required", ""), "close_intent_created": monitor.get("close_intent_created", ""),
        "open_unresolved": monitor.get("open_unresolved", ""), "no_path": monitor.get("no_m1_path", monitor.get("no_m5_path", "")),
        "monitor_reason": monitor.get("reason", ""), "order_intent_path": str(order_intent_path) if order_intent_path.exists() else "",
        "close_intent_path": str(close_intent_path) if close_intent_path.exists() else "",
        "latest_cycle_result_path": str(cycle_path) if cycle_path.exists() else "",
    }


def read_order_intent(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    obj = read_json_or_empty(p)
    return obj if obj else None


def read_close_intents(path: str) -> list[dict[str, Any]]:
    if not path:
        return []
    obj = read_json_or_empty(Path(path))
    if not obj:
        return []
    return obj["intents"] if isinstance(obj.get("intents"), list) else [obj]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def count_order_intents(order_intents: list[dict[str, Any]], intent_type: str) -> int:
    return sum(1 for item in order_intents if str(item.get("intent_type", "")) == intent_type)


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def main() -> int:
    args = parse_args()
    args.router_out_dir.mkdir(parents=True, exist_ok=True)
    router_start = utc_now_text()
    router_mode = "AGGREGATE_ONLY" if args.aggregate_only else "RUN_AND_AGGREGATE"
    print(f"[INFO] router_start_utc={router_start}")
    print(f"[INFO] router_mode={router_mode}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] router_out_dir={args.router_out_dir}")
    print(f"[INFO] buy_enabled={not args.disable_buy} sell_enabled={not args.disable_sell} alt_enabled={not args.disable_alt}")

    buy_rc: int | str = "DISABLED"
    sell_rc: int | str = "DISABLED"
    alt_rc: int | str = "DISABLED"

    if args.aggregate_only:
        if not args.disable_buy: buy_rc = "AGGREGATE_ONLY"
        if not args.disable_sell: sell_rc = "AGGREGATE_ONLY"
        if not args.disable_alt: alt_rc = "AGGREGATE_ONLY"
    else:
        if not args.disable_buy:
            buy_rc = run_cmd(build_buy_cmd(args))
            if buy_rc != 0 and not args.continue_on_strategy_error:
                print("[ERROR] BUY strategy runner failed; stopping router", flush=True)
        if (buy_rc == 0 or args.disable_buy or args.continue_on_strategy_error) and not args.disable_sell:
            sell_rc = run_cmd(build_sell_cmd(args))
            if sell_rc != 0 and not args.continue_on_strategy_error:
                print("[ERROR] SELL strategy runner failed", flush=True)
        if (buy_rc == 0 or args.disable_buy or args.continue_on_strategy_error) and (sell_rc == 0 or args.disable_sell or args.continue_on_strategy_error) and not args.disable_alt:
            alt_rc = run_cmd(build_alt_cmd(args))
            if alt_rc != 0 and not args.continue_on_strategy_error:
                print("[ERROR] ALT PF strategy runner failed", flush=True)

    statuses: list[dict[str, Any]] = []
    if not args.disable_buy:
        statuses.append(normalize_status(router_start, args.buy_out_dir, buy_rc, slot="BUY_C_ENV_RR2_72H", strategy_id=BUY_STRATEGY_ID, direction="BUY", cycle_kind="cycle"))
    if not args.disable_sell:
        statuses.append(normalize_status(router_start, args.sell_out_dir, sell_rc, slot="SELL_H1H4_BEAR_AB", strategy_id=SELL_STRATEGY_ID, direction="SELL", cycle_kind="loop"))
    if not args.disable_alt:
        statuses.append(normalize_status(router_start, args.alt_out_dir, alt_rc, slot="GOLD_ALT_PF_SIGNAL_PACK", strategy_id=ALT_STRATEGY_ID, direction="MIXED", cycle_kind="cycle"))

    strategy_status_path = args.router_out_dir / "strategy_status_latest.csv"
    write_csv(strategy_status_path, statuses, STRATEGY_STATUS_COLUMNS)

    order_intents: list[dict[str, Any]] = []
    close_intents: list[dict[str, Any]] = []
    for status in statuses:
        order_intent = read_order_intent(str(status.get("order_intent_path", "")))
        if order_intent is not None:
            order_intent = dict(order_intent)
            order_intent["router_strategy_slot"] = status["strategy_slot"]
            order_intent["router_strategy_id"] = status["strategy_id"]
            order_intent["router_source_path"] = status.get("order_intent_path", "")
            order_intents.append(order_intent)
        for close_intent in read_close_intents(str(status.get("close_intent_path", ""))):
            close_intent = dict(close_intent)
            close_intent["router_strategy_slot"] = status["strategy_slot"]
            close_intent["router_strategy_id"] = status["strategy_id"]
            close_intent["router_source_path"] = status.get("close_intent_path", "")
            close_intents.append(close_intent)

    order_intents_path = args.router_out_dir / "combined_order_intent_dry_run.jsonl"
    close_intents_path = args.router_out_dir / "combined_close_intent_dry_run.jsonl"
    write_jsonl(order_intents_path, order_intents)
    write_jsonl(close_intents_path, close_intents)

    strategies_ok = all(boolish(status.get("cycle_ok", False)) for status in statuses) if statuses else True
    router_end = utc_now_text()
    rc_ok = all(rc in [0, "DISABLED", "AGGREGATE_ONLY"] for rc in [buy_rc, sell_rc, alt_rc])
    router_ok = strategies_ok and rc_ok
    summary = {
        "schema_version": "gold_multi_strategy_dry_run_router_v4_alt_pf_pack",
        "router_cycle_start_utc": router_start, "router_cycle_end_utc": router_end, "router_mode": router_mode,
        "router_ok": bool(router_ok), "csv_dir": str(args.csv_dir), "router_out_dir": str(args.router_out_dir),
        "buy_enabled": not args.disable_buy, "sell_enabled": not args.disable_sell, "alt_enabled": not args.disable_alt,
        "skip_monitor_when_no_open_signals": bool(args.skip_monitor_when_no_open_signals),
        "buy_returncode": buy_rc, "sell_returncode": sell_rc, "alt_returncode": alt_rc, "strategies_ok": bool(strategies_ok),
        "signals_found_count": int(sum(1 for s in statuses if boolish(s.get("signal_found", False)))),
        "open_order_intent_count": int(count_order_intents(order_intents, "OPEN_POSITION")),
        "observe_only_intent_count": int(count_order_intents(order_intents, "OBSERVE_ONLY")),
        "duplicate_skip_count": int(count_order_intents(order_intents, "DUPLICATE_SKIP")),
        "close_intent_count": int(len(close_intents)), "strategy_status": statuses,
        "outputs": {"strategy_status_latest": str(strategy_status_path), "combined_order_intents_jsonl": str(order_intents_path),
                    "combined_close_intents_jsonl": str(close_intents_path), "router_cycle_log": str(args.router_out_dir / "multi_strategy_cycle_log.csv"),
                    "latest_multi_strategy_cycle_result": str(args.router_out_dir / "latest_multi_strategy_cycle_result.json")},
    }
    latest_path = args.router_out_dir / "latest_multi_strategy_cycle_result.json"
    write_json(latest_path, summary)
    append_csv_row(args.router_out_dir / "multi_strategy_cycle_log.csv", {
        "router_cycle_start_utc": router_start, "router_cycle_end_utc": router_end, "router_ok": bool(router_ok),
        "router_mode": router_mode, "csv_dir": str(args.csv_dir), "router_out_dir": str(args.router_out_dir),
        "buy_enabled": not args.disable_buy, "sell_enabled": not args.disable_sell, "alt_enabled": not args.disable_alt,
        "skip_monitor_when_no_open_signals": bool(args.skip_monitor_when_no_open_signals),
        "buy_returncode": buy_rc, "sell_returncode": sell_rc, "alt_returncode": alt_rc, "strategies_ok": bool(strategies_ok),
        "signals_found_count": summary["signals_found_count"], "open_order_intent_count": summary["open_order_intent_count"],
        "observe_only_intent_count": summary["observe_only_intent_count"], "duplicate_skip_count": summary["duplicate_skip_count"],
        "close_intent_count": summary["close_intent_count"], "strategy_status_latest": str(strategy_status_path),
        "combined_order_intents_jsonl": str(order_intents_path), "combined_close_intents_jsonl": str(close_intents_path),
        "latest_multi_strategy_cycle_result": str(latest_path),
    }, ROUTER_CYCLE_LOG_COLUMNS)
    print("[INFO] multi-strategy dry-run router completed")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if router_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
