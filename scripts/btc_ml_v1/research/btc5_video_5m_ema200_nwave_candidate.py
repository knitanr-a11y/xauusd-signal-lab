from __future__ import annotations

import argparse
import bisect
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

PIP_USD = 10.0
SPREAD_USD = 30.0
STOP_BUFFER_PIPS = 30.0
STOP_BUFFER_USD = STOP_BUFFER_PIPS * PIP_USD
MIN_REWARD_PIPS = 50.0
MIN_REWARD_USD = MIN_REWARD_PIPS * PIP_USD
RR_MIN = 1.0
RR_MAX = 3.0
PIVOT_WIDTH = 2
CLEAR_CROSS_ATR = 0.02
AB_LOOKBACK_BARS = 288
N_RETRACE_MIN = 0.382
N_RETRACE_MAX = 0.786
DISCOVERY_START = pd.Timestamp("2024-08-01 00:00:00")
DISCOVERY_END = pd.Timestamp("2025-07-01 00:00:00")
VALIDATION_END = pd.Timestamp("2026-01-01 00:00:00")


@dataclass(frozen=True)
class Pivot:
    idx: int
    confirm_idx: int
    price: float


@dataclass(frozen=True)
class Regime:
    direction: str
    raw_start_idx: int
    clear_start_idx: int
    end_idx: int


class PivotIndex:
    def __init__(self, pivots: list[Pivot], width: int):
        self.pivots = pivots
        self.width = width
        self.indices = [pivot.idx for pivot in pivots]

    def last_before(self, idx: int, min_idx: int = -1) -> Pivot | None:
        maximum_idx = idx - self.width - 1
        position = bisect.bisect_right(self.indices, maximum_idx) - 1
        if position < 0:
            return None
        pivot = self.pivots[position]
        return pivot if pivot.idx >= min_idx else None

    def first_after(self, start_idx: int, end_idx: int) -> Pivot | None:
        position = bisect.bisect_left(self.indices, start_idx)
        maximum_idx = end_idx - self.width - 1
        if position < len(self.pivots) and self.pivots[position].idx <= maximum_idx:
            return self.pivots[position]
        return None

    def between(self, start_idx: int, end_idx: int, confirm_before: int) -> list[Pivot]:
        maximum_idx = min(end_idx, confirm_before - self.width - 1)
        left = bisect.bisect_left(self.indices, start_idx)
        right = bisect.bisect_right(self.indices, maximum_idx)
        return self.pivots[left:right]


