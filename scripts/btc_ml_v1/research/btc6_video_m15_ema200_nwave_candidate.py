from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

import btc5_video_5m_ema200_nwave_candidate as engine

CANDIDATE_ID = "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886"
TIMEFRAME_MINUTES = 15
PIVOT_WIDTH = 3
AB_LOOKBACK_BARS = 96  # 24 hours on M15
N_RETRACE_MIN = 0.236
N_RETRACE_MAX = 0.886
DOUBLE_MAX_SEPARATION_BARS_EQUIVALENT = 24  # 6 hours on M15

# Reuse the audited M5 implementation while replacing only timeframe-scaled constants.
engine.AB_LOOKBACK_BARS = AB_LOOKBACK_BARS
engine.N_RETRACE_MIN = N_RETRACE_MIN
engine.N_RETRACE_MAX = N_RETRACE_MAX
_original_detect_pivots = engine.detect_pivots
engine.detect_pivots = lambda frame: _original_detect_pivots(frame, width=PIVOT_WIDTH)


def simulate(frame: pd.DataFrame, plan: pd.Series, period_end: pd.Timestamp) -> dict[str, Any]:
    direction = str(plan["direction"])
    for index in range(int(plan["entry_idx"]), len(frame)):
        bar_time = pd.Timestamp(frame.iloc[index]["time"])
        if bar_time >= period_end:
            return {"outcome_status": "BOUNDARY_EXCLUDED"}
        high = float(frame.iloc[index]["high"])
        low = float(frame.iloc[index]["low"])
        stop_hit = low <= plan["stop_chart"] if direction == "LONG" else high >= plan["stop_chart"]
        target_hit = high >= plan["target_chart"] if direction == "LONG" else low <= plan["target_chart"]
        # Conservative same-bar ordering: SL first.
        if stop_hit:
            pnl_pips = -float(plan["risk_pips"])
            reason = "SL"
        elif target_hit:
            pnl_pips = float(plan["reward_pips"])
            reason = "TP"
        else:
            continue
        return {
            "outcome_status": "RESOLVED",
            "exit_time": bar_time + pd.Timedelta(minutes=TIMEFRAME_MINUTES),
            "exit_reason": reason,
            "pnl_pips": pnl_pips,
        }
    return {"outcome_status": "OPEN_AT_DATA_END"}


engine.simulate = simulate


def run(m15_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = engine.read_m5(m15_path)
    evaluated = engine.evaluate(frame, engine.generate_plans(frame))
    evaluated["candidate_id"] = CANDIDATE_ID
    evaluated.to_csv(output_dir / "btc6_m15_candidate_trade_ledger.csv", index=False)

    summary = [
        {"period": "DISCOVERY", **engine.metrics(evaluated[evaluated["period"] == "DISCOVERY"])},
        {"period": "VALIDATION", **engine.metrics(evaluated[evaluated["period"] == "VALIDATION"])},
        {
            "period": "COMBINED",
            **engine.metrics(evaluated[evaluated["period"].isin(["DISCOVERY", "VALIDATION"])]),
        },
    ]
    pd.DataFrame(summary).to_csv(output_dir / "btc6_m15_candidate_summary.csv", index=False)
    evaluated[evaluated["period"] == "POST_2026_ENTRY_ONLY"].to_csv(
        output_dir / "btc6_m15_post2026_entry_only.csv",
        index=False,
    )
    contract = {
        "candidate": CANDIDATE_ID,
        "timeframe": "M15",
        "pivot_width": PIVOT_WIDTH,
        "ab_lookback_hours": 24,
        "n_retracement": f"{N_RETRACE_MIN} <= BC/AB <= {N_RETRACE_MAX}",
        "stop_buffer_pips": engine.STOP_BUFFER_PIPS,
        "rr": "1 < RR < 3",
        "minimum_reward_pips": engine.MIN_REWARD_PIPS,
        "post2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc6_m15_candidate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"summary": summary, "contract": contract}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m15", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(Path(args.m15), Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=engine._json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
