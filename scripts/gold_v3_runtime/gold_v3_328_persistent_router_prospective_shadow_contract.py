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

TOL = 1e-12
SPEC_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "gold_v3_328"
    / "stage328_persistent_router_prospective_shadow_spec.json"
)
EXPECTED_STAGE327_STATUS = (
    "GOLD_V3_327_PERSISTENT_ROUTER_STATE_CHECKPOINT_RESTART_PARITY_AUDIT_COMPLETE"
)
EXPECTED_STAGE327_DECISION = (
    "PERSISTENT_ROUTER_STATE_CHECKPOINT_RESTART_PARITY_CONFIRMED"
)
EXPECTED_TERMINAL_STATUS = (
    "GOLD_V3_327_ROUTER_TERMINAL_STATE_SNAPSHOT_READY_AUDIT_ONLY"
)
EXPECTED_STAGE326A_STATUS = (
    "GOLD_V3_326A_ROUTER_DISAGREEMENT_COUNTER_CORRECTION_COMPLETE"
)
EXPECTED_STAGE326A_DECISION = (
    "STAGE326_CORE_DECISION_CONFIRMED_REPORTING_COUNTER_CORRECTED"
)
EXPECTED_STAGE318_STATUS = (
    "GOLD_V3_318_MOCHIPOYO_HIGH_CONFIDENCE_REFINEMENT_COMPLETE"
)
EXPECTED_STAGE318_DECISION = "MOCHIPOYO_HIGHER_WIN_RATE_PRIMARY_FOUND"
EXPECTED_STAGE319_CONTRACT_STATUS = (
    "GOLD_V3_319_DUAL_TIER_PROSPECTIVE_WATCH_CONTRACT_FROZEN"
)
EXPECTED_POLICY = "RELATIVE_TRAILING_MEAN_R_N2"
EXPECTED_LANE = "BALANCED_OR_PREMIUM"
EXPECTED_SOURCE = "M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND"
EXPECTED_BALANCED = "CONSENSUS_OR_ATR_STEADY_AND_RANGE"
EXPECTED_PREMIUM = "TREND_FLOW_COMPRESSION_GE_0_95"
GROUPS = ("PREMIUM_INVOLVED", "BALANCED_WITHOUT_PREMIUM")


