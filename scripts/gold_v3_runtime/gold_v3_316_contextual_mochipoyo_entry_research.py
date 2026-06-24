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
import gold_v3_311_mochipoyo_and_independent_candidate_research as stage311
import gold_v3_315_second_independent_candidate_sweep as stage315
from gold_v3_289_feature_core import GOLD_FILES, read_candles

POINT_SIZE = 0.01
YEARS = (2024, 2025, 2026)
SELECTION_YEARS = (2024, 2025)
WAIT_BARS = {"M5_H4": 4, "M15_H4": 3, "H1_D1": 2}


@dataclass(frozen=True)
class RecipeSpec:
    name: str
    regime: str
    confirmation: str


RECIPES = (
    RecipeSpec("MIDTREND_RECLAIM", "MID_TREND", "EMA_RCI_MACD_RECLAIM"),
    RecipeSpec("EXPANSION_MICROBREAK", "EXPANSION_RESTART", "MICRO_BREAK_3"),
    RecipeSpec("PULLBACK_STRUCTURE_BREAK", "PULLBACK_RECOVERY", "SIGNAL_STRUCTURE_BREAK"),
    RecipeSpec("IMPULSE_RESUME", "TREND_IMPULSE", "THREE_BAR_IMPULSE"),
)

EXIT_PROFILES = (
    {"name": "RR1_25", "kind": "RR", "rr": 1.25},
    {"name": "RR1_5", "kind": "RR", "rr": 1.5},
)

