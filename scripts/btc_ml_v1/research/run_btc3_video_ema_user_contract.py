from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

import numpy as np
import pandas as pd

import btc3_video_ema_method_exploration as engine
import mt5_indicator_compat as mt5_compat

MINIMUM_H4_WARMUP_BARS = 1500


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    applied_parser = argparse.ArgumentParser(add_help=False)
    applied_parser.add_argument(
        "--ema-applied-price",
        choices=mt5_compat.EMA_APPLIED_PRICE_CHOICES,
        required=True,
        help="Use the exact MT5 EMA Applied to setting; do not choose from backtest performance.",
    )
    applied, remaining = applied_parser.parse_known_args(argv)
    args = engine.parse_args(remaining)
    args.ema_applied_price = applied.ema_applied_price
    # User contract: EMA200 invalidation exists only before entry.
    # After entry, exits are the structural SL, TP1, break-even after TP1, and TP2.
    args.close_on_ema200_invalidation = False
    return args


def _add_h4_features(h4: pd.DataFrame, *, ema_applied_price: str) -> pd.DataFrame:
    mt5_compat.require_h4_warmup(
        h4,
        research_start=engine.DISCOVERY_START,
        minimum_closed_bars=MINIMUM_H4_WARMUP_BARS,
    )
    return mt5_compat.add_h4_features_mt5(
        h4,
        ema_applied_price=ema_applied_price,
    )


def _setup_invalid_before_entry(row: pd.Series, direction: str, *, invalidate_on_wick: bool) -> bool:
    if direction == "LONG":
        price_invalid = (
            row["low"] < row["ema200"]
            if invalidate_on_wick
            else row["close"] < row["ema200"]
        )
        return bool(price_invalid or row["ema20"] < row["ema200"])
    price_invalid = (
        row["high"] > row["ema200"]
        if invalidate_on_wick
        else row["close"] > row["ema200"]
    )
    return bool(price_invalid or row["ema20"] > row["ema200"])


def _wick_respects_ema200(row: pd.Series, direction: str) -> bool:
    """A basis candle may touch EMA20, but its wick must stay on the trend side of EMA200."""
    if direction == "LONG":
        return bool(row["low"] >= row["ema200"])
    return bool(row["high"] <= row["ema200"])


def _generate_setups(h4: pd.DataFrame, *, invalidate_on_wick: bool = False) -> list[engine.Setup]:
    cross_indices = np.flatnonzero(
        (h4["cross_long"] | h4["cross_short"]).fillna(False).to_numpy()
    )
    setups: list[engine.Setup] = []

    for cross_idx in cross_indices:
        direction = "LONG" if bool(h4.iloc[cross_idx]["cross_long"]) else "SHORT"
        touch_idx: int | None = None
        trigger_idx: int | None = None
        invalid_idx: int | None = None
        touch_high = np.nan
        touch_low = np.nan
        status = "NO_VALID_TOUCH"

        for idx in range(cross_idx + 1, len(h4)):
            row = h4.iloc[idx]
            if _setup_invalid_before_entry(row, direction, invalidate_on_wick=invalidate_on_wick):
                invalid_idx = idx
                status = "INVALID_BEFORE_ENTRY"
                break

            wick_crossed_ema200 = not _wick_respects_ema200(row, direction)
            if touch_idx is not None and wick_crossed_ema200:
                touch_idx = None
                touch_high = np.nan
                touch_low = np.nan
                status = "WAITING_NEXT_VALID_TOUCH"
                continue

            if touch_idx is None:
                touched_ema20 = (
                    row["low"] <= row["ema20"]
                    if direction == "LONG"
                    else row["high"] >= row["ema20"]
                )
                if touched_ema20 and _wick_respects_ema200(row, direction):
                    touch_idx = idx
                    touch_high = float(row["high"])
                    touch_low = float(row["low"])
                    status = "VALID_TOUCH"
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
            engine.Setup(
                cross_idx=int(cross_idx),
                direction=direction,
                touch_idx=touch_idx,
                trigger_idx=trigger_idx,
                invalid_idx=invalid_idx,
                status=status,
            )
        )
    return setups


