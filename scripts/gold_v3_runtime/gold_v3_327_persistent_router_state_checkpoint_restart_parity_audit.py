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

EXPECTED_326A_STATUS = "GOLD_V3_326A_ROUTER_DISAGREEMENT_COUNTER_CORRECTION_COMPLETE"
EXPECTED_326A_DECISION = "STAGE326_CORE_DECISION_CONFIRMED_REPORTING_COUNTER_CORRECTED"
EXPECTED_326_STATUS = "GOLD_V3_326_ROUTER_STATE_AND_LATENCY_ROBUSTNESS_AUDIT_COMPLETE"
EXPECTED_326_DECISION = "ROUTER_OPERATIONALLY_ROBUST_BUT_REQUIRES_PERSISTENT_STATE"
EXPECTED_POLICY = "RELATIVE_TRAILING_MEAN_R_N2"
EXPECTED_LANE = "BALANCED_OR_PREMIUM"
DISPLAY_ONLY_YEAR = 2026
TOL = 1e-12
STATE_SCHEMA_VERSION = 1
GROUPS = ("PREMIUM_INVOLVED", "BALANCED_WITHOUT_PREMIUM")
COST_VIEWS = {
    "1p0x": ("stress_r_1p0x", "stress_pnl_1p0x"),
    "1p5x": ("stress_r_1p5x", "stress_pnl_1p5x"),
}
REPEATED_INTERVALS = (1, 2, 3, 5, 8)
BOUNDARY_MODES = ("year", "halfyear", "quarter")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage326a-json", required=True)
    parser.add_argument("--stage326-json", required=True)
    parser.add_argument("--stage324-timeline", required=True)
    parser.add_argument("--stage325-selected", required=True)
    parser.add_argument("--stage325-trace", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--checkpoint-csv", required=True)
    parser.add_argument("--snapshot-csv", required=True)
    parser.add_argument("--terminal-state-json", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def parse_bool(series: pd.Series, name: str) -> pd.Series:
    if series.dtype == bool:
        return series
    parsed = series.astype(str).str.lower().map({"true": True, "false": False})
    if parsed.isna().any():
        raise ValueError(f"BOOLEAN_PARSE_FAILED: {name}")
    return parsed.astype(bool)


def summarize(frame: pd.DataFrame) -> dict[str, Any]:
    return stage308.summarize(frame.to_dict(orient="records"))


def assign_group(row: pd.Series) -> str:
    if bool(row.premium):
        return "PREMIUM_INVOLVED"
    if bool(row.balanced):
        return "BALANCED_WITHOUT_PREMIUM"
    raise ValueError("SOURCE_TRADE_HAS_NO_ROUTER_GROUP")


def new_state(cost_view: str) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "policy": EXPECTED_POLICY,
        "selected_lane": EXPECTED_LANE,
        "cost_view": cost_view,
        "processed_candidates": 0,
        "last_entry_dt": None,
        "last_exit_dt": None,
        "groups": {
            group: {"resolved_count": 0, "last_two_r": []}
            for group in GROUPS
        },
    }


def validate_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise ValueError("STATE_SCHEMA_VERSION_MISMATCH")
    if state.get("policy") != EXPECTED_POLICY:
        raise ValueError("STATE_POLICY_MISMATCH")
    if state.get("selected_lane") != EXPECTED_LANE:
        raise ValueError("STATE_LANE_MISMATCH")
    if state.get("cost_view") not in COST_VIEWS:
        raise ValueError("STATE_COST_VIEW_MISMATCH")
    if sorted(state.get("groups", {}).keys()) != sorted(GROUPS):
        raise ValueError("STATE_GROUP_SET_MISMATCH")
    processed = int(state.get("processed_candidates", -1))
    if processed < 0:
        raise ValueError("STATE_PROCESSED_COUNT_INVALID")
    total_resolved = 0
    for group in GROUPS:
        payload = state["groups"][group]
        resolved_count = int(payload.get("resolved_count", -1))
        values = payload.get("last_two_r")
        if resolved_count < 0 or not isinstance(values, list) or len(values) > 2:
            raise ValueError(f"STATE_GROUP_PAYLOAD_INVALID: {group}")
        if len(values) != min(2, resolved_count):
            raise ValueError(f"STATE_LAST_TWO_LENGTH_INVALID: {group}")
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError(f"STATE_NONFINITE_VALUE: {group}")
        total_resolved += resolved_count
    if total_resolved != processed:
        raise ValueError(
            f"STATE_RESOLVED_COUNT_MISMATCH: total={total_resolved} processed={processed}"
        )


def canonical_state_json(state: dict[str, Any]) -> str:
    validate_state(state)
    return json.dumps(
        json_safe(state),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def restore_state(payload: str) -> dict[str, Any]:
    state = json.loads(payload)
    validate_state(state)
    return state


def state_snapshot_row(
    schedule_name: str,
    cost_view: str,
    restart_index: int,
    state: dict[str, Any],
) -> dict[str, Any]:
    payload = canonical_state_json(state)
    return {
        "schedule_name": schedule_name,
        "cost_view": cost_view,
        "restart_index": restart_index,
        "processed_candidates": state["processed_candidates"],
        "last_entry_dt": state["last_entry_dt"],
        "last_exit_dt": state["last_exit_dt"],
        "premium_resolved_count": state["groups"]["PREMIUM_INVOLVED"]["resolved_count"],
        "premium_last_two_r_json": json.dumps(
            state["groups"]["PREMIUM_INVOLVED"]["last_two_r"],
            separators=(",", ":"),
        ),
        "balanced_resolved_count": state["groups"]["BALANCED_WITHOUT_PREMIUM"]["resolved_count"],
        "balanced_last_two_r_json": json.dumps(
            state["groups"]["BALANCED_WITHOUT_PREMIUM"]["last_two_r"],
            separators=(",", ":"),
        ),
        "state_json": payload,
        "state_sha256": sha256_text(payload),
    }


def process_candidate(
    state: dict[str, Any],
    row: pd.Series,
    r_column: str,
    pnl_column: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    validate_state(state)
    entry_dt = pd.Timestamp(row.entry_dt)
    exit_dt = pd.Timestamp(row.exit_dt)
    if state["last_exit_dt"] is not None:
        if entry_dt < pd.Timestamp(state["last_exit_dt"]):
            raise ValueError("STATE_ASOF_OVERLAP")

    group = str(row.router_group)
    other = (
        "BALANCED_WITHOUT_PREMIUM"
        if group == "PREMIUM_INVOLVED"
        else "PREMIUM_INVOLVED"
    )
    group_payload = state["groups"][group]
    other_payload = state["groups"][other]
    group_count = int(group_payload["resolved_count"])
    other_count = int(other_payload["resolved_count"])
    group_score: float | None = None
    other_score: float | None = None

    if group_count < 2 or other_count < 2:
        take = True
        reason = "WARMUP_TAKE_ALL"
    else:
        group_score = float(np.mean(group_payload["last_two_r"]))
        other_score = float(np.mean(other_payload["last_two_r"]))
        take = group_score >= other_score
        reason = "GROUP_SCORE_GE_OTHER" if take else "GROUP_SCORE_LT_OTHER"

    decision = {
        "entry_dt": entry_dt,
        "exit_dt": exit_dt,
        "router_group": group,
        "take": bool(take),
        "decision_reason": reason,
        "group_score_before_entry": group_score,
        "other_group_score_before_entry": other_score,
        "premium_history_count_before_entry": int(
            state["groups"]["PREMIUM_INVOLVED"]["resolved_count"]
        ),
        "balanced_without_premium_history_count_before_entry": int(
            state["groups"]["BALANCED_WITHOUT_PREMIUM"]["resolved_count"]
        ),
    }

    selected: dict[str, Any] | None = None
    if take:
        selected = row.to_dict()
        selected["router_policy"] = EXPECTED_POLICY
        selected["router_group"] = group
        selected["router_decision_reason"] = reason
        selected["spread_adjusted_r"] = float(row[r_column])
        selected["spread_adjusted_pnl"] = float(row[pnl_column])

    outcome_r = float(row[r_column])
    group_payload["resolved_count"] = group_count + 1
    group_payload["last_two_r"] = (
        list(group_payload["last_two_r"]) + [outcome_r]
    )[-2:]
    state["processed_candidates"] = int(state["processed_candidates"]) + 1
    state["last_entry_dt"] = str(entry_dt)
    state["last_exit_dt"] = str(exit_dt)
    validate_state(state)
    return decision, selected


def boundary_token(dt: pd.Timestamp, mode: str) -> Any:
    if mode == "year":
        return int(dt.year)
    if mode == "halfyear":
        return (int(dt.year), 1 if int(dt.month) <= 6 else 2)
    if mode == "quarter":
        return (int(dt.year), (int(dt.month) - 1) // 3 + 1)
    raise ValueError(mode)


def should_restart_after(
    schedule_kind: str,
    schedule_value: int | None,
    processed_count: int,
    total_count: int,
) -> bool:
    if processed_count >= total_count:
        return False
    if schedule_kind == "single":
        return processed_count == int(schedule_value)
    if schedule_kind == "repeated":
        return processed_count % int(schedule_value) == 0
    return False


def run_schedule(
    source: pd.DataFrame,
    cost_view: str,
    schedule_name: str,
    schedule_kind: str,
    schedule_value: int | str | None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], list[dict[str, Any]], int]:
    r_column, pnl_column = COST_VIEWS[cost_view]
    state = new_state(cost_view)
    decisions: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    restart_count = 0
    previous_boundary: Any = None

    for index, (_, row) in enumerate(source.iterrows(), start=1):
        if schedule_kind == "boundary":
            token = boundary_token(pd.Timestamp(row.entry_dt), str(schedule_value))
            if previous_boundary is not None and token != previous_boundary:
                payload = canonical_state_json(state)
                state = restore_state(payload)
                restart_count += 1
                snapshots.append(
                    state_snapshot_row(
                        schedule_name,
                        cost_view,
                        restart_count,
                        state,
                    )
                )
            previous_boundary = token

        decision, selected_row = process_candidate(
            state,
            row,
            r_column,
            pnl_column,
        )
        decisions.append(decision)
        if selected_row is not None:
            selected.append(selected_row)

        if should_restart_after(
            schedule_kind,
            int(schedule_value) if isinstance(schedule_value, int) else None,
            index,
            len(source),
        ):
            payload = canonical_state_json(state)
            state = restore_state(payload)
            restart_count += 1
            snapshots.append(
                state_snapshot_row(
                    schedule_name,
                    cost_view,
                    restart_count,
                    state,
                )
            )

    decision_frame = pd.DataFrame(decisions)
    selected_frame = pd.DataFrame(selected)
    if not selected_frame.empty:
        selected_frame = selected_frame.sort_values(
            ["entry_dt", "exit_dt"], kind="mergesort"
        ).reset_index(drop=True)
    return decision_frame, selected_frame, state, snapshots, restart_count


def optional_max_diff(left: pd.Series, right: pd.Series) -> float:
    left_values = pd.to_numeric(left, errors="coerce").to_numpy(float)
    right_values = pd.to_numeric(right, errors="coerce").to_numpy(float)
    if not np.array_equal(np.isnan(left_values), np.isnan(right_values)):
        raise ValueError("OPTIONAL_SCORE_NAN_PATTERN_MISMATCH")
    finite = ~(np.isnan(left_values) | np.isnan(right_values))
    if not bool(finite.any()):
        return 0.0
    return float(np.max(np.abs(left_values[finite] - right_values[finite])))


def compare_decisions(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
) -> dict[str, Any]:
    left = actual.sort_values("entry_dt", kind="mergesort").reset_index(drop=True)
    right = expected.sort_values("entry_dt", kind="mergesort").reset_index(drop=True)
    if len(left) != len(right):
        raise ValueError("DECISION_ROW_COUNT_MISMATCH")
    exact_columns = [
        "entry_dt",
        "router_group",
        "take",
        "decision_reason",
        "premium_history_count_before_entry",
        "balanced_without_premium_history_count_before_entry",
    ]
    for column in exact_columns:
        if not bool(left[column].equals(right[column])):
            raise ValueError(f"DECISION_EXACT_MISMATCH: {column}")
    group_score_diff = optional_max_diff(
        left["group_score_before_entry"],
        right["group_score_before_entry"],
    )
    other_score_diff = optional_max_diff(
        left["other_group_score_before_entry"],
        right["other_group_score_before_entry"],
    )
    if group_score_diff > TOL or other_score_diff > TOL:
        raise ValueError(
            "DECISION_SCORE_MISMATCH: "
            f"group={group_score_diff} other={other_score_diff}"
        )
    return {
        "row_count": int(len(left)),
        "exact_columns_equal": True,
        "max_group_score_diff": group_score_diff,
        "max_other_score_diff": other_score_diff,
    }


def compare_selected(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
) -> dict[str, Any]:
    key = ["pair", "direction", "exit_profile", "entry_dt"]
    left = actual.sort_values(key, kind="mergesort").reset_index(drop=True)
    right = expected.sort_values(key, kind="mergesort").reset_index(drop=True)
    if len(left) != len(right):
        raise ValueError("SELECTED_TRADE_COUNT_MISMATCH")
    if not bool(left[key].equals(right[key])):
        raise ValueError("SELECTED_ENTRY_KEY_MISMATCH")
    if len(left) == 0:
        return {
            "trade_count": 0,
            "entry_keys_equal": True,
            "max_pnl_diff": 0.0,
            "max_r_diff": 0.0,
        }
    pnl_diff = float(
        np.max(
            np.abs(
                pd.to_numeric(left["spread_adjusted_pnl"], errors="raise").to_numpy(float)
                - pd.to_numeric(right["spread_adjusted_pnl"], errors="raise").to_numpy(float)
            )
        )
    )
    r_diff = float(
        np.max(
            np.abs(
                pd.to_numeric(left["spread_adjusted_r"], errors="raise").to_numpy(float)
                - pd.to_numeric(right["spread_adjusted_r"], errors="raise").to_numpy(float)
            )
        )
    )
    if pnl_diff > TOL or r_diff > TOL:
        raise ValueError(
            f"SELECTED_NUMERIC_MISMATCH: pnl={pnl_diff} r={r_diff}"
        )
    return {
        "trade_count": int(len(left)),
        "entry_keys_equal": True,
        "max_pnl_diff": pnl_diff,
        "max_r_diff": r_diff,
    }


def external_baseline_parity(
    baseline_decisions: pd.DataFrame,
    baseline_selected: pd.DataFrame,
    expected_trace: pd.DataFrame,
    expected_selected: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "decision_trace": compare_decisions(
            baseline_decisions,
            expected_trace,
        ),
        "selected_trades": compare_selected(
            baseline_selected,
            expected_selected,
        ),
    }


def main() -> int:
    args = parse_args()
    stage326a_path = Path(args.stage326a_json).expanduser().resolve()
    stage326_path = Path(args.stage326_json).expanduser().resolve()
    timeline_path = Path(args.stage324_timeline).expanduser().resolve()
    selected_path = Path(args.stage325_selected).expanduser().resolve()
    trace_path = Path(args.stage325_trace).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    checkpoint_path = Path(args.checkpoint_csv).expanduser().resolve()
    snapshot_path = Path(args.snapshot_csv).expanduser().resolve()
    terminal_state_path = Path(args.terminal_state_json).expanduser().resolve()

    stage326a = json.loads(stage326a_path.read_text(encoding="utf-8"))
    if stage326a.get("status") != EXPECTED_326A_STATUS:
        raise ValueError("STAGE326A_STATUS_UNEXPECTED")
    if stage326a.get("decision") != EXPECTED_326A_DECISION:
        raise ValueError("STAGE326A_DECISION_UNEXPECTED")
    if stage326a.get("stage326_core_confirmation", {}).get(
        "operational_gate_pass"
    ) is not True:
        raise ValueError("STAGE326A_CORE_GATE_NOT_PASS")
    if stage326a.get("stage326_core_confirmation", {}).get(
        "state_dependence_detected"
    ) is not True:
        raise ValueError("STAGE326A_STATE_DEPENDENCE_NOT_CONFIRMED")

    actual_stage326_sha = sha256_file(stage326_path)
    expected_stage326_sha = stage326a.get("source", {}).get(
        "stage326_json_sha256"
    )
    if actual_stage326_sha != expected_stage326_sha:
        raise ValueError("STAGE326_JSON_SHA_MISMATCH")

    stage326 = json.loads(stage326_path.read_text(encoding="utf-8"))
    if stage326.get("status") != EXPECTED_326_STATUS:
        raise ValueError("STAGE326_STATUS_UNEXPECTED")
    if stage326.get("decision") != EXPECTED_326_DECISION:
        raise ValueError("STAGE326_DECISION_UNEXPECTED")
    if stage326.get("research_contract", {}).get("fixed_policy") != EXPECTED_POLICY:
        raise ValueError("STAGE326_POLICY_UNEXPECTED")
    if stage326.get("research_contract", {}).get("selected_lane") != EXPECTED_LANE:
        raise ValueError("STAGE326_LANE_UNEXPECTED")

    hash_checks = {
        "stage324_timeline": (
            sha256_file(timeline_path),
            stage326.get("source", {}).get("stage324_timeline_sha256"),
        ),
        "stage325_selected": (
            sha256_file(selected_path),
            stage326.get("source", {}).get("stage325_selected_sha256"),
        ),
        "stage325_trace": (
            sha256_file(trace_path),
            stage326.get("source", {}).get("stage325_trace_sha256"),
        ),
    }
    for name, (actual, expected) in hash_checks.items():
        if actual != expected:
            raise ValueError(
                f"SOURCE_SHA_MISMATCH: {name} expected={expected} actual={actual}"
            )

    source = pd.read_csv(timeline_path, encoding="utf-8-sig")
    expected_selected = pd.read_csv(selected_path, encoding="utf-8-sig")
    expected_trace = pd.read_csv(trace_path, encoding="utf-8-sig")
    required = {
        "pair",
        "direction",
        "exit_profile",
        "entry_dt",
        "exit_dt",
        "balanced",
        "premium",
        "stress_r_1p0x",
        "stress_pnl_1p0x",
        "stress_r_1p5x",
        "stress_pnl_1p5x",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"SOURCE_COLUMNS_MISSING: {missing}")

    for frame in (source, expected_selected, expected_trace):
        for column in ("entry_dt", "exit_dt"):
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column], errors="raise")
    source["balanced"] = parse_bool(source["balanced"], "balanced")
    source["premium"] = parse_bool(source["premium"], "premium")
    expected_trace["take"] = parse_bool(expected_trace["take"], "take")
    source = source.sort_values(
        ["entry_dt", "exit_dt"], kind="mergesort"
    ).reset_index(drop=True)
    if len(source) > 1:
        current = source.entry_dt.iloc[1:].reset_index(drop=True)
        previous_exit = source.exit_dt.iloc[:-1].reset_index(drop=True)
        if bool((current < previous_exit).any()):
            raise ValueError("SOURCE_TRADES_OVERLAP")
    source["router_group"] = source.apply(assign_group, axis=1)

    baselines: dict[str, dict[str, Any]] = {}
    external_parity: dict[str, Any] = {}
    checkpoint_rows: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []
    all_pass = True

    for cost_view in COST_VIEWS:
        decisions, selected, terminal_state, snapshots, restart_count = run_schedule(
            source,
            cost_view,
            "BASELINE_NO_RESTART",
            "none",
            None,
        )
        baselines[cost_view] = {
            "decisions": decisions,
            "selected": selected,
            "terminal_state": terminal_state,
        }
        snapshot_rows.extend(snapshots)
        if cost_view == "1p0x":
            external_parity = external_baseline_parity(
                decisions,
                selected,
                expected_trace,
                expected_selected,
            )

        schedules: list[tuple[str, str, int | str | None]] = []
        for checkpoint in range(1, len(source)):
            schedules.append(
                (f"SINGLE_AFTER_{checkpoint}", "single", checkpoint)
            )
        for interval in REPEATED_INTERVALS:
            schedules.append(
                (f"REPEATED_EVERY_{interval}", "repeated", interval)
            )
        for mode in BOUNDARY_MODES:
            schedules.append(
                (f"BOUNDARY_RESTART_{mode.upper()}", "boundary", mode)
            )

        for schedule_name, schedule_kind, schedule_value in schedules:
            actual_decisions, actual_selected, actual_terminal, snapshots, restarts = run_schedule(
                source,
                cost_view,
                schedule_name,
                schedule_kind,
                schedule_value,
            )
            decision_parity = compare_decisions(
                actual_decisions,
                decisions,
            )
            selected_parity = compare_selected(
                actual_selected,
                selected,
            )
            terminal_equal = (
                canonical_state_json(actual_terminal)
                == canonical_state_json(terminal_state)
            )
            passed = bool(terminal_equal)
            all_pass = all_pass and passed
            checkpoint_rows.append(
                {
                    "cost_view": cost_view,
                    "schedule_name": schedule_name,
                    "schedule_kind": schedule_kind,
                    "schedule_value": schedule_value,
                    "restart_count": restarts,
                    "decision_rows": decision_parity["row_count"],
                    "selected_trades": selected_parity["trade_count"],
                    "max_group_score_diff": decision_parity[
                        "max_group_score_diff"
                    ],
                    "max_other_score_diff": decision_parity[
                        "max_other_score_diff"
                    ],
                    "max_selected_pnl_diff": selected_parity[
                        "max_pnl_diff"
                    ],
                    "max_selected_r_diff": selected_parity["max_r_diff"],
                    "terminal_state_equal": terminal_equal,
                    "pass": passed,
                }
            )
            snapshot_rows.extend(snapshots)

    baseline_terminal_1p0 = baselines["1p0x"]["terminal_state"]
    terminal_payload = {
        "status": "GOLD_V3_327_ROUTER_TERMINAL_STATE_SNAPSHOT_READY_AUDIT_ONLY",
        "mode": "AUDIT_ONLY_NOT_PRODUCTION_PROMOTION",
        "source_stage": 327,
        "state": baseline_terminal_1p0,
        "state_canonical_json": canonical_state_json(baseline_terminal_1p0),
        "state_sha256": sha256_text(canonical_state_json(baseline_terminal_1p0)),
        "candidate_count": int(len(source)),
        "selected_trade_count": int(len(baselines["1p0x"]["selected"])),
        "display_only_year_used_for_selection": False,
    }
    terminal_state_path.parent.mkdir(parents=True, exist_ok=True)
    terminal_state_path.write_text(
        json.dumps(json_safe(terminal_payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checkpoint_rows).to_csv(
        checkpoint_path,
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(snapshot_rows).to_csv(
        snapshot_path,
        index=False,
        encoding="utf-8-sig",
    )

    checkpoint_frame = pd.DataFrame(checkpoint_rows)
    failed = checkpoint_frame[~checkpoint_frame["pass"]]
    if not failed.empty:
        all_pass = False

    decision = (
        "PERSISTENT_ROUTER_STATE_CHECKPOINT_RESTART_PARITY_CONFIRMED"
        if all_pass
        else "PERSISTENT_ROUTER_STATE_CHECKPOINT_RESTART_PARITY_FAILED"
    )
    output = {
        "status": "GOLD_V3_327_PERSISTENT_ROUTER_STATE_CHECKPOINT_RESTART_PARITY_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_FIXED_ROUTER_STATE_SERIALIZATION_PARITY",
        "decision": decision,
        "source": {
            "stage326a_json": str(stage326a_path),
            "stage326a_json_sha256": sha256_file(stage326a_path),
            "stage326_json": str(stage326_path),
            "stage326_json_sha256": actual_stage326_sha,
            "stage324_timeline": str(timeline_path),
            "stage324_timeline_sha256": hash_checks["stage324_timeline"][0],
            "stage325_selected": str(selected_path),
            "stage325_selected_sha256": hash_checks["stage325_selected"][0],
            "stage325_trace": str(trace_path),
            "stage325_trace_sha256": hash_checks["stage325_trace"][0],
        },
        "research_contract": {
            "fixed_policy": EXPECTED_POLICY,
            "selected_lane": EXPECTED_LANE,
            "state_schema_version": STATE_SCHEMA_VERSION,
            "state_groups": list(GROUPS),
            "state_payload_per_group": ["resolved_count", "last_two_r"],
            "cost_views": COST_VIEWS,
            "single_restart_after_every_possible_candidate": True,
            "repeated_restart_intervals": list(REPEATED_INTERVALS),
            "calendar_boundary_restart_modes": list(BOUNDARY_MODES),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "display_only_year_used_for_selection": False,
            "no_policy_retune": True,
            "no_new_raw_feature_threshold": True,
            "numeric_tolerance": TOL,
        },
        "external_baseline_parity": external_parity,
        "restart_parity_gate": {
            "pass": bool(all_pass),
            "scenario_count": int(len(checkpoint_rows)),
            "failed_scenario_count": int(len(failed)),
            "maximum_score_diff": float(
                checkpoint_frame[
                    ["max_group_score_diff", "max_other_score_diff"]
                ].max().max()
            ),
            "maximum_selected_pnl_diff": float(
                checkpoint_frame["max_selected_pnl_diff"].max()
            ),
            "maximum_selected_r_diff": float(
                checkpoint_frame["max_selected_r_diff"].max()
            ),
            "all_terminal_states_equal": bool(
                checkpoint_frame["terminal_state_equal"].all()
            ),
        },
        "baseline": {
            "candidate_count": int(len(source)),
            "selected_trade_count_1p0x": int(len(baselines["1p0x"]["selected"])),
            "selected_trade_count_1p5x": int(len(baselines["1p5x"]["selected"])),
            "selection_summary_1p0x": summarize(
                baselines["1p0x"]["selected"][
                    baselines["1p0x"]["selected"].entry_dt.dt.year.isin(
                        [2024, 2025]
                    )
                ]
            ),
            "terminal_state_1p0x": baseline_terminal_1p0,
            "terminal_state_1p5x": baselines["1p5x"]["terminal_state"],
        },
        "interpretation": {
            "finding": (
                "The exact N2 router can be stopped and restarted without changing any "
                "decision, selected trade, score, PnL, R, or terminal state when the "
                "minimal persistent payload is restored."
            ),
            "required_operational_state": (
                "Persist resolved_count and last_two_r independently for Premium-involved "
                "and Balanced-without-Premium, together with the last processed timestamps."
            ),
            "limits": (
                "This confirms serialization parity only. It is not a production promotion, "
                "and Stage319 remains frozen."
            ),
        },
        "outputs": {
            "result_json": str(output_path),
            "checkpoint_csv": str(checkpoint_path),
            "snapshot_csv": str(snapshot_path),
            "terminal_state_json": str(terminal_state_path),
            "checkpoint_sha256": sha256_file(checkpoint_path),
            "snapshot_sha256": sha256_file(snapshot_path),
            "terminal_state_sha256": sha256_file(terminal_state_path),
        },
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage326_core_decision": "UNCHANGED_CONFIRMED",
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage292_candidate_pool_changed": False,
        },
        "safety_flags": {
            "historical_trade_registry_only": True,
            "resolved_only_router_history": True,
            "closed_candles_only": True,
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(json_safe(output), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(json_safe(output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
