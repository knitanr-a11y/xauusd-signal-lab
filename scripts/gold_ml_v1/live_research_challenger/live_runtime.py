from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from live_data import probe_latest_bars, read_live_bars
from live_position import LiveM1Engine
from live_proposals_h1 import bstate_proposals
from live_proposals_m15 import acore_proposals, p18_proposals, w024_proposals
from live_admission import process_component
from live_store import (
    DeferredRun,
    append_jsonl,
    atomic_write_csv,
    atomic_write_text,
    json_value,
    load_registry,
    load_state,
    merge_registry,
    position_from_state,
    position_to_state,
)
from live_runtime_base import (
    acquire_lock,
    earliest_m1_needed,
    has_open_position,
    hydrate_state,
    latest_closed_from_probe,
    observed_times,
    processable_through,
    ready_source_times,
    signatures,
)


def _write_status(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def run_live_once(live_dir: Path, output_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "live_state.json"
    registry_path = output_dir / "live_candidates.csv"
    candidate_jsonl = output_dir / "live_candidates.jsonl"
    audit_jsonl = output_dir / "live_audit.jsonl"
    latest_status_path = output_dir / "latest_status.json"
    lock_path = output_dir / "live_once.lock"

    acquire_lock(lock_path)
    run_id = uuid.uuid4().hex
    now = pd.Timestamp.now().floor("s")
    now_text = now.strftime("%Y-%m-%d %H:%M:%S")

    try:
        state = load_state(state_path)
        before = signatures(live_dir)
        if state is not None and state.get("input_signatures") == before:
            return {
                "run_id": run_id,
                "status": "IDLE_NO_CHANGE",
                "time": now_text,
                "live_dir": str(live_dir),
                "new_candidate_count": 0,
                "processing_mode": "signature_only",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "controls": state["controls"],
            }

        probe = probe_latest_bars(live_dir)
        after_probe = signatures(live_dir)
        if before != after_probe:
            raise DeferredRun(
                "INPUT_CHANGED_DURING_PROBE: retry on next BAT loop iteration"
            )

        ready_m15_hint, ready_h1_hint, waiting = ready_source_times(probe)
        if state is not None:
            last_m15 = pd.Timestamp(state["last_processed"]["M15"])
            last_h1 = pd.Timestamp(state["last_processed"]["H1"])
            if ready_m15_hint < last_m15 or ready_h1_hint < last_h1:
                raise ValueError(
                    "Synchronized source time regressed behind live_state cursor"
                )
            source_advanced = ready_m15_hint > last_m15 or ready_h1_hint > last_h1
            last_observed_m1 = state.get("last_observed_times", {}).get("M1", {}).get("close")
            m1_advanced = last_observed_m1 is None or probe["M1"]["close"] > pd.Timestamp(last_observed_m1)
            position_needs_update = has_open_position(state) and m1_advanced

            if not source_advanced and not position_needs_update:
                state["input_signatures"] = after_probe
                state["last_observed_times"] = observed_times(probe)
                state["live_dir"] = str(live_dir)
                state["last_successful_run"] = now_text
                atomic_write_text(
                    state_path,
                    json.dumps(state, ensure_ascii=False, indent=2),
                )
                status = "WAITING_FOR_TIMEFRAME_SYNC" if waiting else "IDLE_NO_RELEVANT_BAR"
                payload = {
                    "run_id": run_id,
                    "status": status,
                    "time": now_text,
                    "live_dir": str(live_dir),
                    "latest_closed": latest_closed_from_probe(probe),
                    "processable_through": {
                        "M15": ready_m15_hint.strftime("%Y-%m-%d %H:%M:%S"),
                        "H1": ready_h1_hint.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                    "waiting_for": waiting,
                    "new_candidate_count": 0,
                    "processing_mode": "tail_probe_only",
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "controls": state["controls"],
                }
                append_jsonl(audit_jsonl, payload)
                _write_status(latest_status_path, payload)
                return payload

        m1_since = earliest_m1_needed(state, ready_m15_hint, ready_h1_hint)
        bars = read_live_bars(
            live_dir,
            m1_since=m1_since,
            latest_probe=probe,
        )
        after = signatures(live_dir)
        if after_probe != after:
            raise DeferredRun(
                "INPUT_CHANGED_DURING_READ: retry on next BAT loop iteration"
            )

        registry = load_registry(registry_path)
        engine = LiveM1Engine(bars["M1"])
        latest_m15 = processable_through(bars["M15"], ready_m15_hint)
        latest_h1 = processable_through(bars["H1"], ready_h1_hint)

        if state is None:
            if not registry.empty:
                raise ValueError(
                    "live_state.json is missing while live_candidates.csv already has rows"
                )
            hydrated, hydration_counts = hydrate_state(
                bars,
                engine,
                latest_m15,
                latest_h1,
                now_text,
            )
            state = {
                "schema_version": 1,
                "activation_time": max(latest_m15, latest_h1).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "last_processed": {
                    "M15": latest_m15.strftime("%Y-%m-%d %H:%M:%S"),
                    "H1": latest_h1.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "b_state": {
                    "pending_reentry_due": hydrated["pending_reentry_due"],
                    "pending_origin": hydrated["pending_origin"],
                },
                "open_parent_positions": hydrated["open_parent_positions"],
                "input_signatures": after,
                "last_observed_times": observed_times(probe),
                "live_dir": str(live_dir),
                "controls": {
                    "audit_only": True,
                    "final_signal": False,
                    "discord": False,
                    "mt5_order": False,
                    "p16_live": False,
                    "p19_live": False,
                },
            }
            atomic_write_csv(registry_path, registry)
            atomic_write_text(
                state_path,
                json.dumps(state, ensure_ascii=False, indent=2),
            )
            payload = {
                "run_id": run_id,
                "status": "INITIALIZED_NO_BACKFILL",
                "time": now_text,
                "live_dir": str(live_dir),
                "latest_closed": latest_closed_from_probe(probe),
                "processable_through": {
                    "M15": latest_m15.strftime("%Y-%m-%d %H:%M:%S"),
                    "H1": latest_h1.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "waiting_for": waiting,
                "hydration_proposal_counts": hydration_counts,
                "open_parent_positions": hydrated["open_parent_positions"],
                "b_state": state["b_state"],
                "new_candidate_count": 0,
                "processing_mode": "full_initialization_tail_m1",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "controls": state["controls"],
            }
            append_jsonl(audit_jsonl, payload)
            _write_status(latest_status_path, payload)
            return payload

        last_m15 = pd.Timestamp(state["last_processed"]["M15"])
        last_h1 = pd.Timestamp(state["last_processed"]["H1"])
        due = (
            pd.Timestamp(state["b_state"]["pending_reentry_due"])
            if state["b_state"].get("pending_reentry_due")
            else None
        )
        origin = (
            pd.Timestamp(state["b_state"]["pending_origin"])
            if state["b_state"].get("pending_origin")
            else None
        )

        proposals = {
            "A_CORE": acore_proposals(bars, last_m15),
            "P18": p18_proposals(bars, last_m15),
            "W024A": w024_proposals(bars, last_m15),
        }
        for comp in ("A_CORE", "P18", "W024A"):
            proposals[comp] = proposals[comp][
                proposals[comp]["bar_close_time"] <= latest_m15
            ].copy()
        proposals["B_STATE"], due, origin = bstate_proposals(
            bars,
            last_h1,
            latest_h1,
            due,
            origin,
        )

        all_new: list[dict[str, Any]] = []
        all_updates: list[dict[str, Any]] = []
        all_audits: list[dict[str, Any]] = []
        new_positions: dict[str, Any] = {}
        for comp in ("A_CORE", "B_STATE", "P18", "W024A"):
            prior = position_from_state(
                state["open_parent_positions"].get(comp)
            )
            new_records, updates, active, audits = process_component(
                comp,
                proposals[comp],
                prior,
                engine,
                now_text,
            )
            all_new.extend(new_records)
            all_updates.extend(updates)
            all_audits.extend(audits)
            new_positions[comp] = position_to_state(active)

        merged, new = merge_registry(registry, all_new, all_updates)
        atomic_write_csv(registry_path, merged)
        for record in new.to_dict(orient="records"):
            append_jsonl(
                candidate_jsonl,
                {key: json_value(value) for key, value in record.items()},
            )

        state["last_processed"] = {
            "M15": latest_m15.strftime("%Y-%m-%d %H:%M:%S"),
            "H1": latest_h1.strftime("%Y-%m-%d %H:%M:%S"),
        }
        state["b_state"] = {
            "pending_reentry_due": json_value(due),
            "pending_origin": json_value(origin),
        }
        state["open_parent_positions"] = new_positions
        state["input_signatures"] = after
        state["last_observed_times"] = observed_times(probe)
        state["live_dir"] = str(live_dir)
        state["last_successful_run"] = now_text
        atomic_write_text(
            state_path,
            json.dumps(state, ensure_ascii=False, indent=2),
        )

        payload = {
            "run_id": run_id,
            "status": "PASS",
            "time": now_text,
            "live_dir": str(live_dir),
            "latest_closed": latest_closed_from_probe(probe),
            "processable_through": {
                "M15": latest_m15.strftime("%Y-%m-%d %H:%M:%S"),
                "H1": latest_h1.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "waiting_for": waiting,
            "proposal_counts": {
                comp: int(len(frame)) for comp, frame in proposals.items()
            },
            "new_candidate_count": int(len(new)),
            "new_candidate_keys": (
                new["candidate_key"].tolist() if not new.empty else []
            ),
            "registry_rows": int(len(merged)),
            "open_parent_positions": new_positions,
            "b_state": state["b_state"],
            "admission_audit": all_audits,
            "processing_mode": "full_rules_tail_m1",
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "controls": state["controls"],
        }
        append_jsonl(audit_jsonl, payload)
        _write_status(latest_status_path, payload)
        return payload
    finally:
        lock_path.unlink(missing_ok=True)