MOCHI_TRACKS = tuple(
    track for track in stage311.TRACK_SPECS if track.category == "MOCHIPOYO"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--trades-csv", required=True)
    parser.add_argument("--selected-csv", required=True)
    parser.add_argument("--stage311-trades", required=True)
    parser.add_argument("--stage309-trades", default="")
    parser.add_argument("--stage313-trades", default="")
    parser.add_argument("--stage315-trades", default="")
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    parser.add_argument("--top", type=int, default=250)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return str(value)
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def add_context_features(frame: pd.DataFrame) -> pd.DataFrame:
    work = stage315.add_features(frame)
    work["prior_high3"] = work.high.shift(1).rolling(3, min_periods=3).max()
    work["prior_low3"] = work.low.shift(1).rolling(3, min_periods=3).min()
    work["recent_compression"] = (
        work.compression_ratio.shift(1).rolling(6, min_periods=1).min() <= 0.90
    ).fillna(False)
    work["recent_pullback_long"] = (
        work.pullback_long.shift(1).rolling(6, min_periods=1).max().fillna(False).astype(bool)
    )
    work["recent_pullback_short"] = (
        work.pullback_short.shift(1).rolling(6, min_periods=1).max().fillna(False).astype(bool)
    )
    return work


def direction_context(frame: pd.DataFrame, direction: int) -> dict[str, pd.Series]:
    if direction == 1:
        return {
            "htf_trend": frame.htf_bull_trend,
            "ltf_trend": frame.ltf_bull_trend,
            "rci_turn": frame.rci_turn_long,
            "htf_rci_turn": frame.htf_rci_turn_long,
            "macd_accel": frame.macd_accel_long,
            "reclaim": frame.ema20_reclaim_long,
            "pullback": frame.pullback_long,
            "recent_pullback": frame.recent_pullback_long,
            "deep_touch": frame.deep_touch_long,
            "extension": frame.extension_long_atr,
            "close_strength": frame.close_pos,
            "three": frame.three_up,
            "three_body": frame.three_body_long,
            "prior_break": frame.close > frame.prior_high3,
        }
    return {
        "htf_trend": frame.htf_bear_trend,
        "ltf_trend": frame.ltf_bear_trend,
        "rci_turn": frame.rci_turn_short,
        "htf_rci_turn": frame.htf_rci_turn_short,
        "macd_accel": frame.macd_accel_short,
        "reclaim": frame.ema20_reclaim_short,
        "pullback": frame.pullback_short,
        "recent_pullback": frame.recent_pullback_short,
        "deep_touch": frame.deep_touch_short,
        "extension": frame.extension_short_atr,
        "close_strength": 1.0 - frame.close_pos,
        "three": frame.three_down,
        "three_body": frame.three_body_short,
        "prior_break": frame.close < frame.prior_low3,
    }


def regime_and_confirmation(
    frame: pd.DataFrame,
    index: int,
    base_index: int,
    direction: int,
    recipe: RecipeSpec,
) -> tuple[bool, float, dict[str, Any]]:
    c = direction_context(frame, direction)
    row = frame.iloc[index]
    htf = bool(c["htf_trend"].iloc[index])
    ltf = bool(c["ltf_trend"].iloc[index])
    rci = bool(c["rci_turn"].iloc[index])
    htf_rci = bool(c["htf_rci_turn"].iloc[index])
    macd = bool(c["macd_accel"].iloc[index])
    reclaim = bool(c["reclaim"].iloc[index])
    pullback = bool(c["pullback"].iloc[index])
    recent_pullback = bool(c["recent_pullback"].iloc[index])
    deep_touch = bool(c["deep_touch"].iloc[index])
    ext = safe_float(c["extension"].iloc[index])
    close_strength = safe_float(c["close_strength"].iloc[index]) or 0.0
    adx = safe_float(row.adx14)
    adx_rise = safe_float(row.adx_rise3)
    atr_ratio = safe_float(row.atr_ratio)
    body = safe_float(row.body_signed_atr)
    range_atr = safe_float(row.range_atr)
    not_climax = bool(row.not_climax)
    recent_compression = bool(row.recent_compression)
    recent_inside = bool(row.recent_inside)

    if any(value is None for value in (ext, adx, adx_rise, atr_ratio, body, range_atr)):
        return False, 0.0, {}

    directional_body = body if direction == 1 else -body
    base_high = float(frame.high.iloc[base_index])
    base_low = float(frame.low.iloc[base_index])
    prior_high3 = safe_float(row.prior_high3)
    prior_low3 = safe_float(row.prior_low3)

    if recipe.name == "MIDTREND_RECLAIM":
        regime = (
            htf
            and ltf
            and 18.0 <= adx <= 42.0
            and 0.85 <= atr_ratio <= 1.55
            and -0.20 <= ext <= 0.85
            and not_climax
        )
        confirmation = (
            reclaim
            and (rci or macd)
            and directional_body >= 0.10
            and close_strength >= 0.55
        )
    elif recipe.name == "EXPANSION_MICROBREAK":
        regime = (
            htf
            and ltf
            and adx >= 18.0
            and adx_rise >= 0.50
            and 0.95 <= atr_ratio <= 1.60
            and (recent_compression or recent_inside)
            and 0.0 <= ext <= 1.10
            and not_climax
        )
        confirmation = (
            bool(c["prior_break"].iloc[index])
            and (rci or macd or htf_rci)
            and directional_body >= 0.18
            and close_strength >= 0.65
        )
    elif recipe.name == "PULLBACK_STRUCTURE_BREAK":
        regime = (
            htf
            and (ltf or reclaim)
            and (pullback or recent_pullback or deep_touch)
            and 16.0 <= adx <= 40.0
            and 0.80 <= atr_ratio <= 1.50
            and -0.35 <= ext <= 0.65
            and not_climax
        )
        if direction == 1:
            structure_level = max(base_high, prior_high3 if prior_high3 is not None else base_high)
            structure_break = float(row.close) > structure_level
        else:
            structure_level = min(base_low, prior_low3 if prior_low3 is not None else base_low)
            structure_break = float(row.close) < structure_level
        confirmation = (
            structure_break
            and (rci or macd)
            and directional_body >= 0.12
            and close_strength >= 0.58
        )
    elif recipe.name == "IMPULSE_RESUME":
        regime = (
            htf
            and ltf
            and adx >= 18.0
            and 0.90 <= atr_ratio <= 1.60
            and 0.0 <= ext <= 1.00
            and not_climax
            and range_atr <= 1.80
        )
        confirmation = (
            bool(c["three"].iloc[index])
            and float(c["three_body"].iloc[index]) >= 0.80
            and close_strength >= 0.60
        )
    else:
        raise ValueError(recipe.name)

    passed = bool(regime and confirmation)
    score = (
        2.0 * float(htf)
        + 2.0 * float(ltf)
        + 1.0 * float(rci)
        + 1.0 * float(htf_rci)
        + 1.0 * float(macd)
        + 1.0 * float(reclaim)
        + min(max((adx - 18.0) / 10.0, 0.0), 1.5)
        + min(max(adx_rise / 3.0, 0.0), 1.0)
        + close_strength
    )
    diagnostics = {
        "regime": recipe.regime,
        "confirmation": recipe.confirmation,
        "htf_trend": htf,
        "ltf_trend": ltf,
        "rci_turn": rci,
        "htf_rci_turn": htf_rci,
        "macd_accel": macd,
        "ema20_reclaim": reclaim,
        "pullback_or_deep_touch": bool(pullback or recent_pullback or deep_touch),
        "adx14": adx,
        "adx_rise3": adx_rise,
        "atr_ratio": atr_ratio,
        "extension_atr": ext,
        "directional_body_atr": directional_body,
        "range_atr": range_atr,
        "close_strength": close_strength,
        "recent_compression": recent_compression,
        "recent_inside": recent_inside,
    }
    return passed, float(score), diagnostics


def base_events(
    frame: pd.DataFrame,
    pair: stage308.PairSpec,
    track: stage311.TrackSpec,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if pair.name not in track.allowed_pairs:
        return events
    for direction in (1, -1):
        mask, quality = stage311.track_mask(frame, track, direction)
        onset = stage308.edge_with_cooldown(
            mask,
            pair.cooldown_bars * track.cooldown_multiplier,
        )
        for index in frame.index[onset]:
            events.append(
                {
                    "track": track,
                    "direction": direction,
                    "base_index": int(index),
                    "base_decision_dt": pd.Timestamp(frame.close_time.iloc[index]),
                    "base_quality": float(quality.loc[index]),
                }
            )
    return events


def contextual_signals(
    frame: pd.DataFrame,
    pair: stage308.PairSpec,
) -> list[dict[str, Any]]:
    dedup: dict[tuple[str, str, int, pd.Timestamp], dict[str, Any]] = {}
    max_wait = WAIT_BARS[pair.name]
    for track in MOCHI_TRACKS:
        for event in base_events(frame, pair, track):
            base_index = int(event["base_index"])
            direction = int(event["direction"])
            for recipe in RECIPES:
                found: dict[str, Any] | None = None
                last_confirmation_index = min(base_index + max_wait, len(frame) - 2)
                for index in range(base_index + 1, last_confirmation_index + 1):
                    passed, context_score, diagnostics = regime_and_confirmation(
                        frame,
                        index,
                        base_index,
                        direction,
                        recipe,
                    )
                    if not passed:
                        continue
                    row = frame.iloc[index]
                    quality = float(event["base_quality"]) + context_score
                    found = {
                        "pair": pair.name,
                        "main_tf": pair.main_tf,
                        "higher_tf": pair.higher_tf,
                        "setup": f"{track.name}__{recipe.name}",
                        "track": track.name,
                        "recipe": recipe.name,
                        "regime": recipe.regime,
                        "confirmation": recipe.confirmation,
                        "category": "MOCHIPOYO_CONTEXTUAL_ENTRY",
                        "direction": "LONG" if direction == 1 else "SHORT",
                        "direction_num": direction,
                        "signal_index": int(index),
                        "decision_dt": pd.Timestamp(row.close_time),
                        "base_signal_index": base_index,
                        "base_signal_dt": event["base_decision_dt"],
                        "bars_waited": int(index - base_index),
                        "base_quality_score": float(event["base_quality"]),
                        "context_score": float(context_score),
                        "quality_score": quality,
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
                            row.extension_long_atr
                            if direction == 1
                            else row.extension_short_atr
                        ),
                        "adx14_signal": safe_float(row.adx14),
                        "adx_rise3_signal": safe_float(row.adx_rise3),
                        "range_atr_signal": float(row.range_atr),
                        "context_diagnostics": diagnostics,
                    }
                    break
                if found is None:
                    continue
                key = (
                    track.name,
                    recipe.name,
                    direction,
                    pd.Timestamp(found["decision_dt"]),
                )
                current = dedup.get(key)
                if current is None or float(found["quality_score"]) > float(
                    current["quality_score"]
                ):
                    dedup[key] = found
    return sorted(
        dedup.values(),
        key=lambda row: (
            pd.Timestamp(row["decision_dt"]),
            row["track"],
            row["recipe"],
            row["direction"],
        ),
    )


def family_key(signal: dict[str, Any], exit_name: str) -> str:
    return "|".join(
        [
            signal["pair"],
            signal["track"],
            signal["recipe"],
            signal["direction"],
            exit_name,
        ]
    )


def load_trade_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, encoding="utf-8-sig")
    for column in ("decision_dt", "entry_dt", "exit_dt", "base_signal_dt"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def frame_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def baseline_comparison(
    context_rows: list[dict[str, Any]],
    pair: str,
    track: str,
    direction: str,
    exit_name: str,
    baseline: pd.DataFrame,
) -> dict[str, Any]:
    context_selection = [
        row
        for row in context_rows
        if pd.Timestamp(row["entry_dt"]).year in SELECTION_YEARS
    ]
    context_summary = stage308.summarize(context_selection)
    base_key = "|".join([pair, track, direction, exit_name])
    if baseline.empty or "family_key" not in baseline.columns:
        return {
            "available": False,
            "base_family_key": base_key,
            "context_selection": context_summary,
            "improvement_pass": False,
        }
    base_frame = baseline[baseline.family_key.eq(base_key)].copy()
    if "entry_dt" in base_frame.columns:
        base_frame = base_frame[base_frame.entry_dt.dt.year.isin(SELECTION_YEARS)]
    base_summary = stage308.summarize(frame_records(base_frame))
    context_pf = stage311.pf_value(context_summary)
    base_pf = stage311.pf_value(base_summary)
    context_yearly = stage308.yearly_summary(context_rows)
    context_min_pf = min(
        stage311.pf_value(context_yearly["2024"]),
        stage311.pf_value(context_yearly["2025"]),
    )
    base_all_frame = baseline[baseline.family_key.eq(base_key)].copy()
    base_yearly = stage308.yearly_summary(frame_records(base_all_frame))
    base_min_pf = min(
        stage311.pf_value(base_yearly["2024"]),
        stage311.pf_value(base_yearly["2025"]),
    )
    improvement_pass = bool(
        context_summary["trades"] >= 30
        and context_pf >= max(1.25, base_pf)
        and context_min_pf >= base_min_pf
        and context_summary["spread_adjusted_max_drawdown_r"]
        <= base_summary["spread_adjusted_max_drawdown_r"] + 1.0
    )
    return {
        "available": True,
        "base_family_key": base_key,
        "baseline_selection": base_summary,
        "context_selection": context_summary,
        "delta": {
            "trades": int(context_summary["trades"] - base_summary["trades"]),
            "profit_factor": float(context_pf - base_pf),
            "total_r": float(
                context_summary["spread_adjusted_total_r"]
                - base_summary["spread_adjusted_total_r"]
            ),
            "max_drawdown_r": float(
                context_summary["spread_adjusted_max_drawdown_r"]
                - base_summary["spread_adjusted_max_drawdown_r"]
            ),
            "minimum_year_pf": float(context_min_pf - base_min_pf),
        },
        "improvement_pass": improvement_pass,
        "contract": {
            "context_pf_not_below_baseline": True,
            "context_minimum_year_pf_not_below_baseline": True,
            "context_drawdown_not_more_than_1R_worse": True,
        },
    }


def select_leads(leaderboard: list[dict[str, Any]], limit: int = 6) -> list[str]:
    selected: list[str] = []
    used_contracts: set[str] = set()
    recipe_counts: dict[str, int] = {}
    for row in leaderboard:
        if not row["gate"]["research_pass"]:
            continue
        if not row["baseline_comparison"].get("improvement_pass", False):
            continue
        contract = "|".join(
            [row["pair"], row["track"], row["recipe"], row["direction"]]
        )
        if contract in used_contracts:
            continue
        if recipe_counts.get(row["recipe"], 0) >= 2:
            continue
        selected.append(row["family_key"])
        used_contracts.add(contract)
        recipe_counts[row["recipe"]] = recipe_counts.get(row["recipe"], 0) + 1
        if len(selected) >= limit:
            break
    return selected


def reference_overlap(
    trades: list[dict[str, Any]],
    path: Path,
) -> dict[str, Any]:
    frame = load_trade_csv(path)
    if frame.empty or not {"entry_dt", "exit_dt"}.issubset(frame.columns):
        return stage311.overlap_diagnostics(trades, pd.DataFrame())
    return stage311.overlap_diagnostics(
        trades,
        frame.dropna(subset=["entry_dt", "exit_dt"]),
    )


def empty_csv(path: Path) -> None:
    pd.DataFrame(
        columns=[
            "family_key",
            "pair",
            "track",
            "recipe",
            "regime",
            "confirmation",
            "direction",
            "base_signal_dt",
            "decision_dt",
            "entry_dt",
            "exit_dt",
            "spread_adjusted_pnl",
            "spread_adjusted_r",
        ]
    ).to_csv(path, index=False, encoding="utf-8-sig")


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    trades_csv = Path(args.trades_csv).expanduser().resolve()
    selected_csv = Path(args.selected_csv).expanduser().resolve()
    stage311_path = Path(args.stage311_trades).expanduser().resolve()
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
    stage315_path = (
        Path(args.stage315_trades).expanduser().resolve()
        if args.stage315_trades
        else candle_dir / "stage315_selected_independent_portfolio_trades.csv"
    )
    point_size = float(args.point_size)

    baseline = load_trade_csv(stage311_path)
    if baseline.empty or "family_key" not in baseline.columns:
        raise ValueError("STAGE311_BASELINE_TRADES_MISSING_OR_INVALID")

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
    base_event_count = 0
    contextual_signal_count = 0
    for pair in stage308.PAIR_SPECS:
        base_frame = stage308.build_signal_frame(
            indicators[pair.main_tf],
            indicators[pair.higher_tf],
        )
        frame = add_context_features(base_frame)
        for track in MOCHI_TRACKS:
            base_event_count += len(base_events(frame, pair, track))
        signals = contextual_signals(frame, pair)
        contextual_signal_count += len(signals)
        for signal in signals:
            if pd.Timestamp(signal["decision_dt"]).year not in YEARS:
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
        pair_name, track_name, recipe_name, direction, exit_name = key.split("|", 4)
        recipe = next(item for item in RECIPES if item.name == recipe_name)
        development, yearly, gate = stage311.development_confirmation_metrics(rows)
        comparison = baseline_comparison(
            rows,
            pair_name,
            track_name,
            direction,
            exit_name,
            baseline,
        )
        leaderboard.append(
            {
                "family_key": key,
                "pair": pair_name,
                "track": track_name,
                "recipe": recipe_name,
                "regime": recipe.regime,
                "confirmation": recipe.confirmation,
                "direction": direction,
                "exit_profile": exit_name,
                "raw_trade_count": len(family_raw[key]),
                "aggregate": stage308.summarize(rows),
                "development_confirmation": development,
                "yearly": yearly,
                "gate": gate,
                "baseline_comparison": comparison,
                "contextual_value_pass": bool(
                    gate["research_pass"] and comparison.get("improvement_pass", False)
                ),
            }
        )
    leaderboard.sort(
        key=lambda row: (
            -int(row["contextual_value_pass"]),
            -int(row["gate"]["research_pass"]),
            -float(row["gate"]["robust_score_2024_2025_only"]),
            row["family_key"],
        )
    )

    selected_keys = select_leads(leaderboard, 6)
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
            if isinstance(item.get("context_diagnostics"), dict):
                item["context_diagnostics"] = json.dumps(
                    json_safe(item["context_diagnostics"]),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            all_rows.append(item)

    trades_csv.parent.mkdir(parents=True, exist_ok=True)
    if all_rows:
        pd.DataFrame(stage311.csv_safe_rows(all_rows)).to_csv(
            trades_csv,
            index=False,
            encoding="utf-8-sig",
        )
    else:
        empty_csv(trades_csv)
    selected_csv.parent.mkdir(parents=True, exist_ok=True)
    if selected_portfolio:
        selected_rows = []
        for row in selected_portfolio:
            item = dict(row)
            if isinstance(item.get("context_diagnostics"), dict):
                item["context_diagnostics"] = json.dumps(
                    json_safe(item["context_diagnostics"]),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            selected_rows.append(item)
        pd.DataFrame(stage311.csv_safe_rows(selected_rows)).to_csv(
            selected_csv,
            index=False,
            encoding="utf-8-sig",
        )
    else:
        empty_csv(selected_csv)

    contextual_passes = [row for row in leaderboard if row["contextual_value_pass"]]
    research_passes = [row for row in leaderboard if row["gate"]["research_pass"]]
    report = {
        "status": "GOLD_V3_316_CONTEXTUAL_MOCHIPOYO_ENTRY_RESEARCH_COMPLETE",
        "mode": "AUDIT_ONLY_SIGNAL_REGIME_CONFIRMATION_RESEARCH",
        "decision": (
            "CONTEXTUAL_MOCHIPOYO_VALUE_LEADS_FOUND"
            if contextual_passes
            else (
                "MOCHIPOYO_RESEARCH_PASSES_WITHOUT_CONTEXT_VALUE_PROOF"
                if research_passes
                else "NO_CONTEXTUAL_MOCHIPOYO_RESEARCH_LEAD_FOUND"
            )
        ),
        "research_contract": {
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": 2026,
            "selection_does_not_use_2026": True,
            "base_signal_tracks": [track.name for track in MOCHI_TRACKS],
            "recipes": [
                {
                    "name": recipe.name,
                    "regime": recipe.regime,
                    "confirmation": recipe.confirmation,
                }
                for recipe in RECIPES
            ],
            "maximum_wait_bars": WAIT_BARS,
            "entry": "next exact main-timeframe open after the closed confirmation bar",
            "exit_profiles": [row["name"] for row in EXIT_PROFILES],
            "stage311_gate_unchanged": True,
            "context_value_gate_uses_2024_2025_only": True,
            "context_value_gate": {
                "context_research_pass_required": True,
                "context_pf_not_below_immediate_entry_baseline": True,
                "context_minimum_year_pf_not_below_baseline": True,
                "context_drawdown_not_more_than_1R_worse": True,
            },
        },
        "search": {
            "base_event_count": int(base_event_count),
            "contextual_signal_count": int(contextual_signal_count),
            "family_count": len(leaderboard),
            "research_pass_count": len(research_passes),
            "contextual_value_pass_count": len(contextual_passes),
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
            "stage307_top": reference_overlap(selected_portfolio, stage309_path),
            "stage313_mochipoyo_watch": reference_overlap(
                selected_portfolio,
                stage313_path,
            ),
            "stage315_independent_portfolio": reference_overlap(
                selected_portfolio,
                stage315_path,
            ),
        },
        "contextual_value_passes": contextual_passes[: int(args.top)],
        "research_passes": research_passes[: int(args.top)],
        "leaderboard": leaderboard[: int(args.top)],
        "multiple_testing_warning": (
            "The recipes are fixed before this run, but the family sweep remains research. "
            "No historical pass may be promoted without a new frozen prospective watch."
        ),
        "outputs": {
            "result_json": str(output),
            "all_trades_csv": str(trades_csv),
            "selected_trades_csv": str(selected_csv),
            "all_trades_sha256": sha256_file(trades_csv),
            "selected_trades_sha256": sha256_file(selected_csv),
            "stage311_baseline_sha256": sha256_file(stage311_path),
        },
        "promotion": {
            "performed": False,
            "stage314_prospective_watch": "UNCHANGED_ACTIVE",
            "stage315_independent_research": "UNCHANGED",
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
        json.dumps(json_safe(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(json_safe(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
