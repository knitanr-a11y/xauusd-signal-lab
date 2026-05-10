#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""A/B validate same-M15 no-signal skip invariance.

This validator verifies the second-stage lightweight skip:

    --skip-same-m15-no-signal

Validation sequence:

1. Baseline full scan
   - Uses the robust fast-M15 wrapper.
   - Enables monitor skip only.
   - Does NOT enable same-M15 skip.

2. Optimized warm-up scan
   - Uses the robust fast-M15 wrapper.
   - Enables monitor skip and same-M15 skip.
   - Uses a fresh output directory, so the first pass should NOT skip.
   - It writes runtime_state.json.

3. Optimized skip scan
   - Runs the exact same command/output directory again.
   - With the same latest confirmed M15 and prior no-signal state, router should
     be skipped with SKIPPED_SAME_M15_NO_SIGNAL.

Then it compares baseline full-scan outputs to optimized skip outputs for signal
and order-generation invariants:

- strategy slots
- signal_found
- signal_key
- scan_reason
- latest_m15_close_time
- candidate_count / latest_candidate_entry_time
- signals_found_count
- open_order_intent_count
- close_intent_count
- payload_rows_out
- valid_order_payloads

Allowed differences:
- runner_returncode may become SKIPPED_SAME_M15_NO_SIGNAL.
- monitor_reason may become MONITOR_SKIPPED_BY_SAME_M15_NO_SIGNAL.
- timing should improve.

Safety:
- Never passes --send.
- Uses dedicated short output directories under data/r/sm15ab.
- Does not write production registry.
- Does not call existing Mochipoyo production/demo BATs.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("data/r/sm15ab")
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")

CASE_LOG_COLUMNS = [
    "case_name",
    "returncode",
    "elapsed_seconds",
    "summary_json",
    "stdout_log",
    "stderr_log",
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


def remove_dir(path: Path) -> None:
    if Path(windows_long_path(path)).exists():
        shutil.rmtree(windows_long_path(path), ignore_errors=True)


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


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
    exists = Path(windows_long_path(path)).exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in columns})


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def norm(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_wrapper_cmd(args: argparse.Namespace, out_dir: Path, *, same_m15_skip: bool) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_mochipoyo_loop_dry_run_fast_m15_patch.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(out_dir),
        "--broker-symbol", str(args.broker_symbol),
        "--expected-login", str(args.expected_login),
        "--require-demo-account",
        "--select-symbol",
        "--fixed-lot", str(args.fixed_lot),
        "--magic", str(args.magic),
        "--max-orders", str(args.max_orders),
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--latest-confirmed-policy", str(args.latest_confirmed_policy),
        "--latest-confirmed-m5-policy", str(args.latest_confirmed_m5_policy),
        "--latest-confirmed-m1-policy", str(args.latest_confirmed_m1_policy),
        "--skip-monitor-when-no-open-signals",
    ]
    if same_m15_skip:
        cmd.append("--skip-same-m15-no-signal")
    return cmd


def run_case(case_name: str, cmd: list[str], out_dir: Path, log_dir: Path) -> dict[str, Any]:
    mkdir_path(log_dir)
    stdout_log = log_dir / f"{case_name}_stdout.txt"
    stderr_log = log_dir / f"{case_name}_stderr.txt"
    print("=" * 80, flush=True)
    print(f"[CASE] {case_name}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    write_text(stdout_log, completed.stdout or "")
    write_text(stderr_log, completed.stderr or "")
    if completed.stdout:
        print(completed.stdout.rstrip(), flush=True)
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr, flush=True)
    summary_json = out_dir / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_result.json"
    return {
        "case_name": case_name,
        "returncode": int(completed.returncode),
        "elapsed_seconds": elapsed,
        "summary_json": str(summary_json),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "summary": read_json_or_empty(summary_json),
    }


def strategy_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    router = summary.get("router_result", {}) if isinstance(summary.get("router_result"), dict) else {}
    statuses = router.get("strategy_status", []) if isinstance(router.get("strategy_status"), list) else []
    out: dict[str, dict[str, Any]] = {}
    for status in statuses:
        if not isinstance(status, dict):
            continue
        slot = str(status.get("strategy_slot", ""))
        if slot:
            out[slot] = status
    return out


