#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gold_v3_308_mochipoyo_method_walkforward as stage308
import gold_v3_311_mochipoyo_and_independent_candidate_research as stage311
from gold_v3_289_feature_core import GOLD_FILES, read_candles

POINT_SIZE = 0.01
YEARS = (2024, 2025, 2026)


@dataclass(frozen=True)
class TrackSpec:
    name: str
    allowed_pairs: tuple[str, ...]
    cooldown_multiplier: int = 1


TRACKS = (
    TrackSpec("DEEP_EMA40_PULLBACK", ("M5_H4", "M15_H4", "H1_D1")),
    TrackSpec("ADX_RECLAIM_CONT", ("M5_H4", "M15_H4", "H1_D1")),
    TrackSpec("DONCHIAN_RETEST_CONT", ("M5_H4", "M15_H4")),
    TrackSpec("VOL_EXPANSION_BREAK", ("M5_H4", "M15_H4")),
    TrackSpec("FAILED_BREAK_RECLAIM", ("M5_H4", "M15_H4"), 2),
    TrackSpec("THREE_BAR_IMPULSE", ("M5_H4", "M15_H4")),
)

EXIT_PROFILES = (
    {"name": "RR1_25", "kind": "RR", "rr": 1.25},
    {"name": "RR1_5", "kind": "RR", "rr": 1.5},
    {"name": "RR2_0", "kind": "RR", "rr": 2.0},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--trades-csv", required=True)
    parser.add_argument("--selected-csv", required=True)
    parser.add_argument("--stage309-trades", default="")
    parser.add_argument("--stage313-trades", default="")
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    parser.add_argument("--top", type=int, default=250)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def adx(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    high_diff = frame.high.diff()
    low_diff = -frame.low.diff()
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0.0), 0.0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0.0), 0.0)
    previous = frame.close.shift(1)
    true_range = pd.concat(
        [
            frame.high - frame.low,
            (frame.high - previous).abs(),
            (frame.low - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_value = true_range.ewm(
        alpha=1.0 / period,
        adjust=False,
        min_periods=period,
    ).mean()
    plus_di = 100.0 * plus_dm.ewm(
        alpha=1.0 / period,
        adjust=False,
        min_periods=period,
    ).mean() / atr_value.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(
        alpha=1.0 / period,
        adjust=False,
        min_periods=period,
    ).mean() / atr_value.replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    work = stage311.add_research_features(frame)
    atr_value = work.atr14.replace(0.0, np.nan)
    work["adx14"] = adx(work, 14)
    work["adx_rise3"] = work.adx14 - work.adx14.shift(3)
    work["close_pos"] = (
        (work.close - work.low) / (work.high - work.low).replace(0.0, np.nan)
    ).clip(0.0, 1.0)
    work["upper_wick_atr"] = (
        work.high - work[["open", "close"]].max(axis=1)
    ) / atr_value
    work["lower_wick_atr"] = (
        work[["open", "close"]].min(axis=1) - work.low
    ) / atr_value
    work["inside_bar"] = (
        (work.high <= work.high.shift(1)) & (work.low >= work.low.shift(1))
    )
    work["recent_inside"] = (
        work.inside_bar.shift(1).rolling(4, min_periods=1).max().fillna(False).astype(bool)
    )
    work["atr_expansion_cross"] = (
        (work.atr_ratio >= 1.05)
        & (work.atr_ratio.shift(1).rolling(5, min_periods=1).min() <= 0.95)
    )
    work["deep_touch_long"] = (
        ((work.low - work.ema40) / atr_value)
        .rolling(8, min_periods=1)
        .min()
        <= 0.15
    )
    work["deep_touch_short"] = (
        ((work.high - work.ema40) / atr_value)
        .rolling(8, min_periods=1)
        .max()
        >= -0.15
    )
    work["ema20_reclaim_long"] = (
        (work.close > work.ema20) & (work.close.shift(1) <= work.ema20.shift(1))
    )
    work["ema20_reclaim_short"] = (
        (work.close < work.ema20) & (work.close.shift(1) >= work.ema20.shift(1))
    )
    work["three_up"] = (
        (work.close > work.open)
        & (work.close.shift(1) > work.open.shift(1))
        & (work.close.shift(2) > work.open.shift(2))
        & (work.close > work.close.shift(1))
        & (work.close.shift(1) > work.close.shift(2))
    )
    work["three_down"] = (
        (work.close < work.open)
        & (work.close.shift(1) < work.open.shift(1))
        & (work.close.shift(2) < work.open.shift(2))
        & (work.close < work.close.shift(1))
        & (work.close.shift(1) < work.close.shift(2))
    )
    work["three_body_long"] = (
        work.body_signed_atr
        + work.body_signed_atr.shift(1)
        + work.body_signed_atr.shift(2)
    )
    work["three_body_short"] = -work["three_body_long"]
    return work


def direction_columns(frame: pd.DataFrame, direction: int) -> dict[str, pd.Series]:
    if direction == 1:
        return {
            "htf_trend": frame.htf_bull_trend,
            "ltf_trend": frame.ltf_bull_trend,
            "rci_turn": frame.rci_turn_long,
            "htf_rci_turn": frame.htf_rci_turn_long,
            "macd_accel": frame.macd_accel_long,
            "reclaim": frame.ema20_reclaim_long,
            "deep_touch": frame.deep_touch_long,
            "breakout": frame.breakout_long,
            "sweep": frame.sweep_reclaim_long,
            "regular": frame.bull_regular_div | frame.htf_bull_regular_div,
            "extension": frame.extension_long_atr,
            "wick": frame.lower_wick_atr,
            "close_strength": frame.close_pos,
            "three": frame.three_up,
            "three_body": frame.three_body_long,
            "opposite_htf": frame.htf_bear_trend,
        }
    return {
        "htf_trend": frame.htf_bear_trend,
        "ltf_trend": frame.ltf_bear_trend,
        "rci_turn": frame.rci_turn_short,
        "htf_rci_turn": frame.htf_rci_turn_short,
        "macd_accel": frame.macd_accel_short,
        "reclaim": frame.ema20_reclaim_short,
        "deep_touch": frame.deep_touch_short,
        "breakout": frame.breakout_short,
        "sweep": frame.sweep_reclaim_short,
        "regular": frame.bear_regular_div | frame.htf_bear_regular_div,
        "extension": frame.extension_short_atr,
        "wick": frame.upper_wick_atr,
        "close_strength": 1.0 - frame.close_pos,
        "three": frame.three_down,
        "three_body": frame.three_body_short,
        "opposite_htf": frame.htf_bull_trend,
    }


def mask_and_quality(
    frame: pd.DataFrame,
    track: TrackSpec,
    direction: int,
) -> tuple[pd.Series, pd.Series]:
    c = direction_columns(frame, direction)
    not_climax = frame.not_climax & c["extension"].between(-0.30, 1.50)

    if track.name == "DEEP_EMA40_PULLBACK":
        mask = (
            c["htf_trend"]
            & c["deep_touch"]
            & c["reclaim"]
            & (c["rci_turn"] | c["macd_accel"])
            & frame.atr_ratio.ge(0.85)
            & not_climax
        )
        quality = (
            5.0
            + 1.5 * c["rci_turn"].astype(float)
            + 1.0 * c["macd_accel"].astype(float)
            + 1.0 * c["ltf_trend"].astype(float)
            + 1.0 * c["htf_rci_turn"].astype(float)
            + c["close_strength"].fillna(0.0)
        )
    elif track.name == "ADX_RECLAIM_CONT":
        mask = (
            c["htf_trend"]
            & c["ltf_trend"]
            & c["reclaim"]
            & c["macd_accel"]
            & frame.adx14.ge(22.0)
            & frame.adx_rise3.ge(1.0)
            & frame.atr_ratio.ge(0.90)
            & not_climax
        )
        quality = (
            5.0
            + (frame.adx14.clip(22.0, 40.0) - 22.0) / 9.0
            + frame.adx_rise3.clip(0.0, 6.0) / 3.0
            + 1.0 * c["rci_turn"].astype(float)
            + c["close_strength"].fillna(0.0)
        )
    elif track.name == "DONCHIAN_RETEST_CONT":
        recent_break = (
            c["breakout"].shift(1).rolling(10, min_periods=1).max().fillna(False).astype(bool)
        )
        if direction == 1:
            level = frame.rolling_high20
            retest = (
                (frame.low <= level + 0.20 * frame.atr14)
                & (frame.close >= level)
                & (frame.close > frame.open)
            )
        else:
            level = frame.rolling_low20
            retest = (
                (frame.high >= level - 0.20 * frame.atr14)
                & (frame.close <= level)
                & (frame.close < frame.open)
            )
        mask = (
            c["htf_trend"]
            & c["ltf_trend"]
            & recent_break
            & retest
            & (c["rci_turn"] | c["macd_accel"])
            & frame.atr_ratio.ge(0.90)
            & not_climax
        )
        quality = (
            6.0
            + 1.5 * c["rci_turn"].astype(float)
            + 1.0 * c["macd_accel"].astype(float)
            + c["close_strength"].fillna(0.0)
        )
    elif track.name == "VOL_EXPANSION_BREAK":
        mask = (
            c["htf_trend"]
            & c["ltf_trend"]
            & frame.atr_expansion_cross
            & c["breakout"]
            & frame.body_abs_atr.ge(0.45)
            & frame.range_atr.between(0.80, 1.80)
            & c["extension"].between(0.0, 1.50)
        )
        quality = (
            5.0
            + frame.body_abs_atr.clip(0.45, 1.20)
            + frame.range_atr.clip(0.80, 1.80)
            + 1.0 * frame.recent_inside.astype(float)
            + 1.0 * c["htf_rci_turn"].astype(float)
        )
    elif track.name == "FAILED_BREAK_RECLAIM":
        mask = (
            (~c["opposite_htf"])
            & c["sweep"]
            & c["wick"].ge(0.35)
            & c["close_strength"].ge(0.60)
            & (c["regular"] | c["rci_turn"] | c["htf_rci_turn"])
            & frame.atr_ratio.ge(0.90)
            & frame.range_atr.le(1.80)
        )
        quality = (
            5.0
            + 1.5 * c["regular"].astype(float)
            + 1.0 * c["rci_turn"].astype(float)
            + 1.0 * c["htf_rci_turn"].astype(float)
            + c["wick"].clip(0.35, 1.20)
            + c["close_strength"].fillna(0.0)
        )
    elif track.name == "THREE_BAR_IMPULSE":
        mask = (
            c["htf_trend"]
            & c["ltf_trend"]
            & c["three"]
            & c["three_body"].ge(1.0)
            & frame.atr_ratio.ge(0.90)
            & c["extension"].between(0.0, 1.50)
            & frame.range_atr.le(1.80)
        )
        quality = (
            5.0
            + c["three_body"].clip(1.0, 2.5)
            + frame.adx_rise3.clip(0.0, 6.0) / 3.0
            + 1.0 * frame.recent_inside.astype(float)
        )
    else:
        raise ValueError(track.name)

    mask = mask.fillna(False) & frame.atr14.notna()
    quality = quality.where(mask, 0.0).fillna(0.0)
    return mask, quality


def generate_signals(
    frame: pd.DataFrame,
    pair: stage308.PairSpec,
    track: TrackSpec,
) -> list[dict[str, Any]]:
    if pair.name not in track.allowed_pairs:
        return []
    signals: list[dict[str, Any]] = []
    for direction in (1, -1):
        mask, quality = mask_and_quality(frame, track, direction)
        onset = stage308.edge_with_cooldown(
            mask,
            pair.cooldown_bars * track.cooldown_multiplier,
        )
        for index in frame.index[onset]:
            row = frame.loc[index]
            signals.append(
                {
                    "pair": pair.name,
                    "main_tf": pair.main_tf,
                    "higher_tf": pair.higher_tf,
                    "setup": track.name,
                    "track": track.name,
                    "category": "INDEPENDENT_SECOND_SWEEP",
                    "direction": "LONG" if direction == 1 else "SHORT",
                    "direction_num": direction,
                    "signal_index": int(index),
                    "decision_dt": pd.Timestamp(row.close_time),
                    "quality_score": float(quality.loc[index]),
                    "atr_entry_context": float(row.atr14),
                    "last_swing_high": (
                        float(row.last_swing_high)
                        if pd.notna(row.last_swing_high)
                        else None
                    ),
                    "last_swing_low": (
                        float(row.last_swing_low)
                        if pd.notna(row.last_swing_low)
                        else None
                    ),
                    "round_number_near": bool(row.round_number_near),
                    "high_volatility": bool(row.moderate_or_high_volatility),
                    "atr_ratio_signal": float(row.atr_ratio),
                    "extension_atr_signal": float(
                        row.extension_long_atr if direction == 1 else row.extension_short_atr
                    ),
                    "adx14_signal": (
                        float(row.adx14) if pd.notna(row.adx14) else None
                    ),
                    "range_atr_signal": float(row.range_atr),
                }
            )
    return signals


def family_key(signal: dict[str, Any], exit_name: str) -> str:
    return "|".join(
        [signal["pair"], signal["track"], signal["direction"], exit_name]
    )


def load_reference(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["entry_dt", "exit_dt"])
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if not {"entry_dt", "exit_dt"}.issubset(frame.columns):
        return pd.DataFrame(columns=["entry_dt", "exit_dt"])
    frame["entry_dt"] = pd.to_datetime(frame.entry_dt, errors="coerce")
    frame["exit_dt"] = pd.to_datetime(frame.exit_dt, errors="coerce")
    return frame.dropna(subset=["entry_dt", "exit_dt"])


def select_distinct(
    leaderboard: list[dict[str, Any]],
    limit: int = 6,
) -> list[str]:
    selected: list[str] = []
    signal_contracts: set[str] = set()
    track_count: dict[str, int] = {}
    for row in leaderboard:
        if not row["gate"]["research_pass"]:
            continue
        signal_contract = "|".join(
            [row["pair"], row["track"], row["direction"]]
        )
        if signal_contract in signal_contracts:
            continue
        if track_count.get(row["track"], 0) >= 2:
            continue
        selected.append(row["family_key"])
        signal_contracts.add(signal_contract)
        track_count[row["track"]] = track_count.get(row["track"], 0) + 1
        if len(selected) >= limit:
            break
    return selected


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    trades_csv = Path(args.trades_csv).expanduser().resolve()
    selected_csv = Path(args.selected_csv).expanduser().resolve()
    stage309_path = (
        Path(args.stage309_trades).expanduser().resolve()
        if args.stage309_trades
        else candle_dir / "stage309_stage307_top_candidate_trades.csv"
    )
    stage313_path = (
        Path(args.stage313_trades).expanduser().resolve()
        if args.stage313_trades
        else candle_dir / "stage313_diversified_research_watch_trades.csv"
    )
    point_size = float(args.point_size)

    m1 = read_candles(
        candle_dir / GOLD_FILES["M1"],
        None,
        timeframe="M1",
        require_spread=True,
    ).copy()
    indicators: dict[str, pd.DataFrame] = {}
    for timeframe in ("M5", "M15", "H1", "H4", "D1"):
        indicators[timeframe] = stage308.indicator_frame(
            candle_dir,
            timeframe,
            point_size,
        )

    family_raw: dict[str, list[dict[str, Any]]] = {}
    signal_count = 0
    for pair in stage308.PAIR_SPECS:
        frame = stage308.build_signal_frame(
            indicators[pair.main_tf],
            indicators[pair.higher_tf],
        )
        frame = add_features(frame)
        for track in TRACKS:
            signals = generate_signals(frame, pair, track)
            signal_count += len(signals)
            for signal in signals:
                year = pd.Timestamp(signal["decision_dt"]).year
                if year not in YEARS:
                    continue
                for exit_profile in EXIT_PROFILES:
                    trade = stage308.simulate_trade(
                        signal,
                        frame,
                        m1,
                        pair,
                        exit_profile,
                        point_size,
                    )
                    if trade is None:
                        continue
                    key = family_key(signal, exit_profile["name"])
                    trade["family_key"] = key
                    family_raw.setdefault(key, []).append(trade)

    family_trades = {
        key: stage308.one_position(rows)
        for key, rows in family_raw.items()
    }
    leaderboard: list[dict[str, Any]] = []
    for key, rows in family_trades.items():
        pair_name, track_name, direction, exit_name = key.split("|", 3)
        development, yearly, gate = stage311.development_confirmation_metrics(rows)
        leaderboard.append(
            {
                "family_key": key,
                "pair": pair_name,
                "track": track_name,
                "direction": direction,
                "exit_profile": exit_name,
                "raw_trade_count": len(family_raw[key]),
                "aggregate": stage308.summarize(rows),
                "development_confirmation": development,
                "yearly": yearly,
                "gate": gate,
            }
        )
    leaderboard.sort(
        key=lambda row: (
            -int(row["gate"]["research_pass"]),
            -float(row["gate"]["robust_score_2024_2025_only"]),
            row["family_key"],
        )
    )

    selected_keys = select_distinct(leaderboard, 6)
    selected_raw: list[dict[str, Any]] = []
    for key in selected_keys:
        selected_raw.extend(family_trades[key])
    selected_portfolio = stage308.one_position(selected_raw)
    selected_development, selected_yearly, selected_gate = (
        stage311.development_confirmation_metrics(selected_portfolio)
    )

    all_rows: list[dict[str, Any]] = []
    for key, rows in family_trades.items():
        for row in rows:
            item = dict(row)
            item["family_key"] = key
            all_rows.append(item)
    trades_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(stage311.csv_safe_rows(all_rows)).to_csv(
        trades_csv,
        index=False,
        encoding="utf-8-sig",
    )
    selected_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(stage311.csv_safe_rows(selected_portfolio)).to_csv(
        selected_csv,
        index=False,
        encoding="utf-8-sig",
    )

    stage309_reference = load_reference(stage309_path)
    stage313_reference = load_reference(stage313_path)
    report = {
        "status": "GOLD_V3_315_SECOND_INDEPENDENT_CANDIDATE_SWEEP_COMPLETE",
        "mode": "AUDIT_ONLY_STANDALONE_RULE_BASED_RESEARCH",
        "decision": (
            "INDEPENDENT_RESEARCH_LEADS_FOUND"
            if any(row["gate"]["research_pass"] for row in leaderboard)
            else "NO_INDEPENDENT_RESEARCH_LEAD_FOUND"
        ),
        "research_contract": {
            "selection_years": [2024, 2025],
            "display_only_year": 2026,
            "selection_does_not_use_2026": True,
            "timeframe_pairs": [pair.name for pair in stage308.PAIR_SPECS],
            "tracks": [
                {"name": track.name, "allowed_pairs": list(track.allowed_pairs)}
                for track in TRACKS
            ],
            "exit_profiles": [row["name"] for row in EXIT_PROFILES],
            "gate_unchanged_from_stage311": True,
        },
        "search": {
            "signal_count": int(signal_count),
            "family_count": len(leaderboard),
            "research_pass_count": sum(
                bool(row["gate"]["research_pass"]) for row in leaderboard
            ),
            "balanced_pass_count": sum(
                bool(row["gate"]["balanced_pass"]) for row in leaderboard
            ),
        },
        "selected_portfolio": {
            "members": selected_keys,
            "raw_trade_count": len(selected_raw),
            "aggregate": stage308.summarize(selected_portfolio),
            "development_confirmation": selected_development,
            "yearly": selected_yearly,
            "gate": selected_gate,
        },
        "overlap": {
            "stage307_top": stage311.overlap_diagnostics(
                selected_portfolio,
                stage309_reference,
            ),
            "stage313_mochipoyo_watch": stage311.overlap_diagnostics(
                selected_portfolio,
                stage313_reference,
            ),
        },
        "passing_candidates": [
            row for row in leaderboard if row["gate"]["research_pass"]
        ][: int(args.top)],
        "leaderboard": leaderboard[: int(args.top)],
        "outputs": {
            "result_json": str(output),
            "all_trades_csv": str(trades_csv),
            "selected_trades_csv": str(selected_csv),
            "all_trades_sha256": sha256_file(trades_csv),
            "selected_trades_sha256": sha256_file(selected_csv),
        },
        "promotion": {
            "performed": False,
            "stage314_prospective_watch": "UNCHANGED_ACTIVE",
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage292_candidate_pool_changed": False,
        },
        "safety_flags": {
            "closed_candles_only": True,
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
