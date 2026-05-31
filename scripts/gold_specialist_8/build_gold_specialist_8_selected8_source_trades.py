#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build GOLD specialist 8 selected_8 config and source trade ledger from exploration CSVs only.

This script intentionally does NOT read OHLC files and does NOT call OpenAI / MT5 / Discord.
It is allowed to use only exploration summary CSVs and already-resolved exploration trade CSVs
as the source of truth.

Design principle:
- If exactly 8 selected strategies cannot be identified from source CSV metadata, stop.
- Do not hand-recreate strategy conditions.
- Do not regenerate trades from candles.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SUMMARY_CSVS = [
    Path("data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_recommended_no_weekday_safe_hours.csv"),
    Path("data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_high_pf_no_weekday_safe_hours.csv"),
    Path("data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_low_sl_no_weekday_safe_hours.csv"),
    Path("data/gold_new_signal_candidate_backtest_v9_jst_multiview_specialists_fast/gold_candidate_v9_auto_specialist_candidate_pack_jst_corrected.csv"),
]

SEARCH_ROOTS = [
    Path("data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy"),
    Path("data/gold_new_signal_candidate_backtest_v9_jst_multiview_specialists_fast"),
]

OUT_SELECTED = Path("data/gold_specialist_8/config/selected_8_strategies.csv")
OUT_LEDGER = Path("data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_ledger.csv")
OUT_INVENTORY = Path("data/gold_specialist_8/verification/source_inventory/gold_specialist_8_selected8_source_inventory.json")

# These are audit/display identifiers from the postmortem documents. They are NOT used to
# recreate signal conditions. If the exploration CSV already contains these exact identifiers,
# they can be used as explicit selected rows. Otherwise, source_strategy_id remains the
# exploration CSV identifier.
EXPECTED_AUDIT_IDS = [
    "BUY_H1_DONCH72_ADX18_STRUCT_RR2_MIN50_CAP220",
    "BUY_H1_DONCH72_ADX10_H4ATR_TP055_RR18_MIN50_CAP220",
    "SELL_H1_DONCH36_ADX10_TP150_SL75_JST20_22",
    "SELL_H1_DONCH72_ADX10_TP50_SL25_JST18_22",
    "BUY_H1_DONCH20_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST01_05",
    "BUY_H1_IMPULSE_M15_EMA20_REJECT_ADX10_H1ATR_TP15_RR2_MIN50_CAP220_JST23_04",
    "SELL_H1H4_TREND_M15_EMA34_REJECT_ADX10_H4ATR_TP075_RR2_MIN50_CAP250_JST10_11",
    "SELL_H1H4_TREND_M15_RSI50_RECLAIM_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST23_04",
]

STRATEGY_COLS = [
    "source_strategy_id", "strategy_id", "strategy", "rule_name", "signal_name", "name", "id",
]
DIRECTION_COLS = ["direction", "side", "signal_side", "trade_side"]
BASE_COLS = ["strategy_base", "base", "base_tf", "timeframe", "tf"]
EXIT_COLS = ["exit_model", "exit", "tp_sl_model", "risk_model"]
TRADES_COLS = ["expected_trades", "trades", "trade_count", "count", "n_trades", "total_trades"]
WR_COLS = ["expected_wr", "wr", "win_rate", "winrate"]
PF_COLS = ["expected_pf", "pf", "profit_factor"]
TEST_PF_COLS = ["expected_test_pf", "test_pf", "pf_test", "oos_pf"]
JST_COLS = ["jst_hours", "hours_jst", "entry_hours", "hour_filter", "jst_hour_filter"]
WEEKDAY_COLS = ["weekday_filter", "weekdays", "weekday"]
SAFE_OPEN_COLS = ["safe_open_excluded", "safe_hours", "safe_open", "rollover_excluded"]
SELECT_MARKER_COLS = [
    "selected_8", "is_selected_8", "gold_specialist_8", "specialist_8", "selected", "use_for_ai_review",
]
SELECT_ID_COLS = ["selected_id", "audit_id", "display_strategy_id", "strategy_alias", "implementation_strategy_id"]

