from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from mt5_indicator_compat import mt5_atr, mt5_ema

PIP_USD = 10.0
SPREAD_USD = 30.0
RISK_CAP_PIPS = 100.0
MIN_REWARD_PIPS = 50.0
MIN_REWARD_USD = MIN_REWARD_PIPS * PIP_USD
TARGET_R = 2.0
TREND_SEPARATION_ATR = 0.5
IMPULSE_ATR_MULTIPLE = 2.0
CLOSE_LOCATION_MIN = 0.85
STOP_ATR_BUFFER = 0.1
DISCOVERY_START = pd.Timestamp("2024-08-01 00:00:00")
DISCOVERY_END = pd.Timestamp("2025-07-01 00:00:00")
VALIDATION_END = pd.Timestamp("2026-01-01 00:00:00")


def read_bars(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["time"] = pd.to_datetime(frame["time"])
    frame = frame.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["ema20"] = mt5_ema(output["close"], 20)
    output["ema50"] = mt5_ema(output["close"], 50)
    output["ema200"] = mt5_ema(output["close"], 200)
    output["atr14"] = mt5_atr(output["high"], output["low"], output["close"], 14)
    return output


def align_h1(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    higher = h1[["time", "ema50", "ema200", "atr14"]].copy()
    higher["h1_decision_time"] = higher["time"] + pd.Timedelta(hours=1)
    higher = higher.drop(columns="time").sort_values("h1_decision_time")
    return pd.merge_asof(
        m15.sort_values("time"),
        higher,
        left_on="time",
        right_on="h1_decision_time",
        direction="backward",
        suffixes=("", "_h1"),
    )


def generate_plans(m15: pd.DataFrame, h1: pd.DataFrame, m5: pd.DataFrame) -> pd.DataFrame:
    frame = align_h1(m15, h1)
    separation = (frame["ema50_h1"] - frame["ema200_h1"]).abs() / frame["atr14_h1"]
    long_trend = (
        (frame["ema50_h1"] > frame["ema200_h1"])
        & (frame["ema200_h1"] > frame["ema200_h1"].shift(4))
        & (separation >= TREND_SEPARATION_ATR)
    )
    short_trend = (
        (frame["ema50_h1"] < frame["ema200_h1"])
        & (frame["ema200_h1"] < frame["ema200_h1"].shift(4))
        & (separation >= TREND_SEPARATION_ATR)
    )
    candle_range = frame["high"] - frame["low"]
    close_location = (frame["close"] - frame["low"]) / candle_range.replace(0.0, np.nan)
    long_signal = (
        long_trend
        & (candle_range >= IMPULSE_ATR_MULTIPLE * frame["atr14"])
        & (close_location >= CLOSE_LOCATION_MIN)
        & (frame["close"] > frame["ema20"])
    )
    short_signal = (
        short_trend
        & (candle_range >= IMPULSE_ATR_MULTIPLE * frame["atr14"])
        & (close_location <= 1.0 - CLOSE_LOCATION_MIN)
        & (frame["close"] < frame["ema20"])
    )
    long_signal &= ~long_signal.shift(1, fill_value=False)
    short_signal &= ~short_signal.shift(1, fill_value=False)

    m5_lookup = {timestamp: index for index, timestamp in enumerate(m5["time"])}
    rows: list[dict[str, Any]] = []
    signal_mask = (long_signal | short_signal) & (frame["time"] >= DISCOVERY_START)
    for index in np.flatnonzero(signal_mask.to_numpy()):
        row = frame.iloc[index]
        entry_time = pd.Timestamp(row["time"]) + pd.Timedelta(minutes=15)
        entry_index = m5_lookup.get(entry_time)
        if entry_index is None:
            continue
        direction = "LONG" if bool(long_signal.iloc[index]) else "SHORT"
        entry_bid = float(m5.iloc[entry_index]["open"])
        if direction == "LONG":
            stop_chart = float(row["low"] - STOP_ATR_BUFFER * row["atr14"])
            risk_usd = entry_bid + SPREAD_USD - stop_chart
            target_chart = entry_bid + SPREAD_USD + TARGET_R * risk_usd
            reward_usd = target_chart - (entry_bid + SPREAD_USD)
        else:
            stop_chart = float(row["high"] + STOP_ATR_BUFFER * row["atr14"])
            risk_usd = stop_chart + SPREAD_USD - entry_bid
            target_chart = entry_bid - SPREAD_USD - TARGET_R * risk_usd
            reward_usd = entry_bid - (target_chart + SPREAD_USD)
        risk_pips = risk_usd / PIP_USD
        if (
            risk_usd <= 0
            or risk_pips > RISK_CAP_PIPS
            or reward_usd < MIN_REWARD_USD
        ):
            continue
        rows.append(
            {
                "direction": direction,
                "signal_time": pd.Timestamp(row["time"]),
                "entry_time": entry_time,
                "entry_m5_idx": entry_index,
                "entry_bid": entry_bid,
                "stop_chart": stop_chart,
                "target_chart": target_chart,
                "risk_pips": risk_pips,
                "reward_pips": reward_usd / PIP_USD,
                "rr": reward_usd / risk_usd,
                "trend_separation_atr": float(separation.iloc[index]),
                "impulse_atr_multiple": float(candle_range.iloc[index] / row["atr14"]),
                "close_location": float(close_location.iloc[index]),
            }
        )
    return pd.DataFrame(rows)


def period_for_entry(timestamp: pd.Timestamp) -> tuple[str, pd.Timestamp | None]:
    if DISCOVERY_START <= timestamp < DISCOVERY_END:
        return "DISCOVERY", DISCOVERY_END
    if DISCOVERY_END <= timestamp < VALIDATION_END:
        return "VALIDATION", VALIDATION_END
    if timestamp >= VALIDATION_END:
        return "POST_2026_ENTRY_ONLY", None
    return "PRE_RESEARCH", None


def simulate(m5: pd.DataFrame, plan: pd.Series, period_end: pd.Timestamp) -> dict[str, Any]:
    for index in range(int(plan["entry_m5_idx"]), len(m5)):
        bar_time = pd.Timestamp(m5.iloc[index]["time"])
        if bar_time >= period_end:
            return {"outcome_status": "BOUNDARY_EXCLUDED"}
        high = float(m5.iloc[index]["high"])
        low = float(m5.iloc[index]["low"])
        if plan["direction"] == "LONG":
            stop_hit = low <= plan["stop_chart"]
            target_hit = high >= plan["target_chart"]
        else:
            stop_hit = high >= plan["stop_chart"]
            target_hit = low <= plan["target_chart"]
        if stop_hit:
            return {
                "outcome_status": "RESOLVED",
                "exit_time": bar_time + pd.Timedelta(minutes=5),
                "exit_reason": "SL",
                "pnl_pips": -float(plan["risk_pips"]),
            }
        if target_hit:
            return {
                "outcome_status": "RESOLVED",
                "exit_time": bar_time + pd.Timedelta(minutes=5),
                "exit_reason": "TP",
                "pnl_pips": float(plan["reward_pips"]),
            }
    return {"outcome_status": "OPEN_AT_DATA_END"}


def evaluate(m5: pd.DataFrame, plans: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, plan in plans.iterrows():
        row = plan.to_dict()
        period, period_end = period_for_entry(pd.Timestamp(plan["entry_time"]))
        row["period"] = period
        if period == "POST_2026_ENTRY_ONLY":
            row["outcome_status"] = "NOT_EVALUATED"
        elif period in ("DISCOVERY", "VALIDATION") and period_end is not None:
            row.update(simulate(m5, plan, period_end))
        else:
            row["outcome_status"] = "NOT_IN_RESEARCH"
        rows.append(row)
    return pd.DataFrame(rows)


def metrics(frame: pd.DataFrame) -> dict[str, Any]:
    resolved = frame[frame["outcome_status"] == "RESOLVED"].sort_values("entry_time")
    if resolved.empty:
        return {"trades": 0}
    gross_profit = float(resolved.loc[resolved["pnl_pips"] > 0, "pnl_pips"].sum())
    gross_loss = float(-resolved.loc[resolved["pnl_pips"] < 0, "pnl_pips"].sum())
    equity = resolved["pnl_pips"].cumsum()
    return {
        "trades": len(resolved),
        "wins": int((resolved["pnl_pips"] > 0).sum()),
        "losses": int((resolved["pnl_pips"] < 0).sum()),
        "win_rate_pct": float((resolved["pnl_pips"] > 0).mean() * 100.0),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else math.inf,
        "total_pips": float(resolved["pnl_pips"].sum()),
        "average_pips": float(resolved["pnl_pips"].mean()),
        "max_drawdown_pips": float((equity.cummax() - equity).max()),
    }


def run(m5_path: Path, m15_path: Path, h1_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    m5 = add_features(read_bars(m5_path))
    m15 = add_features(read_bars(m15_path))
    h1 = add_features(read_bars(h1_path))
    evaluated = evaluate(m5, generate_plans(m15, h1, m5))
    evaluated.to_csv(output_dir / "btc7_candidate_trade_ledger.csv", index=False)
    summary = [
        {"period": "DISCOVERY", **metrics(evaluated[evaluated["period"] == "DISCOVERY"])},
        {"period": "VALIDATION", **metrics(evaluated[evaluated["period"] == "VALIDATION"])},
        {
            "period": "COMBINED",
            **metrics(evaluated[evaluated["period"].isin(["DISCOVERY", "VALIDATION"])]),
        },
    ]
    pd.DataFrame(summary).to_csv(output_dir / "btc7_candidate_summary.csv", index=False)
    contract = {
        "candidate": "BTC7_M15_IMPULSE_CONTINUATION_RISK100",
        "spread_usd": SPREAD_USD,
        "risk_cap_pips": RISK_CAP_PIPS,
        "target_r": TARGET_R,
        "post2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc7_candidate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"summary": summary, "contract": contract}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m5", required=True)
    parser.add_argument("--m15", required=True)
    parser.add_argument("--h1", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(Path(args.m5), Path(args.m15), Path(args.h1), Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
