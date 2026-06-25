from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

HERE = Path(__file__).resolve().parent
PROSPECTIVE_DIR = HERE.parent / "prospective"
if str(PROSPECTIVE_DIR) not in sys.path:
    sys.path.insert(0, str(PROSPECTIVE_DIR))

from fresh_prospective_engine import (  # noqa: E402
    CANDIDATE_IDS,
    build_candidate_registry,
    candidate_summary,
    clean_json_value,
    load_inputs,
)
from prospective_monitor_state import (  # noqa: E402
    append_run_history,
    input_continuity_snapshot,
    load_previous_monitor,
    reconcile_candidates,
    reconcile_parent_events,
)

STATEFUL_FILES = [
    "monitor_state.json",
    "monitor_candidate_ledger.csv",
    "monitor_parent_event_ledger.csv",
    "monitor_candidate_summary.csv",
    "monitor_run_history.csv",
    "input_provenance.json",
    "monitor_latest_snapshot_summary.json",
    "LATEST_RUN_SUMMARY.txt",
    "MONITOR_RUN_ERROR.txt",
]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def json_text(value: Any) -> str:
    return json.dumps(clean_json_value(value), ensure_ascii=False, indent=2) + "\n"


def dataframe_csv_text(frame: pd.DataFrame) -> str:
    return frame.to_csv(index=False, date_format="%Y-%m-%d %H:%M:%S")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dataframe_display(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(none)"
    return frame.to_csv(index=False, date_format="%Y-%m-%d %H:%M:%S").rstrip()


def backup_state(output_dir: Path, run_id: str) -> Path | None:
    existing = [output_dir / name for name in STATEFUL_FILES if (output_dir / name).exists()]
    if not existing:
        return None
    backup_dir = output_dir / "backups" / run_id
    backup_dir.mkdir(parents=True, exist_ok=False)
    for source in existing:
        shutil.copy2(source, backup_dir / source.name)
    return backup_dir


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def atomic_write_dataframe(path: Path, frame: pd.DataFrame) -> None:
    atomic_write_text(path, dataframe_csv_text(frame))


def observation_state(candidates: pd.DataFrame) -> str:
    if candidates.empty:
        return "NO_CANDIDATE_YET"
    unresolved = candidates.get("resolution_state", pd.Series(dtype=str)) == "UNRESOLVED"
    if bool(unresolved.any()):
        return "CANDIDATES_PRESENT_WITH_UNRESOLVED"
    return "CANDIDATES_PRESENT_ALL_CURRENTLY_RESOLVED"


def cycle_state(
    previous_state: dict[str, Any] | None,
    data_advanced: bool,
    new_candidates: pd.DataFrame,
    resolved_transitions: pd.DataFrame,
    new_parent_events: pd.DataFrame,
    parent_admission_transitions: pd.DataFrame,
) -> str:
    if previous_state is None:
        return "MONITOR_INITIALIZED"
    if not data_advanced:
        return "NO_NEW_CLOSED_BAR"
    if any(
        not frame.empty
        for frame in (
            new_candidates,
            resolved_transitions,
            new_parent_events,
            parent_admission_transitions,
        )
    ):
        return "ADVANCED_WITH_LEDGER_CHANGES"
    return "ADVANCED_NO_LEDGER_CHANGE"


def build_summary_text(
    *,
    run_id: str,
    cycle: str,
    cutoff: pd.Timestamp,
    previous_latest_m1_close: pd.Timestamp | None,
    latest_m1_close: pd.Timestamp,
    candidates: pd.DataFrame,
    parent_events: pd.DataFrame,
    summary: pd.DataFrame,
    new_candidates: pd.DataFrame,
    resolved_transitions: pd.DataFrame,
    new_parent_events: pd.DataFrame,
    parent_admission_transitions: pd.DataFrame,
    run_count: int,
    backup_dir: Path | None,
) -> str:
    unresolved_count = int(
        (candidates.get("resolution_state", pd.Series(dtype=str)) == "UNRESOLVED").sum()
    )
    resolved_count = int(
        (candidates.get("resolution_state", pd.Series(dtype=str)) == "RESOLVED").sum()
    )
    accepted_parent_count = int(
        (
            parent_events.get("admission_state", pd.Series(dtype=str))
            == "ACCEPTED_PARENT_EVENT"
        ).sum()
    )
    suppressed_parent_count = int(
        parent_events.get("admission_state", pd.Series(dtype=str))
        .astype(str)
        .str.startswith("SUPPRESSED")
        .sum()
    )
    lines = [
        "GOLD_ML_V1 STATEFUL PROSPECTIVE MONITOR",
        "status=PASS",
        f"run_id={run_id}",
        f"cycle_state={cycle}",
        f"run_count={run_count}",
        f"cutoff_mt5_server_close={cutoff}",
        f"previous_latest_m1_close={previous_latest_m1_close if previous_latest_m1_close is not None else 'NONE'}",
        f"latest_m1_close={latest_m1_close}",
        f"candidate_total={len(candidates)}",
        f"new_candidate_count={len(new_candidates)}",
        f"resolved_transition_count={len(resolved_transitions)}",
        f"resolved_candidate_total={resolved_count}",
        f"unresolved_candidate_total={unresolved_count}",
        f"parent_event_total={len(parent_events)}",
        f"new_parent_event_count={len(new_parent_events)}",
        f"parent_admission_transition_count={len(parent_admission_transitions)}",
        f"accepted_parent_total={accepted_parent_count}",
        f"suppressed_parent_total={suppressed_parent_count}",
        f"backup_dir={backup_dir if backup_dir else 'NONE'}",
        f"observation_state={observation_state(candidates)}",
        "candidate_rules=FROZEN",
        "retuning=FORBIDDEN_NOT_PERFORMED",
        "historical_prefix_mutation=FAIL_CLOSED",
        "duplicate_candidate_registration=FORBIDDEN",
        "resolved_result_rewrite=FORBIDDEN",
        "performance_gate=NOT_APPLICABLE_PROSPECTIVE_AUDIT_ONLY",
        "scheduled_task_installed=FALSE",
        "automatic_next_phase=FALSE",
        "new_exploration=FALSE",
        "live_ready=FALSE",
        "final_signal=FALSE",
        "mt5_order=FALSE",
        "discord=FALSE",
        "ai_api=FALSE",
        "live_hook=FALSE",
        "",
        "Candidate cumulative summary:",
        dataframe_display(summary),
        "",
        "New candidates in this cycle:",
        dataframe_display(new_candidates),
        "",
        "Candidates resolved in this cycle:",
        dataframe_display(resolved_transitions),
        "",
        "New parent events in this cycle:",
        dataframe_display(new_parent_events),
        "",
        "Parent events changed from suppressed to accepted:",
        dataframe_display(parent_admission_transitions),
        "",
        "Cumulative candidate ledger:",
        dataframe_display(candidates),
        "",
        "Caveats:",
        "- This is one audit-only monitoring cycle, not a continuously running background task.",
        "- Re-running the root BAT reads newer closed bars and updates this same cumulative ledger.",
        "- Candidate IDs, rules, thresholds, horizons and lineage assignments remain frozen.",
        "- Unresolved candidates remain open until later closed M1 bars resolve them or the frozen horizon ends.",
        "- No order, signal notification, Discord message, API call, promotion or registration is performed.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run_monitor(
    files_dir: Path,
    config_path: Path,
    output_dir: Path,
) -> int:
    config = load_json(config_path)
    cutoff = pd.Timestamp(config["cutoff_mt5_server_close"])
    configured_ids = list(config["candidate_pool"]["frozen_accumulated_ids"])
    if configured_ids != CANDIDATE_IDS:
        raise ValueError("Monitoring config candidate order/set differs from frozen engine IDs")

    output_dir.mkdir(parents=True, exist_ok=True)
    previous_state, previous_candidates, previous_parent_events, history = load_previous_monitor(
        output_dir
    )
    if previous_state:
        if pd.Timestamp(previous_state["cutoff_mt5_server_close"]) != cutoff:
            raise ValueError("Monitor cutoff differs from persisted state")
        if list(previous_state["candidate_ids"]) != CANDIDATE_IDS:
            raise ValueError("Persisted monitor candidate IDs differ from frozen IDs")

    bars, provenance = load_inputs(files_dir, cutoff)
    continuity, data_advanced = input_continuity_snapshot(bars, previous_state)
    current_candidates, current_parent_events, coverage = build_candidate_registry(bars, cutoff)

    candidate_ledger, new_candidates, resolved_transitions = reconcile_candidates(
        previous_candidates,
        current_candidates,
    )
    parent_ledger, new_parent_events, parent_admission_transitions = reconcile_parent_events(
        previous_parent_events,
        current_parent_events,
    )
    cumulative_summary = candidate_summary(candidate_ledger)

    now = datetime.now()
    run_id = now.strftime("%Y%m%dT%H%M%S_%f")
    latest_m1_close = pd.Timestamp(bars["M1"]["bar_close_time"].iloc[-1])
    previous_latest_m1_close = (
        pd.Timestamp(previous_state["latest_m1_close"]) if previous_state else None
    )
    cycle = cycle_state(
        previous_state,
        data_advanced,
        new_candidates,
        resolved_transitions,
        new_parent_events,
        parent_admission_transitions,
    )
    run_count = int(previous_state.get("run_count", 0) if previous_state else 0) + 1

    run_row = {
        "run_id": run_id,
        "run_time_local": pd.Timestamp(now),
        "cycle_state": cycle,
        "previous_latest_m1_close": previous_latest_m1_close,
        "latest_m1_close": latest_m1_close,
        "candidate_total": int(len(candidate_ledger)),
        "new_candidate_count": int(len(new_candidates)),
        "resolved_transition_count": int(len(resolved_transitions)),
        "unresolved_candidate_total": int(
            (
                candidate_ledger.get("resolution_state", pd.Series(dtype=str))
                == "UNRESOLVED"
            ).sum()
        ),
        "parent_event_total": int(len(parent_ledger)),
        "new_parent_event_count": int(len(new_parent_events)),
        "parent_admission_transition_count": int(len(parent_admission_transitions)),
        "status": "PASS",
    }
    run_history = append_run_history(history, run_row)

    candidate_text = dataframe_csv_text(candidate_ledger)
    parent_text = dataframe_csv_text(parent_ledger)
    summary_text_csv = dataframe_csv_text(cumulative_summary)
    history_text = dataframe_csv_text(run_history)

    state = {
        "schema_version": 1,
        "status": "PASS",
        "audit_only": True,
        "initialized_local": previous_state.get("initialized_local")
        if previous_state
        else now.isoformat(timespec="seconds"),
        "last_run_local": now.isoformat(timespec="seconds"),
        "last_run_id": run_id,
        "run_count": run_count,
        "cutoff_mt5_server_close": str(cutoff),
        "candidate_ids": CANDIDATE_IDS,
        "latest_m1_close": str(latest_m1_close),
        "cycle_state": cycle,
        "observation_state": observation_state(candidate_ledger),
        "candidate_total": int(len(candidate_ledger)),
        "unresolved_candidate_total": int(
            (
                candidate_ledger.get("resolution_state", pd.Series(dtype=str))
                == "UNRESOLVED"
            ).sum()
        ),
        "parent_event_total": int(len(parent_ledger)),
        "input_continuity": continuity,
        "ledger_hashes": {
            "monitor_candidate_ledger_csv_sha256": sha256_text(candidate_text),
            "monitor_parent_event_ledger_csv_sha256": sha256_text(parent_text),
            "monitor_candidate_summary_csv_sha256": sha256_text(summary_text_csv),
            "monitor_run_history_csv_sha256": sha256_text(history_text),
        },
        "policy": {
            "candidate_rules_frozen": True,
            "retuning": False,
            "historical_prefix_mutation": "FAIL_CLOSED",
            "duplicate_candidate_registration": "FORBIDDEN",
            "resolved_result_rewrite": "FORBIDDEN",
            "scheduled_task_installed": False,
            "new_exploration": False,
            "live_ready": False,
            "final_signal": False,
            "mt5_order": False,
            "discord": False,
            "ai_api": False,
            "live_hook": False,
            "automatic_promotion": False,
            "automatic_registration": False,
        },
    }

    backup_dir = backup_state(output_dir, run_id)
    snapshot_dir = output_dir / "snapshots" / run_id
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    atomic_write_text(output_dir / "monitor_candidate_ledger.csv", candidate_text)
    atomic_write_text(output_dir / "monitor_parent_event_ledger.csv", parent_text)
    atomic_write_text(output_dir / "monitor_candidate_summary.csv", summary_text_csv)
    atomic_write_text(output_dir / "monitor_run_history.csv", history_text)
    atomic_write_dataframe(output_dir / "monitor_new_candidates_latest.csv", new_candidates)
    atomic_write_dataframe(
        output_dir / "monitor_resolved_transitions_latest.csv", resolved_transitions
    )
    atomic_write_dataframe(output_dir / "monitor_new_parent_events_latest.csv", new_parent_events)
    atomic_write_dataframe(
        output_dir / "monitor_parent_admission_transitions_latest.csv",
        parent_admission_transitions,
    )
    atomic_write_text(output_dir / "monitor_state.json", json_text(state))
    atomic_write_text(output_dir / "input_provenance.json", json_text(provenance))

    latest_snapshot_summary = {
        "status": "PASS",
        "run_id": run_id,
        "cycle_state": cycle,
        "coverage": coverage,
        "new_candidate_count": int(len(new_candidates)),
        "resolved_transition_count": int(len(resolved_transitions)),
        "new_parent_event_count": int(len(new_parent_events)),
        "parent_admission_transition_count": int(len(parent_admission_transitions)),
        "candidate_summary": cumulative_summary.to_dict(orient="records"),
        "policy": state["policy"],
    }
    atomic_write_text(
        output_dir / "monitor_latest_snapshot_summary.json",
        json_text(latest_snapshot_summary),
    )
    atomic_write_text(
        output_dir / "LATEST_RUN_SUMMARY.txt",
        build_summary_text(
            run_id=run_id,
            cycle=cycle,
            cutoff=cutoff,
            previous_latest_m1_close=previous_latest_m1_close,
            latest_m1_close=latest_m1_close,
            candidates=candidate_ledger,
            parent_events=parent_ledger,
            summary=cumulative_summary,
            new_candidates=new_candidates,
            resolved_transitions=resolved_transitions,
            new_parent_events=new_parent_events,
            parent_admission_transitions=parent_admission_transitions,
            run_count=run_count,
            backup_dir=backup_dir,
        ),
    )
    atomic_write_text(output_dir / "MONITOR_RUN_ERROR.txt", "status=PASS\nerror=NONE\n")

    atomic_write_dataframe(snapshot_dir / "candidate_snapshot.csv", current_candidates)
    atomic_write_dataframe(snapshot_dir / "parent_event_snapshot.csv", current_parent_events)
    atomic_write_text(snapshot_dir / "input_provenance.json", json_text(provenance))
    atomic_write_text(snapshot_dir / "monitor_state_after_run.json", json_text(state))

    print("=" * 72)
    print("GOLD_ML_V1 STATEFUL PROSPECTIVE MONITOR - PASS")
    print(f"Cycle state: {cycle}")
    print(f"Latest closed M1: {latest_m1_close}")
    print(f"Cumulative candidates: {len(candidate_ledger)}")
    print(f"New candidates: {len(new_candidates)}")
    print(f"Resolved transitions: {len(resolved_transitions)}")
    print("No order, notification, exploration or automatic next phase was performed.")
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    try:
        return run_monitor(
            args.files_dir.resolve(),
            args.config.resolve(),
            output_dir,
        )
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        error = f"{type(exc).__name__}: {exc}"
        trace = traceback.format_exc()
        atomic_write_text(
            output_dir / "MONITOR_RUN_ERROR.txt",
            f"status=FAIL\nerror={error}\n\n{trace}",
        )
        atomic_write_text(
            output_dir / "LATEST_RUN_SUMMARY.txt",
            "GOLD_ML_V1 STATEFUL PROSPECTIVE MONITOR\n"
            "status=FAIL\n"
            f"error={error}\n"
            "Persisted candidate and parent ledgers were not intentionally rewritten by this failed cycle.\n",
        )
        print(f"[FAIL] {error}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
