#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append GOLD strict7 guarded-demo payloads to the shadow signal ledger.

Purpose:
- Keep strict7 signal generation observable while real/demo MT5 sending is paused.
- Convert generated order payload CSV rows into a persistent shadow ledger.
- Never send MT5 orders. Never call AI. Never edit strategy rules.

Default input search:
  data/runtime_logs/gold_strict_7_guarded_demo_autotrade/**/gold_strict_7_order_payloads.csv

Default output ledger:
  data/runtime_state/gold/strict_7/gold_strict7_shadow_signal_ledger.csv

Default run summary:
  data/verification/gold_strict7_shadow_collect/YYYY/MM/YYYYMMDD_HHMMSS/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "gold_strict7_shadow_ledger_collect_from_guarded_payloads_v1"
DEFAULT_LOGS_ROOT = Path("data/runtime_logs/gold_strict_7_guarded_demo_autotrade")
DEFAULT_PAYLOAD_GLOB = "**/gold_strict_7_order_payloads.csv"
DEFAULT_SHADOW_LEDGER = Path("data/runtime_state/gold/strict_7/gold_strict7_shadow_signal_ledger.csv")
DEFAULT_OUT_ROOT = Path("data/verification/gold_strict7_shadow_collect")

SHADOW_COLUMNS = [
    "shadow_schema_version",
    "collected_at_utc",
    "source_payload_csv",
    "source_payload_mtime_utc",
    "source_row_index",
    "signal_time",
    "created_at",
    "strategy_id",
    "direction",
    "symbol",
    "broker_symbol",
    "lot",
    "entry_price",
    "tp_price",
    "sl_price",
    "tp_distance",
    "sl_distance",
    "rr",
    "decision",
    "decision_reason",
    "order_key",
    "payload_key",
    "signal_key",
    "ai_tag_summary",
    "ai_tag_hits",
    "combo_hits",
    "virtual_status",
    "virtual_outcome",
    "virtual_close_time",
    "virtual_close_price",
    "virtual_r",
    "virtual_result_source",
]


