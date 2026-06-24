#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gold_v3_311_mochipoyo_and_independent_candidate_research as stage311
import gold_v3_314_prospective_mochipoyo_watch as stage314
import gold_v3_319_mochipoyo_dual_tier_prospective_watch as stage319

TOL = 1e-12
POINT_SIZE = 0.01

EXPECTED_STATUS = (
    "GOLD_V3_329_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_RUNTIME_AUDIT_ONLY"
)
EXPECTED_SOURCE = "M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND"
EXPECTED_POLICY = "RELATIVE_TRAILING_MEAN_R_N2"
EXPECTED_LANE = "BALANCED_OR_PREMIUM"
EXPECTED_COST_VIEW = "1p0x"
EXPECTED_CUTOFF = pd.Timestamp("2026-06-23 13:55:00")
EXPECTED_CONTRACT_SHA256 = (
    "cfdfdd74050d33d68dcaa97dcb14b9c812f0cad00807870c922d0d13c6e050f9"
)
EXPECTED_BOOTSTRAP_SHA256 = (
    "90824803f7bb3992e73f8e0727760ffba6c31f68f77e771884a099a2cc26178e"
)
EXPECTED_BOOTSTRAP_STATE_SHA256 = (
    "6b165f518f67212ca217f41dc40b7e24228a5c9e3eabd2cf5a517869bb19dbaf"
)
EXPECTED_CONTRACT_STATUS = (
    "GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_FROZEN"
)
EXPECTED_BOOTSTRAP_STATUS = (
    "GOLD_V3_328_PERSISTENT_ROUTER_BOOTSTRAP_STATE_FROZEN"
)
GROUPS = ("PREMIUM_INVOLVED", "BALANCED_WITHOUT_PREMIUM")
POOLED_TRACKS = (
    "MOCHI_EARLY_PULLBACK",
    "MOCHI_HIDDEN_PULLBACK",
    "MOCHI_HTF_RCI_RESUME",
    "MOCHI_ROLL_RETEST",
)
PENDING_STATES = {
    "PENDING_RESOLUTION",
    "AWAITING_NEXT_CLOSED_M5_ENTRY",
    "AWAITING_M1_ENTRY_BAR",
}
JOURNAL_COLUMNS = [
    "event_id",
    "source_candidate",
    "decision_dt",
    "entry_dt",
    "exit_dt",
    "router_group",
    "router_selected",
    "router_decision_reason",
    "group_score_before_entry",
    "other_group_score_before_entry",
    "premium_history_count_before_entry",
    "balanced_without_premium_history_count_before_entry",
    "spread_adjusted_pnl",
    "spread_adjusted_r",
    "exit_reason",
    "state_processed_candidates_after",
    "state_last_entry_dt_after",
    "state_last_exit_dt_after",
    "state_sha256_after",
]
SIGNAL_COLUMNS = [
    "event_id",
    "raw_track_event_id",
    "source_candidate",
    "candidate_id",
    "pair",
    "direction",
    "direction_num",
    "signal_index",
    "decision_dt",
    "entry_dt",
    "exit_dt",
    "max_exit_dt",
    "pooled_tracks",
    "pooled_track_count",
    "balanced_eligible",
    "premium_eligible",
    "router_group",
    "router_selected",
    "router_decision_reason",
    "group_score_before_entry",
    "other_group_score_before_entry",
    "premium_history_count_before_entry",
    "balanced_without_premium_history_count_before_entry",
    "trade_state",
    "state_reason",
    "portfolio_status",
    "quality_score",
    "atr_entry_context",
    "atr_ratio_signal",
    "extension_atr_signal",
    "compression_ratio_signal",
    "range_atr_signal",
    "round_number_near",
    "entry_price",
    "entry_spread_points",
    "entry_spread_price",
    "atr_entry",
    "risk_price",
    "sl_price",
    "tp_price",
    "exit_price",
    "exit_reason",
    "gross_pnl",
    "spread_adjusted_pnl",
    "gross_r",
    "spread_adjusted_r",
]


