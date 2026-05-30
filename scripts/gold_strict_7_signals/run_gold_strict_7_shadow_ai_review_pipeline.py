#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD strict7 shadow-only AI review pipeline.

Reads shadow strict7 signals, settles virtual TP/SL outcomes from M1 candles,
then reuses the existing trade AI review pipeline pieces. This script never
sends MT5 orders and never edits strategy rules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from trade_ai_review_utils import (  # noqa: E402
    canonical_trade_id,
    classify_outcome,
    clean_float,
    clean_str,
    normalize_direction,
    normalize_ohlcv_columns,
    parse_time_any,
    profit_factor_from_r,
    profit_r_from_prices,
    read_csv,
    read_jsonl,
    stop_distance,
    take_distance,
    write_csv,
    write_json,
    write_jsonl,
)

DEFAULT_MQL5_FILES_DIR = Path("C:/Users/regen/AppData/Roaming/MetaQuotes/Terminal/2FA8A7E69CED7DC259B1AD86A247F675/MQL5/Files")
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review_shadow_gold_strict_7")
DEFAULT_SHADOW_LEDGER = Path("data/runtime_state/gold/strict_7/gold_strict7_shadow_signal_ledger.csv")
SCHEMA_VERSION = "gold_strict_7_shadow_ai_review_pipeline_v1"
RESOLVED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN", "SMALL_WIN", "SMALL_LOSS"}


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


def exists(path: str | Path) -> bool:
    return Path(wpath(path)).exists()


def mkdirp(path: str | Path) -> None:
    Path(wpath(path)).mkdir(parents=True, exist_ok=True)


def write_text(path: str | Path, text: str) -> None:
    mkdirp(Path(path).parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def stable_hash(text: str, n: int = 20) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n]


def cmd_run(label: str, cmd: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - t0, 3)
    ok = proc.returncode == 0 or allow_failure
    print(f"[STEP] {label} returncode={proc.returncode} elapsed_seconds={elapsed} ok={ok}", flush=True)
    return {"label": label, "cmd": cmd, "returncode": int(proc.returncode), "elapsed_seconds": elapsed, "allow_failure": bool(allow_failure), "ok": bool(ok)}


