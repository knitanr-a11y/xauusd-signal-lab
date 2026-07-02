from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

import btc9_m15_prevday_breakout_candidate as base

CANDIDATE_ID = "BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080"
TARGET_R = 0.8
MIN_REWARD_PIPS = 50.0


def refine_plans(plans: pd.DataFrame) -> pd.DataFrame:
    if plans.empty:
        return plans.copy()
    output = plans[
        (plans["risk_pips"] <= base.RISK_CAP_PIPS)
        & (TARGET_R * plans["risk_pips"] >= MIN_REWARD_PIPS)
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


def monthly_summary(evaluated: pd.DataFrame) -> pd.DataFrame:
    resolved = evaluated[evaluated["outcome_status"] == "RESOLVED"].copy()
    resolved["month"] = pd.to_datetime(resolved["entry_time"]).dt.to_period("M").astype(str)
    return pd.DataFrame(
        [
            {"month": month, **base.metrics(group)}
            for month, group in resolved.groupby("month")
        ]
    )


def direction_summary(evaluated: pd.DataFrame) -> pd.DataFrame:
    resolved = evaluated[evaluated["outcome_status"] == "RESOLVED"].copy()
    return pd.DataFrame(
        [
            {"direction": direction, **base.metrics(group)}
            for direction, group in resolved.groupby("direction")
        ]
    )


def run(
    m5_path: Path,
    m15_path: Path,
    h1_path: Path,
    d1_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    m5 = base.base.add_features(base.base.read_bars(m5_path))
    m15 = base.base.add_features(base.base.read_bars(m15_path))
    h1 = base.base.add_features(base.base.read_bars(h1_path))
    d1 = base.base.add_features(base.base.read_bars(d1_path))

    original_plans = base.generate_plans(m15, h1, d1, m5)
    refined_plans = refine_plans(original_plans)
    evaluated = base.evaluate(m5, refined_plans)
    evaluated.to_csv(output_dir / "btc9r_candidate_trade_ledger.csv", index=False)

    summary: list[dict[str, Any]] = []
    for period in ("TRAIN", "DEV", "VALIDATION"):
        summary.append(
            {"period": period, **base.metrics(evaluated[evaluated["period"] == period])}
        )
    summary.append(
        {
            "period": "DISCOVERY",
            **base.metrics(evaluated[evaluated["period"].isin(["TRAIN", "DEV"])]),
        }
    )
    summary.append(
        {
            "period": "COMBINED",
            **base.metrics(
                evaluated[evaluated["period"].isin(["TRAIN", "DEV", "VALIDATION"])]
            ),
        }
    )
    pd.DataFrame(summary).to_csv(output_dir / "btc9r_candidate_summary.csv", index=False)
    monthly_summary(evaluated).to_csv(output_dir / "btc9r_candidate_monthly.csv", index=False)
    direction_summary(evaluated).to_csv(output_dir / "btc9r_candidate_direction.csv", index=False)
    evaluated[evaluated["period"] == "POST_2026_ENTRY_ONLY"].to_csv(
        output_dir / "btc9r_post2026_entry_only.csv", index=False
    )

    contract = {
        "candidate": CANDIDATE_ID,
        "base_candidate": base.CANDIDATE_ID,
        "selection_protocol": (
            "Target-R grid selected with TRAIN and DEV only. Require at least 15 TRAIN "
            "and 10 DEV trades, both PF above 1.1. R=0.75 was rejected because DEV "
            "had only 9 trades. R=0.80 had the highest minimum TRAIN/DEV win rate "
            "among eligible target settings. Official validation was opened after freeze."
        ),
        "target_r": TARGET_R,
        "minimum_reward_pips": MIN_REWARD_PIPS,
        "implied_minimum_risk_pips": MIN_REWARD_PIPS / TARGET_R,
        "maximum_risk_pips": base.RISK_CAP_PIPS,
        "spread_usd": base.SPREAD_USD,
        "post2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc9r_candidate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8"
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
