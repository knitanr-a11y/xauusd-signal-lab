#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gold_v3_308_mochipoyo_method_walkforward as stage308
import gold_v3_311_mochipoyo_and_independent_candidate_research as stage311
from gold_v3_289_feature_core import GOLD_FILES, read_candles

POINT_SIZE = 0.01
SPEC_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "gold_v3_314"
    / "stage314_mochipoyo_prospective_watch_spec.json"
)


class ContractError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--stage313-json", required=True)
    parser.add_argument("--stage313-trades", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--signals-csv", required=True)
    parser.add_argument("--resolved-csv", required=True)
    parser.add_argument("--pending-csv", required=True)
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_event_id(candidate_id: str, decision_dt: pd.Timestamp) -> str:
    raw = f"{candidate_id}|{pd.Timestamp(decision_dt).isoformat()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def iso(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(pd.Timestamp(value))


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
    if pd.isna(value) if not isinstance(value, (str, bool)) else False:
        return None
    return value


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def profit_factor(values: pd.Series) -> float | None:
    positive = float(values[values > 0.0].sum())
    negative = float(-values[values < 0.0].sum())
    if negative == 0.0:
        return None if positive > 0.0 else 0.0
    return positive / negative


def max_drawdown_r(values: pd.Series) -> float:
    if values.empty:
        return 0.0
    equity = values.cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return float((peak - equity).max())


def summarize_resolved(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "spread_adjusted_total_usd": 0.0,
            "spread_adjusted_profit_factor": 0.0,
            "spread_adjusted_total_r": 0.0,
            "spread_adjusted_max_drawdown_r": 0.0,
            "largest_win_share_of_positive_pnl": 0.0,
            "long_trades": 0,
            "short_trades": 0,
            "first_entry_dt": None,
            "last_exit_dt": None,
        }
    ordered = frame.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    pnl = pd.to_numeric(ordered.spread_adjusted_pnl, errors="raise")
    r_values = pd.to_numeric(ordered.spread_adjusted_r, errors="raise")
    wins = int((pnl > 0.0).sum())
    losses = int((pnl < 0.0).sum())
    positives = pnl[pnl > 0.0]
    positive_sum = float(positives.sum())
    return {
        "trades": int(len(ordered)),
        "wins": wins,
        "losses": losses,
        "win_rate": float(wins / len(ordered)),
        "spread_adjusted_total_usd": float(pnl.sum()),
        "spread_adjusted_profit_factor": profit_factor(pnl),
        "spread_adjusted_total_r": float(r_values.sum()),
        "spread_adjusted_max_drawdown_r": max_drawdown_r(r_values),
        "largest_win_share_of_positive_pnl": (
            float(positives.max() / positive_sum) if positive_sum > 0.0 else 0.0
        ),
        "long_trades": int((ordered.direction_num == 1).sum()),
        "short_trades": int((ordered.direction_num == -1).sum()),
        "first_entry_dt": iso(ordered.entry_dt.min()),
        "last_exit_dt": iso(ordered.exit_dt.max()),
    }


def pf_number(summary: dict[str, Any]) -> float:
    value = summary["spread_adjusted_profit_factor"]
    if value is None and summary["spread_adjusted_total_usd"] > 0.0:
        return float("inf")
    return float(value or 0.0)


def review_gate(summary: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    gate = spec["future_review_gate"]
    eligible = bool(
        summary["trades"] >= int(gate["minimum_resolved_accepted_trades"])
        and summary["long_trades"] >= int(gate["minimum_long_trades"])
        and summary["short_trades"] >= int(gate["minimum_short_trades"])
        and pf_number(summary) >= float(gate["minimum_profit_factor"])
        and summary["spread_adjusted_total_r"] > float(gate["minimum_total_r_exclusive"])
        and summary["spread_adjusted_max_drawdown_r"] <= float(gate["maximum_drawdown_r"])
        and summary["largest_win_share_of_positive_pnl"] <= 0.35
    )
    return {
        "review_eligible": eligible,
        "automatic_promotion": False,
        "requirements": gate,
        "important": (
            "Eligibility only opens a human audit. It does not change Stage292, final signal, "
            "Discord, or MT5 execution."
        ),
    }


def read_closed_context(
    candle_dir: Path,
    point_size: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, stage308.PairSpec]:
    m1 = read_candles(
        candle_dir / GOLD_FILES["M1"],
        None,
        timeframe="M1",
        require_spread=True,
    ).copy()
    m5 = stage308.indicator_frame(candle_dir, "M5", point_size)
    h4 = stage308.indicator_frame(candle_dir, "H4", point_size)
    frame = stage308.build_signal_frame(m5, h4)
    frame = stage311.add_research_features(frame)
    pair = next(item for item in stage308.PAIR_SPECS if item.name == "M5_H4")
    return m1, m5, h4, frame, pair


def freeze_contract(
    contract_path: Path,
    spec: dict[str, Any],
    spec_sha: str,
    stage313_json_path: Path,
    stage313_json: dict[str, Any],
    stage313_trades_path: Path,
    m1: pd.DataFrame,
    m5: pd.DataFrame,
    h4: pd.DataFrame,
) -> tuple[dict[str, Any], bool]:
    stage313_sha = sha256_file(stage313_json_path)
    stage313_trades_sha = sha256_file(stage313_trades_path)
    expected_trades_sha = stage313_json.get("outputs", {}).get(
        "combined_trades_sha256"
    )
    if expected_trades_sha != stage313_trades_sha:
        raise ContractError(
            "STAGE313_TRADES_SHA_MISMATCH: "
            f"expected={expected_trades_sha} actual={stage313_trades_sha}"
        )
    if stage313_json.get("status") != (
        "GOLD_V3_313_FRAGILITY_AND_DIVERSIFICATION_AUDIT_COMPLETE"
    ):
        raise ContractError(
            f"STAGE313_STATUS_UNEXPECTED: {stage313_json.get('status')}"
        )
    if stage313_json.get("decision") != "DIVERSIFIED_RESEARCH_PORTFOLIO_WATCH_FOUND":
        raise ContractError(
            f"STAGE313_DECISION_UNEXPECTED: {stage313_json.get('decision')}"
        )

    cutoffs = {
        "m1_latest_closed_open_time": iso(m1.time.iloc[-1]),
        "m1_latest_closed_close_time": iso(m1.close_time.iloc[-1]),
        "m5_latest_closed_open_time": iso(m5.time.iloc[-1]),
        "m5_latest_closed_close_time": iso(m5.close_time.iloc[-1]),
        "h4_latest_closed_open_time": iso(h4.time.iloc[-1]),
        "h4_latest_closed_close_time": iso(h4.close_time.iloc[-1]),
        "prospective_decision_dt_strictly_after": iso(m5.close_time.iloc[-1]),
    }
    immutable = {
        "spec_id": spec["spec_id"],
        "spec_sha256": spec_sha,
        "source_stage313_json_sha256": stage313_sha,
        "source_stage313_trades_sha256": stage313_trades_sha,
        "candidates": spec["candidates"],
        "portfolio_policy": spec["portfolio_policy"],
        "risk_contract": spec["risk_contract"],
        "future_review_gate": spec["future_review_gate"],
    }

    if contract_path.exists():
        contract = load_json(contract_path)
        for key, expected in immutable.items():
            if contract.get(key) != expected:
                raise ContractError(f"FROZEN_CONTRACT_IMMUTABLE_MISMATCH: {key}")
        frozen_cutoff = pd.Timestamp(
            contract["frozen_cutoffs"]["prospective_decision_dt_strictly_after"]
        )
        if pd.Timestamp(m5.close_time.iloc[-1]) < frozen_cutoff:
            raise ContractError(
                "CURRENT_M5_HISTORY_ENDS_BEFORE_FROZEN_CUTOFF: "
                f"current={m5.close_time.iloc[-1]} cutoff={frozen_cutoff}"
            )
        return contract, False

    contract = {
        "status": "GOLD_V3_314_PROSPECTIVE_WATCH_CONTRACT_FROZEN",
        **immutable,
        "frozen_cutoffs": cutoffs,
        "source_stage313": {
            "result_path": str(stage313_json_path),
            "trades_path": str(stage313_trades_path),
            "decision": stage313_json["decision"],
            "historical_reference_only": True,
            "combined_reference": stage313_json["combined"]["aggregate"],
            "secondary_reference": stage313_json["secondary"]["aggregate"],
            "primary_rejected_by_fragility_gate": not bool(
                stage313_json["primary"]["research_retain_gate"]
            ),
        },
        "contract_rules": spec["prospective_contract"],
        "preserved_state": spec["preserved_state"],
    }
    write_json(contract_path, contract)
    return contract, True


def candidate_signals(
    frame: pd.DataFrame,
    pair: stage308.PairSpec,
    spec: dict[str, Any],
    frozen_cutoff: pd.Timestamp,
) -> list[dict[str, Any]]:
    track_lookup = {item.name: item for item in stage311.TRACK_SPECS}
    signals: list[dict[str, Any]] = []
    for candidate in spec["candidates"]:
        track = track_lookup[candidate["track"]]
        generated = stage311.generate_track_signals(frame, pair, track)
        for signal in generated:
            decision_dt = pd.Timestamp(signal["decision_dt"])
            if decision_dt <= frozen_cutoff:
                continue
            if signal["direction"] != candidate["direction"]:
                continue
            if candidate["quality_min"] is not None and float(
                signal["quality_score"]
            ) < float(candidate["quality_min"]):
                continue
            if candidate["atr_ratio_min"] is not None and float(
                signal["atr_ratio_signal"]
            ) < float(candidate["atr_ratio_min"]):
                continue
            if candidate["exclude_round_number"] and bool(
                signal["round_number_near"]
            ):
                continue
            enriched = dict(signal)
            enriched.update(
                {
                    "candidate_id": candidate["candidate_id"],
                    "priority": int(candidate["priority"]),
                    "event_id": stable_event_id(candidate["candidate_id"], decision_dt),
                    "exit_profile": candidate["exit_profile"],
                }
            )
            signals.append(enriched)
    signals.sort(
        key=lambda row: (
            pd.Timestamp(row["decision_dt"]),
            int(row["priority"]),
            row["candidate_id"],
        )
    )
    return signals


def prepare_trade(
    signal: dict[str, Any],
    frame: pd.DataFrame,
    m1: pd.DataFrame,
    pair: stage308.PairSpec,
    point_size: float,
) -> dict[str, Any]:
    result = dict(signal)
    result.update(
        {
            "portfolio_status": "RAW",
            "trade_state": None,
            "state_reason": None,
            "entry_dt": None,
            "exit_dt": None,
            "max_exit_dt": None,
            "entry_price": None,
            "entry_spread_points": None,
            "entry_spread_price": None,
            "atr_entry": None,
            "risk_price": None,
            "sl_price": None,
            "tp_price": None,
            "exit_price": None,
            "exit_reason": None,
            "gross_pnl": None,
            "spread_adjusted_pnl": None,
            "gross_r": None,
            "spread_adjusted_r": None,
        }
    )

    signal_index = int(signal["signal_index"])
    entry_index = signal_index + 1
    if entry_index >= len(frame):
        result["trade_state"] = "AWAITING_NEXT_CLOSED_M5_ENTRY"
        result["state_reason"] = "The next exact M5 open is not in the closed-candle CSV yet."
        return result

    entry_dt = pd.Timestamp(frame.time.iloc[entry_index])
    if entry_dt != pd.Timestamp(signal["decision_dt"]):
        result["trade_state"] = "INVALID_ENTRY_ALIGNMENT"
        result["state_reason"] = (
            f"next M5 open {entry_dt} does not equal decision_dt {signal['decision_dt']}"
        )
        return result

    entry_price = float(frame.open.iloc[entry_index])
    spread_points = max(float(frame.spread.iloc[entry_index]), 0.0)
    spread_price = spread_points * point_size
    atr_value = float(frame.atr14.iloc[signal_index])
    if not math.isfinite(atr_value) or atr_value <= 0.0:
        result["trade_state"] = "RISK_REJECTED"
        result["state_reason"] = "ATR is unavailable or non-positive."
        return result

    direction = int(signal["direction_num"])
    if direction == 1:
        swing = signal.get("last_swing_low")
        fallback = float(frame.rolling_low20.iloc[signal_index])
        structural = float(swing) if swing is not None else fallback
        if not math.isfinite(structural):
            result["trade_state"] = "RISK_REJECTED"
            result["state_reason"] = "No confirmed/fallback structural low."
            return result
        raw_stop = structural - 0.10 * atr_value
        stop_distance = entry_price - raw_stop
    else:
        swing = signal.get("last_swing_high")
        fallback = float(frame.rolling_high20.iloc[signal_index])
        structural = float(swing) if swing is not None else fallback
        if not math.isfinite(structural):
            result["trade_state"] = "RISK_REJECTED"
            result["state_reason"] = "No confirmed/fallback structural high."
            return result
        raw_stop = structural + 0.10 * atr_value
        stop_distance = raw_stop - entry_price

    stop_distance = max(stop_distance, 0.75 * atr_value)
    if stop_distance > 2.0 * atr_value:
        result["trade_state"] = "RISK_REJECTED"
        result["state_reason"] = "Structural risk exceeds 2.0 ATR."
        return result

    sl_price = entry_price - direction * stop_distance
    tp_price = entry_price + direction * 1.5 * stop_distance
    max_exit_dt = entry_dt + pd.Timedelta(minutes=pair.max_hold_minutes)
    result.update(
        {
            "entry_dt": entry_dt,
            "max_exit_dt": max_exit_dt,
            "entry_price": entry_price,
            "entry_spread_points": spread_points,
            "entry_spread_price": spread_price,
            "atr_entry": atr_value,
            "risk_price": stop_distance,
            "sl_price": sl_price,
            "tp_price": tp_price,
        }
    )

    latest_m1_close = pd.Timestamp(m1.close_time.iloc[-1])
    m1_times = m1.time.to_numpy("datetime64[ns]")
    first = int(np.searchsorted(m1_times, np.datetime64(entry_dt), side="left"))
    if first >= len(m1) or pd.Timestamp(m1.time.iloc[first]) != entry_dt:
        if entry_dt >= latest_m1_close:
            result["trade_state"] = "AWAITING_M1_ENTRY_BAR"
            result["state_reason"] = "The exact entry M1 bar is not closed yet."
        else:
            result["trade_state"] = "INVALID_M1_ENTRY_GAP"
            result["state_reason"] = "Historical M1 entry bar is missing."
        return result

    available_end = min(max_exit_dt, latest_m1_close)
    last_exclusive = int(
        np.searchsorted(m1_times, np.datetime64(available_end), side="left")
    )
    exit_dt: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str | None = None

    for index in range(first, min(last_exclusive, len(m1))):
        high = float(m1.high.iloc[index])
        low = float(m1.low.iloc[index])
        hit_sl = low <= sl_price if direction == 1 else high >= sl_price
        hit_tp = high >= tp_price if direction == 1 else low <= tp_price
        if hit_sl:
            exit_dt = pd.Timestamp(m1.close_time.iloc[index])
            exit_price = sl_price
            exit_reason = "SL"
            break
        if hit_tp:
            exit_dt = pd.Timestamp(m1.close_time.iloc[index])
            exit_price = tp_price
            exit_reason = "TP"
            break

    if exit_dt is None and max_exit_dt <= latest_m1_close:
        if last_exclusive <= first:
            result["trade_state"] = "INVALID_M1_HOLD_WINDOW"
            result["state_reason"] = "No closed M1 bar exists in the holding window."
            return result
        last_bar = min(last_exclusive - 1, len(m1) - 1)
        exit_dt = pd.Timestamp(m1.close_time.iloc[last_bar])
        exit_price = float(m1.close.iloc[last_bar])
        exit_reason = "TIME"

    if exit_dt is None:
        result["trade_state"] = "PENDING_RESOLUTION"
        result["state_reason"] = (
            "No TP/SL has resolved on closed M1 bars and the 720-minute horizon is incomplete."
        )
        return result

    gross_pnl = direction * (float(exit_price) - entry_price)
    net_pnl = gross_pnl - spread_price
    result.update(
        {
            "trade_state": "RESOLVED",
            "state_reason": None,
            "exit_dt": exit_dt,
            "exit_price": float(exit_price),
            "exit_reason": exit_reason,
            "gross_pnl": float(gross_pnl),
            "spread_adjusted_pnl": float(net_pnl),
            "gross_r": float(gross_pnl / stop_distance),
            "spread_adjusted_r": float(net_pnl / stop_distance),
        }
    )
    return result


def apply_portfolio_policy(
    prepared: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tradable = [
        row
        for row in prepared
        if row["trade_state"] in {"RESOLVED", "PENDING_RESOLUTION"}
        and row["entry_dt"] is not None
    ]
    tradable.sort(
        key=lambda row: (
            pd.Timestamp(row["entry_dt"]),
            int(row["priority"]),
            row["event_id"],
        )
    )
    accepted_ids: set[str] = set()
    rejected_ids: set[str] = set()
    active_until = pd.Timestamp.min
    for row in tradable:
        entry_dt = pd.Timestamp(row["entry_dt"])
        if entry_dt < active_until:
            rejected_ids.add(row["event_id"])
            continue
        accepted_ids.add(row["event_id"])
        if row["trade_state"] == "RESOLVED":
            active_until = pd.Timestamp(row["exit_dt"])
        else:
            active_until = pd.Timestamp(row["max_exit_dt"])

    output: list[dict[str, Any]] = []
    for row in prepared:
        item = dict(row)
        if row["event_id"] in accepted_ids:
            item["portfolio_status"] = "ACCEPTED"
        elif row["event_id"] in rejected_ids:
            item["portfolio_status"] = "REJECTED_OVERLAP"
        else:
            item["portfolio_status"] = "NOT_TRADABLE_YET"
        output.append(item)
    return output


def dataframe_for_csv(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=[
                "event_id",
                "candidate_id",
                "priority",
                "decision_dt",
                "entry_dt",
                "exit_dt",
                "trade_state",
                "portfolio_status",
                "direction",
                "direction_num",
                "quality_score",
                "atr_ratio_signal",
                "round_number_near",
                "entry_price",
                "sl_price",
                "tp_price",
                "exit_price",
                "exit_reason",
                "spread_adjusted_pnl",
                "spread_adjusted_r",
            ]
        )
    frame = pd.DataFrame(rows)
    for column in ("decision_dt", "entry_dt", "exit_dt", "max_exit_dt"):
        if column in frame.columns:
            frame[column] = frame[column].map(iso)
    return frame


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    stage313_json_path = Path(args.stage313_json).expanduser().resolve()
    stage313_trades_path = Path(args.stage313_trades).expanduser().resolve()
    contract_path = Path(args.contract).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    signals_csv = Path(args.signals_csv).expanduser().resolve()
    resolved_csv = Path(args.resolved_csv).expanduser().resolve()
    pending_csv = Path(args.pending_csv).expanduser().resolve()
    point_size = float(args.point_size)

    spec = load_json(SPEC_PATH)
    spec_sha = sha256_file(SPEC_PATH)
    stage313_json = load_json(stage313_json_path)
    m1, m5, h4, frame, pair = read_closed_context(candle_dir, point_size)

    contract, contract_created = freeze_contract(
        contract_path,
        spec,
        spec_sha,
        stage313_json_path,
        stage313_json,
        stage313_trades_path,
        m1,
        m5,
        h4,
    )
    frozen_cutoff = pd.Timestamp(
        contract["frozen_cutoffs"]["prospective_decision_dt_strictly_after"]
    )

    signals = candidate_signals(frame, pair, spec, frozen_cutoff)
    prepared = [prepare_trade(signal, frame, m1, pair, point_size) for signal in signals]
    portfolio_rows = apply_portfolio_policy(prepared)

    accepted_resolved = [
        row
        for row in portfolio_rows
        if row["portfolio_status"] == "ACCEPTED"
        and row["trade_state"] == "RESOLVED"
    ]
    accepted_pending = [
        row
        for row in portfolio_rows
        if row["portfolio_status"] == "ACCEPTED"
        and row["trade_state"] in {
            "PENDING_RESOLUTION",
            "AWAITING_NEXT_CLOSED_M5_ENTRY",
            "AWAITING_M1_ENTRY_BAR",
        }
    ]

    signal_frame = dataframe_for_csv(portfolio_rows)
    resolved_frame = dataframe_for_csv(accepted_resolved)
    pending_frame = dataframe_for_csv(accepted_pending)
    for path, csv_frame in (
        (signals_csv, signal_frame),
        (resolved_csv, resolved_frame),
        (pending_csv, pending_frame),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        csv_frame.to_csv(path, index=False, encoding="utf-8-sig")

    if not resolved_frame.empty:
        resolved_frame["entry_dt"] = pd.to_datetime(resolved_frame.entry_dt)
        resolved_frame["exit_dt"] = pd.to_datetime(resolved_frame.exit_dt)
        resolved_frame["direction_num"] = pd.to_numeric(
            resolved_frame.direction_num, errors="raise"
        )
    summary = summarize_resolved(resolved_frame)
    gate = review_gate(summary, spec)

    raw_count = len(portfolio_rows)
    resolved_count = len(accepted_resolved)
    pending_count = len(accepted_pending)
    if contract_created and raw_count == 0:
        status = "GOLD_V3_314_PROSPECTIVE_WATCH_FROZEN_WAITING_FOR_UNSEEN_DATA"
        decision = "WAIT_FOR_FIRST_POST_FREEZE_CLOSED_M5_SIGNAL"
    elif resolved_count == 0:
        status = "GOLD_V3_314_PROSPECTIVE_WATCH_ACTIVE_NO_RESOLVED_TRADES"
        decision = "CONTINUE_PROSPECTIVE_COLLECTION"
    elif gate["review_eligible"]:
        status = "GOLD_V3_314_PROSPECTIVE_REVIEW_SAMPLE_READY"
        decision = "HUMAN_AUDIT_REQUIRED_NO_AUTOMATIC_PROMOTION"
    else:
        status = "GOLD_V3_314_PROSPECTIVE_WATCH_ACTIVE"
        decision = "CONTINUE_PROSPECTIVE_COLLECTION"

    state_counts: dict[str, int] = {}
    portfolio_counts: dict[str, int] = {}
    candidate_counts: dict[str, int] = {}
    for row in portfolio_rows:
        state_counts[row["trade_state"]] = state_counts.get(row["trade_state"], 0) + 1
        portfolio_counts[row["portfolio_status"]] = (
            portfolio_counts.get(row["portfolio_status"], 0) + 1
        )
        candidate_counts[row["candidate_id"]] = (
            candidate_counts.get(row["candidate_id"], 0) + 1
        )

    report = {
        "status": status,
        "mode": "AUDIT_ONLY_FUTURE_ONLY_PROSPECTIVE_RESEARCH_WATCH",
        "decision": decision,
        "contract": {
            "path": str(contract_path),
            "created_this_run": contract_created,
            "sha256": sha256_file(contract_path),
            "spec_path": str(SPEC_PATH),
            "spec_sha256": spec_sha,
            "frozen_cutoffs": contract["frozen_cutoffs"],
            "cutoff_moved": False,
        },
        "current_closed_data": {
            "m1_latest_open_time": iso(m1.time.iloc[-1]),
            "m1_latest_close_time": iso(m1.close_time.iloc[-1]),
            "m5_latest_open_time": iso(m5.time.iloc[-1]),
            "m5_latest_close_time": iso(m5.close_time.iloc[-1]),
            "h4_latest_open_time": iso(h4.time.iloc[-1]),
            "h4_latest_close_time": iso(h4.close_time.iloc[-1]),
            "latest_rows_closed_by_csv_contract": True,
        },
        "prospective_counts": {
            "raw_post_freeze_signals": raw_count,
            "state_counts": state_counts,
            "portfolio_status_counts": portfolio_counts,
            "candidate_signal_counts": candidate_counts,
            "accepted_resolved": resolved_count,
            "accepted_pending_or_awaiting": pending_count,
            "accepted_long_resolved": int(
                sum(row["direction_num"] == 1 for row in accepted_resolved)
            ),
            "accepted_short_resolved": int(
                sum(row["direction_num"] == -1 for row in accepted_resolved)
            ),
        },
        "resolved_only_metrics": summary,
        "future_review_gate": gate,
        "important": [
            "No decision_dt at or before the frozen M5 cutoff is included.",
            "Pending trades have no as-of PnL and are excluded from every metric.",
            "Resolved metrics contain only trades whose exit is known on closed M1 bars.",
            "No threshold is retuned after the Stage313 result.",
        ],
        "outputs": {
            "result_json": str(output_path),
            "signals_csv": str(signals_csv),
            "resolved_csv": str(resolved_csv),
            "pending_csv": str(pending_csv),
            "signals_sha256": sha256_file(signals_csv),
            "resolved_sha256": sha256_file(resolved_csv),
            "pending_sha256": sha256_file(pending_csv),
        },
        "promotion": {
            "performed": False,
            "stage307_candidate": "UNCHANGED_RETAINED",
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
    write_json(output_path, report)
    print(json.dumps(json_safe(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