def compare_field(checks: dict[str, bool], failures: list[dict[str, Any]], *, name: str, baseline: Any, optimized: Any) -> None:
    ok = norm(baseline) == norm(optimized)
    checks[name] = ok
    if not ok:
        failures.append({"check": name, "baseline": baseline, "optimized": optimized})


def compare_summaries(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    failures: list[dict[str, Any]] = []

    for key in [
        "cycle_ok",
        "latest_confirmed_m15_close_time_fast",
    ]:
        compare_field(checks, failures, name=key, baseline=baseline.get(key), optimized=optimized.get(key))

    for key in [
        "signals_found_count",
        "open_order_intent_count",
        "close_intent_count",
        "payload_rows_out",
        "valid_order_payloads",
    ]:
        compare_field(checks, failures, name=f"key_metrics.{key}", baseline=baseline.get("key_metrics", {}).get(key), optimized=optimized.get("key_metrics", {}).get(key))

    b_router = baseline.get("router_result", {}) if isinstance(baseline.get("router_result"), dict) else {}
    o_router = optimized.get("router_result", {}) if isinstance(optimized.get("router_result"), dict) else {}
    for key in ["signals_found_count", "open_order_intent_count", "close_intent_count"]:
        compare_field(checks, failures, name=f"router.{key}", baseline=b_router.get(key), optimized=o_router.get(key))

    b_strategies = strategy_map(baseline)
    o_strategies = strategy_map(optimized)
    compare_field(checks, failures, name="strategy_slots", baseline=sorted(b_strategies.keys()), optimized=sorted(o_strategies.keys()))

    invariant_fields = [
        "strategy_id",
        "direction",
        "cycle_ok",
        "signal_found",
        "rank",
        "trade_enabled",
        "duplicate",
        "signal_key",
        "scan_reason",
        "latest_m15_close_time",
        "candidate_count",
        "latest_candidate_entry_time",
    ]
    for slot in sorted(set(b_strategies.keys()) | set(o_strategies.keys())):
        b = b_strategies.get(slot, {})
        o = o_strategies.get(slot, {})
        for field in invariant_fields:
            compare_field(checks, failures, name=f"{slot}.{field}", baseline=b.get(field), optimized=o.get(field))
        compare_field(checks, failures, name=f"{slot}.has_order_intent", baseline=bool(b.get("order_intent_path")), optimized=bool(o.get("order_intent_path")))
        compare_field(checks, failures, name=f"{slot}.has_close_intent", baseline=bool(b.get("close_intent_path")), optimized=bool(o.get("close_intent_path")))

    o_safety = optimized.get("safety", {}) if isinstance(optimized.get("safety"), dict) else {}
    b_safety = baseline.get("safety", {}) if isinstance(baseline.get("safety"), dict) else {}
    safety_checks = {
        "baseline_no_send": not as_bool(b_safety.get("send_flag_passed"), False) and as_int(b_safety.get("sender_order_send_called_count"), 0) == 0 and as_int(b_safety.get("sender_sent_rows"), 0) == 0,
        "optimized_no_send": not as_bool(o_safety.get("send_flag_passed"), False) and as_int(o_safety.get("sender_order_send_called_count"), 0) == 0 and as_int(o_safety.get("sender_sent_rows"), 0) == 0,
        "optimized_same_m15_skip_true": as_bool(optimized.get("same_m15_no_signal_skipped"), False),
        "optimized_router_skipped": norm(optimized.get("returncodes", {}).get("router")) == "SKIPPED_SAME_M15_NO_SIGNAL",
        "optimized_payload_zero": as_int(optimized.get("key_metrics", {}).get("payload_rows_out"), 0) == 0,
    }
    checks.update(safety_checks)
    for name, ok in safety_checks.items():
        if not ok:
            failures.append({"check": name, "baseline": b_safety, "optimized": o_safety})

    return {"checks": checks, "failures": failures, "comparison_ok": len(failures) == 0}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="A/B validate same-M15 no-signal skip invariance.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--expected-login", type=int, default=75539039)
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
    p.add_argument("--keep-existing-out-dir", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.keep_existing_out_dir:
        remove_dir(args.out_dir)
    mkdir_path(args.out_dir)
    started = utc_now_text()
    baseline_dir = args.out_dir / "base"
    optimized_dir = args.out_dir / "opt"
    log_dir = args.out_dir / "logs"

    baseline = run_case("baseline_full_scan", build_wrapper_cmd(args, baseline_dir, same_m15_skip=False), baseline_dir, log_dir)
    optimized_warm = run_case("optimized_warmup_full_scan", build_wrapper_cmd(args, optimized_dir, same_m15_skip=True), optimized_dir, log_dir)
    optimized_skip = run_case("optimized_same_m15_skip", build_wrapper_cmd(args, optimized_dir, same_m15_skip=True), optimized_dir, log_dir)

    for case in [baseline, optimized_warm, optimized_skip]:
        append_csv_row(args.out_dir / "same_m15_skip_ab_case_log.csv", {k: v for k, v in case.items() if k != "summary"}, CASE_LOG_COLUMNS)

    comparison = compare_summaries(baseline.get("summary", {}), optimized_skip.get("summary", {}))
    returncodes_ok = baseline["returncode"] == 0 and optimized_warm["returncode"] == 0 and optimized_skip["returncode"] == 0
    warmup_not_skipped = not as_bool(optimized_warm.get("summary", {}).get("same_m15_no_signal_skipped"), False)
    validation_ok = bool(returncodes_ok and warmup_not_skipped and comparison["comparison_ok"])

    b_timing = baseline.get("summary", {}).get("timing", {}) if isinstance(baseline.get("summary", {}).get("timing"), dict) else {}
    w_timing = optimized_warm.get("summary", {}).get("timing", {}) if isinstance(optimized_warm.get("summary", {}).get("timing"), dict) else {}
    s_timing = optimized_skip.get("summary", {}).get("timing", {}) if isinstance(optimized_skip.get("summary", {}).get("timing"), dict) else {}
    summary = {
        "schema_version": "gold_multi_strategy_same_m15_skip_ab_validation_v1",
        "started_at_utc": started,
        "ended_at_utc": utc_now_text(),
        "validation_ok": validation_ok,
        "reason": "SAME_M15_NO_SIGNAL_SKIP_INVARIANCE_PASS" if validation_ok else "SAME_M15_NO_SIGNAL_SKIP_INVARIANCE_FAILED",
        "returncodes_ok": returncodes_ok,
        "warmup_not_skipped": warmup_not_skipped,
        "comparison": comparison,
        "timing": {
            "baseline": b_timing,
            "optimized_warmup": w_timing,
            "optimized_skip": s_timing,
            "baseline_total_seconds": b_timing.get("total_seconds", ""),
            "optimized_warmup_total_seconds": w_timing.get("total_seconds", ""),
            "optimized_skip_total_seconds": s_timing.get("total_seconds", ""),
            "baseline_router_seconds": b_timing.get("router_seconds", ""),
            "optimized_skip_router_seconds": s_timing.get("router_seconds", ""),
        },
        "safety": {
            "send_flag_passed": False,
            "production_registry_mutated": False,
            "existing_mochipoyo_bat_modified": False,
        },
        "paths": {
            "baseline_dir": str(baseline_dir),
            "optimized_dir": str(optimized_dir),
            "summary_json": str(args.out_dir / "latest_gold_multi_strategy_same_m15_skip_ab_validation_result.json"),
        },
        "cases": [
            {k: v for k, v in baseline.items() if k != "summary"},
            {k: v for k, v in optimized_warm.items() if k != "summary"},
            {k: v for k, v in optimized_skip.items() if k != "summary"},
        ],
    }
    write_json(args.out_dir / "latest_gold_multi_strategy_same_m15_skip_ab_validation_result.json", summary)
    print("=" * 80, flush=True)
    print("GOLD multi-strategy same-M15 skip A/B validation summary", flush=True)
    print(json.dumps({
        "validation_ok": validation_ok,
        "reason": summary["reason"],
        "returncodes_ok": returncodes_ok,
        "warmup_not_skipped": warmup_not_skipped,
        "checks_failed": comparison["failures"],
        "timing": summary["timing"],
        "summary_json": summary["paths"]["summary_json"],
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if validation_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