def mt5_ema(values: Sequence[float], period: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    output = np.full(len(array), np.nan, dtype=float)
    if len(array) < period:
        return output
    output[period - 1] = float(array[:period].mean())
    alpha = 2.0 / (period + 1.0)
    for index in range(period, len(array)):
        output[index] = alpha * array[index] + (1.0 - alpha) * output[index - 1]
    return output


def mt5_atr(high: Sequence[float], low: Sequence[float], close: Sequence[float], period: int = 14) -> np.ndarray:
    high_array = np.asarray(high, dtype=float)
    low_array = np.asarray(low, dtype=float)
    close_array = np.asarray(close, dtype=float)
    true_range = np.full(len(close_array), np.nan, dtype=float)
    if len(close_array) == 0:
        return true_range
    true_range[0] = high_array[0] - low_array[0]
    for index in range(1, len(close_array)):
        true_range[index] = max(
            high_array[index] - low_array[index],
            abs(high_array[index] - close_array[index - 1]),
            abs(low_array[index] - close_array[index - 1]),
        )
    output = np.full(len(close_array), np.nan, dtype=float)
    if len(close_array) < period:
        return output
    output[period - 1] = float(true_range[:period].mean())
    for index in range(period, len(close_array)):
        output[index] = (output[index - 1] * (period - 1) + true_range[index]) / period
    return output


def read_m5(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["time"] = pd.to_datetime(frame["time"])
    frame = frame.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    for column in ["open", "high", "low", "close"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    frame["ema20"] = mt5_ema(frame["close"], 20)
    frame["ema200"] = mt5_ema(frame["close"], 200)
    frame["atr14"] = mt5_atr(frame["high"], frame["low"], frame["close"], 14)
    difference = frame["ema20"] - frame["ema200"]
    frame["raw_sign"] = np.where(difference > 0, 1, np.where(difference < 0, -1, 0))
    frame["sep_atr"] = difference.abs() / frame["atr14"]
    frame["touch200"] = (frame["low"] <= frame["ema200"]) & (frame["high"] >= frame["ema200"])
    return frame


def detect_pivots(frame: pd.DataFrame, width: int = PIVOT_WIDTH) -> tuple[PivotIndex, PivotIndex]:
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    highs: list[Pivot] = []
    lows: list[Pivot] = []
    for index in range(width, len(frame) - width):
        high_window = high[index - width : index + width + 1]
        low_window = low[index - width : index + width + 1]
        if high[index] >= np.max(high_window) and np.sum(high_window == high[index]) == 1:
            highs.append(Pivot(index, index + width, float(high[index])))
        if low[index] <= np.min(low_window) and np.sum(low_window == low[index]) == 1:
            lows.append(Pivot(index, index + width, float(low[index])))
    return PivotIndex(highs, width), PivotIndex(lows, width)


def build_regimes(frame: pd.DataFrame) -> list[Regime]:
    sign = frame["raw_sign"].to_numpy(dtype=int)
    separation = frame["sep_atr"].to_numpy(dtype=float)
    regimes: list[Regime] = []
    index = 0
    while index < len(frame):
        current_sign = sign[index]
        end = index + 1
        while end < len(frame) and sign[end] == current_sign:
            end += 1
        if current_sign in (-1, 1):
            clear_start = next(
                (
                    candidate
                    for candidate in range(index, end)
                    if np.isfinite(separation[candidate]) and separation[candidate] >= CLEAR_CROSS_ATR
                ),
                None,
            )
            if clear_start is not None:
                regimes.append(
                    Regime(
                        direction="LONG" if current_sign == 1 else "SHORT",
                        raw_start_idx=index,
                        clear_start_idx=clear_start,
                        end_idx=end,
                    )
                )
        index = end
    return regimes


def touch_events(frame: pd.DataFrame, regime: Regime) -> list[int]:
    touching = frame["touch200"].to_numpy(dtype=bool)
    return [
        index
        for index in range(regime.clear_start_idx, regime.end_idx)
        if touching[index] and (index == regime.clear_start_idx or not touching[index - 1])
    ]


def prior_ab(direction: str, touch_idx: int, highs: PivotIndex, lows: PivotIndex) -> tuple[Pivot, Pivot] | None:
    minimum_idx = max(0, touch_idx - AB_LOOKBACK_BARS)
    if direction == "SHORT":
        b = lows.last_before(touch_idx, minimum_idx)
        a = highs.last_before(b.idx, minimum_idx) if b is not None else None
        if a is None or b is None or a.price <= b.price:
            return None
    else:
        b = highs.last_before(touch_idx, minimum_idx)
        a = lows.last_before(b.idx, minimum_idx) if b is not None else None
        if a is None or b is None or b.price <= a.price:
            return None
    if abs(b.price - a.price) < MIN_REWARD_USD:
        return None
    return a, b


def line_value(first: Pivot, second: Pivot, index: int) -> float:
    return first.price + (second.price - first.price) * (index - first.idx) / (second.idx - first.idx)


def find_line_break(
    close: np.ndarray,
    direction: str,
    b: Pivot,
    c: Pivot,
    highs: PivotIndex,
    lows: PivotIndex,
    regime_end: int,
) -> tuple[int, float] | None:
    line_pivots = (lows if direction == "SHORT" else highs).between(b.idx, c.idx, c.confirm_idx + 1)
    if len(line_pivots) < 2:
        return None
    first = line_pivots[0]
    second = line_pivots[-1]
    if second.idx == first.idx:
        return None
    slope = (second.price - first.price) / (second.idx - first.idx)
    if direction == "SHORT" and slope <= 0:
        return None
    if direction == "LONG" and slope >= 0:
        return None
    start = max(c.confirm_idx + 1, second.confirm_idx + 1)
    for index in range(start, regime_end):
        current_line = line_value(first, second, index)
        previous_line = line_value(first, second, index - 1)
        if direction == "SHORT" and close[index] < current_line and close[index - 1] >= previous_line:
            return index, slope
        if direction == "LONG" and close[index] > current_line and close[index - 1] <= previous_line:
            return index, slope
    return None


def make_plan(
    frame: pd.DataFrame,
    regime: Regime,
    touch_idx: int,
    a: Pivot,
    b: Pivot,
    c: Pivot,
    trigger_idx: int,
    slope: float,
) -> dict[str, Any] | None:
    entry_idx = trigger_idx + 1
    if entry_idx >= len(frame):
        return None
    direction = regime.direction
    impulse = abs(b.price - a.price)
    retracement = (
        (c.price - b.price) / (a.price - b.price)
        if direction == "SHORT"
        else (b.price - c.price) / (b.price - a.price)
    )
    if not (N_RETRACE_MIN <= retracement <= N_RETRACE_MAX):
        return None
    entry_bid = float(frame.iloc[entry_idx]["open"])
    if direction == "LONG":
        stop = c.price - STOP_BUFFER_USD
        target = c.price + impulse
        risk = entry_bid + SPREAD_USD - stop
        reward = target - (entry_bid + SPREAD_USD)
    else:
        stop = c.price + STOP_BUFFER_USD
        target = c.price - impulse
        risk = stop + SPREAD_USD - entry_bid
        reward = entry_bid - (target + SPREAD_USD)
    if risk <= 0 or reward < MIN_REWARD_USD:
        return None
    rr = reward / risk
    if not (RR_MIN < rr < RR_MAX):
        return None
    return {
        "direction": direction,
        "regime_clear_start_time": frame.iloc[regime.clear_start_idx]["time"],
        "touch_time": frame.iloc[touch_idx]["time"],
        "a_time": frame.iloc[a.idx]["time"],
        "a_price": a.price,
        "b_time": frame.iloc[b.idx]["time"],
        "b_price": b.price,
        "c_time": frame.iloc[c.idx]["time"],
        "c_price": c.price,
        "trigger_time": frame.iloc[trigger_idx]["time"],
        "entry_time": frame.iloc[entry_idx]["time"],
        "entry_idx": entry_idx,
        "entry_bid": entry_bid,
        "stop_chart": stop,
        "target_chart": target,
        "risk_pips": risk / PIP_USD,
        "reward_pips": reward / PIP_USD,
        "rr": rr,
        "retracement_ratio": retracement,
        "line_slope": slope,
    }


def generate_plans(frame: pd.DataFrame) -> pd.DataFrame:
    highs, lows = detect_pivots(frame)
    close = frame["close"].to_numpy(dtype=float)
    plans: list[dict[str, Any]] = []
    for regime in build_regimes(frame):
        for touch_idx in touch_events(frame, regime):
            if pd.Timestamp(frame.iloc[touch_idx]["time"]) < DISCOVERY_START:
                continue
            ab = prior_ab(regime.direction, touch_idx, highs, lows)
            if ab is None:
                continue
            a, b = ab
            c = (highs if regime.direction == "SHORT" else lows).first_after(touch_idx, regime.end_idx)
            if c is None:
                continue
            if regime.direction == "SHORT" and c.price <= b.price:
                continue
            if regime.direction == "LONG" and c.price >= b.price:
                continue
            line_break = find_line_break(close, regime.direction, b, c, highs, lows, regime.end_idx)
            if line_break is None:
                continue
            trigger_idx, slope = line_break
            plan = make_plan(frame, regime, touch_idx, a, b, c, trigger_idx, slope)
            if plan is not None:
                plans.append(plan)
    output = pd.DataFrame(plans)
    if output.empty:
        return output
    return (
        output.sort_values(["entry_idx", "direction", "touch_time"], ascending=[True, True, False])
        .drop_duplicates(["entry_idx", "direction"], keep="first")
        .reset_index(drop=True)
    )


def period_for_entry(timestamp: pd.Timestamp) -> tuple[str, pd.Timestamp | None]:
    if DISCOVERY_START <= timestamp < DISCOVERY_END:
        return "DISCOVERY", DISCOVERY_END
    if DISCOVERY_END <= timestamp < VALIDATION_END:
        return "VALIDATION", VALIDATION_END
    if timestamp >= VALIDATION_END:
        return "POST_2026_ENTRY_ONLY", None
    return "PRE_RESEARCH", None


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
            "exit_time": bar_time + pd.Timedelta(minutes=5),
            "exit_reason": reason,
            "pnl_pips": pnl_pips,
        }
    return {"outcome_status": "OPEN_AT_DATA_END"}


def evaluate(frame: pd.DataFrame, plans: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, plan in plans.iterrows():
        row = plan.to_dict()
        period, period_end = period_for_entry(pd.Timestamp(plan["entry_time"]))
        row["period"] = period
        if period == "POST_2026_ENTRY_ONLY":
            row["outcome_status"] = "NOT_EVALUATED"
        elif period in ("DISCOVERY", "VALIDATION") and period_end is not None:
            row.update(simulate(frame, plan, period_end))
        else:
            row["outcome_status"] = "NOT_IN_RESEARCH"
        rows.append(row)
    return pd.DataFrame(rows)


def metrics(group: pd.DataFrame) -> dict[str, Any]:
    resolved = group[group["outcome_status"] == "RESOLVED"].copy()
    if resolved.empty:
        return {"trades": 0}
    gross_profit = float(resolved.loc[resolved["pnl_pips"] > 0, "pnl_pips"].sum())
    gross_loss = float(-resolved.loc[resolved["pnl_pips"] < 0, "pnl_pips"].sum())
    equity = resolved.sort_values("entry_time")["pnl_pips"].cumsum()
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m5", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = read_m5(Path(args.m5))
    evaluated = evaluate(frame, generate_plans(frame))
    evaluated.to_csv(output_dir / "btc5_candidate_trade_ledger.csv", index=False)
    summary = [
        {"period": "DISCOVERY", **metrics(evaluated[evaluated["period"] == "DISCOVERY"])},
        {"period": "VALIDATION", **metrics(evaluated[evaluated["period"] == "VALIDATION"])},
        {
            "period": "COMBINED",
            **metrics(evaluated[evaluated["period"].isin(["DISCOVERY", "VALIDATION"])]),
        },
    ]
    pd.DataFrame(summary).to_csv(output_dir / "btc5_candidate_summary.csv", index=False)
    contract = {
        "candidate": "BTC5_TWO_PIVOT_P2_CLEAN_N_382_786",
        "post2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc5_candidate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(pd.DataFrame(summary).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
