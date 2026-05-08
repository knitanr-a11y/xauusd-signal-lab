#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Dry-run adapter from GOLD multi-strategy router intents to autotrade previews.

This script reads router-level combined intent files and creates adapter-only
preview files. It intentionally does NOT write to any existing Mochipoyo/demo
/autotrade inputs.

Inputs from router out-dir:
- combined_order_intent_dry_run.jsonl
- combined_close_intent_dry_run.jsonl
- latest_multi_strategy_cycle_result.json
- strategy_status_latest.csv

Outputs in adapter out-dir:
- latest_adapter_result.json
- adapter_cycle_log.csv
- adapter_order_preview.csv
- adapter_order_preview.jsonl
- adapter_close_preview.csv
- adapter_close_preview.jsonl
- adapter_rejects.csv
- adapter_preview_ledger.csv

Safety boundaries:
- No Discord send.
- No MT5 order placement.
- No existing Mochipoyo ledger writes.
- No existing demo/autotrade order-intent writes.
- No mutation of router outputs or strategy outputs.

Validation examples:

    python scripts\run_gold_multi_strategy_autotrade_adapter_dry_run.py ^
      --router-out-dir data\research_results\gold_multi_strategy_dry_run_aggregate_only_time_exit ^
      --out-dir data\research_results\gold_multi_strategy_autotrade_adapter_dry_run_time_exit

Run the same command twice to validate duplicate preview skipping.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_ROUTER_OUT_DIR = Path("data/research_results/gold_multi_strategy_dry_run")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_autotrade_adapter_dry_run")

ORDER_PREVIEW_COLUMNS = [
    "created_at_utc",
    "preview_key",
    "adapter_action",
    "symbol",
    "broker_symbol",
    "side",
    "strategy_id",
    "condition_id",
    "signal_key",
    "rank",
    "entry_type",
    "signal_time",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "risk_price",
    "reward_price",
    "rr",
    "max_hold_hours",
    "base_lot",
    "lot_multiplier",
    "effective_lot",
    "router_strategy_slot",
    "router_strategy_id",
    "router_source_path",
]

CLOSE_PREVIEW_COLUMNS = [
    "created_at_utc",
    "preview_key",
    "adapter_action",
    "symbol",
    "broker_symbol",
    "strategy_id",
    "condition_id",
    "signal_key",
    "close_key",
    "direction",
    "close_side",
    "close_reason",
    "entry_time",
    "entry_price_reference",
    "exit_time_reference",
    "exit_price_reference",
    "realized_r_reference",
    "lot_weighted_r_reference",
    "effective_lot",
    "router_strategy_slot",
    "router_strategy_id",
    "router_source_path",
]

REJECT_COLUMNS = [
    "reject_time_utc",
    "intent_kind",
    "intent_type",
    "strategy_id",
    "condition_id",
    "signal_key",
    "close_key",
    "router_strategy_slot",
    "router_strategy_id",
    "router_source_path",
    "reject_reason",
    "raw_json",
]

LEDGER_COLUMNS = [
    "created_at_utc",
    "preview_key",
    "intent_kind",
    "intent_type",
    "strategy_id",
    "condition_id",
    "signal_key",
    "close_key",
    "adapter_action",
    "router_strategy_slot",
    "router_source_path",
]

CYCLE_LOG_COLUMNS = [
    "adapter_cycle_start_utc",
    "adapter_cycle_end_utc",
    "adapter_ok",
    "router_out_dir",
    "out_dir",
    "order_intents_read",
    "close_intents_read",
    "order_previews_created",
    "close_previews_created",
    "observe_only_skipped",
    "duplicate_signal_skipped",
    "duplicate_previews_skipped",
    "rejects",
    "strict",
    "latest_adapter_result",
    "adapter_order_preview_csv",
    "adapter_close_preview_csv",
    "adapter_rejects_csv",
    "adapter_preview_ledger_csv",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create dry-run autotrade adapter previews from router combined intents.")
    p.add_argument("--router-out-dir", type=Path, default=DEFAULT_ROUTER_OUT_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--allowed-symbol", action="append", default=["GOLD"], help="Allowed source symbol. Can be specified multiple times.")
    p.add_argument("--broker-symbol", type=str, default="", help="Optional broker symbol preview, e.g. GOLD# or XAUUSD. No order is placed.")
    p.add_argument("--strict", action="store_true", help="Return non-zero if any reject exists.")
    p.add_argument("--reset-ledger", action="store_true", help="Delete adapter_preview_ledger.csv before processing.")
    return p.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                rows.append({"_read_error": f"line {line_no} is not a JSON object", "_raw_line": text})
        except Exception as exc:
            rows.append({"_read_error": f"line {line_no}: {exc}", "_raw_line": text})
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns} for row in rows]).to_csv(path, index=False, encoding="utf-8-sig")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