class ContractError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage327-json", required=True)
    parser.add_argument("--stage327-terminal-state", required=True)
    parser.add_argument("--stage326a-json", required=True)
    parser.add_argument("--stage324-timeline", required=True)
    parser.add_argument("--stage318-json", required=True)
    parser.add_argument("--stage319-contract", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--bootstrap-state", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        json_safe(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def parse_bool(series: pd.Series, name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    parsed = series.astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    if parsed.isna().any():
        raise ContractError(f"BOOLEAN_PARSE_FAILED: {name}")
    return parsed.astype(bool)


def validate_router_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != 1:
        raise ContractError("ROUTER_STATE_SCHEMA_UNEXPECTED")
    if state.get("policy") != EXPECTED_POLICY:
        raise ContractError("ROUTER_STATE_POLICY_UNEXPECTED")
    if state.get("selected_lane") != EXPECTED_LANE:
        raise ContractError("ROUTER_STATE_LANE_UNEXPECTED")
    if state.get("cost_view") != "1p0x":
        raise ContractError("ROUTER_STATE_COST_VIEW_UNEXPECTED")
    if sorted(state.get("groups", {}).keys()) != sorted(GROUPS):
        raise ContractError("ROUTER_STATE_GROUPS_UNEXPECTED")
    processed = int(state.get("processed_candidates", -1))
    if processed < 0:
        raise ContractError("ROUTER_STATE_PROCESSED_INVALID")
    total = 0
    for group in GROUPS:
        item = state["groups"][group]
        count = int(item.get("resolved_count", -1))
        values = item.get("last_two_r")
        if count < 0 or not isinstance(values, list):
            raise ContractError(f"ROUTER_STATE_GROUP_INVALID: {group}")
        if len(values) != min(2, count):
            raise ContractError(f"ROUTER_STATE_LAST_TWO_INVALID: {group}")
        if not all(math.isfinite(float(value)) for value in values):
            raise ContractError(f"ROUTER_STATE_NONFINITE: {group}")
        total += count
    if total != processed:
        raise ContractError(
            f"ROUTER_STATE_COUNT_MISMATCH: total={total} processed={processed}"
        )
    if processed > 0 and (
        state.get("last_entry_dt") is None or state.get("last_exit_dt") is None
    ):
        raise ContractError("ROUTER_STATE_LAST_TIMESTAMPS_MISSING")


def assign_group(row: pd.Series) -> str:
    if bool(row.premium):
        return "PREMIUM_INVOLVED"
    if bool(row.balanced):
        return "BALANCED_WITHOUT_PREMIUM"
    raise ContractError("TIMELINE_ROW_OUTSIDE_SELECTED_LANE")


def replay_timeline(frame: pd.DataFrame) -> dict[str, Any]:
    groups = {
        group: {"resolved_count": 0, "last_two_r": []}
        for group in GROUPS
    }
    for _, row in frame.iterrows():
        group = str(row.router_group)
        value = float(row.stress_r_1p0x)
        item = groups[group]
        item["resolved_count"] = int(item["resolved_count"]) + 1
        item["last_two_r"] = (list(item["last_two_r"]) + [value])[-2:]
    return {
        "processed_candidates": int(len(frame)),
        "last_entry_dt": str(pd.Timestamp(frame.entry_dt.iloc[-1])) if len(frame) else None,
        "last_exit_dt": str(pd.Timestamp(frame.exit_dt.iloc[-1])) if len(frame) else None,
        "groups": groups,
    }


def assert_float_lists_equal(
    actual: list[Any],
    expected: list[Any],
    label: str,
) -> float:
    if len(actual) != len(expected):
        raise ContractError(f"FLOAT_LIST_LENGTH_MISMATCH: {label}")
    if not actual:
        return 0.0
    diff = float(
        np.max(
            np.abs(
                np.asarray(actual, dtype=float)
                - np.asarray(expected, dtype=float)
            )
        )
    )
    if diff > TOL:
        raise ContractError(f"FLOAT_LIST_MISMATCH: {label} diff={diff}")
    return diff


def find_profile(stage318: dict[str, Any], name: str) -> dict[str, Any]:
    for row in stage318.get("leaderboard", []):
        if row.get("profile_name") == name:
            return row
    raise ContractError(f"STAGE318_PROFILE_NOT_FOUND: {name}")


def immutable_contract_fields(
    spec: dict[str, Any],
    spec_sha: str,
    source_hashes: dict[str, str],
    cutoff: dict[str, Any],
    initial_state: dict[str, Any],
    initial_state_sha: str,
    stage318: dict[str, Any],
) -> dict[str, Any]:
    balanced = find_profile(stage318, EXPECTED_BALANCED)
    premium = find_profile(stage318, EXPECTED_PREMIUM)
    return {
        "spec_id": spec["spec_id"],
        "spec_sha256": spec_sha,
        "source_candidate": spec["source_candidate"],
        "selected_lane": spec["selected_lane"],
        "router_policy": spec["router_policy"],
        "router_cost_view": spec["router_cost_view"],
        "balanced_membership": spec["balanced_membership"],
        "premium_membership": spec["premium_membership"],
        "router_group_assignment": spec["router_group_assignment"],
        "state_contract": spec["state_contract"],
        "prospective_contract": spec["prospective_contract"],
        "portfolio_policy": spec["portfolio_policy"],
        "future_review_gate": spec["future_review_gate"],
        "frozen_cutoffs": cutoff,
        "initial_router_state": initial_state,
        "initial_router_state_sha256": initial_state_sha,
        "source_hashes": source_hashes,
        "historical_profile_reference": {
            "balanced": balanced,
            "premium": premium,
        },
    }


def freeze_contract(
    path: Path,
    immutable: dict[str, Any],
    preserved_state: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if path.exists():
        contract = load_json(path)
        if contract.get("status") != (
            "GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_FROZEN"
        ):
            raise ContractError("STAGE328_EXISTING_CONTRACT_STATUS_UNEXPECTED")
        for key, expected in immutable.items():
            if contract.get(key) != expected:
                raise ContractError(f"STAGE328_CONTRACT_IMMUTABLE_MISMATCH: {key}")
        if contract.get("preserved_state") != preserved_state:
            raise ContractError("STAGE328_PRESERVED_STATE_MISMATCH")
        return contract, False

    contract = {
        "status": (
            "GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_FROZEN"
        ),
        "mode": "AUDIT_ONLY_FUTURE_ONLY_PERSISTENT_ROUTER_SHADOW",
        **immutable,
        "contract_rules": {
            "freeze_on_first_run": True,
            "immutable_after_first_run": True,
            "cutoff_must_never_move": True,
            "router_state_must_never_reset": True,
            "future_candidate_decision_dt_strictly_after_cutoff": True,
            "resolved_only_state_updates": True,
            "pending_has_no_as_of_pnl": True,
            "automatic_promotion": False,
        },
        "preserved_state": preserved_state,
    }
    write_json(path, contract)
    return contract, True


def freeze_bootstrap_state(
    path: Path,
    contract_sha: str,
    cutoff_dt: str,
    state: dict[str, Any],
    state_sha: str,
) -> tuple[dict[str, Any], bool]:
    immutable = {
        "contract_sha256": contract_sha,
        "prospective_decision_dt_strictly_after": cutoff_dt,
        "initial_state": state,
        "initial_state_sha256": state_sha,
    }
    if path.exists():
        payload = load_json(path)
        if payload.get("status") != (
            "GOLD_V3_328_PERSISTENT_ROUTER_BOOTSTRAP_STATE_FROZEN"
        ):
            raise ContractError("STAGE328_BOOTSTRAP_STATUS_UNEXPECTED")
        for key, expected in immutable.items():
            if payload.get(key) != expected:
                raise ContractError(f"STAGE328_BOOTSTRAP_IMMUTABLE_MISMATCH: {key}")
        return payload, False

    payload = {
        "status": "GOLD_V3_328_PERSISTENT_ROUTER_BOOTSTRAP_STATE_FROZEN",
        "mode": "AUDIT_ONLY_INITIAL_STATE_NOT_MUTABLE_RUNTIME_STATE",
        **immutable,
        "rules": {
            "copy_to_runtime_state_before_first_prospective_candidate": True,
            "never_modify_this_bootstrap_file": True,
            "runtime_state_updates_after_candidate_resolution_only": True,
        },
    }
    write_json(path, payload)
    return payload, True


def main() -> int:
    args = parse_args()
    stage327_path = Path(args.stage327_json).expanduser().resolve()
    terminal_path = Path(args.stage327_terminal_state).expanduser().resolve()
    stage326a_path = Path(args.stage326a_json).expanduser().resolve()
    timeline_path = Path(args.stage324_timeline).expanduser().resolve()
    stage318_path = Path(args.stage318_json).expanduser().resolve()
    stage319_contract_path = Path(args.stage319_contract).expanduser().resolve()
    contract_path = Path(args.contract).expanduser().resolve()
    bootstrap_path = Path(args.bootstrap_state).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    spec = load_json(SPEC_PATH)
    spec_sha = sha256_file(SPEC_PATH)
    if spec.get("source_candidate") != EXPECTED_SOURCE:
        raise ContractError("STAGE328_SPEC_SOURCE_UNEXPECTED")
    if spec.get("selected_lane") != EXPECTED_LANE:
        raise ContractError("STAGE328_SPEC_LANE_UNEXPECTED")
    if spec.get("router_policy") != EXPECTED_POLICY:
        raise ContractError("STAGE328_SPEC_POLICY_UNEXPECTED")

    stage327 = load_json(stage327_path)
    if stage327.get("status") != EXPECTED_STAGE327_STATUS:
        raise ContractError("STAGE327_STATUS_UNEXPECTED")
    if stage327.get("decision") != EXPECTED_STAGE327_DECISION:
        raise ContractError("STAGE327_DECISION_UNEXPECTED")
    if stage327.get("restart_parity_gate", {}).get("pass") is not True:
        raise ContractError("STAGE327_RESTART_PARITY_NOT_PASS")
    if int(stage327.get("restart_parity_gate", {}).get("failed_scenario_count", -1)) != 0:
        raise ContractError("STAGE327_FAILED_SCENARIOS_NONZERO")

    terminal_file_sha = sha256_file(terminal_path)
    expected_terminal_file_sha = stage327.get("outputs", {}).get(
        "terminal_state_sha256"
    )
    if terminal_file_sha != expected_terminal_file_sha:
        raise ContractError("STAGE327_TERMINAL_FILE_SHA_MISMATCH")
    terminal = load_json(terminal_path)
    if terminal.get("status") != EXPECTED_TERMINAL_STATUS:
        raise ContractError("STAGE327_TERMINAL_STATUS_UNEXPECTED")
    initial_state = terminal.get("state")
    if not isinstance(initial_state, dict):
        raise ContractError("STAGE327_TERMINAL_STATE_MISSING")
    validate_router_state(initial_state)
    state_canonical = canonical_json(initial_state)
    state_sha = sha256_text(state_canonical)
    if terminal.get("state_canonical_json") != state_canonical:
        raise ContractError("STAGE327_TERMINAL_CANONICAL_MISMATCH")
    if terminal.get("state_sha256") != state_sha:
        raise ContractError("STAGE327_TERMINAL_STATE_SHA_MISMATCH")

    stage326a_sha = sha256_file(stage326a_path)
    expected_stage326a_sha = stage327.get("source", {}).get(
        "stage326a_json_sha256"
    )
    if stage326a_sha != expected_stage326a_sha:
        raise ContractError("STAGE326A_SHA_MISMATCH")
    stage326a = load_json(stage326a_path)
    if stage326a.get("status") != EXPECTED_STAGE326A_STATUS:
        raise ContractError("STAGE326A_STATUS_UNEXPECTED")
    if stage326a.get("decision") != EXPECTED_STAGE326A_DECISION:
        raise ContractError("STAGE326A_DECISION_UNEXPECTED")

    timeline_sha = sha256_file(timeline_path)
    expected_timeline_sha = stage327.get("source", {}).get(
        "stage324_timeline_sha256"
    )
    if timeline_sha != expected_timeline_sha:
        raise ContractError("STAGE324_TIMELINE_SHA_MISMATCH")
    timeline = pd.read_csv(timeline_path, encoding="utf-8-sig")
    required = {
        "entry_dt",
        "exit_dt",
        "balanced",
        "premium",
        "stress_r_1p0x",
    }
    missing = sorted(required - set(timeline.columns))
    if missing:
        raise ContractError(f"STAGE324_TIMELINE_COLUMNS_MISSING: {missing}")
    timeline["entry_dt"] = pd.to_datetime(timeline["entry_dt"], errors="raise")
    timeline["exit_dt"] = pd.to_datetime(timeline["exit_dt"], errors="raise")
    timeline["balanced"] = parse_bool(timeline["balanced"], "balanced")
    timeline["premium"] = parse_bool(timeline["premium"], "premium")
    timeline = timeline.sort_values(
        ["entry_dt", "exit_dt"], kind="mergesort"
    ).reset_index(drop=True)
    if len(timeline) > 1:
        current = timeline.entry_dt.iloc[1:].reset_index(drop=True)
        prior_exit = timeline.exit_dt.iloc[:-1].reset_index(drop=True)
        if bool((current < prior_exit).any()):
            raise ContractError("STAGE324_TIMELINE_OVERLAP")
    timeline["router_group"] = timeline.apply(assign_group, axis=1)
    replay = replay_timeline(timeline)
    if replay["processed_candidates"] != int(initial_state["processed_candidates"]):
        raise ContractError("INITIAL_STATE_CANDIDATE_COUNT_MISMATCH")
    if replay["last_entry_dt"] != str(pd.Timestamp(initial_state["last_entry_dt"])):
        raise ContractError("INITIAL_STATE_LAST_ENTRY_MISMATCH")
    if replay["last_exit_dt"] != str(pd.Timestamp(initial_state["last_exit_dt"])):
        raise ContractError("INITIAL_STATE_LAST_EXIT_MISMATCH")
    replay_max_diff = 0.0
    for group in GROUPS:
        if replay["groups"][group]["resolved_count"] != int(
            initial_state["groups"][group]["resolved_count"]
        ):
            raise ContractError(f"INITIAL_STATE_GROUP_COUNT_MISMATCH: {group}")
        replay_max_diff = max(
            replay_max_diff,
            assert_float_lists_equal(
                replay["groups"][group]["last_two_r"],
                initial_state["groups"][group]["last_two_r"],
                group,
            ),
        )

    stage318 = load_json(stage318_path)
    if stage318.get("status") != EXPECTED_STAGE318_STATUS:
        raise ContractError("STAGE318_STATUS_UNEXPECTED")
    if stage318.get("decision") != EXPECTED_STAGE318_DECISION:
        raise ContractError("STAGE318_DECISION_UNEXPECTED")
    balanced_profile = find_profile(stage318, EXPECTED_BALANCED)
    premium_profile = find_profile(stage318, EXPECTED_PREMIUM)
    if balanced_profile.get("profile_name") != EXPECTED_BALANCED:
        raise ContractError("STAGE318_BALANCED_PROFILE_UNEXPECTED")
    if premium_profile.get("profile_name") != EXPECTED_PREMIUM:
        raise ContractError("STAGE318_PREMIUM_PROFILE_UNEXPECTED")

    stage319_contract = load_json(stage319_contract_path)
    if stage319_contract.get("status") != EXPECTED_STAGE319_CONTRACT_STATUS:
        raise ContractError("STAGE319_CONTRACT_STATUS_UNEXPECTED")
    cutoff = stage319_contract.get("frozen_cutoffs")
    if not isinstance(cutoff, dict):
        raise ContractError("STAGE319_FROZEN_CUTOFF_MISSING")
    cutoff_dt = pd.Timestamp(cutoff["prospective_decision_dt_strictly_after"])
    state_last_exit = pd.Timestamp(initial_state["last_exit_dt"])
    state_last_entry = pd.Timestamp(initial_state["last_entry_dt"])
    if cutoff_dt <= state_last_exit:
        raise ContractError(
            f"PROSPECTIVE_CUTOFF_NOT_AFTER_STATE: cutoff={cutoff_dt} last_exit={state_last_exit}"
        )
    gap_candidates = timeline[
        (timeline.entry_dt > state_last_entry)
        & (timeline.entry_dt <= cutoff_dt)
    ]
    if not gap_candidates.empty:
        raise ContractError(
            f"UNAPPLIED_PRE_CUTOFF_CANDIDATES: count={len(gap_candidates)}"
        )

    source_hashes = {
        "stage327_json_sha256": sha256_file(stage327_path),
        "stage327_terminal_state_file_sha256": terminal_file_sha,
        "stage326a_json_sha256": stage326a_sha,
        "stage324_timeline_sha256": timeline_sha,
        "stage318_json_sha256": sha256_file(stage318_path),
        "stage319_contract_sha256": sha256_file(stage319_contract_path),
    }
    immutable = immutable_contract_fields(
        spec,
        spec_sha,
        source_hashes,
        cutoff,
        initial_state,
        state_sha,
        stage318,
    )
    contract, contract_created = freeze_contract(
        contract_path,
        immutable,
        spec["preserved_state"],
    )
    contract_sha = sha256_file(contract_path)
    bootstrap, bootstrap_created = freeze_bootstrap_state(
        bootstrap_path,
        contract_sha,
        str(cutoff_dt),
        initial_state,
        state_sha,
    )

    premium_values = initial_state["groups"]["PREMIUM_INVOLVED"][
        "last_two_r"
    ]
    balanced_values = initial_state["groups"]["BALANCED_WITHOUT_PREMIUM"][
        "last_two_r"
    ]
    premium_score = float(np.mean(premium_values))
    balanced_score = float(np.mean(balanced_values))
    initial_view = {
        "premium_score": premium_score,
        "balanced_without_premium_score": balanced_score,
        "premium_candidate_would_be_selected": premium_score >= balanced_score,
        "balanced_without_premium_candidate_would_be_selected": (
            balanced_score >= premium_score
        ),
        "score_difference_premium_minus_balanced": (
            premium_score - balanced_score
        ),
        "warmup_complete": all(
            int(initial_state["groups"][group]["resolved_count"]) >= 2
            for group in GROUPS
        ),
    }

    output = {
        "status": (
            "GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_READY"
        ),
        "mode": "AUDIT_ONLY_FUTURE_ONLY_PERSISTENT_ROUTER_SHADOW",
        "decision": "WAIT_FOR_FIRST_POST_FREEZE_BALANCED_OR_PREMIUM_CANDIDATE",
        "contract_created_this_run": contract_created,
        "bootstrap_created_this_run": bootstrap_created,
        "contract": {
            "path": str(contract_path),
            "sha256": contract_sha,
            "status": contract["status"],
        },
        "bootstrap_state": {
            "path": str(bootstrap_path),
            "sha256": sha256_file(bootstrap_path),
            "status": bootstrap["status"],
            "state_sha256": state_sha,
        },
        "integrity": {
            "stage327_restart_parity_pass": True,
            "stage327_failed_scenarios": 0,
            "timeline_candidate_count": int(len(timeline)),
            "terminal_state_processed_candidates": int(
                initial_state["processed_candidates"]
            ),
            "timeline_to_state_max_r_diff": replay_max_diff,
            "gap_candidate_count_between_state_and_cutoff": int(
                len(gap_candidates)
            ),
            "state_last_entry_dt": str(state_last_entry),
            "state_last_exit_dt": str(state_last_exit),
            "prospective_cutoff_dt": str(cutoff_dt),
        },
        "initial_router_view": initial_view,
        "prospective_counts": {
            "post_freeze_source_candidates": 0,
            "post_freeze_selected_trades": 0,
            "post_freeze_resolved_candidates": 0,
            "post_freeze_pending_candidates": 0,
        },
        "future_review_gate": spec["future_review_gate"],
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage327_result": "UNCHANGED_RETAINED",
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage292_candidate_pool_changed": False,
        },
        "safety_flags": {
            "closed_candles_only": True,
            "resolved_only_state_updates": True,
            "pending_has_no_as_of_pnl": True,
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    write_json(output_path, output)
    print(json.dumps(json_safe(output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
