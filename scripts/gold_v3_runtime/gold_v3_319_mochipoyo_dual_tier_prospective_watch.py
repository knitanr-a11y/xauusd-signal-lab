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

import gold_v3_311_mochipoyo_and_independent_candidate_research as stage311
import gold_v3_314_prospective_mochipoyo_watch as stage314

POINT_SIZE = 0.01
TOL = 1e-12
SPEC_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "gold_v3_319"
    / "stage319_mochipoyo_dual_tier_prospective_watch_spec.json"
)
EXPECTED_STAGE318_STATUS = (
    "GOLD_V3_318_MOCHIPOYO_HIGH_CONFIDENCE_REFINEMENT_COMPLETE"
)
EXPECTED_STAGE318_DECISION = "MOCHIPOYO_HIGHER_WIN_RATE_PRIMARY_FOUND"


class ContractError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--stage318-json", required=True)
    parser.add_argument("--stage318-primary", required=True)
    parser.add_argument("--stage318-premium", required=True)
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


def stable_event_id(decision_dt: pd.Timestamp) -> str:
    raw = (
        "GOLD_V3_STAGE319_MOCHIPOYO_DUAL_TIER|"
        f"{pd.Timestamp(decision_dt).isoformat()}"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    stage314.write_json(path, payload)


def same_optional_float(values: pd.Series, label: str) -> None:
    converted = pd.to_numeric(values, errors="coerce")
    finite = converted.dropna()
    if finite.empty:
        return
    if converted.isna().any():
        raise ContractError(f"POOLED_SIGNAL_OPTIONAL_PARITY_FAILED: {label}")
    if float(finite.max() - finite.min()) > TOL:
        raise ContractError(
            f"POOLED_SIGNAL_NUMERIC_PARITY_FAILED: {label} "
            f"spread={float(finite.max() - finite.min())}"
        )


def verify_stage318_sources(
    stage318_json_path: Path,
    stage318_json: dict[str, Any],
    primary_path: Path,
    premium_path: Path,
) -> dict[str, str]:
    if stage318_json.get("status") != EXPECTED_STAGE318_STATUS:
        raise ContractError(
            f"STAGE318_STATUS_UNEXPECTED: {stage318_json.get('status')}"
        )
    if stage318_json.get("decision") != EXPECTED_STAGE318_DECISION:
        raise ContractError(
            f"STAGE318_DECISION_UNEXPECTED: {stage318_json.get('decision')}"
        )
    expected_primary = stage318_json.get("outputs", {}).get(
        "primary_selected_sha256"
    )
    expected_premium = stage318_json.get("outputs", {}).get(
        "sparse_selected_sha256"
    )
    actual_primary = sha256_file(primary_path)
    actual_premium = sha256_file(premium_path)
    if expected_primary != actual_primary:
        raise ContractError(
            "STAGE318_PRIMARY_SHA_MISMATCH: "
            f"expected={expected_primary} actual={actual_primary}"
        )
    if expected_premium != actual_premium:
        raise ContractError(
            "STAGE318_PREMIUM_SHA_MISMATCH: "
            f"expected={expected_premium} actual={actual_premium}"
        )
    primary_profile = stage318_json.get("primary_high_confidence", {}).get(
        "profile_name"
    )
    premium_profile = stage318_json.get("premium_sparse_watch", {}).get(
        "profile_name"
    )
    if primary_profile != "ATR_STEADY_1_10_TO_1_45":
        raise ContractError(f"STAGE318_PRIMARY_PROFILE_UNEXPECTED: {primary_profile}")
    if premium_profile != "TREND_FLOW_COMPRESSION_GE_0_95":
        raise ContractError(f"STAGE318_PREMIUM_PROFILE_UNEXPECTED: {premium_profile}")
    return {
        "stage318_json_sha256": sha256_file(stage318_json_path),
        "primary_csv_sha256": actual_primary,
        "premium_csv_sha256": actual_premium,
    }


def freeze_contract(
    contract_path: Path,
    spec: dict[str, Any],
    spec_sha: str,
    stage318_json_path: Path,
    stage318_json: dict[str, Any],
    primary_path: Path,
    premium_path: Path,
    source_hashes: dict[str, str],
    m1: pd.DataFrame,
    m5: pd.DataFrame,
    h4: pd.DataFrame,
) -> tuple[dict[str, Any], bool]:
    cutoffs = {
        "m1_latest_closed_open_time": stage314.iso(m1.time.iloc[-1]),
        "m1_latest_closed_close_time": stage314.iso(m1.close_time.iloc[-1]),
        "m5_latest_closed_open_time": stage314.iso(m5.time.iloc[-1]),
        "m5_latest_closed_close_time": stage314.iso(m5.close_time.iloc[-1]),
        "h4_latest_closed_open_time": stage314.iso(h4.time.iloc[-1]),
        "h4_latest_closed_close_time": stage314.iso(h4.close_time.iloc[-1]),
        "prospective_decision_dt_strictly_after": stage314.iso(
            m5.close_time.iloc[-1]
        ),
    }
    immutable = {
        "spec_id": spec["spec_id"],
        "spec_sha256": spec_sha,
        "source_stage318_json_sha256": source_hashes["stage318_json_sha256"],
        "source_stage318_primary_csv_sha256": source_hashes[
            "primary_csv_sha256"
        ],
        "source_stage318_premium_csv_sha256": source_hashes[
            "premium_csv_sha256"
        ],
        "source_candidate": spec["source_candidate"],
        "pooled_tracks": spec["pooled_tracks"],
        "base_filter": spec["base_filter"],
        "watch_tiers": spec["watch_tiers"],
        "pooling_contract": spec["pooling_contract"],
        "portfolio_policy": spec["portfolio_policy"],
        "risk_contract": spec["risk_contract"],
        "future_review_gates": spec["future_review_gates"],
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
        "status": "GOLD_V3_319_DUAL_TIER_PROSPECTIVE_WATCH_CONTRACT_FROZEN",
        **immutable,
        "frozen_cutoffs": cutoffs,
        "source_stage318": {
            "result_path": str(stage318_json_path),
            "primary_trades_path": str(primary_path),
            "premium_trades_path": str(premium_path),
            "decision": stage318_json["decision"],
            "historical_reference_only": True,
            "primary_reference": stage318_json["primary_high_confidence"],
            "premium_reference": stage318_json["premium_sparse_watch"],
        },
        "contract_rules": spec["prospective_contract"],
        "preserved_state": spec["preserved_state"],
    }
    write_json(contract_path, contract)
    return contract, True


def pooled_candidate_signals(
    frame: pd.DataFrame,
    pair: Any,
    spec: dict[str, Any],
    frozen_cutoff: pd.Timestamp,
) -> list[dict[str, Any]]:
    lookup = {item.name: item for item in stage311.TRACK_SPECS}
    raw: list[dict[str, Any]] = []
    for track_name in spec["pooled_tracks"]:
        generated = stage311.generate_track_signals(frame, pair, lookup[track_name])
        for signal in generated:
            decision_dt = pd.Timestamp(signal["decision_dt"])
            if decision_dt <= frozen_cutoff:
                continue
            if signal["direction"] != "SHORT":
                continue
            if float(signal["atr_ratio_signal"]) < 1.0:
                continue
            if bool(signal["round_number_near"]):
                continue
            raw.append(signal)

    if not raw:
        return []
    raw_frame = pd.DataFrame(raw)
    signals: list[dict[str, Any]] = []
    for decision_dt, group in raw_frame.groupby("decision_dt", sort=True):
        for column in ("pair", "direction", "direction_num", "signal_index"):
            if group[column].nunique(dropna=False) != 1:
                raise ContractError(f"POOLED_SIGNAL_PARITY_FAILED: {column}")
        for column in (
            "atr_entry_context",
            "last_swing_high",
            "last_swing_low",
            "atr_ratio_signal",
            "extension_atr_signal",
            "compression_ratio_signal",
            "range_atr_signal",
        ):
            same_optional_float(group[column], column)

        ordered = group.sort_values(
            ["quality_score", "track"],
            ascending=[False, True],
            kind="mergesort",
        )
        signal = ordered.iloc[0].to_dict()
        atr_ratio = float(signal["atr_ratio_signal"])
        compression = signal.get("compression_ratio_signal")
        compression_value = (
            float(compression)
            if compression is not None and pd.notna(compression)
            else None
        )
        primary = 1.10 <= atr_ratio <= 1.45
        premium = compression_value is not None and compression_value >= 0.95
        if not primary and not premium:
            continue
        if primary and premium:
            watch_tier = "PRIMARY+PREMIUM"
        elif primary:
            watch_tier = "PRIMARY"
        else:
            watch_tier = "PREMIUM"
        tracks = sorted(set(group.track.astype(str)))
        signal.update(
            {
                "candidate_id": "GOLD_V3_STAGE318_MOCHI_SHORT_DUAL_TIER",
                "event_id": stable_event_id(pd.Timestamp(decision_dt)),
                "priority": 10,
                "setup": "MOCHI_UNION",
                "track": "MOCHI_UNION",
                "category": "MOCHIPOYO_DUAL_TIER_PROSPECTIVE",
                "decision_dt": pd.Timestamp(decision_dt),
                "quality_score": float(group.quality_score.max()),
                "pooled_tracks": "+".join(tracks),
                "pooled_track_count": len(tracks),
                "watch_tier": watch_tier,
                "primary_eligible": bool(primary),
                "premium_eligible": bool(premium),
                "exit_profile": "RR1_5",
            }
        )
        signals.append(signal)
    signals.sort(key=lambda row: pd.Timestamp(row["decision_dt"]))
    return signals


def dataframe_for_csv(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=[
                "event_id",
                "candidate_id",
                "watch_tier",
                "primary_eligible",
                "premium_eligible",
                "pooled_tracks",
                "pooled_track_count",
                "decision_dt",
                "entry_dt",
                "exit_dt",
                "max_exit_dt",
                "trade_state",
                "portfolio_status",
                "direction",
                "direction_num",
                "quality_score",
                "atr_ratio_signal",
                "compression_ratio_signal",
                "range_atr_signal",
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
            frame[column] = frame[column].map(stage314.iso)
    return frame


def future_review_gate(
    summary: dict[str, Any],
    requirements: dict[str, Any],
) -> dict[str, Any]:
    eligible = bool(
        summary["trades"]
        >= int(requirements["minimum_resolved_accepted_trades"])
        and summary["win_rate"] >= float(requirements["minimum_win_rate"])
        and stage314.pf_number(summary)
        >= float(requirements["minimum_profit_factor"])
        and summary["spread_adjusted_total_r"]
        > float(requirements["minimum_total_r_exclusive"])
        and summary["spread_adjusted_max_drawdown_r"]
        <= float(requirements["maximum_drawdown_r"])
        and summary["largest_win_share_of_positive_pnl"]
        <= float(requirements["maximum_largest_winner_share"])
    )
    return {
        "review_eligible": eligible,
        "automatic_promotion": False,
        "requirements": requirements,
        "important": (
            "Eligibility only opens a human audit. It cannot change Stage292, "
            "final signal, Discord, or MT5 execution."
        ),
    }


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    stage318_json_path = Path(args.stage318_json).expanduser().resolve()
    primary_path = Path(args.stage318_primary).expanduser().resolve()
    premium_path = Path(args.stage318_premium).expanduser().resolve()
    contract_path = Path(args.contract).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    signals_csv = Path(args.signals_csv).expanduser().resolve()
    resolved_csv = Path(args.resolved_csv).expanduser().resolve()
    pending_csv = Path(args.pending_csv).expanduser().resolve()
    point_size = float(args.point_size)

    spec = load_json(SPEC_PATH)
    spec_sha = sha256_file(SPEC_PATH)
    stage318_json = load_json(stage318_json_path)
    source_hashes = verify_stage318_sources(
        stage318_json_path,
        stage318_json,
        primary_path,
        premium_path,
    )
    m1, m5, h4, frame, pair = stage314.read_closed_context(
        candle_dir,
        point_size,
    )
    contract, contract_created = freeze_contract(
        contract_path,
        spec,
        spec_sha,
        stage318_json_path,
        stage318_json,
        primary_path,
        premium_path,
        source_hashes,
        m1,
        m5,
        h4,
    )
    frozen_cutoff = pd.Timestamp(
        contract["frozen_cutoffs"]["prospective_decision_dt_strictly_after"]
    )

    signals = pooled_candidate_signals(frame, pair, spec, frozen_cutoff)
    prepared = [
        stage314.prepare_trade(signal, frame, m1, pair, point_size)
        for signal in signals
    ]
    portfolio_rows = stage314.apply_portfolio_policy(prepared)

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
    primary_resolved = [
        row for row in accepted_resolved if bool(row.get("primary_eligible"))
    ]
    premium_resolved = [
        row for row in accepted_resolved if bool(row.get("premium_eligible"))
    ]

    combined_summary = stage314.summarize_resolved(
        pd.DataFrame(accepted_resolved)
    )
    primary_summary = stage314.summarize_resolved(pd.DataFrame(primary_resolved))
    premium_summary = stage314.summarize_resolved(pd.DataFrame(premium_resolved))
    gates = spec["future_review_gates"]
    combined_gate = future_review_gate(combined_summary, gates["COMBINED_UNIQUE"])
    primary_gate = future_review_gate(primary_summary, gates["PRIMARY"])
    premium_gate = future_review_gate(premium_summary, gates["PREMIUM"])

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

    any_eligible = bool(
        primary_gate["review_eligible"]
        or premium_gate["review_eligible"]
        or combined_gate["review_eligible"]
    )
    if any_eligible:
        status = "GOLD_V3_319_DUAL_TIER_PROSPECTIVE_HUMAN_AUDIT_ELIGIBLE"
        decision = "HUMAN_AUDIT_ELIGIBILITY_OPEN_NO_AUTOMATIC_PROMOTION"
    elif not signals:
        status = (
            "GOLD_V3_319_DUAL_TIER_PROSPECTIVE_WATCH_FROZEN_WAITING_FOR_UNSEEN_DATA"
            if contract_created
            else "GOLD_V3_319_DUAL_TIER_PROSPECTIVE_WATCH_WAITING_FOR_SIGNAL"
        )
        decision = "WAIT_FOR_FIRST_POST_FREEZE_CLOSED_M5_SIGNAL"
    else:
        status = "GOLD_V3_319_DUAL_TIER_PROSPECTIVE_WATCH_COLLECTING"
        decision = "COLLECT_FUTURE_RESOLVED_TRADES_WITHOUT_RULE_CHANGES"

    tier_counts = {
        "PRIMARY": sum(row.get("watch_tier") == "PRIMARY" for row in portfolio_rows),
        "PREMIUM": sum(row.get("watch_tier") == "PREMIUM" for row in portfolio_rows),
        "PRIMARY+PREMIUM": sum(
            row.get("watch_tier") == "PRIMARY+PREMIUM" for row in portfolio_rows
        ),
    }
    report = {
        "status": status,
        "mode": "AUDIT_ONLY_FUTURE_ONLY_DUAL_TIER_PROSPECTIVE_WATCH",
        "decision": decision,
        "contract": {
            "path": str(contract_path),
            "sha256": sha256_file(contract_path),
            "created_this_run": contract_created,
            "cutoff_moved": False,
            "frozen_cutoffs": contract["frozen_cutoffs"],
        },
        "current_closed_history": {
            "m1_latest_open_time": stage314.iso(m1.time.iloc[-1]),
            "m1_latest_close_time": stage314.iso(m1.close_time.iloc[-1]),
            "m5_latest_open_time": stage314.iso(m5.time.iloc[-1]),
            "m5_latest_close_time": stage314.iso(m5.close_time.iloc[-1]),
            "h4_latest_open_time": stage314.iso(h4.time.iloc[-1]),
            "h4_latest_close_time": stage314.iso(h4.close_time.iloc[-1]),
        },
        "counts": {
            "raw_post_freeze_signals": len(signals),
            "portfolio_rows": len(portfolio_rows),
            "accepted_resolved_unique": len(accepted_resolved),
            "accepted_pending_unique": len(accepted_pending),
            "rejected_overlap": sum(
                row["portfolio_status"] == "REJECTED_OVERLAP"
                for row in portfolio_rows
            ),
            "primary_eligible_resolved": len(primary_resolved),
            "premium_eligible_resolved": len(premium_resolved),
            "tier_signal_counts": tier_counts,
        },
        "resolved_metrics": {
            "combined_unique": combined_summary,
            "primary_eligible": primary_summary,
            "premium_eligible": premium_summary,
        },
        "future_review_gates": {
            "combined_unique": combined_gate,
            "primary": primary_gate,
            "premium": premium_gate,
        },
        "source_stage318": {
            "result_path": str(stage318_json_path),
            "result_sha256": source_hashes["stage318_json_sha256"],
            "primary_csv_path": str(primary_path),
            "primary_csv_sha256": source_hashes["primary_csv_sha256"],
            "premium_csv_path": str(premium_path),
            "premium_csv_sha256": source_hashes["premium_csv_sha256"],
            "historical_reference_only": True,
            "primary_profile": "ATR_STEADY_1_10_TO_1_45",
            "premium_profile": "TREND_FLOW_COMPRESSION_GE_0_95",
        },
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
            "automatic_promotion": False,
            "stage314_prospective_watch": "UNCHANGED_ACTIVE",
            "stage317_research_watch": "UNCHANGED_RETAINED",
            "stage318_research_result": "UNCHANGED_RETAINED",
            "stage315_independent_research": "UNCHANGED",
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage292_candidate_pool_changed": False,
        },
        "safety_flags": {
            "closed_candles_only": True,
            "resolved_metrics_only": True,
            "pending_as_of_pnl_forbidden": True,
            "same_m1_tp_sl_priority": "SL",
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    write_json(output_path, report)
    print(json.dumps(stage314.json_safe(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
