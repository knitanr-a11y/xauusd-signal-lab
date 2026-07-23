from __future__ import annotations

import json
import os
import shutil
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import run_frozen_proxy_historical_replay as legacy


CONTEXT_TIMEFRAMES = ("m5", "h1", "h4")


def safe_asof_rci_features(
    bars: list[dict[str, Any]],
    boundary: datetime,
    prefix: str,
    direction: str,
) -> tuple[dict[str, Any], bool, str | None]:
    """Return context when sufficiently warmed up; do not discard the trade otherwise.

    M9C's full M15 proxy replay and exact-M1 outcome population are independent of
    M5/H1/H4 context availability.  Early M1-history trades may therefore have an
    exact entry/exit while aggregated H1/H4 has fewer than 20 closed bars.  That is
    a context-coverage limitation, not a replay or outcome failure.
    """
    try:
        return legacy.asof_rci_features(bars, boundary, prefix, direction), True, None
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("insufficient closed "):
            return {
                f"{prefix}_rci9": None,
                f"{prefix}_rci14": None,
                f"{prefix}_rci18": None,
                f"{prefix}_directional_rci9": None,
                f"{prefix}_directional_rci9_delta1": None,
                f"{prefix}_directional_rci9_acceleration": None,
            }, False, message
        raise


def context_zone(value: Any) -> str:
    if value in (None, ""):
        return "UNAVAILABLE"
    zone = float(value)
    if zone >= 80:
        return "GE_80"
    if zone >= 50:
        return "50_TO_80"
    if zone > -50:
        return "MINUS50_TO_50"
    return "LE_MINUS50"


def htf_state(first: dict[str, Any]) -> str:
    h1_value = first.get("turn_h1_directional_rci9_delta1")
    h4_value = first.get("turn_h4_directional_rci9_delta1")
    if h1_value in (None, "") or h4_value in (None, ""):
        return "UNAVAILABLE"
    h1 = float(h1_value) > 0
    h4 = float(h4_value) > 0
    if h1 and h4:
        return "H1_AND_H4_WITH_TRADE"
    if h1:
        return "H1_ONLY_WITH_TRADE"
    if h4:
        return "H4_ONLY_WITH_TRADE"
    return "NEITHER_WITH_TRADE"


