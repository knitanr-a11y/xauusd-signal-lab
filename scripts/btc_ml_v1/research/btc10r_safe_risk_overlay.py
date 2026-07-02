from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

PROFILE_ID = "BTC10R_SAFE_RISK_OVERLAY_V1"
NORMAL_WEIGHT = 0.20
THROTTLED_WEIGHT = 0.10
LOSS_STREAK_TRIGGER = 2


def apply_overlay(
    trades: pd.DataFrame,
    normal_weight: float = NORMAL_WEIGHT,
    throttled_weight: float = THROTTLED_WEIGHT,
    loss_streak_trigger: int = LOSS_STREAK_TRIGGER,
) -> pd.DataFrame:
    required = {"entry_time", "pnl_pips", "risk_pips"}
    missing = required.difference(trades.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    frame = trades.copy()
    frame["entry_time"] = pd.to_datetime(frame["entry_time"])
    frame = frame.sort_values("entry_time").reset_index(drop=True)
    if (frame["risk_pips"] <= 0).any():
        raise ValueError("risk_pips must be positive")

    frame["raw_pnl_r"] = frame["pnl_pips"] / frame["risk_pips"]
    weights: list[float] = []
    loss_streak = 0
    for pnl_r in frame["raw_pnl_r"]:
        weight = throttled_weight if loss_streak >= loss_streak_trigger else normal_weight
        weights.append(float(weight))
        if pnl_r < 0:
            loss_streak += 1
        else:
            loss_streak = 0
    frame["risk_weight"] = weights
    frame["weighted_pnl_r"] = frame["raw_pnl_r"] * frame["risk_weight"]
    return frame


def metrics(frame: pd.DataFrame) -> dict[str, Any]:
    pnl = frame["weighted_pnl_r"].to_numpy(dtype=float)
    if len(pnl) == 0:
        return {"trades": 0}
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    equity = np.cumsum(pnl)
    running_peak = np.maximum.accumulate(np.concatenate(([0.0], equity)))[1:]
    drawdown = running_peak - equity
    return {
        "trades": int(len(frame)),
        "weighted_profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "total_weighted_r": float(pnl.sum()),
        "max_drawdown_weighted_r": float(drawdown.max()),
        "normal_weight": NORMAL_WEIGHT,
        "throttled_weight": THROTTLED_WEIGHT,
        "loss_streak_trigger": LOSS_STREAK_TRIGGER,
    }


def run(input_csv: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    trades = pd.read_csv(input_csv)
    overlaid = apply_overlay(trades)
    overlaid.to_csv(output_dir / "btc10r_safe_risk_overlay_ledger.csv", index=False)
    report = {
        "profile_id": PROFILE_ID,
        "parent_candidate": "BTC10R_M15_EMA20_SHALLOW_PULLBACK_STRONG_CLOSE_R225",
        "signal_changes": False,
        "exit_changes": False,
        "position_sizing": {
            "normal_relative_weight": NORMAL_WEIGHT,
            "throttled_relative_weight": THROTTLED_WEIGHT,
            "rule": "after two consecutive BTC10R losses, use half weight until the next BTC10R win",
        },
        "metrics": metrics(overlaid),
        "portfolio_adopted": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc10r_safe_risk_overlay_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(Path(args.trades), Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
