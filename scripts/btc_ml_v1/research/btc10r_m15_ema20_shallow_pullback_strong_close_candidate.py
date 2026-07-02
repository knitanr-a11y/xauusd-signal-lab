from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

import btc10_m15_ema20_pullback_reclaim_candidate as parent

CANDIDATE_ID = "BTC10R_M15_EMA20_SHALLOW_PULLBACK_STRONG_CLOSE_R225"
MAX_PULLBACK_DEPTH_ATR = 0.6
MIN_DIRECTIONAL_CLOSE_LOCATION = 0.85


def apply_quality_filters(plans: pd.DataFrame, m15: pd.DataFrame) -> pd.DataFrame:
    if plans.empty:
        return plans.copy()
    index_lookup = {timestamp: index for index, timestamp in enumerate(m15["time"])}
    rows: list[dict[str, Any]] = []
    for _, plan in plans.iterrows():
        signal_time = pd.Timestamp(plan["signal_time"])
        signal_index = index_lookup.get(signal_time)
        if signal_index is None:
            continue
        if signal_index <= 0:
            continue
        previous = m15.iloc[signal_index - 1]
        direction = str(plan["direction"])
        if direction == "LONG":
            pullback_depth_atr = (
                float(previous["ema20"]) - float(previous["close"])
            ) / float(previous["atr14"])
            directional_close_location = float(plan["close_location"])
        else:
            pullback_depth_atr = (
                float(previous["close"]) - float(previous["ema20"])
            ) / float(previous["atr14"])
            directional_close_location = 1.0 - float(plan["close_location"])
        if not np.isfinite(pullback_depth_atr):
            continue
        if pullback_depth_atr > MAX_PULLBACK_DEPTH_ATR:
            continue
        if directional_close_location < MIN_DIRECTIONAL_CLOSE_LOCATION:
            continue
        row = plan.to_dict()
        row["candidate_id"] = CANDIDATE_ID
        row["pullback_depth_atr"] = float(pullback_depth_atr)
        row["directional_close_location"] = float(directional_close_location)
        rows.append(row)
    if not rows:
        return plans.iloc[0:0].copy()
    return pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)


def generate_plans(
    m15: pd.DataFrame,
    h1: pd.DataFrame,
    m5: pd.DataFrame,
) -> pd.DataFrame:
    return apply_quality_filters(parent.generate_plans(m15, h1, m5), m15)


def run(
    m5_path: Path,
    m15_path: Path,
    h1_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    m5 = parent.base.add_features(parent.base.read_bars(m5_path))
    m15 = parent.base.add_features(parent.base.read_bars(m15_path))
    h1 = parent.base.add_features(parent.base.read_bars(h1_path))
    evaluated = parent.base.evaluate(m5, generate_plans(m15, h1, m5))
    evaluated.to_csv(output_dir / "btc10r_candidate_trade_ledger.csv", index=False)
    summary = [
        {
            "period": "DISCOVERY",
            **parent.base.metrics(evaluated[evaluated["period"] == "DISCOVERY"]),
        },
        {
            "period": "VALIDATION",
            **parent.base.metrics(evaluated[evaluated["period"] == "VALIDATION"]),
        },
        {
            "period": "COMBINED",
            **parent.base.metrics(
                evaluated[evaluated["period"].isin(["DISCOVERY", "VALIDATION"])]
            ),
        },
    ]
    pd.DataFrame(summary).to_csv(
        output_dir / "btc10r_candidate_summary.csv",
        index=False,
    )
    evaluated[evaluated["period"] == "POST_2026_ENTRY_ONLY"].to_csv(
        output_dir / "btc10r_post2026_entry_only.csv",
        index=False,
    )
    contract = {
        "candidate": CANDIDATE_ID,
        "parent_candidate": parent.CANDIDATE_ID,
        "status": "provisional_posthoc_quality_filter_research_candidate",
        "maximum_pullback_depth_atr": MAX_PULLBACK_DEPTH_ATR,
        "minimum_directional_close_location": MIN_DIRECTIONAL_CLOSE_LOCATION,
        "target_r": parent.TARGET_R,
        "risk_cap_pips": parent.RISK_CAP_PIPS,
        "same_bar_priority": "SL_FIRST",
        "portfolio_adopted": False,
        "post2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc10r_candidate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
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