def metrics(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    vals = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    return {
        "count": len(vals),
        "win_rate": sum(value > 0 for value in vals) / len(vals) if vals else None,
        "profit_factor_bps": legacy.pf(vals) if vals else None,
        "net_bps": sum(vals),
        "mean_bps": statistics.fmean(vals) if vals else None,
        "median_bps": statistics.median(vals) if vals else None,
    }


def group(rows: list[dict[str, Any]], key: str, return_key: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    labels = sorted({str(row.get(key, "UNAVAILABLE")) for row in rows})
    for label in labels:
        selected = [row for row in rows if str(row.get(key, "UNAVAILABLE")) == label]
        output.append({"grouping": key, "group": label, **metrics(selected, return_key)})
    return output


def main() -> int:
    local_root = (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "xauusd_signal_lab"
        / "mochipoyo_alert_research"
    )
    meta_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not meta_path.is_file():
        print("[M9C BLOCKED] M8B symbol metadata missing")
        return 2

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print("[M9C BLOCKED] MT5 Files root unavailable")
        return 2

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        all_signals: list[dict[str, Any]] = []
        all_pairs: list[dict[str, Any]] = []
        for ticker in ("XAUUSD", "BTCUSD"):
            signals, pairs = legacy.replay_one(ticker, files_root, built_at)
            all_signals.extend(signals)
            all_pairs.extend(pairs)

        m1 = {
            ticker: legacy.load_m1(files_root / legacy.M1_FILES[ticker])
            for ticker in ("XAUUSD", "BTCUSD")
        }
        m1_idx = {
            ticker: {row["time_text"]: index for index, row in enumerate(rows)}
            for ticker, rows in m1.items()
        }
        derived = {
            ticker: {
                name: legacy.aggregate(rows, minutes)
                for name, minutes in {"m5": 5, "h1": 60, "h4": 240}.items()
            }
            for ticker, rows in m1.items()
        }
        point = {
            ticker: float(meta["symbols"][ticker]["point"])
            for ticker in ("XAUUSD", "BTCUSD")
        }

        resolved: list[dict[str, Any]] = []
        turns: list[dict[str, Any]] = []
        context_unavailable_counts: dict[str, int] = defaultdict(int)
        outcome_skip_counts: dict[str, int] = defaultdict(int)

        for pair in all_pairs:
            ticker = pair["ticker"]
            entry_text = pair["entry_server_open"]
            exit_text = pair["exit_server_open"]

            if entry_text not in m1_idx[ticker] or exit_text not in m1_idx[ticker]:
                outcome_skip_counts["missing_exact_m1_entry_or_exit"] += 1
                continue

            entry_index = m1_idx[ticker][entry_text]
            exit_index = m1_idx[ticker][exit_text]
            if exit_index <= entry_index:
                outcome_skip_counts["nonpositive_m1_index_order"] += 1
                continue

            direction = pair["direction"]
            entry_exec = legacy.execution_entry(
                direction, m1[ticker][entry_index], point[ticker]
            )
            exit_exec = legacy.execution_exit(
                direction, m1[ticker][exit_index], point[ticker]
            )
            mfe, mae = legacy.excursions(
                direction,
                entry_exec,
                m1[ticker][entry_index : exit_index + 1],
                point[ticker],
            )
            row: dict[str, Any] = {
                **pair,
                "entry_exec_price": entry_exec,
                "exit_exec_price": exit_exec,
                "return_bps": legacy.trade_return(direction, entry_exec, exit_exec),
                "mfe_bps": mfe,
                "mae_bps": mae,
                "holding_minutes_clock": int(
                    (
                        m1[ticker][exit_index]["time"]
                        - m1[ticker][entry_index]["time"]
                    ).total_seconds()
                    / 60
                ),
                "exact_m1_entry_exit": True,
            }

            signal_context_complete = True
            signal_context_reasons: list[str] = []
            for timeframe in CONTEXT_TIMEFRAMES:
                values, available, reason = safe_asof_rci_features(
                    derived[ticker][timeframe],
                    m1[ticker][entry_index]["time"],
                    f"signal_{timeframe}",
                    direction,
                )
                row.update(values)
                row[f"signal_{timeframe}_context_available"] = available
                if not available:
                    signal_context_complete = False
                    context_unavailable_counts[f"signal_{timeframe}"] += 1
                    if reason:
                        signal_context_reasons.append(reason)

            row["signal_context_complete_m5_h1_h4"] = signal_context_complete
            row["signal_context_unavailable_reason"] = " | ".join(signal_context_reasons)
            row["signal_m5_directional_rci9_zone"] = context_zone(
                row.get("signal_m5_directional_rci9")
            )
            resolved.append(row)

            signal_bid = m1[ticker][entry_index]["open"]
            first: dict[str, Any] | None = None
            for index in range(entry_index + 1, exit_index):
                if index + 1 >= exit_index:
                    break
                if not legacy.is_turn_candidate(direction, m1[ticker], index, signal_bid):
                    continue

                turn_entry_index = index + 1
                turn_exec = legacy.execution_entry(
                    direction, m1[ticker][turn_entry_index], point[ticker]
                )
                turn_mfe, turn_mae = legacy.excursions(
                    direction,
                    turn_exec,
                    m1[ticker][turn_entry_index : exit_index + 1],
                    point[ticker],
                )
                first = {
                    **pair,
                    "turn_confirmation_time": m1[ticker][index]["time_text"],
                    "turn_entry_time": m1[ticker][turn_entry_index]["time_text"],
                    "initial_pullback_depth_bps": legacy.pullback_depth(
                        direction,
                        signal_bid,
                        m1[ticker][entry_index : index + 1],
                    ),
                    "minutes_to_first_turn": int(
                        (
                            m1[ticker][turn_entry_index]["time"]
                            - m1[ticker][entry_index]["time"]
                        ).total_seconds()
                        / 60
                    ),
                    "return_from_first_turn_bps": legacy.trade_return(
                        direction, turn_exec, exit_exec
                    ),
                    "mfe_from_first_turn_bps": turn_mfe,
                    "mae_from_first_turn_bps": turn_mae,
                    "signal_m5_directional_rci9": row.get(
                        "signal_m5_directional_rci9"
                    ),
                    "signal_m5_directional_rci9_zone": row[
                        "signal_m5_directional_rci9_zone"
                    ],
                }

                turn_context_complete = True
                turn_context_reasons: list[str] = []
                for timeframe in CONTEXT_TIMEFRAMES:
                    values, available, reason = safe_asof_rci_features(
                        derived[ticker][timeframe],
                        m1[ticker][turn_entry_index]["time"],
                        f"turn_{timeframe}",
                        direction,
                    )
                    first.update(values)
                    first[f"turn_{timeframe}_context_available"] = available
                    if not available:
                        turn_context_complete = False
                        context_unavailable_counts[f"turn_{timeframe}"] += 1
                        if reason:
                            turn_context_reasons.append(reason)

                first["turn_context_complete_m5_h1_h4"] = turn_context_complete
                first["turn_context_unavailable_reason"] = " | ".join(
                    turn_context_reasons
                )
                first["turn_htf_state"] = htf_state(first)
                break

            if first is not None:
                turns.append(first)

    except Exception as exc:
        print(f"[M9C BLOCKED] {exc}")
        return 2

    ticker_direction: list[dict[str, Any]] = []
    for ticker, direction in sorted(
        {(row["ticker"], row["direction"]) for row in resolved}
    ):
        selected = [
            row
            for row in resolved
            if row["ticker"] == ticker and row["direction"] == direction
        ]
        ticker_direction.append(
            {"ticker": ticker, "direction": direction, **metrics(selected, "return_bps")}
        )

    m5_context_turns = [
        row for row in turns if row.get("signal_m5_directional_rci9_zone") != "UNAVAILABLE"
    ]
    htf_context_turns = [
        row for row in turns if row.get("turn_htf_state") != "UNAVAILABLE"
    ]

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9C_FROZEN_PROXY_HISTORICAL_REPLAY",
        "implementation": "M9C_CONTEXT_WARMUP_FIX_V2",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": built_at,
        "audit_only": True,
        "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "signal_count": len(all_signals),
        "paired_trade_count": len(all_pairs),
        "m1_resolved_trade_count": len(resolved),
        "first_turn_count": len(turns),
        "m5_context_turn_count": len(m5_context_turns),
        "htf_context_turn_count": len(htf_context_turns),
        "m1_resolved_metrics": metrics(resolved, "return_bps"),
        "first_turn_metrics": metrics(turns, "return_from_first_turn_bps"),
        "cutoffs": {
            key: value.strftime(legacy.TIME_FORMAT)
            for key, value in legacy.CUT_OFF.items()
        },
        "formula": {
            "PRIMARY_LONG": "IDLE AND rci9_turn_up AND BULLISH_STACK",
            "PRIMARY_SHORT": "IDLE AND rci9_turn_down AND BEARISH_STACK",
            "LONG_EXIT": f"ACTIVE_LONG AND rci9>={legacy.LONG_EXIT_RCI9}",
            "SHORT_EXIT": f"ACTIVE_SHORT AND rci9<={legacy.SHORT_EXIT_RCI9}",
        },
        "coverage": {
            "context_unavailable_counts": dict(context_unavailable_counts),
            "outcome_skip_counts": dict(outcome_skip_counts),
            "policy": "KEEP_EXACT_M1_OUTCOME_EVEN_WHEN_M5_H1_H4_CONTEXT_IS_NOT_YET_WARM",
        },
        "guardrails": {
            "source_truth": False,
            "formula_tuned_on_replay": False,
            "threshold_promotable": False,
            "m8c_reset": False,
            "m7c_changed": False,
        },
    }

    quality = {
        "m15_feature_engine": "existing feature_snapshot_builder + alert_trigger_signature_audit.flatten_features",
        "minimum_m15_warmup_bars": legacy.MINIMUM_WARMUP_BARS,
        "current_m15_high_low_close_used": False,
        "future_used_for_candidate_generation": False,
        "exact_m1_entry_exit_required_for_outcome": True,
        "nearest_m1_fallback_used": False,
        "historical_spread_used": True,
        "context_warmup_failure_blocks_replay": False,
        "context_missing_value_policy": "NULL_PLUS_EXPLICIT_AVAILABILITY_FLAGS",
        "m5_zone_summary_excludes_unavailable_context": True,
        "turn_htf_summary_excludes_unavailable_context": True,
        "commission": "NOT_MODELED",
        "swap": "NOT_MODELED",
        "mt5_files_root": str(files_root),
    }

    out_root = local_root / "outputs" / "M9C"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)

    legacy.dump_json(archive / "01_summary.json", summary)
    legacy.write_csv(archive / "02_replay_signal_ledger.csv", all_signals)
    legacy.write_csv(archive / "03_replay_trade_pairs.csv", all_pairs)
    legacy.write_csv(archive / "04_m1_resolved_trade_outcomes.csv", resolved)
    legacy.write_csv(archive / "05_first_turn_context.csv", turns)
    legacy.write_csv(
        archive / "06_m5_zone_summary.csv",
        group(
            m5_context_turns,
            "signal_m5_directional_rci9_zone",
            "return_from_first_turn_bps",
        ),
    )
    legacy.write_csv(
        archive / "07_turn_htf_summary.csv",
        group(htf_context_turns, "turn_htf_state", "return_from_first_turn_bps"),
    )
    legacy.write_csv(archive / "08_ticker_direction_summary.csv", ticker_direction)
    legacy.dump_json(archive / "09_data_quality.json", quality)

    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9C frozen M7C proxy historical replay. Tier B is NOT genuine Mochipoyo source truth. "
        "V2 preserves exact-M1 outcomes when early M5/H1/H4 context is not yet sufficiently warmed; "
        "missing context is explicit and excluded only from the affected context summaries.\n",
        encoding="utf-8",
    )
    (archive / "10_audit.log").write_text(
        "\n".join(
            [
                "status=PASS_EXPLORATORY_ONLY",
                "implementation=M9C_CONTEXT_WARMUP_FIX_V2",
                f"signals={len(all_signals)}",
                f"paired_trades={len(all_pairs)}",
                f"m1_resolved={len(resolved)}",
                f"first_turn={len(turns)}",
                f"m5_context_turns={len(m5_context_turns)}",
                f"htf_context_turns={len(htf_context_turns)}",
                "population_tier=TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
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
        "02_replay_signal_ledger.csv",
        "03_replay_trade_pairs.csv",
        "04_m1_resolved_trade_outcomes.csv",
        "05_first_turn_context.csv",
        "06_m5_zone_summary.csv",
        "07_turn_htf_summary.csv",
        "08_ticker_direction_summary.csv",
        "09_data_quality.json",
        "10_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)

    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)

    print(
        f"[M9C PASS] signals={len(all_signals)} paired={len(all_pairs)} "
        f"m1_resolved={len(resolved)} first_turn={len(turns)} "
        f"m5_context={len(m5_context_turns)} htf_context={len(htf_context_turns)}"
    )
    print("[M9C OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
