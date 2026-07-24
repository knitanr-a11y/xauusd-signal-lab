from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import m9v_core as core

MAX_LAG_SECONDS = {
    "M1": 10 * 60,
    "M5": 30 * 60,
    "M15": 60 * 60,
    "H1": 3 * 60 * 60,
    "H4": 12 * 60 * 60,
    "D1": 3 * 24 * 60 * 60,
}


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze a fresh M9V GOLD multi-timeframe prospective start.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--runtime-manifest", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--lock-file", required=True, type=Path)
    parser.add_argument("--stability-seconds", type=float, default=2.0)
    return parser.parse_args()


def inspect_all(data_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for timeframe, filename in contract["data"]["live_file_map"].items():
        path = data_root / str(filename)
        if not path.is_file():
            raise core.M9VContractError(f"missing live GOLD CSV: {path}")
        output[timeframe] = core.tail_snapshot(path)
    return output


def main() -> int:
    args = parse_args()
    try:
        if not args.contract.is_file():
            raise core.M9VContractError(f"missing M9V contract: {args.contract}")
        if not args.data_root.is_dir():
            raise core.M9VContractError(f"missing GOLD live data root: {args.data_root}")
        if args.lock_file.exists():
            raise core.M9VContractError("stop M9V monitor before initialization")
        if args.runtime_manifest.exists():
            raise core.M9VContractError("M9V runtime manifest already exists; reset/re-freeze is forbidden")

        contract = core.load_json(args.contract)
        core.validate_contract(contract)
        canonical = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        contract_sha = core.sha256_bytes(canonical)

        before = inspect_all(args.data_root, contract)
        if args.stability_seconds > 0:
            time.sleep(args.stability_seconds)
        after = inspect_all(args.data_root, contract)
        if before != after:
            raise core.M9VContractError("live CSV files changed during start freeze; rerun initialization on a stable snapshot")

        latest = {tf: core.parse_time(str(info["last_server_open"])) for tf, info in after.items()}
        start = latest["M1"]
        for timeframe, value in latest.items():
            lag = (start - value).total_seconds()
            if lag < 0:
                raise core.M9VContractError(f"{timeframe} is ahead of M1 coverage during fresh-start freeze; rerun after M1 catches up")
            if lag > MAX_LAG_SECONDS[timeframe]:
                raise core.M9VContractError(f"live CSV coverage is not synchronized enough for fresh start: {timeframe} lag={lag}s")

        prefix: dict[str, Any] = {}
        state_at_start: dict[str, Any] = {}
        for timeframe, filename in contract["data"]["live_file_map"].items():
            path = args.data_root / str(filename)
            prefix[timeframe] = core.prefix_fingerprint(path, start)
            if timeframe in ("M5", "M15", "H1", "H4"):
                bars = core.m9p.load_bars(path)
                _, audit = core.replay_episodes(bars, timeframe, start)
                state_at_start[timeframe] = {
                    "state_at_start": audit["state_at_start"],
                    "inherited_active_primary_time": audit["inherited_active_primary_time"],
                }

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        runtime = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": core.STAGE,
            "runtime_status": "FROZEN_FRESH_START",
            "created_at_utc": now,
            "prospective_start_server_time": core.fmt_time(start),
            "contract_sha256": contract_sha,
            "contract_path": str(args.contract),
            "data_root": str(args.data_root),
            "initial_live_snapshot": after,
            "prefix_fingerprints": prefix,
            "state_at_start": state_at_start,
            "pre_start_rows_used_for_state_only": True,
            "pre_start_primary_candidate_eligibility": False,
            "historical_backfill_allowed": False,
            "reset_allowed": False,
            "audit_only": True,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "entry_gate_enabled": False,
        }
        atomic_write_json(args.runtime_manifest, runtime)
        receipt = {
            "status": "PASS",
            "stage": "M9V_FRESH_START_INITIALIZATION_AUDIT_ONLY",
            "created_at_utc": now,
            "prospective_start_server_time": runtime["prospective_start_server_time"],
            "runtime_manifest": str(args.runtime_manifest),
            "contract_sha256": contract_sha,
            "state_at_start": state_at_start,
            "historical_backfill_allowed": False,
            "reset_allowed": False,
            "audit_only": True,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        }
        atomic_write_json(args.receipt, receipt)
        print("[M9V INIT PASS] fresh GOLD prospective start frozen")
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"[M9V INIT FAIL_CLOSED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No new M9V start was frozen or replaced.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
