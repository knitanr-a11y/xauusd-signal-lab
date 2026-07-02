from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

import btc7_m15_impulse_continuation_candidate as base

CANDIDATE_ID = "BTC10_M15_EMA20_PULLBACK_RECLAIM_H1_TREND_R080"
RECENT_STOP_BARS = 8
H1_TREND_SEPARATION_ATR_MIN = 0.5
CLOSE_LOCATION_MIN = 0.6
TARGET_R = 0.8
RISK_CAP_PIPS = 120.0
MIN_REWARD_PIPS = 50.0
STOP_ATR_BUFFER = 0.1
COOLDOWN_M15_BARS = 12


def generate_plans(m15: pd.DataFrame, h1: pd.DataFrame, m5: pd.DataFrame) -> pd.DataFrame:
    frame = base.align_h1(m15, h1)
    separation = (frame["ema50_h1"] - frame["ema200_h1"]).abs() / frame["atr14_h1"]
    long_trend = (
        (frame["ema50_h1"] > frame["ema200_h1"])
        & (frame["ema200_h1"] > frame["ema200_h1"].shift(4))
        & (separation >= H1_TREND_SEPARATION_ATR_MIN)
    )
    short_trend = (
        (frame["ema50_h1"] < frame["ema200_h1"])
        & (frame["ema200_h1"] < frame["ema200_h1"].shift(4))
        & (separation >= H1_TREND_SEPARATION_ATR_MIN)
    )

    candle_range = frame["high"] - frame["low"]
    close_location = (frame["close"] - frame["low"]) / candle_range.replace(0.0, np.nan)

    long_signal = (
        long_trend
        & (frame["close"].shift(1) <= frame["ema20"].shift(1))
        & (frame["close"] > frame["ema20"])
        & (frame["close"] > frame["ema50"])
        & (close_location >= CLOSE_LOCATION_MIN)
    )
    short_signal = (
        short_trend
        & (frame["close"].shift(1) >= frame["ema20"].shift(1))
        & (frame["close"] < frame["ema20"])
        & (frame["close"] < frame["ema50"])
        & (close_location <= 1.0 - CLOSE_LOCATION_MIN)
    )

    recent_low = frame["low"].rolling(RECENT_STOP_BARS).min()
    recent_high = frame["high"].rolling(RECENT_STOP_BARS).max()
    m5_lookup = {timestamp: index for index, timestamp in enumerate(m5["time"])}

    rows: list[dict[str, Any]] = []
    last_long_index = -10**9
    last_short_index = -10**9
    signal_mask = (long_signal | short_signal) & (frame["time"] >= base.DISCOVERY_START)

    for index in np.flatnonzero(signal_mask.to_numpy()):
        direction = "LONG" if bool(long_signal.iloc[index]) else "SHORT"
        if direction == "LONG":
            if index - last_long_index < COOLDOWN_M15_BARS:
                continue
            last_long_index = index
        else:
            if index - last_short_index < COOLDOWN_M15_BARS:
                continue
            last_short_index = index

        row = frame.iloc[index]
        entry_time = pd.Timestamp(row["time"]) + pd.Timedelta(minutes=15)
        entry_index = m5_lookup.get(entry_time)
        if entry_index is None:
            continue
        entry_bid = float(m5.iloc[entry_index]["open"])

        if direction == "LONG":
            stop_chart = float(recent_low.iloc[index] - STOP_ATR_BUFFER * row["atr14"])
            risk_usd = entry_bid + base.SPREAD_USD - stop_chart
            target_chart = entry_bid + base.SPREAD_USD + TARGET_R * risk_usd
        else:
            stop_chart = float(recent_high.iloc[index] + STOP_ATR_BUFFER * row["atr14"])
            risk_usd = stop_chart + base.SPREAD_USD - entry_bid
            target_chart = entry_bid - base.SPREAD_USD - TARGET_R * risk_usd

        risk_pips = risk_usd / base.PIP_USD
        reward_pips = TARGET_R * risk_pips
        if (
            not np.isfinite(risk_pips)
            or risk_pips <= 0.0
            or risk_pips > RISK_CAP_PIPS
            or reward_pips < MIN_REWARD_PIPS
        ):
            continue

        rows.append(
            {
                "candidate_id": CANDIDATE_ID,
                "direction": direction,
                "signal_time": pd.Timestamp(row["time"]),
                "entry_time": entry_time,
                "entry_m5_idx": entry_index,
                "entry_bid": entry_bid,
                "stop_chart": stop_chart,
                "target_chart": target_chart,
                "risk_pips": float(risk_pips),
                "reward_pips": float(reward_pips),
                "rr": TARGET_R,
                "h1_trend_separation_atr": float(separation.iloc[index]),
                "close_location": float(close_location.iloc[index]),
            }
        )

    return pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)