def _structural_stop(h4: pd.DataFrame, touch_idx: int, direction: str) -> tuple[float, float, float]:
    touch = h4.iloc[touch_idx]
    atr14 = float(touch["atr14"])
    buffer_usd = max(30.0, 0.1 * atr14)
    if direction == "LONG":
        anchor = min(float(touch["low"]), float(touch["ema200"]))
        stop_chart = anchor - buffer_usd
    else:
        anchor = max(float(touch["high"]), float(touch["ema200"]))
        stop_chart = anchor + buffer_usd
    return float(anchor), float(buffer_usd), float(stop_chart)


def _build_plan(
    h4: pd.DataFrame,
    m5: pd.DataFrame,
    m5_lookup: dict[pd.Timestamp, int],
    setup: engine.Setup,
    *,
    spread_usd: float,
    pivot_highs: Sequence[engine.Pivot],
    pivot_lows: Sequence[engine.Pivot],
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
    trigger_atr14 = float(h4.iloc[trigger_idx]["atr14"])
    stop_anchor, buffer_usd, stop_chart = _structural_stop(h4, touch_idx, direction)
    risk_net = (
        entry_bid + spread_usd - stop_chart
        if direction == "LONG"
        else stop_chart + spread_usd - entry_bid
    )
    if risk_net <= 0:
        return None

    pivots = pivot_highs if direction == "LONG" else pivot_lows
    levels = engine._target_levels(
        pivots,
        direction=direction,
        trigger_idx=trigger_idx,
        entry_bid=entry_bid,
        atr14=trigger_atr14,
        lookback_bars=lookback_bars,
    )
    targets = engine._select_targets(
        levels,
        direction=direction,
        entry_bid=entry_bid,
        spread_usd=spread_usd,
        risk_net_usd=risk_net,
        atr14=trigger_atr14,
    )
    if targets is None:
        return None

    plan: dict[str, Any] = {
        "symbol": engine.SYMBOL,
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
        "atr14": trigger_atr14,
        "touch_atr14": float(h4.iloc[touch_idx]["atr14"]),
        "touch_ema20": float(h4.iloc[touch_idx]["ema20"]),
        "touch_ema200": float(h4.iloc[touch_idx]["ema200"]),
        "stop_anchor": stop_anchor,
        "stop_anchor_rule": "VALID_TOUCH_EMA200_SIDE_PLUS_BUFFER",
        "buffer_usd": buffer_usd,
        "stop_chart": stop_chart,
        "risk_net_usd": float(risk_net),
        "risk_pips": float(risk_net / engine.PIP_USD),
        "cross_to_touch_h4_bars": touch_idx - cross_idx,
        "touch_to_trigger_h4_bars": trigger_idx - touch_idx,
        "post_entry_invalidation_time": None,
        **targets,
    }
    plan["tp1_pips"] = plan["tp1_net_usd"] / engine.PIP_USD
    plan["tp2_pips"] = plan["tp2_net_usd"] / engine.PIP_USD
    plan.update(engine._trend_flags(h4, cross_idx, direction))
    return plan


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not hasattr(args, "ema_applied_price"):
        raise ValueError("ema_applied_price must be explicitly supplied from the MT5 indicator setting")
    args.close_on_ema200_invalidation = False
    original_add_h4_features = engine._add_h4_features
    original_generate_setups = engine._generate_setups
    original_build_plan = engine._build_plan
    try:
        engine._add_h4_features = lambda h4: _add_h4_features(
            h4,
            ema_applied_price=args.ema_applied_price,
        )
        engine._generate_setups = _generate_setups
        engine._build_plan = _build_plan
        result = engine.run(args)
    finally:
        engine._add_h4_features = original_add_h4_features
        engine._generate_setups = original_generate_setups
        engine._build_plan = original_build_plan

    result["indicator_contract"] = "MT5_SMA_SEEDED_EMA_AND_WILDER_ATR"
    result["ema_applied_price"] = args.ema_applied_price
    result["minimum_h4_warmup_bars"] = MINIMUM_H4_WARMUP_BARS
    result["pre_entry_ema200_invalidation_only"] = True
    result["post_entry_exit_contract"] = "STRUCTURAL_SL_TP_ONLY_NO_EMA200_EXIT"
    result["valid_touch_contract"] = (
        "EMA20 touch is accepted only when the wick stays on the trend side of EMA200; "
        "a wick through EMA200 discards that basis candle and waits for the next valid touch"
    )
    result["stop_contract"] = (
        "stop beyond the valid-touch EMA200/structure anchor by max($30, 0.1*touch ATR14)"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=engine._json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