def wpath(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def mkdirp(path: str | Path) -> None:
    Path(wpath(path)).mkdir(parents=True, exist_ok=True)


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def run_stamp_local() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    mkdirp(Path(path).parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    mkdirp(Path(path).parent)
    df.to_csv(wpath(path), index=False, encoding="utf-8-sig")


def read_csv_auto(path: str | Path) -> pd.DataFrame:
    try:
        return pd.read_csv(wpath(path), encoding="utf-8-sig", sep=None, engine="python")
    except Exception:
        return pd.read_csv(wpath(path), encoding="utf-8-sig")


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def clean_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        out = float(value)
    except Exception:
        return None
    if not pd.notna(out):
        return None
    return out


def parse_time_text(value: Any) -> str:
    text = clean_str(value)
    if not text:
        return ""
    ts = pd.to_datetime(text, errors="coerce")
    if pd.isna(ts):
        return text
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def normalize_direction(value: Any) -> str:
    text = clean_str(value).upper()
    if text in {"BUY", "LONG", "0"}:
        return "BUY"
    if text in {"SELL", "SHORT", "1"}:
        return "SELL"
    if "BUY" in text or "LONG" in text:
        return "BUY"
    if "SELL" in text or "SHORT" in text:
        return "SELL"
    return text


def row_get(row: pd.Series, names: list[str], default: Any = "") -> Any:
    lower = {str(c).lower(): str(c) for c in row.index}
    for name in names:
        col = name if name in row.index else lower.get(name.lower())
        if col is None:
            continue
        value = row.get(col, default)
        try:
            if pd.isna(value):
                continue
        except Exception:
            pass
        if clean_str(value) or not isinstance(value, str):
            return value
    return default


def row_float(row: pd.Series, names: list[str]) -> float | None:
    for name in names:
        value = clean_float(row_get(row, [name], ""))
        if value is not None:
            return value
    return None


def side_distance(direction: str, entry: float | None, price: float | None) -> float | None:
    if entry is None or price is None:
        return None
    if direction == "BUY":
        return price - entry
    if direction == "SELL":
        return entry - price
    return None


def stop_distance(direction: str, entry: float | None, sl: float | None) -> float | None:
    if entry is None or sl is None:
        return None
    if direction == "BUY":
        return entry - sl
    if direction == "SELL":
        return sl - entry
    return None


def stable_hash(text: str, n: int = 20) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n]


def split_strategy_from_order_key(order_key: str) -> tuple[str, str, str]:
    parts = order_key.split("|")
    if len(parts) >= 6 and parts[0].upper() in {"ORDER", "SHADOW"}:
        return parts[3], normalize_direction(parts[4]), parse_time_text(parts[5])
    return "", "", ""


def find_payload_csvs(logs_root: Path, pattern: str, max_files: int) -> list[Path]:
    if not Path(wpath(logs_root)).exists():
        return []
    files = [Path(p) for p in Path(wpath(logs_root)).glob(pattern)]
    files = [p for p in files if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:max_files] if max_files > 0 else files


def normalize_payload_row(row: pd.Series, source_csv: Path, source_row_index: int) -> dict[str, Any]:
    order_key = clean_str(row_get(row, ["order_key", "signal_key", "notification_key"]))
    strategy_from_key, direction_from_key, signal_time_from_key = split_strategy_from_order_key(order_key)
    strategy_id = clean_str(row_get(row, ["strategy_id", "router_strategy_id", "condition_id", "strategy_key"]), strategy_from_key)
    direction = normalize_direction(row_get(row, ["direction", "side", "order_type", "signal_direction"], direction_from_key))
    signal_time = parse_time_text(row_get(row, ["signal_time", "entry_time", "time", "bucket_time", "created_at"], signal_time_from_key))
    created_at = parse_time_text(row_get(row, ["created_at", "created_at_local", "payload_created_at"], ""))
    symbol = clean_str(row_get(row, ["symbol"], "GOLD"), "GOLD")
    broker_symbol = clean_str(row_get(row, ["broker_symbol", "mt5_symbol", "symbol_for_mt5"], "GOLD#"), "GOLD#")
    entry = row_float(row, ["entry_price", "price", "order_price", "entry_price_reference", "requested_price"])
    tp = row_float(row, ["tp_price", "tp", "take_profit"])
    sl = row_float(row, ["sl_price", "sl", "stop_loss"])
    lot = row_float(row, ["lot", "volume"])
    payload_key = clean_str(row_get(row, ["payload_key"]))
    signal_key = clean_str(row_get(row, ["signal_key", "notification_key"]), order_key)
    if not order_key:
        raw = "|".join([symbol, strategy_id, direction, signal_time, str(entry), str(tp), str(sl)])
        order_key = "SHADOW|GOLD|STRICT7|" + strategy_id + "|" + direction + "|" + (signal_time or stable_hash(raw, 12))
    if not payload_key:
        payload_key = "SHADOW_PAYLOAD|" + stable_hash(order_key + "|" + str(source_row_index))
    tp_distance = side_distance(direction, entry, tp)
    sl_distance = stop_distance(direction, entry, sl)
    rr = None
    if tp_distance is not None and sl_distance is not None and sl_distance > 0:
        rr = tp_distance / sl_distance
    mtime_utc = datetime.fromtimestamp(source_csv.stat().st_mtime, UTC).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "shadow_schema_version": SCHEMA_VERSION,
        "collected_at_utc": utc_now_text(),
        "source_payload_csv": str(source_csv),
        "source_payload_mtime_utc": mtime_utc,
        "source_row_index": int(source_row_index),
        "signal_time": signal_time,
        "created_at": created_at,
        "strategy_id": strategy_id,
        "direction": direction,
        "symbol": symbol,
        "broker_symbol": broker_symbol,
        "lot": lot,
        "entry_price": entry,
        "tp_price": tp,
        "sl_price": sl,
        "tp_distance": tp_distance,
        "sl_distance": sl_distance,
        "rr": rr,
        "decision": "SHADOW_ONLY_STRICT7_PAUSED",
        "decision_reason": "STRICT7_PAUSED_NO_MT5_SEND_COLLECT_FROM_GUARDED_PAYLOAD",
        "order_key": order_key,
        "payload_key": payload_key,
        "signal_key": signal_key,
        "ai_tag_summary": clean_str(row_get(row, ["ai_tag_summary", "tag_summary"])),
        "ai_tag_hits": clean_str(row_get(row, ["ai_tag_hits", "tag_hits"])),
        "combo_hits": clean_str(row_get(row, ["combo_hits", "ai_combo_hits"])),
        "virtual_status": "PENDING_M1_REVIEW",
        "virtual_outcome": "",
        "virtual_close_time": "",
        "virtual_close_price": None,
        "virtual_r": None,
        "virtual_result_source": "",
    }


def validate_row(row: dict[str, Any]) -> tuple[bool, str]:
    required = ["strategy_id", "direction", "signal_time", "entry_price", "tp_price", "sl_price", "order_key"]
    missing = [name for name in required if row.get(name) in {None, ""}]
    if missing:
        return False, "missing_" + "+".join(missing)
    if row.get("direction") not in {"BUY", "SELL"}:
        return False, "invalid_direction"
    sl_distance = clean_float(row.get("sl_distance"))
    tp_distance = clean_float(row.get("tp_distance"))
    if sl_distance is None or sl_distance <= 0 or tp_distance is None or tp_distance <= 0:
        return False, "invalid_tp_sl_distance"
    return True, "OK"


def dedupe_key(row: pd.Series | dict[str, Any]) -> str:
    getter = row.get
    order_key = clean_str(getter("order_key", ""))
    if order_key:
        return "order_key|" + order_key
    return "fields|" + "|".join([
        clean_str(getter("strategy_id", "")),
        clean_str(getter("direction", "")),
        clean_str(getter("signal_time", "")),
        clean_str(getter("entry_price", "")),
        clean_str(getter("tp_price", "")),
        clean_str(getter("sl_price", "")),
    ])


