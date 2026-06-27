from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import build_mlr2_candidate_proposals_v1 as common


def definitions(frame: pd.DataFrame):
    c = lambda name: frame[name].astype(float)
    p = lambda name, bars=1: common.previous_exact(frame, name, bars)
    return [
        {
            "candidate_id": "GML1-MLR2-V2-C001-L",
            "family": "H1_TREND_PULLBACK_RESUMPTION",
            "direction": "LONG",
            "state": (c("h1_ema20_ema50_gap_atr14") >= 0.08)
            & (c("h1_ema50_ema200_gap_atr14") >= -0.05)
            & (c("h1_adx14_scaled") >= 0.16)
            & (c("h4_ema20_ema50_gap_atr14") >= -0.20)
            & (p("m15_rsi14_centered") <= -0.10)
            & common.cross_up(frame, "m15_rsi14_centered", 0.0)
            & (c("m15_macd_hist_atr14") > p("m15_macd_hist_atr14"))
            & (c("m15_signed_body_atr14") >= 0.05)
            & (c("m15_close_location") >= 0.52),
        },
        {
            "candidate_id": "GML1-MLR2-V2-C002-S",
            "family": "MULTIBAR_COMPRESSION_BREAKOUT",
            "direction": "SHORT",
            "state": (p("m15_atr14_percentile_lag1_256") <= 0.35)
            & (p("m15_atr14_percentile_lag1_256", 2) <= 0.40)
            & (p("m15_bb20_close_location") >= 0.0)
            & (c("m15_bb20_close_location") < 0.0)
            & (c("m15_distance_from_prev_low_20_atr14") <= 0.0)
            & (c("m15_body_fraction") >= 0.55)
            & (c("m15_tick_volume_ratio20_lagbase") >= 1.15)
            & (c("h1_ema20_slope4_atr14") <= 0.0)
            & (c("h1_adx14_scaled") >= 0.15),
        },
        {
            "candidate_id": "GML1-MLR2-V2-C003-L",
            "family": "STRICT_HIGH_VOL_EXHAUSTION_REVERSAL",
            "direction": "LONG",
            "state": (c("m15_atr14_percentile_lag1_256") >= 0.75)
            & (c("m15_rsi14_centered") <= -0.35)
            & (c("m15_range_atr14") >= 1.00)
            & (c("m15_lower_wick_fraction") >= 0.40),
        },
        {
            "candidate_id": "GML1-MLR2-V2-C003-S",
            "family": "STRICT_HIGH_VOL_EXHAUSTION_REVERSAL",
            "direction": "SHORT",
            "state": (c("m15_atr14_percentile_lag1_256") >= 0.75)
            & (c("m15_rsi14_centered") >= 0.35)
            & (c("m15_range_atr14") >= 1.00)
            & (c("m15_upper_wick_fraction") >= 0.40),
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--feature-columns", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    columns = json.loads(args.feature_columns.read_text(encoding="utf-8"))
    model_columns = list(columns.get("model_feature_columns", columns["market_feature_columns"]))
    frame = pd.read_csv(args.feature_registry, parse_dates=["decision_time"])
    parts = []
    counts = []
    for item in definitions(frame):
        selected = common.onset(item["state"], frame["decision_time"])
        proposal = frame.loc[selected, ["decision_time"] + model_columns].copy()
        proposal.insert(1, "candidate_id", item["candidate_id"])
        proposal.insert(2, "candidate_definition_version", "mlr2-v2-research")
        proposal.insert(3, "candidate_family", item["family"])
        proposal.insert(4, "direction", item["direction"])
        proposal.insert(5, "proposal_strength", 1.0)
        parts.append(proposal)
        counts.append({
            "candidate_id": item["candidate_id"],
            "events": int(len(proposal)),
            "years": sorted(int(v) for v in proposal["decision_time"].dt.year.unique()),
        })
    proposals = pd.concat(parts, ignore_index=True).sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "mlr2_candidate_proposals_v2_research.csv.gz"
    common.deterministic_csv_gzip(proposals, path)
    summary = {
        "system_id": "GML1-MLR2",
        "version": "v2-research",
        "status": "PERFORMANCE_INFORMED_PROPOSALS_BUILT_AUDIT_ONLY",
        "proposal_rows": int(len(proposals)),
        "unique_decisions": int(proposals["decision_time"].nunique()),
        "direction_counts": {str(k): int(v) for k, v in proposals["direction"].value_counts().items()},
        "candidate_counts": counts,
        "proposal_registry_sha256": common.sha256_file(path),
        "labels_read": False,
        "candidate_performance_read_by_builder": False,
        "deployable": False,
    }
    common.write_json(args.output_dir / "mlr2_candidate_proposal_summary_v2_research.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
