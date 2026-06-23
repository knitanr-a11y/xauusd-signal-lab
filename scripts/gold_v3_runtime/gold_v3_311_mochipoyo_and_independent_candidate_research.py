#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gold_v3_308_mochipoyo_method_walkforward as stage308
from gold_v3_289_feature_core import GOLD_FILES, read_candles

YEARS = (2024, 2025, 2026)
DEVELOPMENT_CONFIRMATION_YEARS = (2024, 2025)
POINT_SIZE = 0.01


@dataclass(frozen=True)
class TrackSpec:
    name: str
    category: str
    allowed_pairs: tuple[str, ...]
    cooldown_multiplier: int = 1


TRACK_SPECS = (
    TrackSpec(
        "MOCHI_EARLY_PULLBACK",
        "MOCHIPOYO",
        ("M5_H4", "M15_H4", "H1_D1"),
    ),
    TrackSpec(
        "MOCHI_HIDDEN_PULLBACK",
        "MOCHIPOYO",
        ("M5_H4", "M15_H4", "H1_D1"),
    ),
    TrackSpec(
        "MOCHI_HTF_RCI_RESUME",
        "MOCHIPOYO",
        ("M5_H4", "M15_H4", "H1_D1"),
    ),
    TrackSpec(
        "MOCHI_ROLL_RETEST",
        "MOCHIPOYO",
        ("M5_H4", "M15_H4"),
    ),
    TrackSpec(
        "COMPRESSION_BREAKOUT_CONT",
        "INDEPENDENT",
        ("M5_H4", "M15_H4"),
    ),
    TrackSpec(
        "SWEEP_RECLAIM_REVERSAL",
        "INDEPENDENT",
        ("M5_H4", "M15_H4"),
        cooldown_multiplier=2,
    ),
)

