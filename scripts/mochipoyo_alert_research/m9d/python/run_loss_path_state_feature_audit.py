from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import statistics
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
ATR_CHECKPOINTS = (0.25, 0.50, 0.75, 1.00, 1.50, 2.00)
HORIZONS_MINUTES = (15, 30, 60, 120)
EXPECTED_M9C_RESOLVED = 952
EXPECTED_M9C_PAIRS = 2950

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
RESEARCH_ROOT = REPO_ROOT / "scripts" / "mochipoyo_alert_research"
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from alert_trigger_signature_audit import flatten_features
from feature_snapshot_builder import (
    MINIMUM_WARMUP_BARS,
    FeatureContractError,
    build_feature_payload,
    load_indicator_series,
)
from mt5_csv_contract import FILE_MAP, TIMEFRAME_SECONDS


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def bps(delta: float, reference: float) -> float:
    if abs(reference) <= 1e-12:
        raise RuntimeError("zero price reference")
    return delta / abs(reference) * 10000.0


def load_m1(path: Path) -> list[dict[str, Any]]:
    rows = read_csv(path)
    expected = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    if not rows or list(rows[0].keys()) != expected:
        raise RuntimeError(f"unexpected/empty M1 file: {path}")
    output: list[dict[str, Any]] = []
    previous: datetime | None = None
    for raw in rows:
        current = parse_time(raw["time"])
        if previous is not None and current <= previous:
            raise RuntimeError(f"M1 time not strictly ascending: {path.name} {raw['time']}")
        previous = current
        output.append(
            {
                "time": current,
                "time_text": raw["time"],
                "open": float(raw["open"]),
                "high": float(raw["high"]),
                "low": float(raw["low"]),
                "close": float(raw["close"]),
                "tick_volume": int(raw["tick_volume"]),
                "spread": int(raw["spread"]),
            }
        )
    return output