def monthly_summary(evaluated: pd.DataFrame) -> pd.DataFrame:
    resolved = evaluated[evaluated["outcome_status"] == "RESOLVED"].copy()
    resolved["month"] = pd.to_datetime(resolved["entry_time"]).dt.to_period("M").astype(str)
    return pd.DataFrame(
        [{"month": month, **base.metrics(group)} for month, group in resolved.groupby("month")]
    )


def direction_summary(evaluated: pd.DataFrame) -> pd.DataFrame:
    resolved = evaluated[evaluated["outcome_status"] == "RESOLVED"].copy()
    return pd.DataFrame(
        [
            {"direction": direction, **base.metrics(group)}
            for direction, group in resolved.groupby("direction")
        ]
    )


def run(m5_path: Path, m15_path: Path, h1_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    m5 = base.add_features(base.read_bars(m5_path))
    m15 = base.add_features(base.read_bars(m15_path))
    h1 = base.add_features(base.read_bars(h1_path))

    plans = generate_plans(m15, h1, m5)
    evaluated = base.evaluate(m5, plans)
    evaluated.to_csv(output_dir / "btc10_candidate_trade_ledger.csv", index=False)

    summary = pd.DataFrame(
        [
            {"period": "DISCOVERY", **base.metrics(evaluated[evaluated["period"] == "DISCOVERY"])},
            {"period": "VALIDATION", **base.metrics(evaluated[evaluated["period"] == "VALIDATION"])},
            {
                "period": "COMBINED",
                **base.metrics(evaluated[evaluated["period"].isin(["DISCOVERY", "VALIDATION"])]),
            },
        ]
    )
    summary.to_csv(output_dir / "btc10_candidate_summary.csv", index=False)
    monthly_summary(evaluated).to_csv(output_dir / "btc10_candidate_monthly.csv", index=False)
    direction_summary(evaluated).to_csv(output_dir / "btc10_candidate_direction.csv", index=False)
    evaluated[evaluated["period"] == "POST_2026_ENTRY_ONLY"].to_csv(
        output_dir / "btc10_post2026_entry_only.csv", index=False
    )

    contract = {
        "candidate": CANDIDATE_ID,
        "status": "provisional_research_candidate_not_in_stacking_portfolio",
        "selection_protocol": (
            "Coarse family grid selected using TRAIN 2024-08-01..2025-02-01 and "
            "DEV 2025-02-01..2025-07-01 only. The selected rule was frozen before "
            "opening its 2025-07-01..2026-01-01 validation and opened-2026 results."
        ),
        "h1_trend": (
            "closed H1 EMA50/EMA200 direction, EMA200 slope versus previous closed H1 "
            "using shift(4) after M15 as-of merge, separation at least 0.5 ATR14"
        ),
        "signal": (
            "M15 previous close on pullback side of EMA20, current close reclaims EMA20, "
            "remains beyond EMA50 in H1 trend direction, and closes in outer 40 percent"
        ),
        "entry": "next exact M5 open after the closed M15 signal bar",
        "stop": "extreme of the most recent 8 M15 bars plus 0.1*M15 ATR14",
        "cooldown": "12 M15 bars per direction, applied to raw signals before risk filtering",
        "risk_cap_pips": RISK_CAP_PIPS,
        "target_r": TARGET_R,
        "minimum_reward_pips": MIN_REWARD_PIPS,
        "spread_usd": base.SPREAD_USD,
        "same_bar_priority": "SL_FIRST",
        "portfolio_adopted": False,
        "post2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc10_candidate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"summary": summary.to_dict(orient="records"), "contract": contract}


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
