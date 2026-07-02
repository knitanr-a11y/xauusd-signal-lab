from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

import btc7_m15_impulse_continuation_candidate as base

CANDIDATE_ID = "BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110"
TREND_AGE_MIN_HOURS = 24.0
TREND_AGE_MAX_HOURS = 96.0
IMPULSE_ATR_MIN = 2.2
TARGET_R = 1.1
MIN_REWARD_PIPS = 50.0


def _run_age(mask: pd.Series) -> np.ndarray:
    values = mask.fillna(False).to_numpy(dtype=bool)
    output = np.zeros(len(values), dtype=np.int64)
    age = 0
    for index, value in enumerate(values):
        age = age + 1 if value else 0
        output[index] = age
    return output


def trend_age_table(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    aligned = base.align_h1(m15, h1)
    separation = (aligned["ema50_h1"] - aligned["ema200_h1"]).abs() / aligned["atr14_h1"]
    long_trend = (
        (aligned["ema50_h1"] > aligned["ema200_h1"])
        & (aligned["ema200_h1"] > aligned["ema200_h1"].shift(4))
        & (separation >= base.TREND_SEPARATION_ATR)
    )
    short_trend = (
        (aligned["ema50_h1"] < aligned["ema200_h1"])
        & (aligned["ema200_h1"] < aligned["ema200_h1"].shift(4))
        & (separation >= base.TREND_SEPARATION_ATR)
    )
    return pd.DataFrame(
        {
            "signal_time": aligned["time"],
            "long_trend_age_hours": _run_age(long_trend) * 0.25,
            "short_trend_age_hours": _run_age(short_trend) * 0.25,
        }
    )


def refine_plans(plans: pd.DataFrame, ages: pd.DataFrame) -> pd.DataFrame:
    if plans.empty:
        return plans.copy()
    output = plans.merge(ages, on="signal_time", how="left", validate="many_to_one")
    output["trend_age_hours"] = np.where(
        output["direction"].eq("LONG"),
        output["long_trend_age_hours"],
        output["short_trend_age_hours"],
    )
    output = output[
        output["trend_age_hours"].between(
            TREND_AGE_MIN_HOURS,
            TREND_AGE_MAX_HOURS,
            inclusive="both",
        )
        & (output["impulse_atr_multiple"] >= IMPULSE_ATR_MIN)
        & (output["risk_pips"] <= base.RISK_CAP_PIPS)
        & (TARGET_R * output["risk_pips"] >= MIN_REWARD_PIPS)
    ].copy()
    risk_usd = output["risk_pips"] * base.PIP_USD
    output["reward_pips"] = TARGET_R * output["risk_pips"]
    output["rr"] = TARGET_R
    output["target_chart"] = np.where(
        output["direction"].eq("LONG"),
        output["entry_bid"] + base.SPREAD_USD + TARGET_R * risk_usd,
        output["entry_bid"] - base.SPREAD_USD - TARGET_R * risk_usd,
    )
    output["candidate_id"] = CANDIDATE_ID
    return output.sort_values("entry_time").reset_index(drop=True)


def _metrics_with_pnl(frame: pd.DataFrame) -> dict[str, Any]:
    return base.metrics(frame)


def monthly_summary(evaluated: pd.DataFrame) -> pd.DataFrame:
    resolved = evaluated[evaluated["outcome_status"] == "RESOLVED"].copy()
    resolved["month"] = pd.to_datetime(resolved["entry_time"]).dt.to_period("M").astype(str)
    rows: list[dict[str, Any]] = []
    for month, group in resolved.groupby("month"):
        rows.append({"month": month, **_metrics_with_pnl(group)})
    return pd.DataFrame(rows)


def direction_summary(evaluated: pd.DataFrame) -> pd.DataFrame:
    resolved = evaluated[evaluated["outcome_status"] == "RESOLVED"].copy()
    return pd.DataFrame(
        [{"direction": direction, **_metrics_with_pnl(group)} for direction, group in resolved.groupby("direction")]
    )


def run(m5_path: Path, m15_path: Path, h1_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    m5 = base.add_features(base.read_bars(m5_path))
    m15 = base.add_features(base.read_bars(m15_path))
    h1 = base.add_features(base.read_bars(h1_path))

    base_plans = base.generate_plans(m15, h1, m5)
    refined = refine_plans(base_plans, trend_age_table(m15, h1))
    evaluated = base.evaluate(m5, refined)
    evaluated.to_csv(output_dir / "btc7r_candidate_trade_ledger.csv", index=False)

    summary = pd.DataFrame(
        [
            {
                "period": "DISCOVERY",
                **_metrics_with_pnl(evaluated[evaluated["period"] == "DISCOVERY"]),
            },
            {
                "period": "VALIDATION",
                **_metrics_with_pnl(evaluated[evaluated["period"] == "VALIDATION"]),
            },
            {
                "period": "COMBINED",
                **_metrics_with_pnl(
                    evaluated[evaluated["period"].isin(["DISCOVERY", "VALIDATION"])]
                ),
            },
        ]
    )
    summary.to_csv(output_dir / "btc7r_candidate_summary.csv", index=False)
    monthly_summary(evaluated).to_csv(output_dir / "btc7r_candidate_monthly.csv", index=False)
    direction_summary(evaluated).to_csv(output_dir / "btc7r_candidate_direction.csv", index=False)
    evaluated[evaluated["period"] == "POST_2026_ENTRY_ONLY"].to_csv(
        output_dir / "btc7r_post2026_entry_only.csv",
        index=False,
    )

    contract = {
        "candidate": CANDIDATE_ID,
        "selection_protocol": (
            "Entry-known filter grid selected using TRAIN 2024-08-01..2025-02-01 "
            "and DEV 2025-02-01..2025-07-01 only; official validation "
            "2025-07-01..2026-01-01 was opened after the rule was frozen."
        ),
        "trend_age_hours": [TREND_AGE_MIN_HOURS, TREND_AGE_MAX_HOURS],
        "minimum_impulse_atr": IMPULSE_ATR_MIN,
        "risk_cap_pips": base.RISK_CAP_PIPS,
        "target_r": TARGET_R,
        "minimum_reward_pips": MIN_REWARD_PIPS,
        "spread_usd": base.SPREAD_USD,
        "post2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc7r_candidate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
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
