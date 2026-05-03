from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_abc_v1_backtest_trades.csv"
DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_RULE_SUMMARY_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_abc_v1_improvement_rule_summary.csv"
DEFAULT_HOUR_SUMMARY_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_abc_v1_hour_summary.csv"
DEFAULT_SOURCE_SIDE_HOUR_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_abc_v1_source_side_hour_summary.csv"

RuleFunc = Callable[[pd.DataFrame], pd.Series]

MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 4


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_ohlc(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    required = ["time", "open", "high", "low", "close"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    out = df.copy()
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    out = out.dropna(subset=["time"]).sort_values("time", kind="mergesort").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "spread"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def read_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    required = ["combined_signal_source", "side", "signal_time", "jst_entry_time", "result", "r"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in trades CSV {path}: {missing}")
    out = df.copy()
    out["signal_time"] = pd.to_datetime(out["signal_time"], errors="coerce")
    out["jst_entry_time"] = pd.to_datetime(out["jst_entry_time"], errors="coerce")
    out["jst_entry_hour"] = pd.to_numeric(out.get("jst_entry_hour", out["jst_entry_time"].dt.hour), errors="coerce")
    out["r"] = pd.to_numeric(out["r"], errors="coerce")
    out = out.dropna(subset=["signal_time", "jst_entry_time", "jst_entry_hour", "r"]).copy()
    out["jst_entry_hour"] = out["jst_entry_hour"].astype(int)
    out["combined_signal_source"] = out["combined_signal_source"].astype(str).str.strip()
    out["side"] = out["side"].astype(str).str.upper().str.strip()
    return out.sort_values("jst_entry_time", kind="mergesort").reset_index(drop=True)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    open_ = out["open"]

    out["ema20"] = close.ewm(span=20, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()

    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=1).mean()

    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    out["macd_hist"] = macd_hist
    out["macd_hist_delta"] = macd_hist.diff()
    out["macd_hist_delta_3"] = macd_hist - macd_hist.shift(3)

    out["ema_alignment"] = "mixed"
    out.loc[(out["ema20"] > out["ema50"]) & (out["ema50"] > out["ema200"]), "ema_alignment"] = "bullish"
    out.loc[(out["ema20"] < out["ema50"]) & (out["ema50"] < out["ema200"]), "ema_alignment"] = "bearish"

    candle_range = (high - low).replace(0, np.nan)
    out["body_ratio"] = (close - open_).abs() / candle_range
    out["upper_wick_ratio"] = (high - pd.concat([open_, close], axis=1).max(axis=1)) / candle_range
    out["lower_wick_ratio"] = (pd.concat([open_, close], axis=1).min(axis=1) - low) / candle_range
    out["close_change_3_atr"] = (close - close.shift(3)) / out["atr14"].replace(0, np.nan)
    out["close_ema20_gap_atr"] = (close - out["ema20"]) / out["atr14"].replace(0, np.nan)
    out["range20_atr"] = (high.rolling(20, min_periods=1).max() - low.rolling(20, min_periods=1).min()) / out[
        "atr14"
    ].replace(0, np.nan)
    return out


def support_flag(value: float, side: str) -> str:
    if pd.isna(value):
        return "unknown"
    if side == "BUY":
        return "yes" if value > 0 else "no" if value < 0 else "flat"
    return "yes" if value < 0 else "no" if value > 0 else "flat"


def enrich_trades_with_market_features(trades: pd.DataFrame, m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    m15_i = add_indicators(m15)
    h1_i = add_indicators(h1)

    m15_cols = [
        "time",
        "ema_alignment",
        "atr14",
        "macd_hist",
        "macd_hist_delta",
        "macd_hist_delta_3",
        "body_ratio",
        "upper_wick_ratio",
        "lower_wick_ratio",
        "close_change_3_atr",
        "close_ema20_gap_atr",
        "range20_atr",
    ]
    h1_cols = [
        "time",
        "ema_alignment",
        "atr14",
        "macd_hist",
        "macd_hist_delta",
        "macd_hist_delta_3",
        "close_change_3_atr",
        "close_ema20_gap_atr",
        "range20_atr",
    ]

    m15_feat = m15_i[[col for col in m15_cols if col in m15_i.columns]].copy()
    m15_feat = m15_feat.rename(columns={col: f"m15_{col}" for col in m15_feat.columns if col != "time"})
    m15_feat = m15_feat.rename(columns={"time": "signal_time"})

    h1_feat = h1_i[[col for col in h1_cols if col in h1_i.columns]].copy()
    h1_feat = h1_feat.rename(columns={col: f"h1_{col}" for col in h1_feat.columns if col != "time"})
    h1_feat = h1_feat.rename(columns={"time": "h1_feature_time"})

    out = pd.merge_asof(
        trades.sort_values("signal_time"),
        m15_feat.sort_values("signal_time"),
        on="signal_time",
        direction="backward",
    )
    out = pd.merge_asof(
        out.sort_values("signal_time"),
        h1_feat.sort_values("h1_feature_time"),
        left_on="signal_time",
        right_on="h1_feature_time",
        direction="backward",
    )

    for prefix in ["m15", "h1"]:
        for col in ["macd_hist", "macd_hist_delta", "macd_hist_delta_3", "close_change_3_atr", "close_ema20_gap_atr"]:
            feature_col = f"{prefix}_{col}"
            if feature_col in out.columns:
                out[f"{feature_col}_supports_side"] = [support_flag(value, side) for value, side in zip(out[feature_col], out["side"])]

    out["side_matches_h1_ema"] = "mixed"
    out.loc[(out["side"] == "BUY") & (out["h1_ema_alignment"] == "bullish"), "side_matches_h1_ema"] = "yes"
    out.loc[(out["side"] == "SELL") & (out["h1_ema_alignment"] == "bearish"), "side_matches_h1_ema"] = "yes"
    out.loc[(out["side"] == "BUY") & (out["h1_ema_alignment"] == "bearish"), "side_matches_h1_ema"] = "no"
    out.loc[(out["side"] == "SELL") & (out["h1_ema_alignment"] == "bullish"), "side_matches_h1_ema"] = "no"

    out["side_matches_m15_ema"] = "mixed"
    out.loc[(out["side"] == "BUY") & (out["m15_ema_alignment"] == "bullish"), "side_matches_m15_ema"] = "yes"
    out.loc[(out["side"] == "SELL") & (out["m15_ema_alignment"] == "bearish"), "side_matches_m15_ema"] = "yes"
    out.loc[(out["side"] == "BUY") & (out["m15_ema_alignment"] == "bearish"), "side_matches_m15_ema"] = "no"
    out.loc[(out["side"] == "SELL") & (out["m15_ema_alignment"] == "bullish"), "side_matches_m15_ema"] = "no"

    return out.sort_values("jst_entry_time", kind="mergesort").reset_index(drop=True)


def profit_factor(r: pd.Series) -> float | None:
    wins = r[r > 0]
    losses = r[r < 0]
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss_abs = float(abs(losses.sum())) if len(losses) else 0.0
    if gross_loss_abs <= 0:
        return None
    return gross_win / gross_loss_abs


def max_consecutive_losses(results: pd.Series) -> int:
    max_streak = 0
    streak = 0
    for value in results.astype(str).str.lower():
        if value == "loss":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def summarize_selection(df: pd.DataFrame, name: str, description: str, mask: pd.Series) -> dict[str, object]:
    selected = df[mask.fillna(False)].copy()
    excluded = df[~mask.fillna(False)].copy()
    r = selected["r"].dropna()
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    total = int(len(r))
    total_r = float(r.sum()) if total else 0.0
    excluded_r = float(excluded["r"].sum()) if len(excluded) else 0.0
    return {
        "rule_name": name,
        "description": description,
        "selected_count": int(len(selected)),
        "excluded_count": int(len(excluded)),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total if total else None,
        "total_r": total_r,
        "avg_r": total_r / total if total else None,
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(selected["result"]) if len(selected) else 0,
        "excluded_total_r": excluded_r,
    }


def group_summary(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for key, group in df.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        r = group["r"]
        row = {
            "trades": int(len(group)),
            "wins": int((r > 0).sum()),
            "losses": int((r < 0).sum()),
            "win_rate": float((r > 0).sum() / len(group)) if len(group) else 0.0,
            "total_r": float(r.sum()) if len(group) else 0.0,
            "avg_r": float(r.mean()) if len(group) else 0.0,
            "pf": profit_factor(r),
            "max_consecutive_losses": max_consecutive_losses(group["result"]),
        }
        for col, value in zip(group_cols, key):
            row[col] = value
        rows.append(row)
    ordered = group_cols + ["trades", "wins", "losses", "win_rate", "total_r", "avg_r", "pf", "max_consecutive_losses"]
    return pd.DataFrame(rows)[ordered].sort_values(group_cols, kind="mergesort")


def build_candidate_rules(df: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
    hour = df["jst_entry_hour"]
    source = df["combined_signal_source"]
    side = df["side"]
    h1_delta = df.get("h1_macd_hist_delta_supports_side", pd.Series("unknown", index=df.index)).eq("yes")
    h1_hist = df.get("h1_macd_hist_supports_side", pd.Series("unknown", index=df.index)).eq("yes")

    bad_hours_core = hour.isin([4, 10, 12, 15, 22])
    bad_hours_wide = hour.isin([4, 10, 12, 14, 15, 20, 22])
    c_buy = source.eq("C") & side.eq("BUY")

    return [
        ("all", "BTC ABC v1 現状そのまま。", pd.Series(True, index=df.index)),
        ("exclude_c_buy", "C BUYだけ除外。BTCではC BUYが弱いか確認。", ~c_buy),
        ("exclude_bad_hours_core", "全体で悪かったJST時間 4,10,12,15,22 を除外。", ~bad_hours_core),
        ("exclude_bad_hours_wide", "全体でマイナスだったJST時間 4,10,12,14,15,20,22 を除外。", ~bad_hours_wide),
        ("h1_macd_delta_supports_side", "H1 MACDヒストグラムの直近変化が売買方向を支持する時だけ採用。", h1_delta),
        ("h1_macd_hist_supports_side", "H1 MACDヒストグラムの符号が売買方向を支持する時だけ採用。", h1_hist),
        (
            "h1_delta_and_exclude_bad_hours_core",
            "H1 MACD変化が方向支持、かつ悪い時間 4,10,12,15,22 を除外。勝率改善の第一候補。",
            h1_delta & ~bad_hours_core,
        ),
        (
            "h1_delta_and_exclude_bad_hours_wide",
            "H1 MACD変化が方向支持、かつマイナス時間 4,10,12,14,15,20,22 を除外。勝率改善重視。",
            h1_delta & ~bad_hours_wide,
        ),
        (
            "h1_delta_exclude_bad_hours_core_and_c_buy",
            "H1 MACD変化支持 + 悪い時間除外 + C BUY除外。さらに絞る検証。",
            h1_delta & ~bad_hours_core & ~c_buy,
        ),
        (
            "source_side_keep_non_c_buy_and_bad_hours_core",
            "C BUY除外 + 悪い時間 4,10,12,15,22 除外。シンプルな実装候補。",
            ~c_buy & ~bad_hours_core,
        ),
    ]


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    if df.empty:
        print("No data.")
    else:
        print(df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze improvement candidates for BTCUSD# ABC v1 backtest.")
    parser.add_argument("--trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--rule-summary-csv", type=Path, default=DEFAULT_RULE_SUMMARY_CSV)
    parser.add_argument("--hour-summary-csv", type=Path, default=DEFAULT_HOUR_SUMMARY_CSV)
    parser.add_argument("--source-side-hour-csv", type=Path, default=DEFAULT_SOURCE_SIDE_HOUR_CSV)
    args = parser.parse_args()

    trades_csv = resolve_path(args.trades_csv)
    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    rule_summary_csv = resolve_path(args.rule_summary_csv)
    hour_summary_csv = resolve_path(args.hour_summary_csv)
    source_side_hour_csv = resolve_path(args.source_side_hour_csv)

    trades = read_trades(trades_csv)
    m15 = read_ohlc(m15_csv)
    h1 = read_ohlc(h1_csv)
    df = enrich_trades_with_market_features(trades, m15, h1)

    rule_rows = [summarize_selection(df, name, description, mask) for name, description, mask in build_candidate_rules(df)]
    rule_summary = pd.DataFrame(rule_rows).sort_values(["total_r", "win_rate"], ascending=[False, False], kind="mergesort")
    hour_summary = group_summary(df, ["jst_entry_hour"])
    source_side_hour_summary = group_summary(df, ["combined_signal_source", "side", "jst_entry_hour"])

    write_csv(rule_summary_csv, rule_summary)
    write_csv(hour_summary_csv, hour_summary)
    write_csv(source_side_hour_csv, source_side_hour_summary)

    print("Trades:", len(trades), trades_csv)
    print("M15 rows:", len(m15), m15_csv, m15["time"].min(), "to", m15["time"].max())
    print("H1 rows:", len(h1), h1_csv, h1["time"].min(), "to", h1["time"].max())
    print("Saved rule summary:", rule_summary_csv)
    print("Saved hour summary:", hour_summary_csv)
    print("Saved source/side/hour summary:", source_side_hour_csv)

    display_cols = [
        "rule_name",
        "selected_count",
        "excluded_count",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_consecutive_losses",
        "excluded_total_r",
    ]
    print_table("BTCUSD# ABC v1 IMPROVEMENT RULE SUMMARY", rule_summary[display_cols])

    print_table(
        "WORST HOURS BY TOTAL_R",
        hour_summary.sort_values("total_r", kind="mergesort").head(10),
    )
    print_table(
        "BEST HOURS BY TOTAL_R",
        hour_summary.sort_values("total_r", ascending=False, kind="mergesort").head(10),
    )

    bad_source_side_hour = source_side_hour_summary[
        (source_side_hour_summary["trades"] >= 5) & (source_side_hour_summary["total_r"] < 0)
    ].sort_values("total_r", kind="mergesort")
    print_table("WORST SOURCE/SIDE/HOUR GROUPS min_trades>=5", bad_source_side_hour.head(20))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
