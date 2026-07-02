from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

SYMBOL = "BTCUSD#"
PIP_USD = 10.0
MIN_TP_PIPS = 50.0
MIN_TP_USD = PIP_USD * MIN_TP_PIPS
TIMEFRAME_HOURS = 4

DISCOVERY_START = pd.Timestamp("2024-07-03 00:00:00")
DISCOVERY_END = pd.Timestamp("2025-07-01 00:00:00")
VALIDATION_END = pd.Timestamp("2026-01-01 00:00:00")


@dataclass(frozen=True)
class Setup:
    cross_idx: int
    direction: str
    touch_idx: int | None
    trigger_idx: int | None
    invalid_idx: int | None
    status: str


@dataclass(frozen=True)
class Pivot:
    pivot_idx: int
    confirm_idx: int
    level: float


def _load_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["time"])
    required = {
        "time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    if frame["time"].duplicated().any():
        raise ValueError(f"{path}: duplicate time rows")
    if not frame["time"].is_monotonic_increasing:
        raise ValueError(f"{path}: time must be strictly increasing")
    return frame


def _add_h4_features(h4: pd.DataFrame) -> pd.DataFrame:
    frame = h4.copy()
    frame["decision_time"] = frame["time"] + pd.Timedelta(hours=TIMEFRAME_HOURS)
    frame["ema20"] = frame["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    frame["ema200"] = frame["close"].ewm(span=200, adjust=False, min_periods=200).mean()
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            (frame["high"] - frame["low"]).abs(),
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["atr14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    frame["cross_long"] = (
        (frame["ema20"] > frame["ema200"])
        & (frame["ema20"].shift(1) <= frame["ema200"].shift(1))
    )
    frame["cross_short"] = (
        (frame["ema20"] < frame["ema200"])
        & (frame["ema20"].shift(1) >= frame["ema200"].shift(1))
    )
    return frame


def _generate_setups(h4: pd.DataFrame, *, invalidate_on_wick: bool = False) -> list[Setup]:
    cross_indices = np.flatnonzero(
        (h4["cross_long"] | h4["cross_short"]).fillna(False).to_numpy()
    )
    setups: list[Setup] = []
    for cross_idx in cross_indices:
        direction = "LONG" if bool(h4.iloc[cross_idx]["cross_long"]) else "SHORT"
        touch_idx: int | None = None
        trigger_idx: int | None = None
        invalid_idx: int | None = None
        status = "NO_TOUCH"
        touch_high = np.nan
        touch_low = np.nan

        for idx in range(cross_idx + 1, len(h4)):
            row = h4.iloc[idx]
            if direction == "LONG":
                price_invalid = (
                    row["low"] < row["ema200"]
                    if invalidate_on_wick
                    else row["close"] < row["ema200"]
                )
                invalid = price_invalid or row["ema20"] < row["ema200"]
            else:
                price_invalid = (
                    row["high"] > row["ema200"]
                    if invalidate_on_wick
                    else row["close"] > row["ema200"]
                )
                invalid = price_invalid or row["ema20"] > row["ema200"]

            if invalid:
                invalid_idx = idx
                status = "INVALID_PRE_TOUCH" if touch_idx is None else "INVALID_POST_TOUCH"
                break

            if touch_idx is None:
                touched = (
                    row["low"] <= row["ema20"]
                    if direction == "LONG"
                    else row["high"] >= row["ema20"]
                )
                if touched:
                    touch_idx = idx
                    touch_high = float(row["high"])
                    touch_low = float(row["low"])
                    status = "TOUCHED"
                continue

            triggered = (
                row["close"] > touch_high
                if direction == "LONG"
                else row["close"] < touch_low
            )
            if triggered:
                trigger_idx = idx
                status = "TRIGGERED"
                break

        setups.append(
            Setup(
                cross_idx=int(cross_idx),
                direction=direction,
                touch_idx=touch_idx,
                trigger_idx=trigger_idx,
                invalid_idx=invalid_idx,
                status=status,
            )
        )
    return setups


def _causal_pivots(frame: pd.DataFrame, left: int, right: int) -> tuple[list[Pivot], list[Pivot]]:
    highs = frame["high"].to_numpy(float)
    lows = frame["low"].to_numpy(float)
    pivot_highs: list[Pivot] = []
    pivot_lows: list[Pivot] = []
    for idx in range(left, len(frame) - right):
        high_window = highs[idx - left : idx + right + 1]
        low_window = lows[idx - left : idx + right + 1]
        if highs[idx] == np.max(high_window) and np.sum(high_window == highs[idx]) == 1:
            pivot_highs.append(Pivot(idx, idx + right, float(highs[idx])))
        if lows[idx] == np.min(low_window) and np.sum(low_window == lows[idx]) == 1:
            pivot_lows.append(Pivot(idx, idx + right, float(lows[idx])))
    return pivot_highs, pivot_lows


def _linear_slope(values: Iterable[float]) -> float:
    array = np.asarray(list(values), dtype=float)
    if len(array) < 2 or not np.isfinite(array).all():
        return np.nan
    return float(np.polyfit(np.arange(len(array), dtype=float), array, 1)[0])


def _trend_flags(h4: pd.DataFrame, cross_idx: int, direction: str) -> dict[str, bool]:
    if cross_idx < 24:
        return {
            "V0_NO_FILTER": True,
            "V1_EMA_PERSIST_12": False,
            "V2_EMA200_SLOPE_24": False,
            "V3_SEPARATION_05ATR": False,
            "V4_BALANCED_2OF3": False,
            "V5_SWING_STRUCTURE": False,
        }
    pre12 = h4.iloc[cross_idx - 12 : cross_idx]
    pre24 = h4.iloc[cross_idx - 24 : cross_idx]
    previous = pre24.iloc[-16:-8]
    recent = pre24.iloc[-8:]

    if direction == "LONG":
        ema_persist = bool((pre12["ema20"] < pre12["ema200"]).all())
        ema200_slope = _linear_slope(pre24["ema200"]) < 0
        separation = float(((pre24["ema200"] - pre24["ema20"]) / pre24["atr14"]).max()) >= 0.5
        swing_structure = (
            recent["high"].max() < previous["high"].max()
            and recent["low"].min() < previous["low"].min()
        )
    else:
        ema_persist = bool((pre12["ema20"] > pre12["ema200"]).all())
        ema200_slope = _linear_slope(pre24["ema200"]) > 0
        separation = float(((pre24["ema20"] - pre24["ema200"]) / pre24["atr14"]).max()) >= 0.5
        swing_structure = (
            recent["high"].max() > previous["high"].max()
            and recent["low"].min() > previous["low"].min()
        )

    score = int(ema_persist) + int(ema200_slope) + int(separation)
    return {
        "V0_NO_FILTER": True,
        "V1_EMA_PERSIST_12": ema_persist,
        "V2_EMA200_SLOPE_24": bool(ema200_slope),
        "V3_SEPARATION_05ATR": bool(separation),
        "V4_BALANCED_2OF3": score >= 2,
        "V5_SWING_STRUCTURE": bool(swing_structure),
    }


def _target_levels(
    pivots: Sequence[Pivot],
    *,
    direction: str,
    trigger_idx: int,
    entry_bid: float,
    atr14: float,
    lookback_bars: int,
) -> list[float]:
    lower_bound = max(0, trigger_idx - lookback_bars)
    levels = [
        pivot.level
        for pivot in pivots
        if pivot.confirm_idx <= trigger_idx and pivot.pivot_idx >= lower_bound
    ]
    if direction == "LONG":
        levels = sorted(level for level in levels if level > entry_bid)
    else:
        levels = sorted((level for level in levels if level < entry_bid), reverse=True)

    cluster_tolerance = max(30.0, 0.1 * atr14)
    distinct: list[float] = []
    for level in levels:
        if not distinct or abs(level - distinct[-1]) > cluster_tolerance:
            distinct.append(float(level))
    return distinct


def _select_targets(
    levels: Sequence[float],
    *,
    direction: str,
    entry_bid: float,
    spread_usd: float,
    risk_net_usd: float,
    atr14: float,
) -> dict[str, float] | None:
    eligible: list[tuple[float, float]] = []
    all_levels: list[tuple[float, float]] = []
    for level in levels:
        net = (
            level - (entry_bid + spread_usd)
            if direction == "LONG"
            else entry_bid - (level + spread_usd)
        )
        all_levels.append((float(level), float(net)))
        if net >= MIN_TP_USD and net >= risk_net_usd:
            eligible.append((float(level), float(net)))
    if not eligible:
        return None

    tp1, tp1_net = eligible[0]
    minimum_distinct = max(30.0, 0.05 * atr14)
    farther = [(level, net) for level, net in all_levels if net > tp1_net + minimum_distinct]
    if not farther:
        return None
    tp2, tp2_net = farther[0]
    return {
        "tp1": tp1,
        "tp1_net_usd": tp1_net,
        "tp2": tp2,
        "tp2_net_usd": tp2_net,
    }


def _first_post_entry_invalidation(h4: pd.DataFrame, trigger_idx: int, direction: str) -> pd.Timestamp | None:
    for idx in range(trigger_idx + 1, len(h4)):
        row = h4.iloc[idx]
        invalid = (
            row["close"] < row["ema200"] or row["ema20"] < row["ema200"]
            if direction == "LONG"
            else row["close"] > row["ema200"] or row["ema20"] > row["ema200"]
        )
        if invalid:
            return pd.Timestamp(row["decision_time"])
    return None


def _build_plan(
    h4: pd.DataFrame,
    m5: pd.DataFrame,
    m5_lookup: dict[pd.Timestamp, int],
    setup: Setup,
    *,
    spread_usd: float,
    pivot_highs: Sequence[Pivot],
    pivot_lows: Sequence[Pivot],
    lookback_bars: int,
) -> dict[str, Any] | None:
    if setup.status != "TRIGGERED" or setup.touch_idx is None or setup.trigger_idx is None:
        return None
    cross_idx = setup.cross_idx
    touch_idx = setup.touch_idx
    trigger_idx = setup.trigger_idx
    direction = setup.direction
    decision_time = pd.Timestamp(h4.iloc[trigger_idx]["decision_time"])
    entry_idx = m5_lookup.get(decision_time)
    if entry_idx is None:
        return None

    entry_bid = float(m5.iloc[entry_idx]["open"])
    atr14 = float(h4.iloc[trigger_idx]["atr14"])
    buffer_usd = max(30.0, 0.1 * atr14)
    pullback = h4.iloc[touch_idx : trigger_idx + 1]
    stop_chart = (
        float(pullback["low"].min() - buffer_usd)
        if direction == "LONG"
        else float(pullback["high"].max() + buffer_usd)
    )
    risk_net = (
        entry_bid + spread_usd - stop_chart
        if direction == "LONG"
        else stop_chart + spread_usd - entry_bid
    )
    pivots = pivot_highs if direction == "LONG" else pivot_lows
    levels = _target_levels(
        pivots,
        direction=direction,
        trigger_idx=trigger_idx,
        entry_bid=entry_bid,
        atr14=atr14,
        lookback_bars=lookback_bars,
    )
    targets = _select_targets(
        levels,
        direction=direction,
        entry_bid=entry_bid,
        spread_usd=spread_usd,
        risk_net_usd=risk_net,
        atr14=atr14,
    )
    if targets is None:
        return None

    plan: dict[str, Any] = {
        "symbol": SYMBOL,
        "cross_idx": cross_idx,
        "touch_idx": touch_idx,
        "trigger_idx": trigger_idx,
        "direction": direction,
        "cross_open_time": pd.Timestamp(h4.iloc[cross_idx]["time"]),
        "cross_decision_time": pd.Timestamp(h4.iloc[cross_idx]["decision_time"]),
        "touch_open_time": pd.Timestamp(h4.iloc[touch_idx]["time"]),
        "trigger_open_time": pd.Timestamp(h4.iloc[trigger_idx]["time"]),
        "decision_time": decision_time,
        "entry_m5_idx": entry_idx,
        "entry_bid": entry_bid,
        "spread_usd": spread_usd,
        "atr14": atr14,
        "buffer_usd": buffer_usd,
        "stop_chart": stop_chart,
        "risk_net_usd": float(risk_net),
        "risk_pips": float(risk_net / PIP_USD),
        "cross_to_touch_h4_bars": touch_idx - cross_idx,
        "touch_to_trigger_h4_bars": trigger_idx - touch_idx,
        "post_entry_invalidation_time": _first_post_entry_invalidation(h4, trigger_idx, direction),
        **targets,
    }
    plan["tp1_pips"] = plan["tp1_net_usd"] / PIP_USD
    plan["tp2_pips"] = plan["tp2_net_usd"] / PIP_USD
    plan.update(_trend_flags(h4, cross_idx, direction))
    return plan


def _simulate(
    m5: pd.DataFrame,
    m5_lookup: dict[pd.Timestamp, int],
    plan: dict[str, Any],
    *,
    period_end: pd.Timestamp,
    close_on_ema200_invalidation: bool,
) -> dict[str, Any]:
    direction = str(plan["direction"])
    entry_idx = int(plan["entry_m5_idx"])
    entry = float(plan["entry_bid"])
    spread = float(plan["spread_usd"])
    stop = float(plan["stop_chart"])
    tp1 = float(plan["tp1"])
    tp2 = float(plan["tp2"])
    invalidation_time = plan.get("post_entry_invalidation_time")
    invalidation_idx = (
        m5_lookup.get(pd.Timestamp(invalidation_time))
        if invalidation_time is not None and not pd.isna(invalidation_time)
        else None
    )
    partial = False

    for idx in range(entry_idx, len(m5)):
        row = m5.iloc[idx]
        bar_open = pd.Timestamp(row["time"])
        if bar_open >= period_end:
            return {"outcome_status": "BOUNDARY_EXCLUDED"}

        if close_on_ema200_invalidation and invalidation_idx is not None and idx >= invalidation_idx:
            market = float(row["open"])
            remaining = (
                market - (entry + spread)
                if direction == "LONG"
                else entry - (market + spread)
            )
            pnl = 0.5 * float(plan["tp1_net_usd"]) + 0.5 * remaining if partial else remaining
            return {
                "outcome_status": "RESOLVED",
                "exit_time": bar_open,
                "exit_reason": "EMA200_INVALIDATION_AFTER_TP1" if partial else "EMA200_INVALIDATION",
                "pnl_net_usd": float(pnl),
                "pnl_pips": float(pnl / PIP_USD),
                "r_multiple": float(pnl / plan["risk_net_usd"]),
                "hold_hours": float((bar_open - plan["decision_time"]).total_seconds() / 3600),
            }

        high = float(row["high"])
        low = float(row["low"])
        bar_close_time = bar_open + pd.Timedelta(minutes=5)

        if not partial:
            stop_hit = low <= stop if direction == "LONG" else high >= stop
            tp1_hit = high >= tp1 if direction == "LONG" else low <= tp1
            tp2_hit = high >= tp2 if direction == "LONG" else low <= tp2
            if stop_hit:
                pnl = -float(plan["risk_net_usd"])
                return {
                    "outcome_status": "RESOLVED",
                    "exit_time": bar_close_time,
                    "exit_reason": "SL",
                    "pnl_net_usd": pnl,
                    "pnl_pips": pnl / PIP_USD,
                    "r_multiple": -1.0,
                    "hold_hours": float((bar_close_time - plan["decision_time"]).total_seconds() / 3600),
                }
            if tp2_hit:
                pnl = 0.5 * float(plan["tp1_net_usd"]) + 0.5 * float(plan["tp2_net_usd"])
                return {
                    "outcome_status": "RESOLVED",
                    "exit_time": bar_close_time,
                    "exit_reason": "TP1_AND_TP2",
                    "pnl_net_usd": pnl,
                    "pnl_pips": pnl / PIP_USD,
                    "r_multiple": pnl / float(plan["risk_net_usd"]),
                    "hold_hours": float((bar_close_time - plan["decision_time"]).total_seconds() / 3600),
                }
            if tp1_hit:
                partial = True
                break_even_chart = entry + spread if direction == "LONG" else entry - spread
                break_even_hit = low <= break_even_chart if direction == "LONG" else high >= break_even_chart
                if break_even_hit:
                    pnl = 0.5 * float(plan["tp1_net_usd"])
                    return {
                        "outcome_status": "RESOLVED",
                        "exit_time": bar_close_time,
                        "exit_reason": "TP1_THEN_BE_SAME_M5",
                        "pnl_net_usd": pnl,
                        "pnl_pips": pnl / PIP_USD,
                        "r_multiple": pnl / float(plan["risk_net_usd"]),
                        "hold_hours": float((bar_close_time - plan["decision_time"]).total_seconds() / 3600),
                    }
        else:
            break_even_chart = entry + spread if direction == "LONG" else entry - spread
            break_even_hit = low <= break_even_chart if direction == "LONG" else high >= break_even_chart
            tp2_hit = high >= tp2 if direction == "LONG" else low <= tp2
            if break_even_hit:
                pnl = 0.5 * float(plan["tp1_net_usd"])
                return {
                    "outcome_status": "RESOLVED",
                    "exit_time": bar_close_time,
                    "exit_reason": "TP1_THEN_BE",
                    "pnl_net_usd": pnl,
                    "pnl_pips": pnl / PIP_USD,
                    "r_multiple": pnl / float(plan["risk_net_usd"]),
                    "hold_hours": float((bar_close_time - plan["decision_time"]).total_seconds() / 3600),
                }
            if tp2_hit:
                pnl = 0.5 * float(plan["tp1_net_usd"]) + 0.5 * float(plan["tp2_net_usd"])
                return {
                    "outcome_status": "RESOLVED",
                    "exit_time": bar_close_time,
                    "exit_reason": "TP2",
                    "pnl_net_usd": pnl,
                    "pnl_pips": pnl / PIP_USD,
                    "r_multiple": pnl / float(plan["risk_net_usd"]),
                    "hold_hours": float((bar_close_time - plan["decision_time"]).total_seconds() / 3600),
                }

    return {"outcome_status": "UNRESOLVED"}


def _period_for_entry(entry_time: pd.Timestamp) -> tuple[str, pd.Timestamp | None]:
    if DISCOVERY_START <= entry_time < DISCOVERY_END:
        return "DISCOVERY", DISCOVERY_END
    if DISCOVERY_END <= entry_time < VALIDATION_END:
        return "VALIDATION", VALIDATION_END
    if entry_time >= VALIDATION_END:
        return "POST_2026_ENTRY_ONLY", None
    return "PRE_DISCOVERY", None


def _metrics(frame: pd.DataFrame) -> dict[str, float | int | None]:
    if frame.empty:
        return {
            "trades": 0,
            "total_pips": None,
            "average_pips": None,
            "profit_factor": None,
            "win_rate_pct": None,
            "average_r": None,
            "max_drawdown_pips": None,
        }
    ordered = frame.sort_values("exit_time")
    pnl = ordered["pnl_net_usd"].to_numpy(float)
    positive = float(pnl[pnl > 0].sum())
    negative = float(-pnl[pnl < 0].sum())
    equity = np.r_[0.0, np.cumsum(pnl)]
    peak = np.maximum.accumulate(equity)
    return {
        "trades": int(len(ordered)),
        "total_pips": float(pnl.sum() / PIP_USD),
        "average_pips": float(pnl.mean() / PIP_USD),
        "profit_factor": float(positive / negative) if negative > 0 else None,
        "win_rate_pct": float((pnl > 0).mean() * 100),
        "average_r": float(ordered["r_multiple"].mean()),
        "max_drawdown_pips": float((peak - equity).max() / PIP_USD),
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if pd.isna(value):
        return None
    raise TypeError(type(value).__name__)


def _serialise_times(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in output.columns:
        if pd.api.types.is_datetime64_any_dtype(output[column]):
            output[column] = output[column].dt.strftime("%Y-%m-%d %H:%M:%S")
    return output


def run(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = Path(args.data_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    h4 = _add_h4_features(_load_csv(data_dir / "btcusdsharp_h4.csv"))
    m5 = _load_csv(data_dir / "btcusdsharp_m5.csv")
    m5_lookup = {pd.Timestamp(value): idx for idx, value in enumerate(m5["time"])}

    setups = _generate_setups(h4, invalidate_on_wick=args.invalidate_on_wick)
    pivot_highs, pivot_lows = _causal_pivots(h4, args.pivot_bars, args.pivot_bars)

    plans: list[dict[str, Any]] = []
    for setup in setups:
        plan = _build_plan(
            h4,
            m5,
            m5_lookup,
            setup,
            spread_usd=args.spread_usd,
            pivot_highs=pivot_highs,
            pivot_lows=pivot_lows,
            lookback_bars=args.lookback_bars,
        )
        if plan is not None:
            plans.append(plan)

    resolved: list[dict[str, Any]] = []
    entry_only: list[dict[str, Any]] = []
    for plan in plans:
        period, period_end = _period_for_entry(pd.Timestamp(plan["decision_time"]))
        base = {**plan, "period": period}
        if period_end is None:
            entry_only.append({**base, "outcome_status": "NOT_EVALUATED"})
            continue
        outcome = _simulate(
            m5,
            m5_lookup,
            plan,
            period_end=period_end,
            close_on_ema200_invalidation=args.close_on_ema200_invalidation,
        )
        if outcome.get("outcome_status") == "RESOLVED":
            resolved.append({**base, **outcome})
        else:
            entry_only.append({**base, **outcome})

    resolved_frame = pd.DataFrame(resolved)
    entry_frame = pd.DataFrame(entry_only)

    variants = [
        "V0_NO_FILTER",
        "V1_EMA_PERSIST_12",
        "V2_EMA200_SLOPE_24",
        "V3_SEPARATION_05ATR",
        "V4_BALANCED_2OF3",
        "V5_SWING_STRUCTURE",
    ]
    comparison_rows: list[dict[str, Any]] = []
    for variant in variants:
        for period in ("DISCOVERY", "VALIDATION", "COMBINED"):
            selected = resolved_frame[resolved_frame[variant].astype(bool)] if not resolved_frame.empty else resolved_frame
            if period != "COMBINED":
                selected = selected[selected["period"] == period]
            comparison_rows.append(
                {"variant": variant, "period": period, **_metrics(selected)}
            )
    comparison = pd.DataFrame(comparison_rows)

    setup_counts = pd.Series([setup.status for setup in setups]).value_counts().to_dict()
    summary = {
        "stage": "BTC3_VIDEO_EMA_METHOD_EXPLORATION_RESEARCH_ONLY",
        "symbol": SYMBOL,
        "pip_contract": "$10 price movement = 1 pip",
        "minimum_tp_pips": MIN_TP_PIPS,
        "time_contract": "CSV time is bar open; H4 decision is time+4h; entry is exact M5 open at decision",
        "spread_usd": args.spread_usd,
        "pivot_bars": args.pivot_bars,
        "lookback_bars": args.lookback_bars,
        "invalidate_on_wick": bool(args.invalidate_on_wick),
        "close_on_ema200_invalidation": bool(args.close_on_ema200_invalidation),
        "setup_counts": setup_counts,
        "planned_entries": len(plans),
        "resolved_pre_2026": len(resolved_frame),
        "post_2026_outcomes_evaluated": False,
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
        "trend_comparison": comparison.to_dict("records"),
    }

    _serialise_times(resolved_frame).to_csv(
        output_dir / "btc3_video_ema_trade_ledger_pre2026.csv", index=False
    )
    _serialise_times(entry_frame).to_csv(
        output_dir / "btc3_video_ema_entry_only_and_boundary_excluded.csv", index=False
    )
    comparison.to_csv(output_dir / "btc3_video_ema_trend_comparison.csv", index=False)
    (output_dir / "btc3_video_ema_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="Files")
    parser.add_argument("--output-dir", default="Files/btc3_video_ema_results")
    parser.add_argument("--spread-usd", type=float, default=30.0)
    parser.add_argument("--pivot-bars", type=int, default=3)
    parser.add_argument("--lookback-bars", type=int, default=500)
    parser.add_argument("--invalidate-on-wick", action="store_true")
    parser.add_argument(
        "--no-close-on-ema200-invalidation",
        dest="close_on_ema200_invalidation",
        action="store_false",
    )
    parser.set_defaults(close_on_ema200_invalidation=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