def read_json(path: Path) -> dict[str, Any]:
    try:
        with open(wpath(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def csv_len(path: Path) -> int:
    if not exists(path):
        return 0
    try:
        return int(len(pd.read_csv(wpath(path), encoding="utf-8-sig")))
    except Exception:
        return 0


def csv_path(root: Path, explicit: str, filename: str) -> str:
    return explicit if explicit else str(root / filename)


def opt_existing(path_text: str) -> str:
    return path_text if path_text and exists(Path(path_text)) else ""


def row_value(row: pd.Series, names: list[str], default: Any = "") -> Any:
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
        parsed = clean_float(row_value(row, [name], ""))
        if parsed is not None:
            return parsed
    return None


def load_ohlcv(path: str) -> pd.DataFrame:
    if not path or not exists(path):
        return pd.DataFrame()
    return normalize_ohlcv_columns(read_csv(path))


def settle_from_m1(m1: pd.DataFrame, direction: str, entry_time: pd.Timestamp | None, entry: float | None, sl: float | None, tp: float | None, args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {
        "virtual_status": "NO_M1_PATH" if m1.empty else "UNRESOLVED",
        "outcome": "UNKNOWN",
        "close_reason": "UNKNOWN",
        "close_time": "",
        "close_price": None,
        "profit_r": None,
        "holding_minutes": None,
        "same_m1_both_hit": False,
        "mfe_points": None,
        "mae_points": None,
        "mfe_r": None,
        "mae_r": None,
        "result_source": "M1_FIRST_TOUCH",
    }
    direction = normalize_direction(direction)
    if m1.empty:
        return out
    if entry_time is None or entry is None or sl is None or tp is None or direction not in {"BUY", "SELL"}:
        out.update({"virtual_status": "INVALID_INPUT", "result_source": "INVALID_INPUT"})
        return out
    sd = stop_distance(direction, entry, sl)
    td = take_distance(direction, entry, tp)
    if sd is None or td is None or sd <= 0 or td <= 0:
        out.update({"virtual_status": "INVALID_TP_SL_DISTANCE", "result_source": "INVALID_TP_SL_DISTANCE"})
        return out

    start = entry_time.floor("min") if args.include_entry_minute else entry_time
    end = entry_time + pd.Timedelta(minutes=int(args.horizon_minutes))
    path = m1[(m1["time"] >= start) & (m1["time"] <= end)].copy()
    if path.empty:
        out.update({"virtual_status": "NO_M1_AFTER_ENTRY", "result_source": "NO_M1_AFTER_ENTRY"})
        return out

    if direction == "BUY":
        favorable = path["high"] - entry
        adverse = path["low"] - entry
        tp_hit = path["high"] >= tp
        sl_hit = path["low"] <= sl
    else:
        favorable = entry - path["low"]
        adverse = entry - path["high"]
        tp_hit = path["low"] <= tp
        sl_hit = path["high"] >= sl

    mfe = clean_float(favorable.max())
    mae = clean_float(adverse.min())
    out["mfe_points"] = mfe
    out["mae_points"] = mae
    out["mfe_r"] = None if mfe is None else mfe / sd
    out["mae_r"] = None if mae is None else mae / sd

    for idx, candle in path.iterrows():
        is_tp = bool(tp_hit.loc[idx])
        is_sl = bool(sl_hit.loc[idx])
        if not is_tp and not is_sl:
            continue
        close_reason = "TP" if is_tp else "SL"
        if is_tp and is_sl:
            close_reason = str(args.inbar_priority).upper()
            out["same_m1_both_hit"] = True
            out["result_source"] = "M1_FIRST_TOUCH_SAME_BAR_PRIORITY"
        close_price = tp if close_reason == "TP" else sl
        profit_r = profit_r_from_prices(direction, entry, sl, close_price)
        out.update({
            "virtual_status": "CLOSED",
            "outcome": classify_outcome(None, profit_r),
            "close_reason": close_reason,
            "close_time": candle["time"].strftime("%Y-%m-%d %H:%M:%S"),
            "close_price": close_price,
            "profit_r": profit_r,
            "holding_minutes": max(0.0, (candle["time"] - entry_time).total_seconds() / 60.0),
        })
        return out

    last = path.iloc[-1]
    close_price = clean_float(last.get("close"))
    out.update({
        "virtual_status": "TIMEOUT",
        "outcome": "UNKNOWN",
        "close_reason": "TIMEOUT",
        "close_time": last["time"].strftime("%Y-%m-%d %H:%M:%S"),
        "close_price": close_price,
        "profit_r": profit_r_from_prices(direction, entry, sl, close_price),
        "holding_minutes": max(0.0, (last["time"] - entry_time).total_seconds() / 60.0),
        "result_source": "M1_TIMEOUT_UNREALIZED_R",
    })
    return out


def normalize_shadow_row(row: pd.Series, m1: pd.DataFrame, args: argparse.Namespace) -> dict[str, Any]:
    entry_time_raw = row_value(row, ["entry_time", "signal_time", "bucket_time", "created_at_local", "created_at", "time"])
    entry_time = parse_time_any(entry_time_raw)
    symbol = clean_str(row_value(row, ["symbol"], "GOLD"), "GOLD")
    broker_symbol = clean_str(row_value(row, ["broker_symbol", "mt5_symbol"], "GOLD#"), "GOLD#")
    strategy_id = clean_str(row_value(row, ["strategy_id", "router_strategy_id", "condition_id", "strategy_key"]))
    direction = normalize_direction(row_value(row, ["direction", "side", "order_type", "signal_direction"]))
    entry = row_float(row, ["entry_price", "entry_price_reference", "order_price", "requested_price", "price"])
    sl = row_float(row, ["sl_price", "stop_loss", "sl"])
    tp = row_float(row, ["tp_price", "take_profit", "tp"])

    raw_key = "|".join([symbol, strategy_id, direction, clean_str(entry_time_raw), str(entry), str(sl), str(tp)])
    order_key = clean_str(row_value(row, ["order_key", "notification_key", "signal_key"])) or "SHADOW|" + stable_hash(raw_key)
    signal_key = clean_str(row_value(row, ["signal_key", "notification_key", "order_key"])) or order_key
    trade_base = {"symbol": symbol, "strategy_id": strategy_id, "direction": direction, "entry_time": "" if entry_time is None else entry_time.strftime("%Y-%m-%d %H:%M:%S")}
    trade_id = clean_str(row_value(row, ["trade_id"])) or "SHADOW_" + stable_hash(canonical_trade_id(trade_base))
    payload_key = clean_str(row_value(row, ["payload_key"])) or f"{trade_id}|AI_REVIEW"

    existing_outcome = clean_str(row_value(row, ["outcome", "virtual_outcome"])).upper()
    existing_profit_r = row_float(row, ["profit_r", "virtual_profit_r"])
    unresolved = existing_outcome not in RESOLVED_OUTCOMES or existing_profit_r is None
    if args.recompute_m1 or unresolved:
        settled = settle_from_m1(m1, direction, entry_time, entry, sl, tp, args)
    else:
        settled = {
            "virtual_status": clean_str(row_value(row, ["virtual_status"], "CLOSED")),
            "outcome": existing_outcome,
            "close_reason": clean_str(row_value(row, ["close_reason", "virtual_close_reason"], "UNKNOWN")),
            "close_time": clean_str(row_value(row, ["close_time", "virtual_close_time"])),
            "close_price": row_float(row, ["close_price", "virtual_close_price"]),
            "profit_r": existing_profit_r,
            "holding_minutes": row_float(row, ["holding_minutes", "virtual_holding_minutes"]),
            "same_m1_both_hit": clean_str(row_value(row, ["virtual_same_m1_both_hit"])).lower() in {"1", "true", "yes"},
            "mfe_points": row_float(row, ["virtual_mfe_points", "m1_mfe_points", "m5_mfe_points"]),
            "mae_points": row_float(row, ["virtual_mae_points", "m1_mae_points", "m5_mae_points"]),
            "mfe_r": row_float(row, ["virtual_mfe_r", "m1_mfe_r", "m5_mfe_r"]),
            "mae_r": row_float(row, ["virtual_mae_r", "m1_mae_r", "m5_mae_r"]),
            "result_source": clean_str(row_value(row, ["virtual_result_source"], "SHADOW_LEDGER_EXISTING_RESULT")),
        }

    outcome = clean_str(settled.get("outcome")).upper() or "UNKNOWN"
    sl_dist = stop_distance(direction, entry, sl)
    tp_dist = take_distance(direction, entry, tp)
    rr = tp_dist / sl_dist if tp_dist is not None and sl_dist is not None and sl_dist > 0 else None
    execution_status = "EXECUTED" if outcome in RESOLVED_OUTCOMES else "SHADOW_OPEN"
    match_status = "MATCHED" if outcome in RESOLVED_OUTCOMES else clean_str(settled.get("virtual_status"), "UNKNOWN")
    return {
        "trade_id": trade_id,
        "order_key": order_key,
        "payload_key": payload_key,
        "signal_key": signal_key,
        "symbol": symbol,
        "broker_symbol": broker_symbol,
        "strategy_key": strategy_id,
        "strategy_id": strategy_id,
        "direction": direction,
        "lot": row_float(row, ["lot", "volume"]),
        "entry_time": "" if entry_time is None else entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        "entry_price": entry,
        "entry_price_reference": entry,
        "sl_price": sl,
        "tp_price": tp,
        "tp_distance": tp_dist,
        "sl_distance": sl_dist,
        "rr": rr,
        "close_time": clean_str(settled.get("close_time")),
        "close_price": clean_float(settled.get("close_price")),
        "profit": None,
        "profit_points": None if settled.get("profit_r") is None or sl_dist is None else clean_float(settled.get("profit_r")) * abs(sl_dist),
        "profit_r": clean_float(settled.get("profit_r")),
        "net_profit": None,
        "outcome": outcome,
        "close_reason": clean_str(settled.get("close_reason"), "UNKNOWN"),
        "holding_minutes": clean_float(settled.get("holding_minutes")),
        "match_status": match_status,
        "match_method": "SHADOW_M1_FIRST_TOUCH",
        "execution_status": execution_status,
        "source": "GOLD_STRICT7_SHADOW",
        "shadow_decision": clean_str(row_value(row, ["decision", "guard_decision"], "SHADOW_ONLY")),
        "shadow_decision_reason": clean_str(row_value(row, ["decision_reason", "guard_reason"], "STRICT7_PAUSED_SHADOW_ONLY")),
        "ai_tag_summary": clean_str(row_value(row, ["ai_tag_summary", "tag_summary"])),
        "ai_tag_hits": clean_str(row_value(row, ["ai_tag_hits", "tag_hits"])),
        "combo_hits": clean_str(row_value(row, ["combo_hits", "ai_combo_hits"])),
        "virtual_status": clean_str(settled.get("virtual_status")),
        "virtual_result_source": clean_str(settled.get("result_source")),
        "virtual_same_m1_both_hit": bool(settled.get("same_m1_both_hit")),
        "virtual_mfe_points": clean_float(settled.get("mfe_points")),
        "virtual_mae_points": clean_float(settled.get("mae_points")),
        "virtual_mfe_r": clean_float(settled.get("mfe_r")),
        "virtual_mae_r": clean_float(settled.get("mae_r")),
    }


def build_strategy_summary(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["strategy_id", "direction", "trades", "wins", "losses", "breakevens", "unknowns", "win_rate", "avg_r", "total_r", "profit_factor", "same_m1_both_hit_rows", "avg_holding_minutes", "m1_timeout_rows"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    work = df.copy()
    work["outcome_upper"] = work["outcome"].fillna("").astype(str).str.upper()
    work["profit_r_num"] = pd.to_numeric(work["profit_r"], errors="coerce")
    rows = []
    for (strategy_id, direction), g in work.groupby(["strategy_id", "direction"], dropna=False):
        outcome = g["outcome_upper"]
        r = g["profit_r_num"].dropna()
        rows.append({
            "strategy_id": strategy_id,
            "direction": direction,
            "trades": int(len(g)),
            "wins": int(outcome.isin(["WIN", "SMALL_WIN"]).sum()),
            "losses": int(outcome.isin(["LOSS", "SMALL_LOSS"]).sum()),
            "breakevens": int((outcome == "BREAKEVEN").sum()),
            "unknowns": int((~outcome.isin(list(RESOLVED_OUTCOMES))).sum()),
            "win_rate": None if len(g) <= 0 else float(outcome.isin(["WIN", "SMALL_WIN"]).sum() / len(g)),
            "avg_r": None if r.empty else float(r.mean()),
            "total_r": None if r.empty else float(r.sum()),
            "profit_factor": profit_factor_from_r(r.tolist()) if not r.empty else None,
            "same_m1_both_hit_rows": int(g.get("virtual_same_m1_both_hit", pd.Series([False] * len(g))).fillna(False).astype(bool).sum()),
            "avg_holding_minutes": clean_float(pd.to_numeric(g.get("holding_minutes", pd.Series(dtype=float)), errors="coerce").mean()),
            "m1_timeout_rows": int((g.get("virtual_status", pd.Series([""] * len(g))).fillna("").astype(str).str.upper() == "TIMEOUT").sum()),
        })
    return pd.DataFrame(rows, columns=cols).sort_values(["win_rate", "avg_r", "trades"], ascending=[True, True, False], na_position="first").reset_index(drop=True)


def write_shadow_outcomes(args: argparse.Namespace, paths: dict[str, Path]) -> dict[str, Any]:
    if not exists(args.shadow_ledger_csv):
        empty = pd.DataFrame()
        write_csv(empty, paths["shadow_outcome_csv"])
        write_csv(empty, paths["reviewable_outcome_csv"])
        write_csv(build_strategy_summary(empty), paths["strategy_summary_csv"])
        summary = {"schema_version": SCHEMA_VERSION, "created_at_utc": utc_now(), "reason": "NO_SHADOW_LEDGER_YET", "rows": 0, "reviewable_rows": 0, "shadow_ledger_csv": str(args.shadow_ledger_csv)}
        write_json(paths["shadow_outcome_json"], summary)
        write_json(paths["strategy_summary_json"], {"schema_version": SCHEMA_VERSION, "created_at_utc": utc_now(), "rows": 0, "reason": "NO_SHADOW_LEDGER_YET"})
        return summary

    shadow = read_csv(args.shadow_ledger_csv)
    m1 = load_ohlcv(args.m1_csv)
    rows = [normalize_shadow_row(row, m1, args) for _, row in shadow.iterrows()]
    out_df = pd.DataFrame(rows)
    if not out_df.empty:
        out_df = out_df.drop_duplicates(subset=["trade_id"], keep="last").sort_values(["entry_time", "strategy_id", "direction"]).reset_index(drop=True)
    write_csv(out_df, paths["shadow_outcome_csv"])

    outcome = out_df.get("outcome", pd.Series([], dtype=str)).fillna("").astype(str).str.upper() if not out_df.empty else pd.Series([], dtype=str)
    reviewable = out_df[outcome.isin(RESOLVED_OUTCOMES)].copy() if not out_df.empty else out_df.copy()
    if args.review_timeouts and not out_df.empty:
        reviewable = out_df[outcome.isin(RESOLVED_OUTCOMES | {"UNKNOWN"})].copy()
    write_csv(reviewable, paths["reviewable_outcome_csv"])

    strategy_summary = build_strategy_summary(out_df)
    write_csv(strategy_summary, paths["strategy_summary_csv"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "reason": "OK",
        "shadow_ledger_csv": str(args.shadow_ledger_csv),
        "m1_csv": str(args.m1_csv),
        "m1_rows": int(len(m1)),
        "horizon_minutes": int(args.horizon_minutes),
        "inbar_priority": args.inbar_priority,
        "include_entry_minute": bool(args.include_entry_minute),
        "rows": int(len(out_df)),
        "reviewable_rows": int(len(reviewable)),
        "outcome_counts": outcome.value_counts(dropna=False).to_dict() if len(outcome) else {},
        "strategy_counts": out_df.get("strategy_id", pd.Series([], dtype=str)).fillna("").astype(str).value_counts(dropna=False).to_dict() if not out_df.empty else {},
    }
    write_json(paths["shadow_outcome_json"], summary)
    write_json(paths["strategy_summary_json"], {"schema_version": SCHEMA_VERSION, "created_at_utc": utc_now(), "rows": int(len(strategy_summary)), "output_csv": str(paths["strategy_summary_csv"]), "strategy_summary": strategy_summary.to_dict(orient="records") if not strategy_summary.empty else []})
    return summary


def payload_id(payload: dict[str, Any]) -> tuple[str, str, str]:
    trade = payload.get("trade", {}) if isinstance(payload.get("trade"), dict) else {}
    compact = payload.get("compact_features", {}) if isinstance(payload.get("compact_features"), dict) else {}
    return clean_str(payload.get("trade_id") or trade.get("trade_id") or compact.get("trade_id")), clean_str(payload.get("order_key") or trade.get("order_key") or compact.get("order_key")), clean_str(payload.get("payload_key") or trade.get("payload_key") or compact.get("payload_key"))


def review_id(review: dict[str, Any]) -> tuple[str, str, str]:
    return clean_str(review.get("trade_id")), clean_str(review.get("order_key")), clean_str(review.get("payload_key"))


def write_pending_payloads(payload_jsonl: Path, review_jsonl: Path, pending_jsonl: Path, max_pending: int) -> dict[str, Any]:
    payloads = read_jsonl(payload_jsonl) if exists(payload_jsonl) else []
    reviews = read_jsonl(review_jsonl) if exists(review_jsonl) else []
    reviewed = {review_id(r) for r in reviews}
    trade_ids = {x[0] for x in reviewed if x[0]}
    order_keys = {x[1] for x in reviewed if x[1]}
    payload_keys = {x[2] for x in reviewed if x[2]}
    pending = []
    for payload in payloads:
        tid, ok, pk = payload_id(payload)
        if (tid, ok, pk) in reviewed or (tid and tid in trade_ids) or (ok and ok in order_keys) or (pk and pk in payload_keys):
            continue
        pending.append(payload)
    if max_pending > 0:
        pending = pending[:max_pending]
    write_jsonl(pending_jsonl, pending)
    return {"payload_rows": int(len(payloads)), "existing_review_rows": int(len(reviews)), "pending_rows": int(len(pending)), "skipped_already_reviewed_rows": int(len(payloads) - len(pending))}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run AI review for GOLD strict7 shadow-only virtual trades.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--shadow-ledger-csv", type=Path, default=DEFAULT_SHADOW_LEDGER)
    p.add_argument("--m1-csv", default="")
    p.add_argument("--m15-csv", default="")
    p.add_argument("--m5-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--d1-csv", default="")
    p.add_argument("--m1-file", default="goldsharp_m1.csv")
    p.add_argument("--m15-file", default="goldsharp_m15.csv")
    p.add_argument("--m5-file", default="goldsharp_m5.csv")
    p.add_argument("--h1-file", default="goldsharp_h1.csv")
    p.add_argument("--h4-file", default="goldsharp_h4.csv")
    p.add_argument("--d1-file", default="goldsharp_d1.csv")
    p.add_argument("--horizon-minutes", type=int, default=1440)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    p.add_argument("--include-entry-minute", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--recompute-m1", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--review-timeouts", action="store_true")
    p.add_argument("--pre-m15-bars", type=int, default=100)
    p.add_argument("--post-m15-bars", type=int, default=20)
    p.add_argument("--pre-m5-bars", type=int, default=100)
    p.add_argument("--post-m5-bars", type=int, default=288)
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--max-pending", type=int, default=0)
    p.add_argument("--min-sample", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-ai-review", action="store_true")
    p.add_argument("--allow-partial-review", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--allow-no-reviewable-trades-success", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    t0 = time.perf_counter()
    mkdirp(args.out_dir)
    args.m1_csv = csv_path(args.mql5_files_dir, args.m1_csv, args.m1_file)
    m15_csv = csv_path(args.mql5_files_dir, args.m15_csv, args.m15_file)
    m5_csv = csv_path(args.mql5_files_dir, args.m5_csv, args.m5_file)
    h1_csv = csv_path(args.mql5_files_dir, args.h1_csv, args.h1_file)
    h4_csv = csv_path(args.mql5_files_dir, args.h4_csv, args.h4_file)
    d1_csv = csv_path(args.mql5_files_dir, args.d1_csv, args.d1_file)
    paths = {
        "shadow_outcome_csv": args.out_dir / "shadow_trade_outcome_ledger.csv",
        "reviewable_outcome_csv": args.out_dir / "shadow_trade_outcome_ledger_reviewable.csv",
        "shadow_outcome_json": args.out_dir / "shadow_trade_outcome_ledger_summary.json",
        "strategy_summary_csv": args.out_dir / "shadow_strategy_summary.csv",
        "strategy_summary_json": args.out_dir / "shadow_strategy_summary.json",
        "snapshot_csv": args.out_dir / "trade_feature_snapshot.csv",
        "snapshot_jsonl": args.out_dir / "trade_feature_snapshot.jsonl",
        "snapshot_json": args.out_dir / "trade_feature_snapshot_summary.json",
        "payload_jsonl": args.out_dir / "trade_ai_review_payloads.jsonl",
        "payload_json": args.out_dir / "trade_ai_review_payloads_summary.json",
        "pending_jsonl": args.out_dir / "trade_ai_review_payloads_pending.jsonl",
        "review_jsonl": args.out_dir / "trade_ai_review_ledger.jsonl",
        "review_json": args.out_dir / "trade_ai_review_run_summary.json",
        "tag_csv": args.out_dir / "trade_ai_tag_summary.csv",
        "tag_json": args.out_dir / "trade_ai_tag_summary.json",
        "summary_json": args.out_dir / "gold_strict_7_shadow_ai_review_pipeline_summary.json",
    }
    for path in paths.values():
        mkdirp(path.parent)

    print("=" * 80, flush=True)
    print("GOLD strict 7 shadow AI review pipeline", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"shadow_ledger_csv={args.shadow_ledger_csv}", flush=True)
    print(f"m1_csv={args.m1_csv}", flush=True)
    print("SAFETY: shadow_only=True mt5_order_send=False strategy_rules_modified=False", flush=True)
    print("=" * 80, flush=True)

    if not exists(args.m1_csv):
        print(f"[WARN] M1 CSV not found. Existing virtual outcomes will be used when present: {args.m1_csv}", flush=True)
    if not exists(m15_csv):
        raise SystemExit(f"M15 CSV not found: {m15_csv}")

    steps: list[dict[str, Any]] = []
    outcome_summary = write_shadow_outcomes(args, paths)
    if outcome_summary.get("reason") == "NO_SHADOW_LEDGER_YET":
        if not exists(paths["review_jsonl"]):
            write_text(paths["review_jsonl"], "")
        summary = {"schema_version": SCHEMA_VERSION, "created_at_utc": utc_now(), "cycle_ok": True, "reason": "NO_SHADOW_LEDGER_YET", "out_dir": str(args.out_dir), "paths": {k: str(v) for k, v in paths.items()}, "key_metrics": {"shadow_rows": 0, "reviewable_outcome_rows": 0, "payload_rows": 0, "pending_rows": 0, "review_rows_final": 0}, "safety": {"shadow_only": True, "mt5_order_send": False, "strategy_rules_modified": False}, "steps": steps, "timing": {"total_seconds": round(time.perf_counter() - t0, 3)}}
        write_json(paths["summary_json"], summary)
        print(json.dumps({"cycle_ok": True, "reason": "NO_SHADOW_LEDGER_YET", "summary_json": str(paths["summary_json"])}, ensure_ascii=False, indent=2), flush=True)
        return 0

    if csv_len(paths["reviewable_outcome_csv"]) <= 0 and args.allow_no_reviewable_trades_success:
        if not exists(paths["review_jsonl"]):
            write_text(paths["review_jsonl"], "")
        summary = {"schema_version": SCHEMA_VERSION, "created_at_utc": utc_now(), "cycle_ok": True, "reason": "NO_REVIEWABLE_SHADOW_TRADE", "out_dir": str(args.out_dir), "paths": {k: str(v) for k, v in paths.items()}, "outcome_summary": outcome_summary, "key_metrics": {"shadow_rows": csv_len(paths["shadow_outcome_csv"]), "reviewable_outcome_rows": 0, "payload_rows": 0, "pending_rows": 0, "review_rows_final": 0}, "safety": {"shadow_only": True, "mt5_order_send": False, "strategy_rules_modified": False}, "steps": steps, "timing": {"total_seconds": round(time.perf_counter() - t0, 3)}}
        write_json(paths["summary_json"], summary)
        print(json.dumps({"cycle_ok": True, "reason": "NO_REVIEWABLE_SHADOW_TRADE", "summary_json": str(paths["summary_json"])}, ensure_ascii=False, indent=2), flush=True)
        return 0

    snapshot_cmd = [sys.executable, str(REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py"), "--trade-outcome-csv", str(paths["reviewable_outcome_csv"]), "--m15-csv", str(m15_csv), "--output-csv", str(paths["snapshot_csv"]), "--output-jsonl", str(paths["snapshot_jsonl"]), "--output-json", str(paths["snapshot_json"]), "--pre-m15-bars", str(args.pre_m15_bars), "--post-m15-bars", str(args.post_m15_bars), "--pre-m5-bars", str(args.pre_m5_bars), "--post-m5-bars", str(args.post_m5_bars)]
    for flag, value in [("--m5-csv", m5_csv), ("--h1-csv", h1_csv), ("--h4-csv", h4_csv), ("--d1-csv", d1_csv)]:
        if opt_existing(value):
            snapshot_cmd.extend([flag, value])
    steps.append(cmd_run("build_trade_feature_snapshots", snapshot_cmd))
    if not steps[-1]["ok"]:
        return 3

    steps.append(cmd_run("build_trade_ai_review_payloads", [sys.executable, str(REPO_ROOT / "scripts" / "build_trade_ai_review_payloads.py"), "--feature-snapshot-jsonl", str(paths["snapshot_jsonl"]), "--output-jsonl", str(paths["payload_jsonl"]), "--output-json", str(paths["payload_json"]), "--max-pre-m15-bars-in-prompt", str(args.pre_m15_bars), "--max-post-m15-bars-in-prompt", str(args.post_m15_bars)]))
    if not steps[-1]["ok"]:
        return 4

    pending = write_pending_payloads(paths["payload_jsonl"], paths["review_jsonl"], paths["pending_jsonl"], int(args.max_pending))
    if not args.skip_ai_review and int(pending["pending_rows"]) > 0:
        review_cmd = [sys.executable, str(REPO_ROOT / "scripts" / "run_trade_ai_review_from_payloads.py"), "--payload-jsonl", str(paths["pending_jsonl"]), "--output-jsonl", str(paths["review_jsonl"]), "--output-json", str(paths["review_json"]), "--model", str(args.model)]
        if args.dry_run:
            review_cmd.append("--dry-run")
        steps.append(cmd_run("run_trade_ai_review_from_pending_payloads", review_cmd, allow_failure=bool(args.allow_partial_review)))
    else:
        if not exists(paths["review_jsonl"]):
            write_text(paths["review_jsonl"], "")
        print("[INFO] AI review skipped because pending_rows=0 or --skip-ai-review", flush=True)

    steps.append(cmd_run("summarize_trade_ai_review_ledger", [sys.executable, str(REPO_ROOT / "scripts" / "summarize_trade_ai_review_ledger.py"), "--trade-outcome-csv", str(paths["reviewable_outcome_csv"]), "--ai-review-jsonl", str(paths["review_jsonl"]), "--output-csv", str(paths["tag_csv"]), "--output-json", str(paths["tag_json"]), "--min-sample", str(args.min_sample)]))
    if not steps[-1]["ok"]:
        return 5

    review_summary = read_json(paths["review_json"])
    tag_summary = read_json(paths["tag_json"])
    final_review_rows = len(read_jsonl(paths["review_jsonl"])) if exists(paths["review_jsonl"]) else 0
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "cycle_ok": bool(all(s.get("ok") for s in steps)),
        "reason": "OK",
        "out_dir": str(args.out_dir),
        "shadow_ledger_csv": str(args.shadow_ledger_csv),
        "m1_csv": str(args.m1_csv),
        "paths": {k: str(v) for k, v in paths.items()},
        "outcome_summary": outcome_summary,
        "pending_summary": pending,
        "key_metrics": {
            "shadow_rows": csv_len(paths["shadow_outcome_csv"]),
            "reviewable_outcome_rows": csv_len(paths["reviewable_outcome_csv"]),
            "strategy_summary_rows": csv_len(paths["strategy_summary_csv"]),
            "feature_snapshot_rows": csv_len(paths["snapshot_csv"]),
            "payload_rows": int(pending.get("payload_rows", 0)),
            "pending_rows": int(pending.get("pending_rows", 0)),
            "skipped_already_reviewed_rows": int(pending.get("skipped_already_reviewed_rows", 0)),
            "review_rows_final": final_review_rows,
            "review_rows_written_this_run": review_summary.get("rows_written", 0),
            "review_error_rows": review_summary.get("error_rows", 0),
            "tag_summary_rows": csv_len(paths["tag_csv"]),
            "should_investigate_rows": tag_summary.get("should_investigate_rows"),
        },
        "safety": {"shadow_only": True, "mt5_order_send": False, "mt5_history_required": False, "m1_virtual_outcome": True, "strategy_rules_modified": False, "ai_hypothesis_only": True},
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - t0, 3)},
    }
    write_json(paths["summary_json"], summary)
    print("=" * 80, flush=True)
    print("GOLD strict 7 shadow AI review pipeline summary", flush=True)
    print(json.dumps({"cycle_ok": summary["cycle_ok"], "reason": summary["reason"], "shadow_rows": summary["key_metrics"]["shadow_rows"], "reviewable_outcome_rows": summary["key_metrics"]["reviewable_outcome_rows"], "payload_rows": summary["key_metrics"]["payload_rows"], "pending_rows": summary["key_metrics"]["pending_rows"], "review_rows_final": summary["key_metrics"]["review_rows_final"], "summary_json": str(paths["summary_json"]), "strategy_summary_csv": str(paths["strategy_summary_csv"]), "tag_summary_csv": str(paths["tag_csv"])}, ensure_ascii=False, indent=2), flush=True)
    return 0 if summary["cycle_ok"] else 6


if __name__ == "__main__":
    raise SystemExit(main())