def read_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=LEDGER_COLUMNS)
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame(columns=LEDGER_COLUMNS)
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[LEDGER_COLUMNS].copy()


def existing_preview_keys(ledger_path: Path) -> set[str]:
    ledger = read_ledger(ledger_path)
    if ledger.empty:
        return set()
    return set(ledger["preview_key"].astype(str))


def raw_json_text(intent: dict[str, Any]) -> str:
    try:
        return json.dumps(intent, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(intent)


def reject_row(*, now: str, intent_kind: str, intent: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "reject_time_utc": now,
        "intent_kind": intent_kind,
        "intent_type": intent.get("intent_type", ""),
        "strategy_id": intent.get("strategy_id", intent.get("router_strategy_id", "")),
        "condition_id": intent.get("condition_id", ""),
        "signal_key": intent.get("signal_key", ""),
        "close_key": intent.get("close_key", ""),
        "router_strategy_slot": intent.get("router_strategy_slot", ""),
        "router_strategy_id": intent.get("router_strategy_id", ""),
        "router_source_path": intent.get("router_source_path", ""),
        "reject_reason": reason,
        "raw_json": raw_json_text(intent),
    }


def validate_open_intent(intent: dict[str, Any], allowed_symbols: set[str]) -> list[str]:
    errors: list[str] = []
    if intent.get("_read_error"):
        return [str(intent.get("_read_error"))]
    if not boolish(intent.get("dry_run", False)):
        errors.append("dry_run must be true")
    if str(intent.get("intent_type", "")) != "OPEN_POSITION":
        errors.append("intent_type must be OPEN_POSITION")
    symbol = str(intent.get("symbol", ""))
    if symbol not in allowed_symbols:
        errors.append(f"symbol not allowed: {symbol}")
    strategy_id = str(intent.get("strategy_id", intent.get("router_strategy_id", "")))
    condition_id = str(intent.get("condition_id", ""))
    signal_key = str(intent.get("signal_key", ""))
    if not strategy_id:
        errors.append("strategy_id is required")
    if not condition_id:
        errors.append("condition_id is required")
    if not signal_key:
        errors.append("signal_key is required")
    direction = str(intent.get("direction", ""))
    if direction not in {"BUY", "SELL"}:
        errors.append(f"direction must be BUY or SELL: {direction}")
    entry = safe_float(intent.get("entry_price_reference"))
    sl = safe_float(intent.get("sl_price"))
    tp = safe_float(intent.get("tp_price"))
    risk = safe_float(intent.get("risk_price"))
    rr = safe_float(intent.get("rr"))
    lot_obj = intent.get("lot", {}) if isinstance(intent.get("lot"), dict) else {}
    eff_lot = safe_float(lot_obj.get("effective_lot"))
    if not math.isfinite(entry):
        errors.append("entry_price_reference must be finite")
    if not math.isfinite(sl):
        errors.append("sl_price must be finite")
    if not math.isfinite(tp):
        errors.append("tp_price must be finite")
    if not math.isfinite(risk) or risk <= 0:
        errors.append("risk_price must be > 0")
    if not math.isfinite(rr) or rr <= 0:
        errors.append("rr must be > 0")
    if not math.isfinite(eff_lot) or eff_lot <= 0:
        errors.append("lot.effective_lot must be > 0")
    if direction == "BUY" and all(math.isfinite(v) for v in [entry, sl, tp]):
        if not sl < entry:
            errors.append("BUY requires sl_price < entry_price_reference")
        if not tp > entry:
            errors.append("BUY requires tp_price > entry_price_reference")
    if direction == "SELL" and all(math.isfinite(v) for v in [entry, sl, tp]):
        if not sl > entry:
            errors.append("SELL requires sl_price > entry_price_reference")
        if not tp < entry:
            errors.append("SELL requires tp_price < entry_price_reference")
    return errors


def validate_close_intent(intent: dict[str, Any], allowed_symbols: set[str]) -> list[str]:
    errors: list[str] = []
    if intent.get("_read_error"):
        return [str(intent.get("_read_error"))]
    if not boolish(intent.get("dry_run", False)):
        errors.append("dry_run must be true")
    if str(intent.get("intent_type", "")) != "CLOSE_POSITION":
        errors.append("intent_type must be CLOSE_POSITION")
    symbol = str(intent.get("symbol", ""))
    if symbol not in allowed_symbols:
        errors.append(f"symbol not allowed: {symbol}")
    strategy_id = str(intent.get("strategy_id", intent.get("router_strategy_id", "")))
    condition_id = str(intent.get("condition_id", ""))
    signal_key = str(intent.get("signal_key", ""))
    close_key = str(intent.get("close_key", ""))
    if not strategy_id:
        errors.append("strategy_id is required")
    if not condition_id:
        errors.append("condition_id is required")
    if not signal_key:
        errors.append("signal_key is required")
    if not close_key:
        errors.append("close_key is required")
    direction = str(intent.get("direction", ""))
    close_side = str(intent.get("close_side", ""))
    if direction not in {"BUY", "SELL"}:
        errors.append(f"direction must be BUY or SELL: {direction}")
    if close_side not in {"BUY", "SELL"}:
        errors.append(f"close_side must be BUY or SELL: {close_side}")
    if direction == "BUY" and close_side != "SELL":
        errors.append("BUY source position requires close_side SELL")
    if direction == "SELL" and close_side != "BUY":
        errors.append("SELL source position requires close_side BUY")
    for col in ["entry_price_reference", "exit_price_reference", "realized_r_reference"]:
        if not math.isfinite(safe_float(intent.get(col))):
            errors.append(f"{col} must be finite")
    return errors


def open_preview_key(intent: dict[str, Any]) -> str:
    strategy_id = str(intent.get("strategy_id", intent.get("router_strategy_id", "")))
    return f"{strategy_id}|{intent.get('signal_key', '')}|OPEN_POSITION"


def close_preview_key(intent: dict[str, Any]) -> str:
    strategy_id = str(intent.get("strategy_id", intent.get("router_strategy_id", "")))
    return f"{strategy_id}|{intent.get('close_key', '')}|CLOSE_POSITION"


def build_open_preview(now: str, intent: dict[str, Any], preview_key: str, broker_symbol: str) -> dict[str, Any]:
    lot_obj = intent.get("lot", {}) if isinstance(intent.get("lot"), dict) else {}
    symbol = str(intent.get("symbol", ""))
    return {
        "created_at_utc": now,
        "preview_key": preview_key,
        "adapter_action": "WOULD_OPEN_POSITION_DRY_RUN",
        "symbol": symbol,
        "broker_symbol": broker_symbol or symbol,
        "side": intent.get("direction", ""),
        "strategy_id": intent.get("strategy_id", intent.get("router_strategy_id", "")),
        "condition_id": intent.get("condition_id", ""),
        "signal_key": intent.get("signal_key", ""),
        "rank": intent.get("rank", ""),
        "entry_type": intent.get("entry_type", ""),
        "signal_time": intent.get("signal_time", ""),
        "entry_price_reference": safe_float(intent.get("entry_price_reference")),
        "sl_price": safe_float(intent.get("sl_price")),
        "tp_price": safe_float(intent.get("tp_price")),
        "risk_price": safe_float(intent.get("risk_price")),
        "reward_price": safe_float(intent.get("reward_price")),
        "rr": safe_float(intent.get("rr")),
        "max_hold_hours": safe_float(intent.get("max_hold_hours")),
        "base_lot": safe_float(lot_obj.get("base_lot")),
        "lot_multiplier": safe_float(lot_obj.get("lot_multiplier")),
        "effective_lot": safe_float(lot_obj.get("effective_lot")),
        "router_strategy_slot": intent.get("router_strategy_slot", ""),
        "router_strategy_id": intent.get("router_strategy_id", ""),
        "router_source_path": intent.get("router_source_path", ""),
    }


def build_close_preview(now: str, intent: dict[str, Any], preview_key: str, broker_symbol: str) -> dict[str, Any]:
    symbol = str(intent.get("symbol", ""))
    return {
        "created_at_utc": now,
        "preview_key": preview_key,
        "adapter_action": "WOULD_CLOSE_POSITION_DRY_RUN",
        "symbol": symbol,
        "broker_symbol": broker_symbol or symbol,
        "strategy_id": intent.get("strategy_id", intent.get("router_strategy_id", "")),
        "condition_id": intent.get("condition_id", ""),
        "signal_key": intent.get("signal_key", ""),
        "close_key": intent.get("close_key", ""),
        "direction": intent.get("direction", ""),
        "close_side": intent.get("close_side", ""),
        "close_reason": intent.get("close_reason", ""),
        "entry_time": intent.get("entry_time", ""),
        "entry_price_reference": safe_float(intent.get("entry_price_reference")),
        "exit_time_reference": intent.get("exit_time_reference", ""),
        "exit_price_reference": safe_float(intent.get("exit_price_reference")),
        "realized_r_reference": safe_float(intent.get("realized_r_reference")),
        "lot_weighted_r_reference": safe_float(intent.get("lot_weighted_r_reference")),
        "effective_lot": safe_float(intent.get("effective_lot")),
        "router_strategy_slot": intent.get("router_strategy_slot", ""),
        "router_strategy_id": intent.get("router_strategy_id", ""),
        "router_source_path": intent.get("router_source_path", ""),
    }


def ledger_row(now: str, preview: dict[str, Any], intent_kind: str, intent_type: str) -> dict[str, Any]:
    return {
        "created_at_utc": now,
        "preview_key": preview.get("preview_key", ""),
        "intent_kind": intent_kind,
        "intent_type": intent_type,
        "strategy_id": preview.get("strategy_id", ""),
        "condition_id": preview.get("condition_id", ""),
        "signal_key": preview.get("signal_key", ""),
        "close_key": preview.get("close_key", ""),
        "adapter_action": preview.get("adapter_action", ""),
        "router_strategy_slot": preview.get("router_strategy_slot", ""),
        "router_source_path": preview.get("router_source_path", ""),
    }


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    now = utc_now_text()
    allowed_symbols = {str(s) for s in args.allowed_symbol}
    ledger_path = args.out_dir / "adapter_preview_ledger.csv"
    if args.reset_ledger and ledger_path.exists():
        ledger_path.unlink()
    seen = existing_preview_keys(ledger_path)

    order_intents_path = args.router_out_dir / "combined_order_intent_dry_run.jsonl"
    close_intents_path = args.router_out_dir / "combined_close_intent_dry_run.jsonl"
    router_result_path = args.router_out_dir / "latest_multi_strategy_cycle_result.json"
    router_result = read_json_or_empty(router_result_path)
    order_intents = read_jsonl(order_intents_path)
    close_intents = read_jsonl(close_intents_path)

    print(f"[INFO] router_out_dir={args.router_out_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] order_intents_read={len(order_intents)} close_intents_read={len(close_intents)}")

    order_previews: list[dict[str, Any]] = []
    close_previews: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    observe_only_skipped = 0
    duplicate_signal_skipped = 0
    duplicate_previews_skipped = 0

    for intent in order_intents:
        intent_type = str(intent.get("intent_type", ""))
        if intent_type == "OBSERVE_ONLY":
            observe_only_skipped += 1
            continue
        if intent_type == "DUPLICATE_SKIP":
            duplicate_signal_skipped += 1
            continue
        if intent_type != "OPEN_POSITION":
            rejects.append(reject_row(now=now, intent_kind="ORDER", intent=intent, reason=f"Unsupported order intent_type: {intent_type}"))
            continue
        errors = validate_open_intent(intent, allowed_symbols)
        if errors:
            rejects.append(reject_row(now=now, intent_kind="ORDER", intent=intent, reason="; ".join(errors)))
            continue
        key = open_preview_key(intent)
        if key in seen:
            duplicate_previews_skipped += 1
            continue
        preview = build_open_preview(now, intent, key, args.broker_symbol)
        order_previews.append(preview)
        append_csv_row(ledger_path, ledger_row(now, preview, "ORDER", "OPEN_POSITION"), LEDGER_COLUMNS)
        seen.add(key)

    for intent in close_intents:
        intent_type = str(intent.get("intent_type", ""))
        if intent_type != "CLOSE_POSITION":
            rejects.append(reject_row(now=now, intent_kind="CLOSE", intent=intent, reason=f"Unsupported close intent_type: {intent_type}"))
            continue
        errors = validate_close_intent(intent, allowed_symbols)
        if errors:
            rejects.append(reject_row(now=now, intent_kind="CLOSE", intent=intent, reason="; ".join(errors)))
            continue
        key = close_preview_key(intent)
        if key in seen:
            duplicate_previews_skipped += 1
            continue
        preview = build_close_preview(now, intent, key, args.broker_symbol)
        close_previews.append(preview)
        append_csv_row(ledger_path, ledger_row(now, preview, "CLOSE", "CLOSE_POSITION"), LEDGER_COLUMNS)
        seen.add(key)

    order_preview_csv = args.out_dir / "adapter_order_preview.csv"
    order_preview_jsonl = args.out_dir / "adapter_order_preview.jsonl"
    close_preview_csv = args.out_dir / "adapter_close_preview.csv"
    close_preview_jsonl = args.out_dir / "adapter_close_preview.jsonl"
    rejects_csv = args.out_dir / "adapter_rejects.csv"
    latest_result_path = args.out_dir / "latest_adapter_result.json"
    cycle_log_path = args.out_dir / "adapter_cycle_log.csv"

    write_csv(order_preview_csv, order_previews, ORDER_PREVIEW_COLUMNS)
    write_jsonl(order_preview_jsonl, order_previews)
    write_csv(close_preview_csv, close_previews, CLOSE_PREVIEW_COLUMNS)
    write_jsonl(close_preview_jsonl, close_previews)
    write_csv(rejects_csv, rejects, REJECT_COLUMNS)
    if not ledger_path.exists():
        write_csv(ledger_path, [], LEDGER_COLUMNS)

    adapter_end = utc_now_text()
    adapter_ok = len(rejects) == 0 or not bool(args.strict)
    result = {
        "schema_version": "gold_multi_strategy_autotrade_adapter_dry_run_v1",
        "adapter_cycle_start_utc": now,
        "adapter_cycle_end_utc": adapter_end,
        "adapter_ok": bool(adapter_ok),
        "strict": bool(args.strict),
        "router_out_dir": str(args.router_out_dir),
        "out_dir": str(args.out_dir),
        "router_ok": router_result.get("router_ok", ""),
        "router_mode": router_result.get("router_mode", ""),
        "order_intents_read": len(order_intents),
        "close_intents_read": len(close_intents),
        "order_previews_created": len(order_previews),
        "close_previews_created": len(close_previews),
        "observe_only_skipped": int(observe_only_skipped),
        "duplicate_signal_skipped": int(duplicate_signal_skipped),
        "duplicate_previews_skipped": int(duplicate_previews_skipped),
        "rejects": len(rejects),
        "allowed_symbols": sorted(allowed_symbols),
        "broker_symbol": args.broker_symbol,
        "outputs": {
            "adapter_order_preview_csv": str(order_preview_csv),
            "adapter_order_preview_jsonl": str(order_preview_jsonl),
            "adapter_close_preview_csv": str(close_preview_csv),
            "adapter_close_preview_jsonl": str(close_preview_jsonl),
            "adapter_rejects_csv": str(rejects_csv),
            "adapter_preview_ledger_csv": str(ledger_path),
            "adapter_cycle_log": str(cycle_log_path),
            "latest_adapter_result": str(latest_result_path),
        },
    }
    write_json(latest_result_path, result)
    append_csv_row(cycle_log_path, {
        "adapter_cycle_start_utc": now,
        "adapter_cycle_end_utc": adapter_end,
        "adapter_ok": bool(adapter_ok),
        "router_out_dir": str(args.router_out_dir),
        "out_dir": str(args.out_dir),
        "order_intents_read": len(order_intents),
        "close_intents_read": len(close_intents),
        "order_previews_created": len(order_previews),
        "close_previews_created": len(close_previews),
        "observe_only_skipped": int(observe_only_skipped),
        "duplicate_signal_skipped": int(duplicate_signal_skipped),
        "duplicate_previews_skipped": int(duplicate_previews_skipped),
        "rejects": len(rejects),
        "strict": bool(args.strict),
        "latest_adapter_result": str(latest_result_path),
        "adapter_order_preview_csv": str(order_preview_csv),
        "adapter_close_preview_csv": str(close_preview_csv),
        "adapter_rejects_csv": str(rejects_csv),
        "adapter_preview_ledger_csv": str(ledger_path),
    }, CYCLE_LOG_COLUMNS)

    print("[INFO] autotrade adapter dry-run completed")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if adapter_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
