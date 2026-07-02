from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

PROFILE_ID = "BTC10R_DEMO_FIXED_LOT_002_001_AFTER_2L_V1"
NORMAL_LOT = 0.02
THROTTLED_LOT = 0.01
MAX_ALLOWED_LOT = 0.05
LOSS_STREAK_TRIGGER = 2
PIP_VALUE_PER_LOT_USD = 10.0


def apply_overlay(
    trades: pd.DataFrame,
    normal_lot: float = NORMAL_LOT,
    throttled_lot: float = THROTTLED_LOT,
    loss_streak_trigger: int = LOSS_STREAK_TRIGGER,
    pip_value_per_lot_usd: float = PIP_VALUE_PER_LOT_USD,
) -> pd.DataFrame:
    required = {"entry_time", "exit_time", "pnl_pips", "risk_pips"}
    missing = required.difference(trades.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if not (0.0 < throttled_lot <= normal_lot <= MAX_ALLOWED_LOT):
        raise ValueError("lot contract must satisfy 0 < throttled <= normal <= max")
    if loss_streak_trigger < 1:
        raise ValueError("loss_streak_trigger must be positive")
    if pip_value_per_lot_usd <= 0.0:
        raise ValueError("pip_value_per_lot_usd must be positive")

    frame = trades.copy()
    frame["entry_time"] = pd.to_datetime(frame["entry_time"])
    frame["exit_time"] = pd.to_datetime(frame["exit_time"])
    frame = frame.sort_values(["entry_time"], kind="stable").reset_index(drop=True)
    if frame[["entry_time", "exit_time"]].isna().any().any():
        raise ValueError("entry_time and exit_time must be resolved")
    if (frame["exit_time"] < frame["entry_time"]).any():
        raise ValueError("exit_time cannot be earlier than entry_time")
    if (frame["risk_pips"] <= 0).any():
        raise ValueError("risk_pips must be positive")

    exit_events = frame[["exit_time", "pnl_pips"]].copy()
    exit_events["stable_order"] = np.arange(len(exit_events))
    exit_events = exit_events.sort_values(
        ["exit_time", "stable_order"], kind="stable"
    ).reset_index(drop=True)

    lots: list[float] = []
    streaks_before_entry: list[int] = []
    loss_streak = 0
    event_index = 0
    for entry_time in frame["entry_time"]:
        while (
            event_index < len(exit_events)
            and exit_events.at[event_index, "exit_time"] < entry_time
        ):
            resolved_pnl = float(exit_events.at[event_index, "pnl_pips"])
            loss_streak = loss_streak + 1 if resolved_pnl < 0.0 else 0
            event_index += 1
        streaks_before_entry.append(loss_streak)
        lots.append(
            throttled_lot if loss_streak >= loss_streak_trigger else normal_lot
        )

    frame["resolved_loss_streak_before_entry"] = streaks_before_entry
    frame["assigned_lot"] = lots
    frame["raw_pnl_r"] = frame["pnl_pips"] / frame["risk_pips"]
    frame["pnl_usd_assumed"] = (
        frame["pnl_pips"] * frame["assigned_lot"] * pip_value_per_lot_usd
    )
    return frame


def metrics(frame: pd.DataFrame) -> dict[str, Any]:
    pnl = frame["pnl_usd_assumed"].to_numpy(dtype=float)
    if len(pnl) == 0:
        return {"trades": 0}
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    equity = np.cumsum(pnl)
    running_peak = np.maximum.accumulate(np.concatenate(([0.0], equity)))[1:]
    drawdown = running_peak - equity
    lot_counts = frame["assigned_lot"].value_counts().sort_index()
    return {
        "trades": int(len(frame)),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "total_pnl_usd_assumed": float(pnl.sum()),
        "max_drawdown_usd_assumed": float(drawdown.max()),
        "average_lot": float(frame["assigned_lot"].mean()),
        "lot_counts": {
            f"{float(lot):.2f}": int(count) for lot, count in lot_counts.items()
        },
        "normal_lot": NORMAL_LOT,
        "throttled_lot": THROTTLED_LOT,
        "maximum_allowed_lot": MAX_ALLOWED_LOT,
        "loss_streak_trigger": LOSS_STREAK_TRIGGER,
        "pip_value_per_lot_usd_assumption": PIP_VALUE_PER_LOT_USD,
    }


def run(input_csv: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    trades = pd.read_csv(input_csv)
    overlaid = apply_overlay(trades)
    overlaid.to_csv(output_dir / "btc10r_adopted_lot_overlay_ledger.csv", index=False)
    report = {
        "profile_id": PROFILE_ID,
        "parent_candidate": "BTC10R_M15_EMA20_SHALLOW_PULLBACK_STRONG_CLOSE_R225",
        "status": "adopted_candidate_demo_forward_policy",
        "candidate_adopted": True,
        "portfolio_adopted": False,
        "demo_forward_approved": True,
        "signal_changes": False,
        "exit_changes": False,
        "position_sizing": {
            "normal_lot": NORMAL_LOT,
            "after_two_resolved_consecutive_losses_lot": THROTTLED_LOT,
            "reset": "return to 0.02 lot after the next resolved BTC10R win",
            "maximum_allowed_lot": MAX_ALLOWED_LOT,
            "decision_information": (
                "only exits strictly earlier than the new entry may update the streak"
            ),
        },
        "metrics": metrics(overlaid),
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc10r_adopted_lot_overlay_report.json").write_text(
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