def execution_entry(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "LONG" else row["open"]


def execution_exit(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "SHORT" else row["open"]


def directional_return(direction: str, entry: float, exit_price: float) -> float:
    return bps(exit_price - entry, entry) if direction == "LONG" else bps(entry - exit_price, entry)


def excursions(direction: str, entry: float, rows: list[dict[str, Any]], point: float) -> tuple[float, float]:
    favorable: list[float] = []
    adverse: list[float] = []
    for row in rows:
        if direction == "LONG":
            favorable.append(bps(row["high"] - entry, entry))
            adverse.append(bps(row["low"] - entry, entry))
        else:
            ask_high = row["high"] + row["spread"] * point
            ask_low = row["low"] + row["spread"] * point
            favorable.append(bps(entry - ask_low, entry))
            adverse.append(bps(entry - ask_high, entry))
    return max(favorable), min(adverse)


def prefixed_features(
    series: Any,
    close_times: list[datetime],
    *,
    decision_time: datetime,
    ticker: str,
    timeframe: str,
    prefix: str,
    built_at: str,
) -> tuple[dict[str, Any], bool, str | None]:
    selected_index = bisect.bisect_right(close_times, decision_time) - 1
    if selected_index < MINIMUM_WARMUP_BARS - 1:
        return {}, False, f"insufficient {timeframe} warmup before {decision_time.strftime(TIME_FORMAT)}"
    selected_close = close_times[selected_index]
    try:
        payload = build_feature_payload(
            series,
            selected_index=selected_index,
            ticker=ticker,
            timeframe=timeframe,
            source_filename=FILE_MAP[ticker][timeframe],
            decision_time_utc=decision_time,
            selected_utc_close=selected_close,
            selected_offset_hours=0.0,
            built_at_utc=built_at,
        )
        flat = flatten_features(series, selected_index, payload)
    except (FeatureContractError, ValueError) as exc:
        return {}, False, str(exc)
    output: dict[str, Any] = {
        f"{prefix}_selected_bar_open": series.bars[selected_index].server_open.strftime(TIME_FORMAT),
        f"{prefix}_selected_bar_close": selected_close.strftime(TIME_FORMAT),
    }
    for key, value in flat.items():
        output[f"{prefix}_{key}"] = value
    return output, True, None


def metric_block(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "mean_bps": None}
    wins = sum(value for value in values if value > 0)
    losses = abs(sum(value for value in values if value < 0))
    return {
        "count": len(values),
        "win_rate": sum(value > 0 for value in values) / len(values),
        "profit_factor_bps": None if losses == 0 else wins / losses,
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values),
    }


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m9c_latest = local_root / "outputs" / "M9C" / "LATEST"
    summary_path = m9c_latest / "01_summary.json"
    outcomes_path = m9c_latest / "04_m1_resolved_trade_outcomes.csv"
    turns_path = m9c_latest / "05_first_turn_context.csv"
    meta_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    required = [summary_path, outcomes_path, turns_path, meta_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print(f"[M9D BLOCKED] required upstream file missing: {missing}")
        return 2

    m9c_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        m9c_summary.get("status") != "PASS_EXPLORATORY_ONLY"
        or m9c_summary.get("implementation") != "M9C_CONTEXT_WARMUP_FIX_V2"
        or int(m9c_summary.get("m1_resolved_trade_count", -1)) != EXPECTED_M9C_RESOLVED
        or int(m9c_summary.get("paired_trade_count", -1)) != EXPECTED_M9C_PAIRS
        or m9c_summary.get("population_tier") != "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH"
    ):
        print("[M9D BLOCKED] M9C LATEST does not match the reviewed frozen replay population")
        return 2

    outcomes = read_csv(outcomes_path)
    turns = read_csv(turns_path)
    if len(outcomes) != EXPECTED_M9C_RESOLVED:
        print(f"[M9D BLOCKED] expected {EXPECTED_M9C_RESOLVED} M9C outcomes, got {len(outcomes)}")
        return 2

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print(f"[M9D BLOCKED] MT5 Files root unavailable: {files_root}")
        return 2

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        m1: dict[str, list[dict[str, Any]]] = {}
        m1_index: dict[str, dict[str, int]] = {}
        points: dict[str, float] = {}
        indicator_series: dict[str, dict[str, Any]] = defaultdict(dict)
        close_times: dict[str, dict[str, list[datetime]]] = defaultdict(dict)

        for ticker in ("XAUUSD", "BTCUSD"):
            m1[ticker] = load_m1(files_root / FILE_MAP[ticker]["M1"])
            m1_index[ticker] = {row["time_text"]: index for index, row in enumerate(m1[ticker])}
            points[ticker] = float(meta["symbols"][ticker]["point"])
            for timeframe in ("M1", "M5", "M15", "H1", "H4"):
                series = load_indicator_series(files_root / FILE_MAP[ticker][timeframe])
                indicator_series[ticker][timeframe] = series
                delta = timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
                close_times[ticker][timeframe] = [bar.server_open + delta for bar in series.bars]

        checkpoint_rows: list[dict[str, Any]] = []
        checkpoint_unavailable: dict[str, int] = defaultdict(int)
        original_outcome_by_id = {row["proxy_trade_id"]: row for row in outcomes}

        for trade in outcomes:
            ticker = trade["ticker"]
            direction = trade["direction"]
            entry_text = trade["entry_server_open"]
            exit_text = trade["exit_server_open"]
            if entry_text not in m1_index[ticker] or exit_text not in m1_index[ticker]:
                raise RuntimeError(f"reviewed M9C exact M1 row disappeared: {trade['proxy_trade_id']}")
            entry_index = m1_index[ticker][entry_text]
            exit_index = m1_index[ticker][exit_text]
            if exit_index <= entry_index:
                raise RuntimeError(f"invalid M1 order: {trade['proxy_trade_id']}")

            m15_series = indicator_series[ticker]["M15"]
            signal_open = parse_time(entry_text)
            current_m15_index = m15_series.index_by_server_open.get(signal_open)
            if current_m15_index is None or current_m15_index < 1:
                raise RuntimeError(f"M15 signal boundary missing: {trade['proxy_trade_id']} {entry_text}")
            selected_m15 = current_m15_index - 1
            signal_atr = m15_series.atr14[selected_m15]
            if signal_atr is None or signal_atr <= 0:
                raise RuntimeError(f"M15 ATR unavailable: {trade['proxy_trade_id']}")

            signal_bid = m1[ticker][entry_index]["open"]
            point = points[ticker]
            exit_exec = execution_exit(direction, m1[ticker][exit_index], point)
            signal_atr_bps = bps(float(signal_atr), signal_bid)

            for ratio in ATR_CHECKPOINTS:
                threshold = (
                    signal_bid - float(signal_atr) * ratio
                    if direction == "LONG"
                    else signal_bid + float(signal_atr) * ratio
                )
                crossing_index: int | None = None
                for index in range(entry_index, exit_index):
                    bar = m1[ticker][index]
                    crossed = bar["low"] <= threshold if direction == "LONG" else bar["high"] >= threshold
                    if crossed:
                        crossing_index = index
                        break
                if crossing_index is None or crossing_index + 1 >= exit_index:
                    continue

                checkpoint_index = crossing_index + 1
                checkpoint_row = m1[ticker][checkpoint_index]
                checkpoint_time = checkpoint_row["time"]
                checkpoint_exec = execution_entry(direction, checkpoint_row, point)
                post_rows = m1[ticker][checkpoint_index : exit_index + 1]
                post_mfe, post_mae = excursions(direction, checkpoint_exec, post_rows, point)
                if direction == "LONG":
                    extreme = min(row["low"] for row in m1[ticker][entry_index : crossing_index + 1])
                    realized_adverse_bps = bps(signal_bid - extreme, signal_bid)
                    recovery_bps = bps(checkpoint_row["open"] - extreme, signal_bid)
                    recovered_signal = any(row["high"] >= signal_bid for row in post_rows)
                else:
                    extreme = max(row["high"] for row in m1[ticker][entry_index : crossing_index + 1])
                    realized_adverse_bps = bps(extreme - signal_bid, signal_bid)
                    recovery_bps = bps(extreme - checkpoint_row["open"], signal_bid)
                    recovered_signal = any(row["low"] <= signal_bid for row in post_rows)

                row: dict[str, Any] = {
                    "proxy_trade_id": trade["proxy_trade_id"],
                    "ticker": ticker,
                    "direction": direction,
                    "entry_server_open": entry_text,
                    "exit_server_open": exit_text,
                    "checkpoint_atr_ratio": ratio,
                    "signal_bid_open": signal_bid,
                    "signal_m15_atr14": float(signal_atr),
                    "signal_m15_atr14_bps": signal_atr_bps,
                    "checkpoint_threshold_price": threshold,
                    "crossing_bar_open": m1[ticker][crossing_index]["time_text"],
                    "checkpoint_decision_time": checkpoint_row["time_text"],
                    "elapsed_minutes_from_signal": int((checkpoint_time - m1[ticker][entry_index]["time"]).total_seconds() / 60),
                    "realized_adverse_depth_bps": realized_adverse_bps,
                    "realized_adverse_depth_atr": realized_adverse_bps / signal_atr_bps,
                    "recovery_from_extreme_bps_at_checkpoint": recovery_bps,
                    "checkpoint_spread_points": checkpoint_row["spread"],
                    "checkpoint_exec_price": checkpoint_exec,
                    "return_from_checkpoint_to_proxy_exit_bps": directional_return(direction, checkpoint_exec, exit_exec),
                    "mfe_from_checkpoint_to_proxy_exit_bps": post_mfe,
                    "mae_from_checkpoint_to_proxy_exit_bps": post_mae,
                    "recovered_original_signal_bid_before_proxy_exit": recovered_signal,
                    "positive_at_frozen_proxy_exit": directional_return(direction, checkpoint_exec, exit_exec) > 0,
                    "original_immediate_return_bps": float(trade["return_bps"]),
                    "original_immediate_mfe_bps": float(trade["mfe_bps"]),
                    "original_immediate_mae_bps": float(trade["mae_bps"]),
                    "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
                    "checkpoint_created_without_future_label": True,
                }

                unavailable_reasons: list[str] = []
                for timeframe in ("M1", "M5", "M15", "H1", "H4"):
                    features, available, reason = prefixed_features(
                        indicator_series[ticker][timeframe],
                        close_times[ticker][timeframe],
                        decision_time=checkpoint_time,
                        ticker=ticker,
                        timeframe=timeframe,
                        prefix=f"checkpoint_{timeframe.lower()}",
                        built_at=built_at,
                    )
                    row.update(features)
                    row[f"checkpoint_{timeframe.lower()}_features_available"] = available
                    if not available:
                        checkpoint_unavailable[f"checkpoint_{timeframe.lower()}"] += 1
                        if reason:
                            unavailable_reasons.append(reason)
                row["checkpoint_feature_unavailable_reason"] = " | ".join(unavailable_reasons)

                for minutes in HORIZONS_MINUTES:
                    target_time = checkpoint_time + timedelta(minutes=minutes)
                    target_text = target_time.strftime(TIME_FORMAT)
                    key = f"directional_return_{minutes}m_bps"
                    if target_time <= m1[ticker][exit_index]["time"] and target_text in m1_index[ticker]:
                        future_index = m1_index[ticker][target_text]
                        future_exit = execution_exit(direction, m1[ticker][future_index], point)
                        row[key] = directional_return(direction, checkpoint_exec, future_exit)
                    else:
                        row[key] = None

                checkpoint_rows.append(row)

        turn_feature_rows: list[dict[str, Any]] = []
        turn_unavailable: dict[str, int] = defaultdict(int)
        for turn in turns:
            ticker = turn["ticker"]
            direction = turn["direction"]
            decision_time = parse_time(turn["turn_entry_time"])
            row: dict[str, Any] = dict(turn)
            unavailable_reasons: list[str] = []
            for timeframe in ("M1", "M5", "M15", "H1", "H4"):
                features, available, reason = prefixed_features(
                    indicator_series[ticker][timeframe],
                    close_times[ticker][timeframe],
                    decision_time=decision_time,
                    ticker=ticker,
                    timeframe=timeframe,
                    prefix=f"turnrich_{timeframe.lower()}",
                    built_at=built_at,
                )
                row.update(features)
                row[f"turnrich_{timeframe.lower()}_features_available"] = available
                if not available:
                    turn_unavailable[f"turnrich_{timeframe.lower()}"] += 1
                    if reason:
                        unavailable_reasons.append(reason)
            row["turnrich_feature_unavailable_reason"] = " | ".join(unavailable_reasons)
            original = original_outcome_by_id.get(turn["proxy_trade_id"])
            if original is not None:
                row["original_immediate_return_bps"] = float(original["return_bps"])
                row["original_immediate_mae_bps"] = float(original["mae_bps"])
                row["original_immediate_mfe_bps"] = float(original["mfe_bps"])
            turn_feature_rows.append(row)

    except Exception as exc:
        print(f"[M9D BLOCKED] {exc}")
        return 2

    checkpoint_summary: list[dict[str, Any]] = []
    for ratio in ATR_CHECKPOINTS:
        selected = [row for row in checkpoint_rows if abs(float(row["checkpoint_atr_ratio"]) - ratio) < 1e-12]
        block = metric_block(selected, "return_from_checkpoint_to_proxy_exit_bps")
        checkpoint_summary.append(
            {
                "checkpoint_atr_ratio": ratio,
                **block,
                "recovered_signal_fraction": (
                    sum(bool(row["recovered_original_signal_bid_before_proxy_exit"]) for row in selected) / len(selected)
                    if selected else None
                ),
                "mean_elapsed_minutes": statistics.fmean(float(row["elapsed_minutes_from_signal"]) for row in selected) if selected else None,
            }
        )

    mae_summary: list[dict[str, Any]] = []
    for ticker in ("XAUUSD", "BTCUSD"):
        for direction in ("LONG", "SHORT"):
            group = [row for row in outcomes if row["ticker"] == ticker and row["direction"] == direction]
            for label, subset in (
                ("WIN", [row for row in group if float(row["return_bps"]) > 0]),
                ("LOSS", [row for row in group if float(row["return_bps"]) <= 0]),
            ):
                mae_values = [float(row["mae_bps"]) for row in subset]
                mfe_values = [float(row["mfe_bps"]) for row in subset]
                mae_summary.append(
                    {
                        "ticker": ticker,
                        "direction": direction,
                        "outcome": label,
                        "count": len(subset),
                        "mean_mae_bps": statistics.fmean(mae_values) if mae_values else None,
                        "median_mae_bps": statistics.median(mae_values) if mae_values else None,
                        "mean_mfe_bps": statistics.fmean(mfe_values) if mfe_values else None,
                        "median_mfe_bps": statistics.median(mfe_values) if mfe_values else None,
                    }
                )

    month_summary: list[dict[str, Any]] = []
    month_keys = sorted({parse_time(row["entry_server_open"]).strftime("%Y-%m") for row in outcomes})
    for month in month_keys:
        for ticker in ("XAUUSD", "BTCUSD"):
            for direction in ("LONG", "SHORT"):
                selected = [
                    row for row in outcomes
                    if parse_time(row["entry_server_open"]).strftime("%Y-%m") == month
                    and row["ticker"] == ticker
                    and row["direction"] == direction
                ]
                if selected:
                    month_summary.append(
                        {"month": month, "ticker": ticker, "direction": direction, **metric_block(selected, "return_bps")}
                    )

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9D_LOSS_PATH_STATE_FEATURE_AUDIT",
        "contract": "MOCHIPOYO_M9D_CAUSAL_ADVERSE_PATH_STATE_V1",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": built_at,
        "audit_only": True,
        "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "upstream_exact_m1_resolved_trades": len(outcomes),
        "upstream_first_turn_trades": len(turns),
        "checkpoint_rows": len(checkpoint_rows),
        "turn_rich_feature_rows": len(turn_feature_rows),
        "checkpoint_ratios": list(ATR_CHECKPOINTS),
        "checkpoint_ratio_role": "OBSERVATION_GRID_ONLY_NOT_ENTRY_OR_STOP_RULE",
        "checkpoint_summary": checkpoint_summary,
        "guardrails": {
            "checkpoint_features_use_future_labels": False,
            "future_outcomes_used_only_after_checkpoint": True,
            "same_sample_gate_promotion_allowed": False,
            "automatic_threshold_selection": False,
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m8c_reset": False,
        },
    }
    quality = {
        "expected_m9c_resolved": EXPECTED_M9C_RESOLVED,
        "actual_m9c_resolved": len(outcomes),
        "checkpoint_feature_unavailable_counts": dict(checkpoint_unavailable),
        "turn_feature_unavailable_counts": dict(turn_unavailable),
        "closed_bars_only_for_features": True,
        "crossing_M1_bar_must_close_before_checkpoint_decision": True,
        "exact_M1_used_for_checkpoint_execution": True,
        "historical_spread_used": True,
        "nearest_M1_fallback_used": False,
        "commission": "NOT_MODELED",
        "swap": "NOT_MODELED",
        "mt5_files_root": str(files_root),
    }

    out_root = local_root / "outputs" / "M9D"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)

    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_adverse_checkpoint_feature_panel.csv", checkpoint_rows)
    write_csv(archive / "03_checkpoint_ratio_summary.csv", checkpoint_summary)
    write_csv(archive / "04_first_turn_rich_feature_panel.csv", turn_feature_rows)
    write_csv(archive / "05_mae_winner_loser_summary.csv", mae_summary)
    write_csv(archive / "06_monthly_base_summary.csv", month_summary)
    dump_json(archive / "07_data_quality.json", quality)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9D builds causal adverse-path state observations from the reviewed M9C Tier-B replay population. "
        "ATR ratios are observation checkpoints only, not entry/stop rules. Rich features are computed only from bars closed by the checkpoint decision time. "
        "Future values are labels only and must not be used to create a checkpoint. No threshold or live gate is promoted by this run.\n",
        encoding="utf-8",
    )
    (archive / "08_audit.log").write_text(
        "\n".join(
            [
                "status=PASS_EXPLORATORY_ONLY",
                "contract=MOCHIPOYO_M9D_CAUSAL_ADVERSE_PATH_STATE_V1",
                f"upstream_resolved={len(outcomes)}",
                f"checkpoint_rows={len(checkpoint_rows)}",
                f"turn_rich_rows={len(turn_feature_rows)}",
                "checkpoint_ratios_are_observation_only=true",
                "same_sample_gate_promotion_allowed=false",
                "m7c_formula_changed=false",
                "m7c_threshold_changed=false",
                "m8c_reset=false",
                "",
            ]
        ),
        encoding="utf-8",
    )

    names = [
        "00_READ_ME_FIRST.txt",
        "01_summary.json",
        "02_adverse_checkpoint_feature_panel.csv",
        "03_checkpoint_ratio_summary.csv",
        "04_first_turn_rich_feature_panel.csv",
        "05_mae_winner_loser_summary.csv",
        "06_monthly_base_summary.csv",
        "07_data_quality.json",
        "08_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)

    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)

    print(
        f"[M9D PASS] trades={len(outcomes)} checkpoints={len(checkpoint_rows)} "
        f"turn_rich={len(turn_feature_rows)}"
    )
    print("[M9D OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
