from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

import btc7_m15_impulse_continuation_candidate as base

CANDIDATE_ID = "BTC9_M15_PREVDAY_BREAKOUT_H1_CLV85_RISK100_R110"
PIP_USD = 10.0
SPREAD_USD = 30.0
RISK_CAP_PIPS = 100.0
MIN_REWARD_PIPS = 50.0
TARGET_R = 1.1
H1_TREND_SEPARATION_ATR = 0.5
CLOSE_LOCATION = 0.85
STOP_ATR_BUFFER = 0.1
DISCOVERY_START = pd.Timestamp("2024-08-01")
TRAIN_END = pd.Timestamp("2025-02-01")
DISCOVERY_END = pd.Timestamp("2025-07-01")
VALIDATION_END = pd.Timestamp("2026-01-01")


def align_previous_day(m15: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    previous = d1[["time", "high", "low"]].copy()
    previous["previous_day_decision_time"] = previous["time"] + pd.Timedelta(days=1)
    previous = previous.rename(
        columns={"high": "previous_day_high", "low": "previous_day_low"}
    ).drop(columns="time")
    return pd.merge_asof(
        m15.sort_values("time"),
        previous.sort_values("previous_day_decision_time"),
        left_on="time",
        right_on="previous_day_decision_time",
        direction="backward",
    )


def add_h1_context(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    frame = base.align_h1(m15, h1)
    separation = (
        frame["ema50_h1"] - frame["ema200_h1"]
    ).abs() / frame["atr14_h1"]
    frame["h1_long"] = (
        (frame["ema50_h1"] > frame["ema200_h1"])
        & (frame["ema200_h1"] > frame["ema200_h1"].shift(4))
        & (separation >= H1_TREND_SEPARATION_ATR)
    )
    frame["h1_short"] = (
        (frame["ema50_h1"] < frame["ema200_h1"])
        & (frame["ema200_h1"] < frame["ema200_h1"].shift(4))
        & (separation >= H1_TREND_SEPARATION_ATR)
    )
    frame["h1_separation_atr"] = separation
    return frame


def generate_plans(
    m15: pd.DataFrame,
    h1: pd.DataFrame,
    d1: pd.DataFrame,
    m5: pd.DataFrame,
) -> pd.DataFrame:
    frame = align_previous_day(add_h1_context(m15, h1), d1)
    candle_range = frame["high"] - frame["low"]
    close_location = (
        frame["close"] - frame["low"]
    ) / candle_range.replace(0.0, np.nan)
    m5_lookup = {timestamp: index for index, timestamp in enumerate(m5["time"])}
    rows: list[dict[str, Any]] = []

    eligible = frame[frame["time"] >= DISCOVERY_START]
    for _, day in eligible.groupby(eligible["time"].dt.floor("D")):
        if day.empty or not np.isfinite(day.iloc[0]["previous_day_high"]):
            continue
        previous_high = float(day.iloc[0]["previous_day_high"])
        previous_low = float(day.iloc[0]["previous_day_low"])
        long_signal = (
            (day["close"] > previous_high)
            & (close_location.loc[day.index] >= CLOSE_LOCATION)
            & day["h1_long"]
        )
        short_signal = (
            (day["close"] < previous_low)
            & (close_location.loc[day.index] <= 1.0 - CLOSE_LOCATION)
            & day["h1_short"]
        )
        hits = np.flatnonzero((long_signal | short_signal).to_numpy())
        if not len(hits):
            continue

        signal_index = day.index[hits[0]]
        row = frame.loc[signal_index]
        direction = "LONG" if bool(long_signal.loc[signal_index]) else "SHORT"
        entry_time = pd.Timestamp(row["time"]) + pd.Timedelta(minutes=15)
        entry_m5_index = m5_lookup.get(entry_time)
        if entry_m5_index is None:
            continue
        entry_bid = float(m5.iloc[entry_m5_index]["open"])
        if direction == "LONG":
            stop_chart = float(row["low"] - STOP_ATR_BUFFER * row["atr14"])
            risk_usd = entry_bid + SPREAD_USD - stop_chart
        else:
            stop_chart = float(row["high"] + STOP_ATR_BUFFER * row["atr14"])
            risk_usd = stop_chart + SPREAD_USD - entry_bid
        risk_pips = risk_usd / PIP_USD
        reward_usd = TARGET_R * risk_usd
        if (
            risk_usd <= 0
            or risk_pips > RISK_CAP_PIPS
            or reward_usd < MIN_REWARD_PIPS * PIP_USD
        ):
            continue
        target_chart = (
            entry_bid + SPREAD_USD + reward_usd
            if direction == "LONG"
            else entry_bid - SPREAD_USD - reward_usd
        )
        rows.append(
            {
                "candidate_id": CANDIDATE_ID,
                "direction": direction,
                "signal_time": pd.Timestamp(row["time"]),
                "entry_time": entry_time,
                "entry_m5_idx": entry_m5_index,
                "entry_bid": entry_bid,
                "stop_chart": stop_chart,
                "target_chart": target_chart,
                "risk_pips": risk_pips,
                "reward_pips": reward_usd / PIP_USD,
                "rr": TARGET_R,
                "previous_day_high": previous_high,
                "previous_day_low": previous_low,
                "close_location": float(close_location.loc[signal_index]),
                "h1_separation_atr": float(row["h1_separation_atr"]),
            }
        )
    return pd.DataFrame(rows)


def period_for_entry(timestamp: pd.Timestamp) -> tuple[str, pd.Timestamp | None]:
    if DISCOVERY_START <= timestamp < TRAIN_END:
        return "TRAIN", TRAIN_END
    if TRAIN_END <= timestamp < DISCOVERY_END:
        return "DEV", DISCOVERY_END
    if DISCOVERY_END <= timestamp < VALIDATION_END:
        return "VALIDATION", VALIDATION_END
    if timestamp >= VALIDATION_END:
        return "POST_2026_ENTRY_ONLY", None
    return "PRE_RESEARCH", None


def simulate(
    m5: pd.DataFrame,
    plan: pd.Series,
    period_end: pd.Timestamp,
) -> dict[str, Any]:
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
        elif period_end is not None:
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


def run(
    m5_path: Path,
    m15_path: Path,
    h1_path: Path,
    d1_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    m5 = base.add_features(base.read_bars(m5_path))
    m15 = base.add_features(base.read_bars(m15_path))
    h1 = base.add_features(base.read_bars(h1_path))
    d1 = base.add_features(base.read_bars(d1_path))
    evaluated = evaluate(m5, generate_plans(m15, h1, d1, m5))
    evaluated.to_csv(output_dir / "btc9_candidate_trade_ledger.csv", index=False)

    summary = []
    for period in ("TRAIN", "DEV", "VALIDATION"):
        summary.append({"period": period, **metrics(evaluated[evaluated["period"] == period])})
    summary.append(
        {
            "period": "DISCOVERY",
            **metrics(evaluated[evaluated["period"].isin(["TRAIN", "DEV"])]),
        }
    )
    summary.append(
        {
            "period": "COMBINED",
            **metrics(
                evaluated[evaluated["period"].isin(["TRAIN", "DEV", "VALIDATION"])]
            ),
        }
    )
    pd.DataFrame(summary).to_csv(output_dir / "btc9_candidate_summary.csv", index=False)
    evaluated[evaluated["period"] == "POST_2026_ENTRY_ONLY"].to_csv(
        output_dir / "btc9_post2026_entry_only.csv",
        index=False,
    )
    contract = {
        "candidate": CANDIDATE_ID,
        "previous_day_levels": "closed D1 high/low known at next 00:00 UTC",
        "h1_trend": "closed H1 EMA50/EMA200, EMA200 four-hour slope, separation at least 0.5 ATR14",
        "signal": "first M15 close per UTC day beyond previous-day high/low in H1 direction, close in outer 15 percent",
        "entry": "next exact M5 open",
        "stop": "signal-bar extreme plus 0.1*M15 ATR14",
        "risk_cap_pips": RISK_CAP_PIPS,
        "target_r": TARGET_R,
        "minimum_reward_pips": MIN_REWARD_PIPS,
        "spread_usd": SPREAD_USD,
        "post2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc9_candidate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"summary": summary, "contract": contract}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m5", required=True)
    parser.add_argument("--m15", required=True)
    parser.add_argument("--h1", required=True)
    parser.add_argument("--d1", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(
        Path(args.m5),
        Path(args.m15),
        Path(args.h1),
        Path(args.d1),
        Path(args.out),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