class RuntimeAuditError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--bootstrap-state", required=True)
    parser.add_argument("--runtime-state", required=True)
    parser.add_argument("--journal-csv", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--raw-signals-csv", required=True)
    parser.add_argument("--canonical-signals-csv", required=True)
    parser.add_argument("--source-pending-csv", required=True)
    parser.add_argument("--source-resolved-csv", required=True)
    parser.add_argument("--selected-signals-csv", required=True)
    parser.add_argument("--selected-pending-csv", required=True)
    parser.add_argument("--selected-resolved-csv", required=True)
    parser.add_argument("--rejected-overlap-csv", required=True)
    parser.add_argument("--health-csv", required=True)
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    return stage314.json_safe(value)


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        json_safe(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_state(state: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(state).encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(
        path,
        json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n",
    )


def atomic_write_csv(path: Path, frame: pd.DataFrame) -> None:
    text = frame.to_csv(index=False, encoding=None, lineterminator="\n")
    atomic_write_text(path, "\ufeff" + text)


def parse_bool_value(value: Any, label: str) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise RuntimeAuditError(f"BOOLEAN_PARSE_FAILED: {label}={value!r}")


def optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeAuditError(f"NONFINITE_FLOAT: {value!r}")
    return result


def floats_equal(left: Any, right: Any, label: str) -> None:
    left_value = optional_float(left)
    right_value = optional_float(right)
    if left_value is None and right_value is None:
        return
    if left_value is None or right_value is None:
        raise RuntimeAuditError(f"OPTIONAL_FLOAT_MISMATCH: {label}")
    difference = abs(left_value - right_value)
    if difference > TOL:
        raise RuntimeAuditError(
            f"FLOAT_MISMATCH: {label} difference={difference}"
        )


def validate_router_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != 1:
        raise RuntimeAuditError("ROUTER_STATE_SCHEMA_UNEXPECTED")
    if state.get("policy") != EXPECTED_POLICY:
        raise RuntimeAuditError("ROUTER_STATE_POLICY_UNEXPECTED")
    if state.get("selected_lane") != EXPECTED_LANE:
        raise RuntimeAuditError("ROUTER_STATE_LANE_UNEXPECTED")
    if state.get("cost_view") != EXPECTED_COST_VIEW:
        raise RuntimeAuditError("ROUTER_STATE_COST_VIEW_UNEXPECTED")
    if sorted(state.get("groups", {}).keys()) != sorted(GROUPS):
        raise RuntimeAuditError("ROUTER_STATE_GROUPS_UNEXPECTED")
    processed = int(state.get("processed_candidates", -1))
    if processed < 0:
        raise RuntimeAuditError("ROUTER_STATE_PROCESSED_INVALID")
    total = 0
    for group in GROUPS:
        payload = state["groups"][group]
        count = int(payload.get("resolved_count", -1))
        values = payload.get("last_two_r")
        if count < 0 or not isinstance(values, list):
            raise RuntimeAuditError(f"ROUTER_STATE_GROUP_INVALID: {group}")
        if len(values) != min(2, count):
            raise RuntimeAuditError(f"ROUTER_STATE_LAST_TWO_INVALID: {group}")
        if not all(math.isfinite(float(value)) for value in values):
            raise RuntimeAuditError(f"ROUTER_STATE_NONFINITE: {group}")
        total += count
    if total != processed:
        raise RuntimeAuditError(
            f"ROUTER_STATE_COUNT_MISMATCH: total={total} processed={processed}"
        )
    if processed > 0:
        if state.get("last_entry_dt") is None or state.get("last_exit_dt") is None:
            raise RuntimeAuditError("ROUTER_STATE_LAST_TIMESTAMPS_MISSING")
        if pd.Timestamp(state["last_exit_dt"]) < pd.Timestamp(state["last_entry_dt"]):
            raise RuntimeAuditError("ROUTER_STATE_TIMESTAMP_ORDER_INVALID")


def validate_frozen_sources(
    contract_path: Path,
    bootstrap_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not contract_path.is_file():
        raise RuntimeAuditError("STAGE328_FROZEN_CONTRACT_MISSING")
    if not bootstrap_path.is_file():
        raise RuntimeAuditError("STAGE328_FROZEN_BOOTSTRAP_MISSING")

    contract_sha = sha256_file(contract_path)
    bootstrap_sha = sha256_file(bootstrap_path)
    if contract_sha != EXPECTED_CONTRACT_SHA256:
        raise RuntimeAuditError(
            "STAGE328_FROZEN_CONTRACT_SHA_MISMATCH: "
            f"expected={EXPECTED_CONTRACT_SHA256} actual={contract_sha}"
        )
    if bootstrap_sha != EXPECTED_BOOTSTRAP_SHA256:
        raise RuntimeAuditError(
            "STAGE328_FROZEN_BOOTSTRAP_SHA_MISMATCH: "
            f"expected={EXPECTED_BOOTSTRAP_SHA256} actual={bootstrap_sha}"
        )

    contract = load_json(contract_path)
    bootstrap = load_json(bootstrap_path)
    if contract.get("status") != EXPECTED_CONTRACT_STATUS:
        raise RuntimeAuditError("STAGE328_CONTRACT_STATUS_UNEXPECTED")
    if bootstrap.get("status") != EXPECTED_BOOTSTRAP_STATUS:
        raise RuntimeAuditError("STAGE328_BOOTSTRAP_STATUS_UNEXPECTED")
    if contract.get("source_candidate") != EXPECTED_SOURCE:
        raise RuntimeAuditError("STAGE328_SOURCE_CANDIDATE_UNEXPECTED")
    if contract.get("selected_lane") != EXPECTED_LANE:
        raise RuntimeAuditError("STAGE328_LANE_UNEXPECTED")
    if contract.get("router_policy") != EXPECTED_POLICY:
        raise RuntimeAuditError("STAGE328_POLICY_UNEXPECTED")
    if contract.get("router_cost_view") != EXPECTED_COST_VIEW:
        raise RuntimeAuditError("STAGE328_COST_VIEW_UNEXPECTED")
    cutoff = pd.Timestamp(
        contract["frozen_cutoffs"]["prospective_decision_dt_strictly_after"]
    )
    if cutoff != EXPECTED_CUTOFF:
        raise RuntimeAuditError(
            f"STAGE319_CUTOFF_MISMATCH: expected={EXPECTED_CUTOFF} actual={cutoff}"
        )
    if bootstrap.get("contract_sha256") != contract_sha:
        raise RuntimeAuditError("BOOTSTRAP_CONTRACT_LINEAGE_MISMATCH")
    if pd.Timestamp(
        bootstrap.get("prospective_decision_dt_strictly_after")
    ) != EXPECTED_CUTOFF:
        raise RuntimeAuditError("BOOTSTRAP_CUTOFF_MISMATCH")

    initial_state = bootstrap.get("initial_state")
    if not isinstance(initial_state, dict):
        raise RuntimeAuditError("BOOTSTRAP_INITIAL_STATE_MISSING")
    validate_router_state(initial_state)
    internal_sha = sha256_state(initial_state)
    if internal_sha != EXPECTED_BOOTSTRAP_STATE_SHA256:
        raise RuntimeAuditError(
            "BOOTSTRAP_INTERNAL_STATE_SHA_MISMATCH: "
            f"expected={EXPECTED_BOOTSTRAP_STATE_SHA256} actual={internal_sha}"
        )
    if bootstrap.get("initial_state_sha256") != internal_sha:
        raise RuntimeAuditError("BOOTSTRAP_DECLARED_STATE_SHA_MISMATCH")
    if contract.get("initial_router_state_sha256") != internal_sha:
        raise RuntimeAuditError("CONTRACT_INITIAL_STATE_SHA_MISMATCH")
    if canonical_json(contract.get("initial_router_state", {})) != canonical_json(
        initial_state
    ):
        raise RuntimeAuditError("CONTRACT_BOOTSTRAP_INITIAL_STATE_MISMATCH")
    return contract, bootstrap, initial_state


def runtime_wrapper(
    state: dict[str, Any],
    contract_sha: str,
    bootstrap_sha: str,
    bootstrap_state_sha: str,
    journal_sha: str | None,
    applied_event_count: int,
    created_at_utc: str,
    *,
    recovered_from_journal: bool,
) -> dict[str, Any]:
    validate_router_state(state)
    return {
        "status": "GOLD_V3_329_PERSISTENT_ROUTER_RUNTIME_STATE_ACTIVE_AUDIT_ONLY",
        "mode": "AUDIT_ONLY_MUTABLE_RUNTIME_STATE",
        "runtime_schema_version": 1,
        "policy": EXPECTED_POLICY,
        "selected_lane": EXPECTED_LANE,
        "cost_view": EXPECTED_COST_VIEW,
        "frozen_lineage": {
            "contract_sha256": contract_sha,
            "bootstrap_sha256": bootstrap_sha,
            "bootstrap_internal_state_sha256": bootstrap_state_sha,
            "prospective_decision_dt_strictly_after": str(EXPECTED_CUTOFF),
        },
        "created_at_utc": created_at_utc,
        "last_written_at_utc": datetime.now(timezone.utc).isoformat(),
        "applied_event_count": int(applied_event_count),
        "journal_sha256": journal_sha,
        "recovered_from_journal_on_last_write": bool(recovered_from_journal),
        "state": state,
        "state_sha256": sha256_state(state),
        "safety": {
            "frozen_bootstrap_mutated": False,
            "resolved_only_updates": True,
            "pending_as_of_pnl_forbidden": True,
            "automatic_promotion": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }


def validate_runtime_wrapper(
    wrapper: dict[str, Any],
    contract_sha: str,
    bootstrap_sha: str,
    bootstrap_state_sha: str,
) -> dict[str, Any]:
    if wrapper.get("status") != (
        "GOLD_V3_329_PERSISTENT_ROUTER_RUNTIME_STATE_ACTIVE_AUDIT_ONLY"
    ):
        raise RuntimeAuditError("RUNTIME_STATE_STATUS_UNEXPECTED")
    if wrapper.get("runtime_schema_version") != 1:
        raise RuntimeAuditError("RUNTIME_STATE_SCHEMA_UNEXPECTED")
    if wrapper.get("policy") != EXPECTED_POLICY:
        raise RuntimeAuditError("RUNTIME_STATE_POLICY_UNEXPECTED")
    if wrapper.get("selected_lane") != EXPECTED_LANE:
        raise RuntimeAuditError("RUNTIME_STATE_LANE_UNEXPECTED")
    if wrapper.get("cost_view") != EXPECTED_COST_VIEW:
        raise RuntimeAuditError("RUNTIME_STATE_COST_VIEW_UNEXPECTED")
    lineage = wrapper.get("frozen_lineage", {})
    expected = {
        "contract_sha256": contract_sha,
        "bootstrap_sha256": bootstrap_sha,
        "bootstrap_internal_state_sha256": bootstrap_state_sha,
        "prospective_decision_dt_strictly_after": str(EXPECTED_CUTOFF),
    }
    if lineage != expected:
        raise RuntimeAuditError("RUNTIME_STATE_FROZEN_LINEAGE_MISMATCH")
    state = wrapper.get("state")
    if not isinstance(state, dict):
        raise RuntimeAuditError("RUNTIME_STATE_PAYLOAD_MISSING")
    validate_router_state(state)
    if wrapper.get("state_sha256") != sha256_state(state):
        raise RuntimeAuditError("RUNTIME_STATE_DECLARED_SHA_MISMATCH")
    if int(wrapper.get("applied_event_count", -1)) < 0:
        raise RuntimeAuditError("RUNTIME_STATE_APPLIED_EVENT_COUNT_INVALID")
    return state


def empty_journal() -> pd.DataFrame:
    return pd.DataFrame(columns=JOURNAL_COLUMNS)


def read_journal(path: Path) -> pd.DataFrame:
    if not path.exists():
        return empty_journal()
    frame = pd.read_csv(path, encoding="utf-8-sig")
    missing = sorted(set(JOURNAL_COLUMNS) - set(frame.columns))
    extra = sorted(set(frame.columns) - set(JOURNAL_COLUMNS))
    if missing or extra:
        raise RuntimeAuditError(
            f"JOURNAL_SCHEMA_MISMATCH: missing={missing} extra={extra}"
        )
    frame = frame[JOURNAL_COLUMNS].copy()
    if frame.empty:
        return frame
    for column in ("decision_dt", "entry_dt", "exit_dt"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    frame["router_selected"] = frame["router_selected"].map(
        lambda value: parse_bool_value(value, "router_selected")
    )
    for column in (
        "spread_adjusted_pnl",
        "spread_adjusted_r",
        "state_processed_candidates_after",
        "premium_history_count_before_entry",
        "balanced_without_premium_history_count_before_entry",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if frame["event_id"].duplicated().any():
        duplicated = frame.loc[frame["event_id"].duplicated(), "event_id"].tolist()
        raise RuntimeAuditError(f"JOURNAL_DUPLICATE_EVENT_ID: {duplicated}")
    if not frame["decision_dt"].is_monotonic_increasing:
        raise RuntimeAuditError("JOURNAL_DECISION_DT_NOT_MONOTONIC")
    if not frame["entry_dt"].is_monotonic_increasing:
        raise RuntimeAuditError("JOURNAL_ENTRY_DT_NOT_MONOTONIC")
    if not frame["exit_dt"].is_monotonic_increasing:
        raise RuntimeAuditError("JOURNAL_EXIT_DT_NOT_MONOTONIC")
    return frame


def router_decision(
    state: dict[str, Any],
    group: str,
) -> dict[str, Any]:
    if group not in GROUPS:
        raise RuntimeAuditError(f"ROUTER_GROUP_UNEXPECTED: {group}")
    other = (
        "BALANCED_WITHOUT_PREMIUM"
        if group == "PREMIUM_INVOLVED"
        else "PREMIUM_INVOLVED"
    )
    group_payload = state["groups"][group]
    other_payload = state["groups"][other]
    group_count = int(group_payload["resolved_count"])
    other_count = int(other_payload["resolved_count"])
    if group_count < 2 or other_count < 2:
        take = True
        reason = "WARMUP_TAKE_ALL"
        group_score = None
        other_score = None
    else:
        group_score = float(np.mean(group_payload["last_two_r"]))
        other_score = float(np.mean(other_payload["last_two_r"]))
        take = group_score >= other_score
        reason = "GROUP_SCORE_GE_OTHER" if take else "GROUP_SCORE_LT_OTHER"
    return {
        "router_selected": bool(take),
        "router_decision_reason": reason,
        "group_score_before_entry": group_score,
        "other_group_score_before_entry": other_score,
        "premium_history_count_before_entry": int(
            state["groups"]["PREMIUM_INVOLVED"]["resolved_count"]
        ),
        "balanced_without_premium_history_count_before_entry": int(
            state["groups"]["BALANCED_WITHOUT_PREMIUM"]["resolved_count"]
        ),
    }


def apply_resolution(
    state: dict[str, Any],
    *,
    group: str,
    entry_dt: Any,
    exit_dt: Any,
    spread_adjusted_r: Any,
) -> None:
    validate_router_state(state)
    entry = pd.Timestamp(entry_dt)
    exit_time = pd.Timestamp(exit_dt)
    if exit_time < entry:
        raise RuntimeAuditError("RESOLUTION_EXIT_BEFORE_ENTRY")
    if state["last_exit_dt"] is not None:
        previous_exit = pd.Timestamp(state["last_exit_dt"])
        if entry < previous_exit:
            raise RuntimeAuditError(
                f"RESOLVED_ACCEPTED_SOURCE_OVERLAP: entry={entry} prior_exit={previous_exit}"
            )
    value = float(spread_adjusted_r)
    if not math.isfinite(value):
        raise RuntimeAuditError("RESOLUTION_R_NONFINITE")
    payload = state["groups"][group]
    payload["resolved_count"] = int(payload["resolved_count"]) + 1
    payload["last_two_r"] = (list(payload["last_two_r"]) + [value])[-2:]
    state["processed_candidates"] = int(state["processed_candidates"]) + 1
    state["last_entry_dt"] = str(entry)
    state["last_exit_dt"] = str(exit_time)
    validate_router_state(state)


def compare_decision_to_journal(
    expected: dict[str, Any],
    row: pd.Series,
) -> None:
    if bool(expected["router_selected"]) != bool(row["router_selected"]):
        raise RuntimeAuditError("JOURNAL_ROUTER_SELECTION_PARITY_FAILED")
    if expected["router_decision_reason"] != str(row["router_decision_reason"]):
        raise RuntimeAuditError("JOURNAL_ROUTER_REASON_PARITY_FAILED")
    floats_equal(
        expected["group_score_before_entry"],
        row["group_score_before_entry"],
        "journal_group_score_before_entry",
    )
    floats_equal(
        expected["other_group_score_before_entry"],
        row["other_group_score_before_entry"],
        "journal_other_group_score_before_entry",
    )
    if int(expected["premium_history_count_before_entry"]) != int(
        row["premium_history_count_before_entry"]
    ):
        raise RuntimeAuditError("JOURNAL_PREMIUM_HISTORY_COUNT_PARITY_FAILED")
    if int(expected["balanced_without_premium_history_count_before_entry"]) != int(
        row["balanced_without_premium_history_count_before_entry"]
    ):
        raise RuntimeAuditError("JOURNAL_BALANCED_HISTORY_COUNT_PARITY_FAILED")


def replay_journal(
    initial_state: dict[str, Any],
    journal: pd.DataFrame,
) -> dict[str, Any]:
    state = json.loads(json.dumps(initial_state))
    validate_router_state(state)
    initial_processed = int(state["processed_candidates"])
    for index, row in journal.iterrows():
        if str(row["source_candidate"]) != EXPECTED_SOURCE:
            raise RuntimeAuditError("JOURNAL_SOURCE_CANDIDATE_UNEXPECTED")
        group = str(row["router_group"])
        expected_decision = router_decision(state, group)
        compare_decision_to_journal(expected_decision, row)
        apply_resolution(
            state,
            group=group,
            entry_dt=row["entry_dt"],
            exit_dt=row["exit_dt"],
            spread_adjusted_r=row["spread_adjusted_r"],
        )
        expected_count = initial_processed + index + 1
        if int(row["state_processed_candidates_after"]) != expected_count:
            raise RuntimeAuditError("JOURNAL_STATE_COUNT_AFTER_PARITY_FAILED")
        if str(pd.Timestamp(row["state_last_entry_dt_after"])) != str(
            pd.Timestamp(state["last_entry_dt"])
        ):
            raise RuntimeAuditError("JOURNAL_STATE_LAST_ENTRY_AFTER_PARITY_FAILED")
        if str(pd.Timestamp(row["state_last_exit_dt_after"])) != str(
            pd.Timestamp(state["last_exit_dt"])
        ):
            raise RuntimeAuditError("JOURNAL_STATE_LAST_EXIT_AFTER_PARITY_FAILED")
        if str(row["state_sha256_after"]) != sha256_state(state):
            raise RuntimeAuditError("JOURNAL_STATE_SHA_AFTER_PARITY_FAILED")
    return state


def create_or_reconcile_runtime(
    runtime_path: Path,
    journal_path: Path,
    initial_state: dict[str, Any],
    contract_sha: str,
    bootstrap_sha: str,
    bootstrap_state_sha: str,
) -> tuple[dict[str, Any], pd.DataFrame, bool, bool, str]:
    journal = read_journal(journal_path)
    if not runtime_path.exists():
        if not journal.empty:
            raise RuntimeAuditError(
                "RUNTIME_STATE_MISSING_WITH_NONEMPTY_JOURNAL_NO_BOOTSTRAP_RESET_ALLOWED"
            )
        created_at = datetime.now(timezone.utc).isoformat()
        state = json.loads(json.dumps(initial_state))
        wrapper = runtime_wrapper(
            state,
            contract_sha,
            bootstrap_sha,
            bootstrap_state_sha,
            None,
            0,
            created_at,
            recovered_from_journal=False,
        )
        atomic_write_json(runtime_path, wrapper)
        if not journal_path.exists():
            atomic_write_csv(journal_path, journal)
        wrapper["journal_sha256"] = sha256_file(journal_path)
        wrapper["last_written_at_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(runtime_path, wrapper)
        return state, journal, True, False, created_at

    wrapper = load_json(runtime_path)
    runtime_state = validate_runtime_wrapper(
        wrapper,
        contract_sha,
        bootstrap_sha,
        bootstrap_state_sha,
    )
    created_at = str(wrapper.get("created_at_utc"))
    declared_count = int(wrapper["applied_event_count"])
    if declared_count > len(journal):
        raise RuntimeAuditError(
            "RUNTIME_STATE_AHEAD_OF_JOURNAL_FAIL_CLOSED: "
            f"runtime={declared_count} journal={len(journal)}"
        )
    replayed = replay_journal(initial_state, journal)
    replayed_sha = sha256_state(replayed)
    runtime_sha = sha256_state(runtime_state)
    recovered = False
    actual_journal_sha = sha256_file(journal_path) if journal_path.exists() else None
    declared_journal_sha = wrapper.get("journal_sha256")
    if declared_count == len(journal):
        journal_hash_matches = declared_journal_sha == actual_journal_sha
        initial_empty_write_interrupted = (
            declared_count == 0
            and declared_journal_sha is None
            and journal.empty
        )
        if not journal_hash_matches and not initial_empty_write_interrupted:
            raise RuntimeAuditError(
                "RUNTIME_STATE_JOURNAL_HASH_MISMATCH_WITH_EQUAL_COUNTS_FAIL_CLOSED"
            )
        if runtime_sha != replayed_sha:
            raise RuntimeAuditError(
                "RUNTIME_STATE_JOURNAL_MISMATCH_WITH_EQUAL_COUNTS_FAIL_CLOSED"
            )
    else:
        recovered = True
        wrapper = runtime_wrapper(
            replayed,
            contract_sha,
            bootstrap_sha,
            bootstrap_state_sha,
            sha256_file(journal_path),
            len(journal),
            created_at,
            recovered_from_journal=True,
        )
        atomic_write_json(runtime_path, wrapper)
    return replayed, journal, False, recovered, created_at


def stable_event_id(decision_dt: pd.Timestamp) -> str:
    raw = f"{EXPECTED_SOURCE}|{pd.Timestamp(decision_dt).isoformat()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def stable_raw_track_event_id(track: str, decision_dt: pd.Timestamp) -> str:
    raw = (
        f"{EXPECTED_SOURCE}|{track}|{pd.Timestamp(decision_dt).isoformat()}"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def generate_raw_signals(
    frame: pd.DataFrame,
    pair: Any,
    frozen_cutoff: pd.Timestamp,
) -> list[dict[str, Any]]:
    track_lookup = {track.name: track for track in stage311.TRACK_SPECS}
    if any(name not in track_lookup for name in POOLED_TRACKS):
        missing = [name for name in POOLED_TRACKS if name not in track_lookup]
        raise RuntimeAuditError(f"FROZEN_POOLED_TRACK_MISSING: {missing}")
    raw: list[dict[str, Any]] = []
    for track_name in POOLED_TRACKS:
        track = track_lookup[track_name]
        if track.category != "MOCHIPOYO":
            raise RuntimeAuditError(
                f"FROZEN_POOLED_TRACK_CATEGORY_MISMATCH: {track_name}"
            )
        generated = stage311.generate_track_signals(frame, pair, track)
        for source in generated:
            decision_dt = pd.Timestamp(source["decision_dt"])
            if decision_dt <= frozen_cutoff:
                continue
            if source["direction"] != "SHORT":
                continue
            if float(source["atr_ratio_signal"]) < 1.0:
                continue
            if bool(source["round_number_near"]):
                continue
            row = dict(source)
            row.update(
                {
                    "source_candidate": EXPECTED_SOURCE,
                    "candidate_id": "GOLD_V3_STAGE329_MOCHI_UNION_SHORT",
                    "raw_track_event_id": stable_raw_track_event_id(
                        str(source["track"]), decision_dt
                    ),
                    "priority": 10,
                    "exit_profile": "RR1_5",
                }
            )
            raw.append(row)
    raw.sort(
        key=lambda row: (
            pd.Timestamp(row["decision_dt"]),
            str(row["track"]),
        )
    )
    return raw


def canonicalize_signals(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not raw:
        return []
    raw_frame = pd.DataFrame(raw)
    canonical: list[dict[str, Any]] = []
    for decision_dt, group in raw_frame.groupby("decision_dt", sort=True):
        for column in ("pair", "direction", "direction_num", "signal_index"):
            if group[column].nunique(dropna=False) != 1:
                raise RuntimeAuditError(f"POOLED_SIGNAL_PARITY_FAILED: {column}")
        for column in (
            "atr_entry_context",
            "last_swing_high",
            "last_swing_low",
            "atr_ratio_signal",
            "extension_atr_signal",
            "compression_ratio_signal",
            "range_atr_signal",
        ):
            stage319.same_optional_float(group[column], column)

        ordered = group.sort_values(
            ["quality_score", "track"],
            ascending=[False, True],
            kind="mergesort",
        )
        signal = ordered.iloc[0].to_dict()
        tracks = sorted(set(group["track"].astype(str)))
        atr_ratio = float(signal["atr_ratio_signal"])
        range_atr = float(signal["range_atr_signal"])
        compression = optional_float(signal.get("compression_ratio_signal"))
        balanced = bool(
            len(tracks) >= 2
            or (
                1.10 <= atr_ratio <= 1.45
                and 0.70 <= range_atr <= 1.05
            )
        )
        premium = bool(compression is not None and compression >= 0.95)
        router_group = (
            "PREMIUM_INVOLVED"
            if premium
            else "BALANCED_WITHOUT_PREMIUM"
            if balanced
            else None
        )
        signal.update(
            {
                "source_candidate": EXPECTED_SOURCE,
                "candidate_id": "GOLD_V3_STAGE329_MOCHI_UNION_SHORT",
                "event_id": stable_event_id(pd.Timestamp(decision_dt)),
                "priority": 10,
                "setup": "MOCHI_UNION",
                "track": "MOCHI_UNION",
                "category": "MOCHIPOYO_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW",
                "decision_dt": pd.Timestamp(decision_dt),
                "quality_score": float(group["quality_score"].max()),
                "pooled_tracks": "+".join(tracks),
                "pooled_track_count": int(len(tracks)),
                "balanced_eligible": balanced,
                "premium_eligible": premium,
                "router_group": router_group,
                "exit_profile": "RR1_5",
                "router_selected": None,
                "router_decision_reason": None,
                "group_score_before_entry": None,
                "other_group_score_before_entry": None,
                "premium_history_count_before_entry": None,
                "balanced_without_premium_history_count_before_entry": None,
            }
        )
        canonical.append(signal)
    canonical.sort(key=lambda row: pd.Timestamp(row["decision_dt"]))
    if len({row["event_id"] for row in canonical}) != len(canonical):
        raise RuntimeAuditError("CANONICAL_EVENT_ID_COLLISION")
    return canonical


def prepare_portfolio(
    canonical: list[dict[str, Any]],
    frame: pd.DataFrame,
    m1: pd.DataFrame,
    pair: Any,
    point_size: float,
) -> list[dict[str, Any]]:
    outside: list[dict[str, Any]] = []
    lane: list[dict[str, Any]] = []
    for signal in canonical:
        if signal["router_group"] is None:
            row = dict(signal)
            row.update(
                {
                    "trade_state": "OUTSIDE_FIXED_LANE",
                    "state_reason": "Canonical source signal is neither Balanced nor Premium.",
                    "portfolio_status": "OUTSIDE_FIXED_LANE",
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
            outside.append(row)
        else:
            lane.append(stage314.prepare_trade(signal, frame, m1, pair, point_size))
    portfolio = stage314.apply_portfolio_policy(lane)
    combined = outside + portfolio
    combined.sort(
        key=lambda row: (
            pd.Timestamp(row["decision_dt"]),
            str(row["event_id"]),
        )
    )
    return combined


def journal_decision_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "router_selected": bool(row["router_selected"]),
        "router_decision_reason": str(row["router_decision_reason"]),
        "group_score_before_entry": optional_float(
            row["group_score_before_entry"]
        ),
        "other_group_score_before_entry": optional_float(
            row["other_group_score_before_entry"]
        ),
        "premium_history_count_before_entry": int(
            row["premium_history_count_before_entry"]
        ),
        "balanced_without_premium_history_count_before_entry": int(
            row["balanced_without_premium_history_count_before_entry"]
        ),
    }


def verify_journal_candidate(row: pd.Series, candidate: dict[str, Any]) -> None:
    if str(row["source_candidate"]) != EXPECTED_SOURCE:
        raise RuntimeAuditError("JOURNAL_SOURCE_IDENTITY_MISMATCH")
    for field in ("decision_dt", "entry_dt", "exit_dt"):
        if pd.Timestamp(row[field]) != pd.Timestamp(candidate[field]):
            raise RuntimeAuditError(f"JOURNAL_CANDIDATE_TIMESTAMP_MISMATCH: {field}")
    if str(row["router_group"]) != str(candidate["router_group"]):
        raise RuntimeAuditError("JOURNAL_CANDIDATE_GROUP_MISMATCH")
    floats_equal(
        row["spread_adjusted_r"],
        candidate["spread_adjusted_r"],
        "journal_candidate_spread_adjusted_r",
    )
    floats_equal(
        row["spread_adjusted_pnl"],
        candidate["spread_adjusted_pnl"],
        "journal_candidate_spread_adjusted_pnl",
    )
    if str(row["exit_reason"]) != str(candidate["exit_reason"]):
        raise RuntimeAuditError("JOURNAL_CANDIDATE_EXIT_REASON_MISMATCH")


def enrich_router_and_apply_new_resolutions(
    portfolio_rows: list[dict[str, Any]],
    state: dict[str, Any],
    journal: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, Any], pd.DataFrame, int, int]:
    accepted = [
        row for row in portfolio_rows if row.get("portfolio_status") == "ACCEPTED"
    ]
    accepted.sort(
        key=lambda row: (
            pd.Timestamp(row["entry_dt"]),
            pd.Timestamp(row["decision_dt"]),
            str(row["event_id"]),
        )
    )
    journal_map = {
        str(row.event_id): row
        for row in journal.itertuples(index=False)
    }
    accepted_resolved_map = {
        str(row["event_id"]): row
        for row in accepted
        if row.get("trade_state") == "RESOLVED"
    }
    missing_from_current = sorted(
        set(journal_map) - set(accepted_resolved_map)
    )
    if missing_from_current:
        raise RuntimeAuditError(
            "APPLIED_JOURNAL_EVENT_NOT_CURRENTLY_ACCEPTED_RESOLVED: "
            + ",".join(missing_from_current)
        )

    last_journal_decision = (
        pd.Timestamp(journal["decision_dt"].iloc[-1]) if not journal.empty else None
    )
    last_journal_entry = (
        pd.Timestamp(journal["entry_dt"].iloc[-1]) if not journal.empty else None
    )
    new_journal_rows: list[dict[str, Any]] = []
    duplicate_ignored = 0
    pending_seen = False

    for item in accepted:
        event_id = str(item["event_id"])
        if event_id in journal_map:
            journal_row = pd.Series(journal_map[event_id]._asdict())
            verify_journal_candidate(journal_row, item)
            item.update(journal_decision_payload(journal_row))
            duplicate_ignored += 1
            continue

        decision_dt = pd.Timestamp(item["decision_dt"])
        entry_dt = pd.Timestamp(item["entry_dt"])
        if last_journal_decision is not None and decision_dt <= last_journal_decision:
            raise RuntimeAuditError(
                "NEW_ACCEPTED_EVENT_INSERTED_BEFORE_OR_AT_APPLIED_DECISION_DT"
            )
        if last_journal_entry is not None and entry_dt <= last_journal_entry:
            raise RuntimeAuditError(
                "NEW_ACCEPTED_EVENT_INSERTED_BEFORE_OR_AT_APPLIED_ENTRY_DT"
            )
        if pending_seen:
            raise RuntimeAuditError(
                "ACCEPTED_EVENT_EXISTS_AFTER_UNRESOLVED_ACCEPTED_SOURCE_CANDIDATE"
            )

        decision = router_decision(state, str(item["router_group"]))
        item.update(decision)
        if item.get("trade_state") != "RESOLVED":
            if item.get("spread_adjusted_pnl") is not None:
                raise RuntimeAuditError("PENDING_SOURCE_HAS_ASOF_PNL")
            if item.get("spread_adjusted_r") is not None:
                raise RuntimeAuditError("PENDING_SOURCE_HAS_ASOF_R")
            pending_seen = True
            continue

        apply_resolution(
            state,
            group=str(item["router_group"]),
            entry_dt=item["entry_dt"],
            exit_dt=item["exit_dt"],
            spread_adjusted_r=item["spread_adjusted_r"],
        )
        journal_row = {
            "event_id": event_id,
            "source_candidate": EXPECTED_SOURCE,
            "decision_dt": str(pd.Timestamp(item["decision_dt"])),
            "entry_dt": str(pd.Timestamp(item["entry_dt"])),
            "exit_dt": str(pd.Timestamp(item["exit_dt"])),
            "router_group": str(item["router_group"]),
            "router_selected": bool(item["router_selected"]),
            "router_decision_reason": str(item["router_decision_reason"]),
            "group_score_before_entry": item["group_score_before_entry"],
            "other_group_score_before_entry": item["other_group_score_before_entry"],
            "premium_history_count_before_entry": int(
                item["premium_history_count_before_entry"]
            ),
            "balanced_without_premium_history_count_before_entry": int(
                item["balanced_without_premium_history_count_before_entry"]
            ),
            "spread_adjusted_pnl": float(item["spread_adjusted_pnl"]),
            "spread_adjusted_r": float(item["spread_adjusted_r"]),
            "exit_reason": str(item["exit_reason"]),
            "state_processed_candidates_after": int(state["processed_candidates"]),
            "state_last_entry_dt_after": str(pd.Timestamp(state["last_entry_dt"])),
            "state_last_exit_dt_after": str(pd.Timestamp(state["last_exit_dt"])),
            "state_sha256_after": sha256_state(state),
        }
        new_journal_rows.append(journal_row)
        last_journal_decision = decision_dt
        last_journal_entry = entry_dt

    if new_journal_rows:
        appended = pd.DataFrame(new_journal_rows, columns=JOURNAL_COLUMNS)
        journal = (
            appended.reset_index(drop=True)
            if journal.empty
            else pd.concat([journal, appended], ignore_index=True)
        )
    return portfolio_rows, state, journal, len(new_journal_rows), duplicate_ignored


def frame_for_output(
    rows: list[dict[str, Any]],
    columns: list[str] = SIGNAL_COLUMNS,
) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
    frame = frame[columns].copy()
    for column in ("decision_dt", "entry_dt", "exit_dt", "max_exit_dt"):
        if column in frame.columns:
            frame[column] = frame[column].map(stage314.iso)
    return frame


def resolved_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = frame_for_output(rows)
    if not frame.empty:
        for column in ("entry_dt", "exit_dt"):
            frame[column] = pd.to_datetime(frame[column], errors="raise")
        frame["direction_num"] = pd.to_numeric(
            frame["direction_num"], errors="raise"
        )
    return stage314.summarize_resolved(frame)


def subgroup_scores(state: dict[str, Any]) -> dict[str, Any]:
    scores: dict[str, Any] = {}
    for group in GROUPS:
        payload = state["groups"][group]
        values = list(payload["last_two_r"])
        scores[group] = {
            "resolved_count": int(payload["resolved_count"]),
            "last_two_r": values,
            "mean_r_n2": float(np.mean(values)) if len(values) == 2 else None,
        }
    premium = scores["PREMIUM_INVOLVED"]["mean_r_n2"]
    balanced = scores["BALANCED_WITHOUT_PREMIUM"]["mean_r_n2"]
    return {
        "groups": scores,
        "warmup_complete": all(
            int(state["groups"][group]["resolved_count"]) >= 2
            for group in GROUPS
        ),
        "premium_minus_balanced": (
            float(premium - balanced)
            if premium is not None and balanced is not None
            else None
        ),
    }


def future_review_gate(
    source_summary: dict[str, Any],
    selected_summary: dict[str, Any],
    requirements: dict[str, Any],
    integrity_ok: bool,
) -> dict[str, Any]:
    checks = {
        "minimum_resolved_source_candidates": (
            int(source_summary["trades"])
            >= int(requirements["minimum_resolved_source_candidates"])
        ),
        "minimum_resolved_selected_trades": (
            int(selected_summary["trades"])
            >= int(requirements["minimum_resolved_selected_trades"])
        ),
        "minimum_selected_win_rate": (
            float(selected_summary["win_rate"])
            >= float(requirements["minimum_selected_win_rate"])
        ),
        "minimum_selected_profit_factor": (
            stage314.pf_number(selected_summary)
            >= float(requirements["minimum_selected_profit_factor"])
        ),
        "minimum_selected_total_r": (
            float(selected_summary["spread_adjusted_total_r"])
            > float(requirements["minimum_selected_total_r_exclusive"])
        ),
        "maximum_selected_drawdown_r": (
            float(selected_summary["spread_adjusted_max_drawdown_r"])
            <= float(requirements["maximum_selected_drawdown_r"])
        ),
        "maximum_largest_winner_share": (
            float(selected_summary["largest_win_share_of_positive_pnl"])
            <= float(requirements["maximum_largest_winner_share"])
        ),
        "state_integrity_required": bool(integrity_ok),
    }
    return {
        "review_eligible": bool(all(checks.values())),
        "checks": checks,
        "requirements": requirements,
        "automatic_promotion": False,
    }


def state_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        key = str(row.get("trade_state"))
        result[key] = result.get(key, 0) + 1
    return result


def portfolio_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        key = str(row.get("portfolio_status"))
        result[key] = result.get(key, 0) + 1
    return result


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    contract_path = Path(args.contract).expanduser().resolve()
    bootstrap_path = Path(args.bootstrap_state).expanduser().resolve()
    runtime_path = Path(args.runtime_state).expanduser().resolve()
    journal_path = Path(args.journal_csv).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_csvs = {
        "raw": Path(args.raw_signals_csv).expanduser().resolve(),
        "canonical": Path(args.canonical_signals_csv).expanduser().resolve(),
        "source_pending": Path(args.source_pending_csv).expanduser().resolve(),
        "source_resolved": Path(args.source_resolved_csv).expanduser().resolve(),
        "selected": Path(args.selected_signals_csv).expanduser().resolve(),
        "selected_pending": Path(args.selected_pending_csv).expanduser().resolve(),
        "selected_resolved": Path(args.selected_resolved_csv).expanduser().resolve(),
        "rejected_overlap": Path(args.rejected_overlap_csv).expanduser().resolve(),
        "health": Path(args.health_csv).expanduser().resolve(),
    }
    point_size = float(args.point_size)

    contract, bootstrap, initial_state = validate_frozen_sources(
        contract_path,
        bootstrap_path,
    )
    contract_sha = sha256_file(contract_path)
    bootstrap_sha = sha256_file(bootstrap_path)
    bootstrap_state_sha = sha256_state(initial_state)

    state, journal, runtime_created, recovered, created_at = (
        create_or_reconcile_runtime(
            runtime_path,
            journal_path,
            initial_state,
            contract_sha,
            bootstrap_sha,
            bootstrap_state_sha,
        )
    )
    state_before_new = json.loads(json.dumps(state))
    applied_before = len(journal)

    m1, m5, h4, frame, pair = stage314.read_closed_context(
        candle_dir,
        point_size,
    )
    if pd.Timestamp(m5.close_time.iloc[-1]) < EXPECTED_CUTOFF:
        raise RuntimeAuditError(
            "CURRENT_M5_HISTORY_ENDS_BEFORE_FROZEN_CUTOFF"
        )

    raw = generate_raw_signals(frame, pair, EXPECTED_CUTOFF)
    canonical = canonicalize_signals(raw)
    portfolio_rows = prepare_portfolio(
        canonical,
        frame,
        m1,
        pair,
        point_size,
    )
    portfolio_rows, state, journal, applied_this_run, duplicate_ignored = (
        enrich_router_and_apply_new_resolutions(
            portfolio_rows,
            state,
            journal,
        )
    )

    expected_processed = int(initial_state["processed_candidates"]) + len(journal)
    if int(state["processed_candidates"]) != expected_processed:
        raise RuntimeAuditError(
            "RUNTIME_STATE_PROCESSED_COUNT_NOT_BOOTSTRAP_PLUS_JOURNAL"
        )

    journal_changed = len(journal) != applied_before
    if journal_changed:
        atomic_write_csv(journal_path, journal[JOURNAL_COLUMNS])
    elif not journal_path.exists():
        atomic_write_csv(journal_path, journal[JOURNAL_COLUMNS])
    journal_sha = sha256_file(journal_path)

    wrapper = runtime_wrapper(
        state,
        contract_sha,
        bootstrap_sha,
        bootstrap_state_sha,
        journal_sha,
        len(journal),
        created_at,
        recovered_from_journal=recovered,
    )
    atomic_write_json(runtime_path, wrapper)

    accepted = [
        row for row in portfolio_rows if row.get("portfolio_status") == "ACCEPTED"
    ]
    accepted_resolved = [
        row for row in accepted if row.get("trade_state") == "RESOLVED"
    ]
    accepted_pending = [
        row for row in accepted if row.get("trade_state") != "RESOLVED"
    ]
    rejected_overlap = [
        row
        for row in portfolio_rows
        if row.get("portfolio_status") == "REJECTED_OVERLAP"
    ]
    selected = [row for row in accepted if bool(row.get("router_selected"))]
    selected_resolved = [
        row for row in selected if row.get("trade_state") == "RESOLVED"
    ]
    selected_pending = [
        row for row in selected if row.get("trade_state") != "RESOLVED"
    ]

    raw_frame = frame_for_output(raw)
    canonical_frame = frame_for_output(portfolio_rows)
    source_pending_frame = frame_for_output(accepted_pending)
    source_resolved_frame = frame_for_output(accepted_resolved)
    selected_frame = frame_for_output(selected)
    selected_pending_frame = frame_for_output(selected_pending)
    selected_resolved_frame = frame_for_output(selected_resolved)
    rejected_overlap_frame = frame_for_output(rejected_overlap)

    source_summary = resolved_summary(accepted_resolved)
    selected_summary = resolved_summary(selected_resolved)
    requirements = contract["future_review_gate"]
    journal_replayed_state = replay_journal(initial_state, journal)
    journal_replayed_state_sha = sha256_state(journal_replayed_state)
    integrity_ok = bool(
        sha256_file(contract_path) == EXPECTED_CONTRACT_SHA256
        and sha256_file(bootstrap_path) == EXPECTED_BOOTSTRAP_SHA256
        and sha256_state(state) == wrapper["state_sha256"]
        and journal_replayed_state_sha == sha256_state(state)
        and int(state["processed_candidates"]) == expected_processed
    )
    gate = future_review_gate(
        source_summary,
        selected_summary,
        requirements,
        integrity_ok,
    )

    lane_canonical_count = sum(
        row.get("router_group") in GROUPS for row in canonical
    )
    router_filtered = sum(
        row.get("portfolio_status") == "ACCEPTED"
        and row.get("router_selected") is False
        for row in portfolio_rows
    )
    invalid_not_tradable = sum(
        row.get("portfolio_status") == "NOT_TRADABLE_YET"
        for row in portfolio_rows
    )
    risk_rejected = sum(
        row.get("trade_state") == "RISK_REJECTED"
        for row in portfolio_rows
    )
    invalid_alignment_or_gap = sum(
        str(row.get("trade_state", "")).startswith("INVALID_")
        for row in portfolio_rows
    )

    if gate["review_eligible"]:
        decision = "HUMAN_AUDIT_ELIGIBLE_NO_AUTOMATIC_PROMOTION"
    elif lane_canonical_count == 0:
        decision = "WAIT_FOR_FIRST_POST_FREEZE_SOURCE_CANDIDATE"
    else:
        decision = "COLLECT_PROSPECTIVE_RESOLVED_SOURCE_AND_SELECTED_TRADES"

    health_row = {
        "status": EXPECTED_STATUS,
        "decision": decision,
        "integrity_ok": integrity_ok,
        "runtime_created_this_run": runtime_created,
        "recovered_from_journal_this_run": recovered,
        "raw_pooled_signal_count": len(raw),
        "canonical_signal_count_all": len(canonical),
        "canonical_deduplicated_lane_count": lane_canonical_count,
        "source_portfolio_accepted_count": len(accepted),
        "rejected_overlap_count": len(rejected_overlap),
        "invalid_risk_not_tradable_count": invalid_not_tradable,
        "risk_rejected_count": risk_rejected,
        "invalid_alignment_or_gap_count": invalid_alignment_or_gap,
        "router_selected_count": len(selected),
        "router_filtered_count": router_filtered,
        "source_pending_count": len(accepted_pending),
        "source_resolved_count": len(accepted_resolved),
        "selected_pending_count": len(selected_pending),
        "selected_resolved_count": len(selected_resolved),
        "state_updates_applied_this_run": applied_this_run,
        "duplicate_events_ignored": duplicate_ignored,
        "runtime_processed_candidates": int(state["processed_candidates"]),
        "journal_event_count": len(journal),
        "contract_sha256": contract_sha,
        "bootstrap_sha256": bootstrap_sha,
        "runtime_state_sha256": sha256_state(state),
        "journal_sha256": journal_sha,
    }
    health_frame = pd.DataFrame([health_row])

    frames = {
        "raw": raw_frame,
        "canonical": canonical_frame,
        "source_pending": source_pending_frame,
        "source_resolved": source_resolved_frame,
        "selected": selected_frame,
        "selected_pending": selected_pending_frame,
        "selected_resolved": selected_resolved_frame,
        "rejected_overlap": rejected_overlap_frame,
        "health": health_frame,
    }
    for name, path in output_csvs.items():
        atomic_write_csv(path, frames[name])

    report = {
        "status": EXPECTED_STATUS,
        "mode": "AUDIT_ONLY_FUTURE_ONLY_PERSISTENT_ROUTER_SHADOW_RUNTIME",
        "decision": decision,
        "fixed_contract": {
            "source_candidate": EXPECTED_SOURCE,
            "policy": EXPECTED_POLICY,
            "lane": EXPECTED_LANE,
            "premium_subgroup_precedence": True,
            "cost_view": EXPECTED_COST_VIEW,
            "prospective_decision_dt_strictly_after": str(EXPECTED_CUTOFF),
            "numeric_tolerance": TOL,
            "one_position_before_router": True,
            "same_m1_tp_sl_priority": "SL",
            "maximum_hold_minutes": 720,
        },
        "frozen_lineage": {
            "contract_path": str(contract_path),
            "contract_sha256": contract_sha,
            "contract_expected_sha256": EXPECTED_CONTRACT_SHA256,
            "bootstrap_path": str(bootstrap_path),
            "bootstrap_sha256": bootstrap_sha,
            "bootstrap_expected_sha256": EXPECTED_BOOTSTRAP_SHA256,
            "bootstrap_internal_state_sha256": bootstrap_state_sha,
            "bootstrap_internal_state_expected_sha256": (
                EXPECTED_BOOTSTRAP_STATE_SHA256
            ),
            "frozen_files_written_this_run": False,
        },
        "runtime": {
            "runtime_state_path": str(runtime_path),
            "runtime_state_sha256": sha256_file(runtime_path),
            "runtime_created_this_run": runtime_created,
            "bootstrap_recopied_this_run": runtime_created,
            "recovered_from_journal_this_run": recovered,
            "journal_path": str(journal_path),
            "journal_sha256": journal_sha,
            "journal_event_count": len(journal),
            "state_updates_applied_this_run": applied_this_run,
            "duplicate_events_ignored": duplicate_ignored,
            "state_before_new_events_sha256": sha256_state(state_before_new),
            "state_after_new_events_sha256": sha256_state(state),
            "state": state,
            "scores": subgroup_scores(state),
        },
        "current_closed_data": {
            "m1_latest_open_time": stage314.iso(m1.time.iloc[-1]),
            "m1_latest_close_time": stage314.iso(m1.close_time.iloc[-1]),
            "m5_latest_open_time": stage314.iso(m5.time.iloc[-1]),
            "m5_latest_close_time": stage314.iso(m5.close_time.iloc[-1]),
            "h4_latest_open_time": stage314.iso(h4.time.iloc[-1]),
            "h4_latest_close_time": stage314.iso(h4.close_time.iloc[-1]),
            "latest_rows_closed_by_csv_contract": True,
            "time_basis": "MT5 server time",
        },
        "separate_counts": {
            "raw_pooled_signal_count": len(raw),
            "canonical_signal_count_all": len(canonical),
            "canonical_deduplicated_lane_count": lane_canonical_count,
            "outside_fixed_lane_count": len(canonical) - lane_canonical_count,
            "source_portfolio_accepted_count": len(accepted),
            "rejected_overlap_count": len(rejected_overlap),
            "not_tradable_count": invalid_not_tradable,
            "risk_rejected_count": risk_rejected,
            "invalid_alignment_or_gap_count": invalid_alignment_or_gap,
            "router_selected_count": len(selected),
            "router_filtered_count": router_filtered,
            "source_pending_count": len(accepted_pending),
            "source_resolved_count": len(accepted_resolved),
            "selected_pending_count": len(selected_pending),
            "selected_resolved_count": len(selected_resolved),
            "trade_state_counts": state_counts(portfolio_rows),
            "portfolio_status_counts": portfolio_counts(portfolio_rows),
        },
        "resolved_only_metrics": {
            "source_accepted": source_summary,
            "router_selected": selected_summary,
        },
        "future_review_gate": gate,
        "integrity": {
            "pass": integrity_ok,
            "runtime_processed_equals_bootstrap_plus_journal": (
                int(state["processed_candidates"]) == expected_processed
            ),
            "contract_hash_valid": contract_sha == EXPECTED_CONTRACT_SHA256,
            "bootstrap_hash_valid": bootstrap_sha == EXPECTED_BOOTSTRAP_SHA256,
            "bootstrap_internal_state_hash_valid": (
                bootstrap_state_sha == EXPECTED_BOOTSTRAP_STATE_SHA256
            ),
            "pending_has_no_as_of_pnl_or_r": all(
                row.get("spread_adjusted_pnl") is None
                and row.get("spread_adjusted_r") is None
                for row in accepted_pending
            ),
            "journal_replay_state_sha256": journal_replayed_state_sha,
            "journal_replay_equals_runtime_state": (
                journal_replayed_state_sha == sha256_state(state)
            ),
            "runtime_state_sha256": sha256_state(state),
            "parity_tolerance": TOL,
        },
        "outputs": {
            "result_json": str(output_path),
            "runtime_state_json": str(runtime_path),
            "runtime_state_sha256": sha256_file(runtime_path),
            "journal_csv": str(journal_path),
            "journal_sha256": journal_sha,
            **{
                f"{name}_csv": str(path)
                for name, path in output_csvs.items()
            },
            **{
                f"{name}_sha256": sha256_file(path)
                for name, path in output_csvs.items()
            },
        },
        "promotion": {
            "performed": False,
            "automatic_promotion": False,
            "stage292_candidate_pool_changed": False,
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage328_contract_and_bootstrap": "UNCHANGED_FROZEN",
            "stage280_exact_recovery": "BLOCKED_UNCHANGED",
            "stage281_exact_model": "UNCHANGED",
        },
        "safety_flags": {
            "gold_v3_audit_only": True,
            "stage329_live_ready": False,
            "stage329_final_signal_emission_enabled": False,
            "closed_candles_only": True,
            "mt5_server_time": True,
            "future_entry_or_router_leakage": False,
            "resolved_only_state_updates": True,
            "router_filtered_accepted_updates_after_resolution": True,
            "rejected_overlap_updates_state": False,
            "risk_invalid_not_tradable_updates_state": False,
            "pending_as_of_pnl_forbidden": True,
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    atomic_write_json(output_path, report)
    print(json.dumps(json_safe(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