ENTRY_TIME_COLS = ["entry_time", "time", "signal_time", "close_time", "bar_time", "entry_bar_time"]
ENTRY_PRICE_COLS = ["entry_price", "price", "close", "entry"]
TP_COLS = ["tp", "take_profit", "tp_price", "target_price"]
SL_COLS = ["sl", "stop_loss", "sl_price", "stop_price"]
OUTCOME_COLS = ["outcome", "result", "trade_result", "label"]
PNL_COLS = ["pnl", "profit", "r", "pnl_r", "rr_result"]

REQUIRED_SELECTED_COLUMNS = [
    "selected_id",
    "source_file",
    "source_strategy_id",
    "strategy_base",
    "exit_model",
    "direction",
    "jst_hours",
    "weekday_filter",
    "safe_open_excluded",
    "expected_trades",
    "expected_wr",
    "expected_pf",
    "expected_test_pf",
    "notes",
]

CANON_LEDGER_COLUMNS = [
    "source_file",
    "selected_id",
    "source_strategy_id",
    "strategy_id",
    "entry_time",
    "direction",
    "entry_price",
    "tp",
    "sl",
    "outcome",
    "pnl",
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


def read_csv_robust(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(wpath(path), encoding=enc)
        except Exception as exc:  # pragma: no cover - diagnostic path
            last_error = exc
    raise RuntimeError(f"failed to read CSV: {path}: {last_error}")


def norm_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def column_map(df: pd.DataFrame) -> dict[str, str]:
    return {norm_col(c): c for c in df.columns}


def first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cmap = column_map(df)
    for cand in candidates:
        key = norm_col(cand)
        if key in cmap:
            return cmap[key]
    return None


def as_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def as_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def as_int(value: Any) -> int | None:
    f = as_float(value)
    if f is None:
        return None
    return int(round(f))


def truthy(value: Any) -> bool:
    text = as_str(value).lower()
    return text in {"1", "true", "yes", "y", "selected", "select", "use", "gold_specialist_8", "specialist_8"}


def infer_direction_from_id(strategy_id: str) -> str:
    sid = strategy_id.upper()
    if sid.startswith("BUY_") or "__BUY" in sid or "_BUY" in sid:
        return "BUY"
    if sid.startswith("SELL_") or "__SELL" in sid or "_SELL" in sid:
        return "SELL"
    return ""


def infer_jst_from_id(strategy_id: str) -> str:
    m = re.search(r"JST(\d{1,2})[_-](\d{1,2})", strategy_id.upper())
    if not m:
        return ""
    return f"{int(m.group(1)):02d}-{int(m.group(2)):02d}"


def infer_exit_model(row: pd.Series, strategy_id: str) -> str:
    explicit = ""
    for col in EXIT_COLS:
        if col in row.index:
            explicit = as_str(row[col])
            if explicit:
                return explicit
    sid = strategy_id.upper()
    tokens = []
    for pat in (r"TP\d+(?:\.\d+)?", r"SL\d+(?:\.\d+)?", r"RR\d+(?:\.\d+)?", r"H1ATR", r"H4ATR", r"STRUCT"):
        for m in re.finditer(pat, sid):
            tokens.append(m.group(0))
    return "+".join(tokens)


def is_trade_like_csv(path: Path, df: pd.DataFrame) -> bool:
    if df.empty:
        return False
    has_strategy = first_col(df, STRATEGY_COLS) is not None
    has_entry = first_col(df, ENTRY_TIME_COLS) is not None
    has_outcome = first_col(df, OUTCOME_COLS) is not None
    return bool(has_strategy and has_entry and has_outcome)


def collect_summary_rows(summary_paths: list[Path]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames = []
    inventory = []
    for path in summary_paths:
        item: dict[str, Any] = {"path": str(path), "exists": path.exists(), "kind": "summary"}
        if not path.exists():
            inventory.append(item)
            continue
        df = read_csv_robust(path)
        item.update({"rows": int(len(df)), "columns": [str(c) for c in df.columns]})
        strategy_col = first_col(df, STRATEGY_COLS)
        item["strategy_col"] = strategy_col
        if strategy_col:
            tmp = df.copy()
            tmp["__source_file"] = str(path)
            tmp["__source_strategy_id"] = tmp[strategy_col].astype(str).str.strip()
            frames.append(tmp)
        inventory.append(item)
    if frames:
        return pd.concat(frames, ignore_index=True), inventory
    return pd.DataFrame(), inventory


def identify_selected8(summary_df: pd.DataFrame, allow_exact_audit_ids: bool = True) -> pd.DataFrame:
    if summary_df.empty:
        raise RuntimeError("No source summary rows were loaded; cannot build selected_8.")

    rows = summary_df.copy()
    selected_mask = pd.Series(False, index=rows.index)

    # Highest-trust path: source CSV explicitly marks rows as selected/specialist_8.
    for col in SELECT_MARKER_COLS:
        real_col = first_col(rows, [col])
        if real_col:
            selected_mask = selected_mask | rows[real_col].map(truthy)

    selected = rows[selected_mask].copy()

    # Secondary safe path: source CSV contains exact audit/implementation ids in an explicit id/alias column.
    # This still does not recreate signal logic; it only selects rows already named by the source data.
    if len(selected) != 8 and allow_exact_audit_ids:
        exact_mask = pd.Series(False, index=rows.index)
        for col in [*STRATEGY_COLS, *SELECT_ID_COLS]:
            real_col = first_col(rows, [col])
            if real_col:
                exact_mask = exact_mask | rows[real_col].astype(str).str.strip().isin(EXPECTED_AUDIT_IDS)
        exact = rows[exact_mask].copy()
        if len(exact.drop_duplicates("__source_strategy_id")) == 8:
            selected = exact.drop_duplicates("__source_strategy_id").copy()

    selected = selected.drop_duplicates("__source_strategy_id").copy()
    if len(selected) != 8:
        sample_cols = [c for c in ["__source_file", "__source_strategy_id"] if c in rows.columns]
        sample = rows[sample_cols].head(30).to_dict(orient="records") if sample_cols else []
        raise RuntimeError(
            "Could not identify exactly 8 selected strategies from exploration CSVs. "
            "This script refuses to guess. Add an explicit selected_8/is_selected_8/gold_specialist_8 marker "
            "or an exact selected_id/audit_id column in the exploration summary CSV. "
            f"identified={len(selected)} sample={sample}"
        )
    return selected


def build_selected_config(selected: pd.DataFrame) -> pd.DataFrame:
    out_rows: list[dict[str, Any]] = []
    for idx, (_, row) in enumerate(selected.iterrows(), start=1):
        source_strategy_id = as_str(row.get("__source_strategy_id"))
        source_file = as_str(row.get("__source_file"))

        direction_col = first_col(selected, DIRECTION_COLS)
        base_col = first_col(selected, BASE_COLS)
        trades_col = first_col(selected, TRADES_COLS)
        wr_col = first_col(selected, WR_COLS)
        pf_col = first_col(selected, PF_COLS)
        test_pf_col = first_col(selected, TEST_PF_COLS)
        jst_col = first_col(selected, JST_COLS)
        weekday_col = first_col(selected, WEEKDAY_COLS)
        safe_col = first_col(selected, SAFE_OPEN_COLS)
        selected_id_col = first_col(selected, SELECT_ID_COLS)

        selected_id = as_str(row.get(selected_id_col)) if selected_id_col else ""
        if not selected_id:
            selected_id = f"GS8_{idx:02d}"

        direction = as_str(row.get(direction_col)) if direction_col else ""
        if not direction:
            direction = infer_direction_from_id(source_strategy_id)

        jst_hours = as_str(row.get(jst_col)) if jst_col else ""
        if not jst_hours:
            jst_hours = infer_jst_from_id(source_strategy_id)

        out_rows.append({
            "selected_id": selected_id,
            "source_file": source_file,
            "source_strategy_id": source_strategy_id,
            "strategy_base": as_str(row.get(base_col)) if base_col else "",
            "exit_model": infer_exit_model(row, source_strategy_id),
            "direction": direction.upper(),
            "jst_hours": jst_hours,
            "weekday_filter": as_str(row.get(weekday_col)) if weekday_col else "",
            "safe_open_excluded": as_str(row.get(safe_col)) if safe_col else "",
            "expected_trades": as_int(row.get(trades_col)) if trades_col else None,
            "expected_wr": as_float(row.get(wr_col)) if wr_col else None,
            "expected_pf": as_float(row.get(pf_col)) if pf_col else None,
            "expected_test_pf": as_float(row.get(test_pf_col)) if test_pf_col else None,
            "notes": "generated from exploration summary CSV only; no OHLC rediscovery",
        })
    out = pd.DataFrame(out_rows, columns=REQUIRED_SELECTED_COLUMNS)
    if out["source_strategy_id"].duplicated().any():
        dupes = out.loc[out["source_strategy_id"].duplicated(), "source_strategy_id"].tolist()
        raise RuntimeError(f"Duplicate source_strategy_id in selected_8: {dupes}")
    if len(out) != 8:
        raise RuntimeError(f"selected_8 row count must be 8, got {len(out)}")
    return out


def find_trade_csvs(search_roots: list[Path], summary_paths: list[Path]) -> tuple[list[Path], list[dict[str, Any]]]:
    summary_set = {p.resolve() for p in summary_paths if p.exists()}
    found: list[Path] = []
    inventory: list[dict[str, Any]] = []
    for root in search_roots:
        if not root.exists():
            inventory.append({"path": str(root), "exists": False, "kind": "trade_search_root"})
            continue
        for path in sorted(root.rglob("*.csv")):
            if path.resolve() in summary_set:
                continue
            item: dict[str, Any] = {"path": str(path), "exists": True, "kind": "csv_candidate"}
            try:
                df_head = read_csv_robust(path).head(5)
                item.update({"columns": [str(c) for c in df_head.columns], "sample_rows_checked": int(len(df_head))})
                if is_trade_like_csv(path, df_head):
                    item["trade_like"] = True
                    found.append(path)
                else:
                    item["trade_like"] = False
            except Exception as exc:  # pragma: no cover - diagnostic path
                item["error"] = str(exc)
            inventory.append(item)
    return found, inventory


def canonicalize_trade_rows(path: Path, df: pd.DataFrame, selected_cfg: pd.DataFrame) -> pd.DataFrame:
    strategy_col = first_col(df, STRATEGY_COLS)
    entry_col = first_col(df, ENTRY_TIME_COLS)
    direction_col = first_col(df, DIRECTION_COLS)
    entry_price_col = first_col(df, ENTRY_PRICE_COLS)
    tp_col = first_col(df, TP_COLS)
    sl_col = first_col(df, SL_COLS)
    outcome_col = first_col(df, OUTCOME_COLS)
    pnl_col = first_col(df, PNL_COLS)
    if not strategy_col or not entry_col or not outcome_col:
        return pd.DataFrame(columns=CANON_LEDGER_COLUMNS)

    selected_lookup = selected_cfg.set_index("source_strategy_id").to_dict(orient="index")
    selected_ids = set(selected_lookup.keys())
    mask = df[strategy_col].astype(str).str.strip().isin(selected_ids)
    if not mask.any():
        return pd.DataFrame(columns=CANON_LEDGER_COLUMNS)

    part = df.loc[mask].copy()
    rows = []
    for _, row in part.iterrows():
        sid = as_str(row.get(strategy_col))
        cfg = selected_lookup.get(sid, {})
        direction = as_str(row.get(direction_col)) if direction_col else ""
        if not direction:
            direction = as_str(cfg.get("direction")) or infer_direction_from_id(sid)
        rows.append({
            "source_file": str(path),
            "selected_id": cfg.get("selected_id", ""),
            "source_strategy_id": sid,
            "strategy_id": sid,
            "entry_time": as_str(row.get(entry_col)),
            "direction": direction.upper(),
            "entry_price": as_float(row.get(entry_price_col)) if entry_price_col else None,
            "tp": as_float(row.get(tp_col)) if tp_col else None,
            "sl": as_float(row.get(sl_col)) if sl_col else None,
            "outcome": as_str(row.get(outcome_col)),
            "pnl": as_float(row.get(pnl_col)) if pnl_col else None,
        })
    return pd.DataFrame(rows, columns=CANON_LEDGER_COLUMNS)


def build_source_ledger(trade_paths: list[Path], selected_cfg: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for path in trade_paths:
        df = read_csv_robust(path)
        canon = canonicalize_trade_rows(path, df, selected_cfg)
        if not canon.empty:
            frames.append(canon)
    if not frames:
        raise RuntimeError("No exploration source trade rows found for selected_8 strategies.")
    ledger = pd.concat(frames, ignore_index=True)
    # Drop exact duplicate rows that can appear when the same trade CSV was exported under several names.
    ledger = ledger.drop_duplicates(["source_strategy_id", "entry_time", "direction", "tp", "sl", "outcome"]).copy()
    ledger = ledger.sort_values(["source_strategy_id", "entry_time"], kind="mergesort").reset_index(drop=True)
    return ledger


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(wpath(path), index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build GOLD specialist 8 selected_8 source trade ledger from exploration CSVs only.")
    p.add_argument("--summary-csv", action="append", type=Path, default=None, help="Exploration summary CSV. Can be repeated.")
    p.add_argument("--search-root", action="append", type=Path, default=None, help="Directory to search for resolved exploration trade CSVs. Can be repeated.")
    p.add_argument("--selected-out", type=Path, default=OUT_SELECTED)
    p.add_argument("--ledger-out", type=Path, default=OUT_LEDGER)
    p.add_argument("--inventory-out", type=Path, default=OUT_INVENTORY)
    p.add_argument("--allow-exact-audit-ids", action="store_true", default=True)
    p.add_argument("--no-exact-audit-ids", action="store_false", dest="allow_exact_audit_ids")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    summary_paths = args.summary_csv if args.summary_csv else SUMMARY_CSVS
    search_roots = args.search_root if args.search_root else SEARCH_ROOTS

    summary_df, summary_inventory = collect_summary_rows(summary_paths)
    trade_paths, trade_inventory = find_trade_csvs(search_roots, summary_paths)

    inventory: dict[str, Any] = {
        "script": Path(__file__).as_posix(),
        "ai_api_calls": 0,
        "mt5_order_sends": 0,
        "discord_sends": 0,
        "ohlc_rediscovery": False,
        "summary_inventory": summary_inventory,
        "trade_inventory": trade_inventory,
        "trade_like_csvs": [str(p) for p in trade_paths],
    }

    try:
        selected_rows = identify_selected8(summary_df, allow_exact_audit_ids=args.allow_exact_audit_ids)
        selected_cfg = build_selected_config(selected_rows)
        ledger = build_source_ledger(trade_paths, selected_cfg)

        write_csv(args.selected_out, selected_cfg)
        write_csv(args.ledger_out, ledger)

        inventory.update({
            "selected_out": str(args.selected_out),
            "ledger_out": str(args.ledger_out),
            "selected_rows": int(len(selected_cfg)),
            "source_rows": int(len(ledger)),
            "selected_strategy_ids": selected_cfg["source_strategy_id"].astype(str).tolist(),
            "source_strategy_counts": {str(k): int(v) for k, v in ledger["source_strategy_id"].value_counts().to_dict().items()},
            "ok": True,
        })
        write_json(args.inventory_out, inventory)
    except Exception as exc:
        inventory.update({"ok": False, "error": str(exc)})
        write_json(args.inventory_out, inventory)
        print("=" * 80)
        print("GOLD specialist 8 selected_8 source build - STOPPED - NO API")
        print("=" * 80)
        print(str(exc))
        print(f"inventory json: {args.inventory_out}")
        return 2

    print("=" * 80)
    print("GOLD specialist 8 selected_8 source build - OK - NO API")
    print("=" * 80)
    print(f"selected rows : {len(selected_cfg)}")
    print(f"source rows   : {len(ledger)}")
    print(f"selected csv  : {args.selected_out}")
    print(f"ledger csv    : {args.ledger_out}")
    print(f"inventory json: {args.inventory_out}")
    print("strategy counts:")
    for sid, count in ledger["source_strategy_id"].value_counts().items():
        print(f"  {int(count):6d}  {sid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
