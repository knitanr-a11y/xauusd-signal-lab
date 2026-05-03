from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import search_btc_mtf_extra_edges as mtf
from build_latest_signal_payload_from_csv import DEFAULT_HISTORY_CSV, DEFAULT_OUT_DIR, build_payload, detect_btc_runner
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_M5_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m5.csv"
DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_H4_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h4.csv"
DEFAULT_OUT_JSON = DEFAULT_OUT_DIR / "latest_btc_mtf_scanned_signal_payload.json"

DEFAULT_EXCLUDE_ENTRY_HOURS = {8, 13, 20, 21}


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def time_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def parse_int_set(value: str) -> set[int]:
    return {int(x.strip()) for x in value.split(",") if x.strip()}


def row_number(row: pd.Series, key: str) -> float:
    value = row.get(key, np.nan)
    try:
        return float(value)
    except Exception:
        return float("nan")


def build_m15_runner_df(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    h1_cols = ["time", "ema_align", "macd_hist", "macd_delta", "macd_delta3", "rsi14", "rci26", "rci52"]
    h1_feat = h1[[c for c in h1_cols if c in h1.columns]].copy()
    h1_feat = h1_feat.rename(columns={c: f"h1_{c}" for c in h1_feat.columns if c != "time"})
    h1_feat = h1_feat.rename(columns={"time": "h1_time"})
    return pd.merge_asof(
        m15.sort_values("time"),
        h1_feat.sort_values("h1_time"),
        left_on="time",
        right_on="h1_time",
        direction="backward",
    ).reset_index(drop=True)


def make_btc_scalp_signal(side: str, *, exclude_entry_hours: set[int]) -> dict[str, Any]:
    return {
        "side": side,
        "signal_model": "BTC_SCALP_H1_M5_REENTRY_FILTERED",
        "strategy_label": "BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8",
        "portfolio_rank": "BTC_SCALP_M5",
        "rr": 2.0,
        "risk_atr": 0.8,
        "base_tf": "M5",
        "ai_review_required": True,
        "ai_review_mode": "standard",
        "ai_risk_profile": "btc_m5_scalp_filtered",
        "lot_hint": "reduced_candidate",
        "exclude_entry_hours": sorted(exclude_entry_hours),
    }


def detect_btc_scalp_m5_reentry_filtered(row: pd.Series, *, exclude_entry_hours: set[int]) -> dict[str, Any] | None:
    entry_hour_value = row.get("entry_hour")
    if pd.isna(entry_hour_value):
        return None
    entry_hour = int(entry_hour_value)
    if entry_hour in exclude_entry_hours:
        return None

    h1_bull = row_number(row, "h1_ema20") > row_number(row, "h1_ema50") and (
        row_number(row, "h1_macd_hist") > 0 or row_number(row, "h1_macd_delta3") > 0
    )
    h1_bear = row_number(row, "h1_ema20") < row_number(row, "h1_ema50") and (
        row_number(row, "h1_macd_hist") < 0 or row_number(row, "h1_macd_delta3") < 0
    )

    m15_ok_buy = row_number(row, "m15_close") >= row_number(row, "m15_ema20") - 0.25 * row_number(row, "m15_atr14") and row_number(row, "m15_macd_delta3") > -0.02
    m15_ok_sell = row_number(row, "m15_close") <= row_number(row, "m15_ema20") + 0.25 * row_number(row, "m15_atr14") and row_number(row, "m15_macd_delta3") < 0.02

    m5_macd_buy = row_number(row, "macd_delta") > 0 and row_number(row, "macd_delta3") > 0
    m5_macd_sell = row_number(row, "macd_delta") < 0 and row_number(row, "macd_delta3") < 0
    m5_rci_buy = row_number(row, "rci9") <= 30 and row_number(row, "rci9_delta") > 0 and row_number(row, "rci26") >= -75
    m5_rci_sell = row_number(row, "rci9") >= -30 and row_number(row, "rci9_delta") < 0 and row_number(row, "rci26") <= 75

    ema8_reclaim_buy = row_number(row, "low") <= row_number(row, "ema8") + 0.30 * row_number(row, "atr14") and row_number(row, "close") > row_number(row, "ema8")
    ema8_reclaim_sell = row_number(row, "high") >= row_number(row, "ema8") - 0.30 * row_number(row, "atr14") and row_number(row, "close") < row_number(row, "ema8")
    not_extended_m5 = abs(row_number(row, "close_change_6_atr")) <= 1.60
    gap_buy = -0.20 <= row_number(row, "close_ema8_gap_atr") <= 0.70
    gap_sell = -0.70 <= row_number(row, "close_ema8_gap_atr") <= 0.20

    if h1_bull and m15_ok_buy and ema8_reclaim_buy and m5_macd_buy and m5_rci_buy and not_extended_m5 and gap_buy:
        return make_btc_scalp_signal("BUY", exclude_entry_hours=exclude_entry_hours)
    if h1_bear and m15_ok_sell and ema8_reclaim_sell and m5_macd_sell and m5_rci_sell and not_extended_m5 and gap_sell:
        return make_btc_scalp_signal("SELL", exclude_entry_hours=exclude_entry_hours)
    return None


def add_entry_hour(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Backtest entered on next bar open, so the filtered hours are entry-hour based.
    out["entry_time_proxy"] = out["time"].shift(-1)
    out["entry_hour"] = out["entry_time_proxy"].dt.hour
    return out


def signal_item(idx: int, row: pd.Series, signal: dict[str, Any], *, source_tf: str) -> dict[str, Any]:
    item = {
        "idx": int(idx),
        "time": time_str(row.get("time")),
        "source_tf": source_tf,
        "strategy_label": signal.get("strategy_label"),
        "signal_model": signal.get("signal_model"),
        "portfolio_rank": signal.get("portfolio_rank"),
        "side": signal.get("side"),
        "rr": signal.get("rr"),
        "risk_atr": signal.get("risk_atr"),
    }
    if source_tf == "M5":
        item["entry_hour"] = None if pd.isna(row.get("entry_hour")) else int(row.get("entry_hour"))
    return item


def build_btc_mtf_payload(row: pd.Series, signal: dict[str, Any] | None, history_csv: Path, *, selection_mode: str, source_tf: str) -> dict[str, Any]:
    payload = build_payload("BTC", row, signal, history_csv, selection_mode=selection_mode)
    payload["payload_type"] = "latest_btc_mtf_csv_signal_check"
    payload["source_tf"] = source_tf
    if signal is None:
        return payload

    current = payload.get("current_signal_snapshot", {})
    current["source_tf"] = source_tf
    if source_tf == "M5":
        current["entry_hour"] = None if pd.isna(row.get("entry_hour")) else int(row.get("entry_hour"))
        current["entry_time_proxy"] = time_str(row.get("entry_time_proxy"))
        current["ai_review_required"] = True
        current["ai_review_mode"] = signal.get("ai_review_mode", "standard")
        current["ai_risk_profile"] = signal.get("ai_risk_profile", "btc_m5_scalp_filtered")
        current["lot_hint"] = signal.get("lot_hint", "reduced_candidate")
        current["exclude_entry_hours"] = signal.get("exclude_entry_hours", [])
    payload["current_signal_snapshot"] = current
    payload["ai_review_required"] = True
    payload["ai_review_status"] = "not_connected_yet"
    payload["discord_priority"] = "normal"
    return payload


def select_latest_signal(
    *,
    m5_ctx: pd.DataFrame,
    m15_runner_df: pd.DataFrame,
    scan_recent_m5_bars: int,
    scan_recent_m15_bars: int,
    bar_offset: int,
    exclude_entry_hours: set[int],
) -> tuple[pd.Series | None, dict[str, Any] | None, str, str, int | None, list[dict[str, Any]]]:
    found: list[tuple[pd.Timestamp, pd.Series, dict[str, Any], str, int]] = []
    preview: list[dict[str, Any]] = []

    m5_end = len(m5_ctx) - 1 - bar_offset
    m5_start = max(300, m5_end - scan_recent_m5_bars + 1)
    for idx in range(m5_start, m5_end + 1):
        row = m5_ctx.iloc[idx]
        signal = detect_btc_scalp_m5_reentry_filtered(row, exclude_entry_hours=exclude_entry_hours)
        if signal is None:
            continue
        t = pd.Timestamp(row.get("time"))
        found.append((t, row, signal, "M5", idx))
        preview.append(signal_item(idx, row, signal, source_tf="M5"))

    m15_end = len(m15_runner_df) - 1 - bar_offset
    m15_start = max(220, m15_end - scan_recent_m15_bars + 1)
    for idx in range(m15_start, m15_end + 1):
        row = m15_runner_df.iloc[idx]
        signal = detect_btc_runner(row)
        if signal is None:
            continue
        t = pd.Timestamp(row.get("time"))
        found.append((t, row, signal, "M15", idx))
        preview.append(signal_item(idx, row, signal, source_tf="M15"))

    preview = sorted(preview, key=lambda x: x.get("time", ""))
    if not found:
        if m5_end >= 0:
            return m5_ctx.iloc[m5_end], None, "no_signal", "M5", int(m5_end), preview
        return None, None, "no_signal", "", None, preview

    # If signals have the same timestamp, prefer BTC_RUNNER over M5 scalp. Otherwise take latest time.
    priority = {"BTC_RUNNER_RR2_RISK1": 1, "BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8": 2}
    found_sorted = sorted(found, key=lambda x: (x[0], -priority.get(str(x[2].get("strategy_label")), 99)))
    t, row, signal, source_tf, idx = found_sorted[-1]
    mode = f"scan_m5_{scan_recent_m5_bars}_m15_{scan_recent_m15_bars}"
    return row, signal, mode, source_tf, int(idx), preview


def main() -> int:
    parser = argparse.ArgumentParser(description="Build latest BTC MTF signal payload from M5/M15/H1/H4 CSV.")
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_M5_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--h4-csv", type=Path, default=DEFAULT_H4_CSV)
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY_CSV)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--scan-recent-m5-bars", type=int, default=3000)
    parser.add_argument("--scan-recent-m15-bars", type=int, default=3000)
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--exclude-entry-hours", default="8,13,20,21")
    args = parser.parse_args()

    m5_csv = resolve_path(args.m5_csv)
    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    h4_csv = resolve_path(args.h4_csv)
    history_csv = resolve_path(args.history_csv)
    out_json = resolve_path(args.out_json)
    exclude_entry_hours = parse_int_set(args.exclude_entry_hours)

    m5 = mtf.add_indicators(read_ohlc_live_csv(m5_csv))
    m15 = mtf.add_indicators(read_ohlc_live_csv(m15_csv))
    h1 = mtf.add_indicators(read_ohlc_live_csv(h1_csv))
    h4 = mtf.add_indicators(read_ohlc_live_csv(h4_csv))

    m5_ctx = mtf.join_context(m5, [(m15, "m15"), (h1, "h1"), (h4, "h4")])
    m5_ctx = add_entry_hour(m5_ctx)
    m15_runner_df = build_m15_runner_df(m15, h1)

    row, signal, selection_mode, source_tf, target_idx, found_preview = select_latest_signal(
        m5_ctx=m5_ctx,
        m15_runner_df=m15_runner_df,
        scan_recent_m5_bars=args.scan_recent_m5_bars,
        scan_recent_m15_bars=args.scan_recent_m15_bars,
        bar_offset=args.bar_offset,
        exclude_entry_hours=exclude_entry_hours,
    )
    if row is None:
        raise ValueError("No rows available after reading CSV files.")

    payload = build_btc_mtf_payload(row, signal, history_csv, selection_mode=selection_mode, source_tf=source_tf or "M5")
    payload["scan_found_count"] = len(found_preview)
    payload["scan_found_preview_last_20"] = found_preview[-20:]
    payload["btc_mtf_config"] = {
        "scan_recent_m5_bars": args.scan_recent_m5_bars,
        "scan_recent_m15_bars": args.scan_recent_m15_bars,
        "exclude_entry_hours": sorted(exclude_entry_hours),
        "m5_rule": "BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8",
        "m5_rr": 2.0,
        "m5_risk_atr": 0.8,
        "m5_max_bars_backtest": 72,
        "m15_rule": "BTC_RUNNER_RR2_RISK1",
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    print("Symbol: BTC")
    print("M5 CSV:", m5_csv)
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("H4 CSV:", h4_csv)
    print("Rows:", "M5", len(m5), "M15", len(m15), "H1", len(h1), "H4", len(h4))
    print("Exclude entry hours:", sorted(exclude_entry_hours))
    print("Selection mode:", selection_mode)
    print("Target source_tf:", source_tf)
    print("Target idx:", target_idx)
    print("Target bar:", row.get("time"))
    print("Signals found in scan:", len(found_preview))
    if found_preview:
        print("Last scan signal:", found_preview[-1])
    print("Signal found:", payload.get("signal_found"))
    if payload.get("signal_found"):
        cur = payload["current_signal_snapshot"]
        print("Signal:", cur.get("strategy_label"), cur.get("side"), "rr", cur.get("rr"), "risk_atr", cur.get("risk_atr"), "source_tf", cur.get("source_tf"))
        if cur.get("entry_hour") is not None:
            print("Entry hour:", cur.get("entry_hour"), "entry_time_proxy", cur.get("entry_time_proxy"))
    print("Saved JSON:", out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