def load_existing_ledger(path: Path) -> pd.DataFrame:
    if Path(wpath(path)).exists():
        return read_csv_auto(path)
    return pd.DataFrame(columns=SHADOW_COLUMNS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect GOLD strict7 guarded payloads into shadow ledger without MT5 sending.")
    p.add_argument("--logs-root", type=Path, default=DEFAULT_LOGS_ROOT)
    p.add_argument("--payload-glob", default=DEFAULT_PAYLOAD_GLOB)
    p.add_argument("--shadow-ledger-csv", type=Path, default=DEFAULT_SHADOW_LEDGER)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument("--max-files", type=int, default=500)
    p.add_argument("--write-empty-summary", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    stamp = run_stamp_local()
    run_dir = args.out_root / stamp[:4] / stamp[4:6] / stamp
    mkdirp(run_dir)
    summary_json = run_dir / "gold_strict7_shadow_collect_summary.json"
    rejected_csv = run_dir / "gold_strict7_shadow_collect_rejected_rows.csv"
    added_csv = run_dir / "gold_strict7_shadow_collect_added_rows.csv"
    latest_summary = args.out_root / "latest_gold_strict7_shadow_collect_summary.json"
    latest_run_dir = args.out_root / "latest_run_dir.txt"

    payload_files = find_payload_csvs(args.logs_root, args.payload_glob, args.max_files)
    normalized_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    file_reports: list[dict[str, Any]] = []

    for payload_csv in reversed(payload_files):
        try:
            df = read_csv_auto(payload_csv)
        except Exception as exc:
            file_reports.append({"payload_csv": str(payload_csv), "read_ok": False, "error": str(exc), "rows": 0})
            continue
        file_reports.append({"payload_csv": str(payload_csv), "read_ok": True, "rows": int(len(df))})
        for idx, row in df.iterrows():
            out = normalize_payload_row(row, payload_csv, int(idx))
            ok, reason = validate_row(out)
            if ok:
                normalized_rows.append(out)
            else:
                bad = dict(out)
                bad["reject_reason"] = reason
                rejected_rows.append(bad)

    existing = load_existing_ledger(args.shadow_ledger_csv)
    for col in SHADOW_COLUMNS:
        if col not in existing.columns:
            existing[col] = ""
    existing_keys = set(existing.apply(dedupe_key, axis=1).tolist()) if not existing.empty else set()
    added = []
    skipped_duplicate = 0
    for row in normalized_rows:
        key = dedupe_key(row)
        if key in existing_keys:
            skipped_duplicate += 1
            continue
        existing_keys.add(key)
        added.append(row)

    added_df = pd.DataFrame(added, columns=SHADOW_COLUMNS)
    rejected_df = pd.DataFrame(rejected_rows)
    if added:
        combined = pd.concat([existing[SHADOW_COLUMNS], added_df], ignore_index=True)
    else:
        combined = existing[SHADOW_COLUMNS].copy()
    if not combined.empty:
        combined = combined.drop_duplicates(subset=["order_key"], keep="last")
        combined = combined.sort_values(["signal_time", "strategy_id", "direction", "order_key"], na_position="last").reset_index(drop=True)
    write_csv(combined, args.shadow_ledger_csv)
    write_csv(added_df, added_csv)
    write_csv(rejected_df, rejected_csv)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "reason": "OK" if payload_files else "NO_PAYLOAD_FILES_FOUND",
        "logs_root": str(args.logs_root),
        "payload_glob": args.payload_glob,
        "payload_files_scanned": int(len(payload_files)),
        "payload_rows_valid": int(len(normalized_rows)),
        "payload_rows_rejected": int(len(rejected_rows)),
        "existing_ledger_rows_before": int(len(existing)),
        "added_rows": int(len(added)),
        "skipped_duplicate_rows": int(skipped_duplicate),
        "ledger_rows_after": int(len(combined)),
        "shadow_ledger_csv": str(args.shadow_ledger_csv),
        "added_rows_csv": str(added_csv),
        "rejected_rows_csv": str(rejected_csv),
        "run_dir": str(run_dir),
        "file_reports": file_reports,
        "safety": {
            "mt5_order_send": False,
            "ai_calls": False,
            "strategy_rules_modified": False,
            "shadow_only": True,
        },
    }
    write_json(summary_json, summary)
    write_json(latest_summary, summary)
    mkdirp(latest_run_dir.parent)
    with open(wpath(latest_run_dir), "w", encoding="utf-8", newline="") as f:
        f.write(str(run_dir))
    print(json.dumps({
        "cycle_ok": True,
        "reason": summary["reason"],
        "payload_files_scanned": summary["payload_files_scanned"],
        "added_rows": summary["added_rows"],
        "skipped_duplicate_rows": summary["skipped_duplicate_rows"],
        "ledger_rows_after": summary["ledger_rows_after"],
        "shadow_ledger_csv": summary["shadow_ledger_csv"],
        "summary_json": str(summary_json),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