EXIT_PROFILES = (
    {"name": "RR1_25", "kind": "RR", "rr": 1.25},
    {"name": "RR1_5", "kind": "RR", "rr": 1.5},
    {"name": "RCI_OPPOSITE70", "kind": "RCI", "rr": None},
    {"name": "STRUCT_TARGET", "kind": "STRUCT", "rr": None},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--trades-csv", default="")
    parser.add_argument("--selected-trades-csv", default="")
    parser.add_argument("--stage309-trades", default="")
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    parser.add_argument("--top", type=int, default=250)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pf_value(summary: dict[str, Any]) -> float:
    value = summary.get("spread_adjusted_profit_factor")
    if value is None and float(summary.get("spread_adjusted_total_usd", 0.0)) > 0.0:
        return float("inf")
    return float(value or 0.0)


def add_research_features(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    atr = work.atr14.replace(0.0, np.nan)
    work["range_atr"] = (work.high - work.low) / atr
    work["body_signed_atr"] = (work.close - work.open) / atr
    work["body_abs_atr"] = work.body_signed_atr.abs()
    work["extension_long_atr"] = (work.close - work.ema20) / atr
    work["extension_short_atr"] = (work.ema20 - work.close) / atr

    previous_range = work.range_atr.shift(1)
    short_range = previous_range.rolling(8, min_periods=6).mean()
    long_range = previous_range.rolling(40, min_periods=20).median()
    work["compression_ratio"] = short_range / long_range.replace(0.0, np.nan)

    prior_high = work.rolling_high20
    prior_low = work.rolling_low20
    work["breakout_long"] = (
        (work.close > prior_high)
        & (work.close.shift(1) <= prior_high.shift(1))
        & (work.body_signed_atr > 0.20)
    )
    work["breakout_short"] = (
        (work.close < prior_low)
        & (work.close.shift(1) >= prior_low.shift(1))
        & (work.body_signed_atr < -0.20)
    )
    work["sweep_reclaim_long"] = (
        (work.low < prior_low)
        & (work.close > prior_low)
        & (work.close > work.open)
        & (work.body_signed_atr > 0.10)
    )
    work["sweep_reclaim_short"] = (
        (work.high > prior_high)
        & (work.close < prior_high)
        & (work.close < work.open)
        & (work.body_signed_atr < -0.10)
    )

    work["not_climax"] = (
        (work.atr_ratio <= 1.80)
        & (work.range_atr <= 1.60)
        & (work.body_abs_atr <= 1.20)
    )
    work["moderate_or_high_volatility"] = (
        (work.atr_ratio >= 0.90)
        & ((work.zigzag_wave_atr >= 1.10) | (work.atr_ratio >= 1.05))
    )
    return work


def extension(frame: pd.DataFrame, direction: int) -> pd.Series:
    return frame.extension_long_atr if direction == 1 else frame.extension_short_atr


def track_mask(
    frame: pd.DataFrame,
    track: TrackSpec,
    direction: int,
) -> tuple[pd.Series, pd.Series]:
    htf_trend = frame.htf_bull_trend if direction == 1 else frame.htf_bear_trend
    ltf_trend = frame.ltf_bull_trend if direction == 1 else frame.ltf_bear_trend
    hidden = (
        (frame.bull_hidden_div | frame.htf_bull_hidden_div)
        if direction == 1
        else (frame.bear_hidden_div | frame.htf_bear_hidden_div)
    )
    regular = (
        (frame.bull_regular_div | frame.htf_bull_regular_div)
        if direction == 1
        else (frame.bear_regular_div | frame.htf_bear_regular_div)
    )
    htf_turn = frame.htf_rci_turn_long if direction == 1 else frame.htf_rci_turn_short
    rci_turn = frame.rci_turn_long if direction == 1 else frame.rci_turn_short
    macd_accel = frame.macd_accel_long if direction == 1 else frame.macd_accel_short
    pullback = frame.pullback_long if direction == 1 else frame.pullback_short
    roll_retest = frame.roll_reversal_long if direction == 1 else frame.roll_reversal_short
    breakout = frame.breakout_long if direction == 1 else frame.breakout_short
    sweep = frame.sweep_reclaim_long if direction == 1 else frame.sweep_reclaim_short
    opposite_htf = frame.htf_bear_trend if direction == 1 else frame.htf_bull_trend
    ext = extension(frame, direction)

    if track.name == "MOCHI_EARLY_PULLBACK":
        mask = (
            htf_trend
            & ltf_trend
            & frame.moderate_or_high_volatility
            & frame.not_climax
            & pullback
            & macd_accel
            & (rci_turn | hidden)
            & ext.between(-0.25, 0.80)
        )
        quality = (
            5.0
            + 1.0 * rci_turn.astype(float)
            + 1.5 * hidden.astype(float)
            + 1.0 * htf_turn.astype(float)
            + 1.0 * roll_retest.astype(float)
            + (0.80 - ext.clip(lower=-0.25, upper=0.80))
        )
    elif track.name == "MOCHI_HIDDEN_PULLBACK":
        mask = (
            htf_trend
            & ltf_trend
            & frame.moderate_or_high_volatility
            & frame.not_climax
            & pullback
            & hidden
            & (rci_turn | macd_accel)
            & ext.between(-0.35, 1.00)
        )
        quality = (
            6.0
            + 1.5 * rci_turn.astype(float)
            + 1.0 * macd_accel.astype(float)
            + 1.0 * htf_turn.astype(float)
            + 1.0 * roll_retest.astype(float)
        )
    elif track.name == "MOCHI_HTF_RCI_RESUME":
        mask = (
            htf_trend
            & ltf_trend
            & frame.moderate_or_high_volatility
            & frame.not_climax
            & htf_turn
            & rci_turn
            & macd_accel
            & ext.between(-0.35, 1.00)
        )
        quality = (
            6.0
            + 1.0 * hidden.astype(float)
            + 1.0 * pullback.astype(float)
            + 1.0 * roll_retest.astype(float)
        )
    elif track.name == "MOCHI_ROLL_RETEST":
        mask = (
            htf_trend
            & ltf_trend
            & frame.moderate_or_high_volatility
            & frame.not_climax
            & roll_retest
            & macd_accel
            & (rci_turn | hidden)
            & ext.between(-0.20, 1.00)
        )
        quality = (
            6.0
            + 1.5 * rci_turn.astype(float)
            + 1.5 * hidden.astype(float)
            + 1.0 * htf_turn.astype(float)
        )
    elif track.name == "COMPRESSION_BREAKOUT_CONT":
        mask = (
            htf_trend
            & ltf_trend
            & frame.moderate_or_high_volatility
            & (frame.compression_ratio <= 0.78)
            & breakout
            & (frame.range_atr >= 0.80)
            & (frame.range_atr <= 1.80)
            & ext.between(0.0, 1.50)
        )
        quality = (
            5.0
            + (0.78 - frame.compression_ratio.clip(lower=0.20, upper=0.78)) * 4.0
            + frame.range_atr.clip(lower=0.80, upper=1.80)
            + 1.0 * htf_turn.astype(float)
        )
    elif track.name == "SWEEP_RECLAIM_REVERSAL":
        mask = (
            (~opposite_htf)
            & frame.moderate_or_high_volatility
            & frame.not_climax
            & sweep
            & (regular | htf_turn)
            & (rci_turn | macd_accel)
            & ext.abs().le(1.10)
        )
        quality = (
            5.0
            + 2.0 * regular.astype(float)
            + 1.5 * htf_turn.astype(float)
            + 1.0 * rci_turn.astype(float)
            + 1.0 * macd_accel.astype(float)
        )
    else:
        raise ValueError(track.name)

    mask = mask.fillna(False) & frame.atr14.notna()
    quality = quality.where(mask, 0.0).fillna(0.0)
    return mask, quality


def generate_track_signals(
    frame: pd.DataFrame,
    pair: stage308.PairSpec,
    track: TrackSpec,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    if pair.name not in track.allowed_pairs:
        return signals

    for direction in (1, -1):
        mask, quality = track_mask(frame, track, direction)
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
                    "category": track.category,
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
                    "compression_ratio_signal": (
                        float(row.compression_ratio)
                        if pd.notna(row.compression_ratio)
                        else None
                    ),
                    "range_atr_signal": float(row.range_atr),
                }
            )
    return signals


def family_key(signal: dict[str, Any], exit_name: str) -> str:
    return "|".join(
        (
            str(signal["pair"]),
            str(signal["track"]),
            str(signal["direction"]),
            exit_name,
        )
    )


def development_confirmation_metrics(
    trades: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    selected = [
        row
        for row in trades
        if pd.Timestamp(row["entry_dt"]).year in DEVELOPMENT_CONFIRMATION_YEARS
    ]
    summary = stage308.summarize(selected)
    yearly = stage308.yearly_summary(trades)
    y2024 = yearly["2024"]
    y2025 = yearly["2025"]
    minimum_count = min(int(y2024["trades"]), int(y2025["trades"]))
    minimum_pf = min(pf_value(y2024), pf_value(y2025))
    minimum_r = min(
        float(y2024["spread_adjusted_total_r"]),
        float(y2025["spread_adjusted_total_r"]),
    )
    combined_pf = pf_value(summary)
    largest_share = float(summary.get("largest_win_share_of_positive_pnl") or 0.0)

    research_pass = bool(
        summary["trades"] >= 30
        and minimum_count >= 10
        and minimum_pf >= 1.10
        and minimum_r > 0.0
        and combined_pf >= 1.25
        and summary["spread_adjusted_total_r"] > 0.0
        and summary["spread_adjusted_max_drawdown_r"] <= 10.0
        and largest_share <= 0.40
    )
    balanced_pass = bool(
        summary["trades"] >= 50
        and minimum_count >= 15
        and minimum_pf >= 1.15
        and minimum_r > 0.0
        and combined_pf >= 1.30
        and summary["win_rate"] >= 0.48
        and summary["spread_adjusted_max_drawdown_r"] <= 9.0
        and largest_share <= 0.35
    )
    all_year_positive = bool(
        research_pass
        and yearly["2026"]["trades"] >= 5
        and float(yearly["2026"]["spread_adjusted_total_r"]) > 0.0
    )

    finite_min_pf = minimum_pf if math.isfinite(minimum_pf) else 5.0
    robust_score = (
        10.0 * min(finite_min_pf, 5.0)
        + float(summary["spread_adjusted_total_r"])
        + 0.05 * float(summary["trades"])
        - 0.75 * float(summary["spread_adjusted_max_drawdown_r"])
        - 5.0 * max(0.0, largest_share - 0.25)
    )
    gate = {
        "research_pass": research_pass,
        "balanced_pass": balanced_pass,
        "all_year_positive_flag": all_year_positive,
        "development_confirmation_minimum_count": minimum_count,
        "development_confirmation_minimum_pf": minimum_pf,
        "development_confirmation_minimum_r": minimum_r,
        "robust_score_2024_2025_only": float(robust_score),
    }
    return summary, yearly, gate


def select_leads(
    leaderboard: list[dict[str, Any]],
    category: str | None,
    limit: int,
) -> list[str]:
    candidates = [
        row
        for row in leaderboard
        if row["gate"]["research_pass"]
        and (category is None or row["category"] == category)
    ]
    candidates.sort(
        key=lambda row: (
            -float(row["gate"]["robust_score_2024_2025_only"]),
            row["family_key"],
        )
    )
    selected: list[str] = []
    used_signal_contracts: set[str] = set()
    used_tracks: dict[str, int] = {}
    for row in candidates:
        signal_contract = "|".join(
            (row["pair"], row["track"], row["direction"])
        )
        if signal_contract in used_signal_contracts:
            continue
        if used_tracks.get(row["track"], 0) >= 2:
            continue
        selected.append(row["family_key"])
        used_signal_contracts.add(signal_contract)
        used_tracks[row["track"]] = used_tracks.get(row["track"], 0) + 1
        if len(selected) >= limit:
            break
    return selected


def pool_result(
    name: str,
    members: list[str],
    family_trades: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    raw: list[dict[str, Any]] = []
    for member in members:
        raw.extend(family_trades[member])
    portfolio = stage308.one_position(raw)
    summary, yearly, gate = development_confirmation_metrics(portfolio)
    return {
        "pool": name,
        "members": members,
        "raw_trade_count": len(raw),
        "aggregate": stage308.summarize(portfolio),
        "development_confirmation": summary,
        "yearly": yearly,
        "gate": gate,
        "portfolio_trades": portfolio,
    }


def overlap_diagnostics(
    left: list[dict[str, Any]],
    right: pd.DataFrame,
) -> dict[str, Any]:
    if right.empty or not left:
        return {
            "available": not right.empty,
            "left_trades": len(left),
            "right_trades": int(len(right)),
            "exact_entry_overlap": 0,
            "overlapping_interval_pairs": 0,
            "left_trades_with_any_overlap": 0,
        }
    left_frame = pd.DataFrame(
        {
            "entry_dt": [pd.Timestamp(row["entry_dt"]) for row in left],
            "exit_dt": [pd.Timestamp(row["exit_dt"]) for row in left],
        }
    )
    right_frame = right[["entry_dt", "exit_dt"]].copy()
    exact = set(left_frame.entry_dt) & set(right_frame.entry_dt)
    pairs = 0
    left_with_overlap = 0
    for row in left_frame.itertuples():
        mask = right_frame.entry_dt.lt(row.exit_dt) & right_frame.exit_dt.gt(row.entry_dt)
        count = int(mask.sum())
        pairs += count
        if count:
            left_with_overlap += 1
    return {
        "available": True,
        "left_trades": int(len(left_frame)),
        "right_trades": int(len(right_frame)),
        "exact_entry_overlap": int(len(exact)),
        "overlapping_interval_pairs": int(pairs),
        "left_trades_with_any_overlap": int(left_with_overlap),
        "left_trades_without_overlap": int(len(left_frame) - left_with_overlap),
    }


def load_stage309_reference(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["entry_dt", "exit_dt"])
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if not {"entry_dt", "exit_dt"}.issubset(frame.columns):
        return pd.DataFrame(columns=["entry_dt", "exit_dt"])
    frame["entry_dt"] = pd.to_datetime(frame.entry_dt, errors="coerce")
    frame["exit_dt"] = pd.to_datetime(frame.exit_dt, errors="coerce")
    return frame.dropna(subset=["entry_dt", "exit_dt"])


def csv_safe_rows(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trade in trades:
        row = dict(trade)
        for key in ("decision_dt", "entry_dt", "exit_dt"):
            if key in row:
                row[key] = str(pd.Timestamp(row[key]))
        rows.append(row)
    return rows


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage311_mochipoyo_and_independent_candidate_research.json"
    )
    trades_csv = (
        Path(args.trades_csv).expanduser().resolve()
        if args.trades_csv
        else candle_dir / "stage311_candidate_research_all_trades.csv"
    )
    selected_trades_csv = (
        Path(args.selected_trades_csv).expanduser().resolve()
        if args.selected_trades_csv
        else candle_dir / "stage311_selected_lead_trades.csv"
    )
    stage309_path = (
        Path(args.stage309_trades).expanduser().resolve()
        if args.stage309_trades
        else candle_dir / "stage309_stage307_top_candidate_trades.csv"
    )

    point_size = float(args.point_size)
    m1 = read_candles(
        candle_dir / GOLD_FILES["M1"],
        None,
        timeframe="M1",
        require_spread=True,
    ).copy()

    indicator_cache: dict[str, pd.DataFrame] = {}
    for timeframe in ("M5", "M15", "H1", "H4", "D1"):
        indicator_cache[timeframe] = stage308.indicator_frame(
            candle_dir,
            timeframe,
            point_size,
        )

    family_raw: dict[str, list[dict[str, Any]]] = {}
    signal_count = 0
    for pair in stage308.PAIR_SPECS:
        base_frame = stage308.build_signal_frame(
            indicator_cache[pair.main_tf],
            indicator_cache[pair.higher_tf],
        )
        frame = add_research_features(base_frame)
        for track in TRACK_SPECS:
            signals = generate_track_signals(frame, pair, track)
            signal_count += len(signals)
            for signal in signals:
                decision_year = pd.Timestamp(signal["decision_dt"]).year
                if decision_year not in YEARS:
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
        key: stage308.one_position(trades)
        for key, trades in family_raw.items()
    }
    leaderboard: list[dict[str, Any]] = []
    for key, trades in family_trades.items():
        pair_name, track_name, direction, exit_name = key.split("|", 3)
        track = next(item for item in TRACK_SPECS if item.name == track_name)
        dev_conf, yearly, gate = development_confirmation_metrics(trades)
        leaderboard.append(
            {
                "family_key": key,
                "pair": pair_name,
                "track": track_name,
                "category": track.category,
                "direction": direction,
                "exit_profile": exit_name,
                "raw_trade_count": len(family_raw[key]),
                "aggregate": stage308.summarize(trades),
                "development_confirmation": dev_conf,
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

    mochi_members = select_leads(leaderboard, "MOCHIPOYO", 4)
    independent_members = select_leads(leaderboard, "INDEPENDENT", 4)
    all_members = select_leads(leaderboard, None, 6)
    pools = [
        pool_result("MOCHIPOYO_SELECTED_2024_2025", mochi_members, family_trades),
        pool_result("INDEPENDENT_SELECTED_2024_2025", independent_members, family_trades),
        pool_result("ALL_SELECTED_2024_2025", all_members, family_trades),
    ]

    stage309_reference = load_stage309_reference(stage309_path)
    overlap = {
        pool["pool"]: overlap_diagnostics(
            pool["portfolio_trades"],
            stage309_reference,
        )
        for pool in pools
    }

    all_trade_rows: list[dict[str, Any]] = []
    for key, trades in family_trades.items():
        for trade in trades:
            row = dict(trade)
            row["family_key"] = key
            all_trade_rows.append(row)
    selected_rows = pools[2]["portfolio_trades"]

    trades_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(csv_safe_rows(all_trade_rows)).to_csv(
        trades_csv,
        index=False,
        encoding="utf-8-sig",
    )
    selected_trades_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(csv_safe_rows(selected_rows)).to_csv(
        selected_trades_csv,
        index=False,
        encoding="utf-8-sig",
    )

    pool_reports = []
    for pool in pools:
        cleaned = dict(pool)
        cleaned.pop("portfolio_trades", None)
        pool_reports.append(cleaned)

    passing = [row for row in leaderboard if row["gate"]["research_pass"]]
    all_year_positive = [
        row for row in passing if row["gate"]["all_year_positive_flag"]
    ]
    decision = (
        "RESEARCH_LEADS_FOUND"
        if passing
        else "NO_NEW_RESEARCH_LEAD_FOUND"
    )
    report = {
        "status": "GOLD_V3_311_MOCHIPOYO_AND_INDEPENDENT_RESEARCH_READY",
        "mode": "AUDIT_ONLY_STANDALONE_CANDIDATE_RESEARCH",
        "decision": decision,
        "purpose": (
            "Research Mochipoyo-style trend entries and independent rule-based candidates. "
            "Do not search for or depend on missing Stage284/286 historical ledgers."
        ),
        "stage307_top_reference": {
            "retained_candidate": True,
            "candidate_id": "GOLD_V3_STAGE307_TOP_REV_LONG_ANY_P90",
            "reference_trades_available": not stage309_reference.empty,
            "reference_path": str(stage309_path),
            "no_promotion_or_modification": True,
        },
        "research_design": {
            "selection_years": [2024, 2025],
            "display_only_year": 2026,
            "selection_does_not_use_2026": True,
            "timeframe_pairs": [pair.name for pair in stage308.PAIR_SPECS],
            "tracks": [
                {
                    "name": track.name,
                    "category": track.category,
                    "allowed_pairs": list(track.allowed_pairs),
                }
                for track in TRACK_SPECS
            ],
            "exit_profiles": [item["name"] for item in EXIT_PROFILES],
            "mochipoyo_principles": [
                "higher-timeframe direction first",
                "EMA20/30/40 alignment",
                "RCI 9/14/18 turn",
                "MACD 6/13/4 acceleration or divergence",
                "confirmed ZigZag wave and pullback/retest",
                "avoid late overextended and climax entries",
                "structural stop and at least 1.25R alternative",
            ],
            "independent_tracks": [
                "compression breakout continuation",
                "sweep and reclaim reversal",
            ],
        },
        "search": {
            "signals": int(signal_count),
            "family_count": len(leaderboard),
            "research_pass_count": len(passing),
            "balanced_pass_count": sum(
                bool(row["gate"]["balanced_pass"]) for row in leaderboard
            ),
            "all_year_positive_lead_count": len(all_year_positive),
            "gate": {
                "selection_only": "2024 and 2025",
                "combined_trades": 30,
                "minimum_each_year": 10,
                "minimum_each_year_pf": 1.10,
                "minimum_each_year_r": "> 0",
                "combined_pf": 1.25,
                "combined_max_dd_r": 10.0,
                "largest_win_share": 0.40,
            },
        },
        "selected_family_keys": {
            "mochipoyo": mochi_members,
            "independent": independent_members,
            "all": all_members,
        },
        "selected_pools": pool_reports,
        "stage307_overlap": overlap,
        "passing_candidates": passing[: int(args.top)],
        "all_year_positive_candidates": all_year_positive[: int(args.top)],
        "family_leaderboard": leaderboard[: int(args.top)],
        "selection_bias_warning": (
            "The fixed grid is selected on 2024 development plus 2025 confirmation. "
            "2026 is display-only and must not be used to alter thresholds after this run."
        ),
        "outputs": {
            "result_json": str(output),
            "all_trades_csv": str(trades_csv),
            "selected_trades_csv": str(selected_trades_csv),
        },
        "promotion": {
            "performed": False,
            "production_stage280": "UNCHANGED_BLOCKED",
            "stage307_candidate": "RETAINED_RESEARCH_CANDIDATE",
            "stage292_candidate_pool_changed": False,
            "shadow_enabled": False,
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
    report["outputs"]["all_trades_sha256"] = sha256_file(trades_csv)
    report["outputs"]["selected_trades_sha256"] = sha256_file(selected_trades_csv)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
