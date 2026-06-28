from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from live_data import read_live_bars
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
    hydrate_state,
    latest_closed,
    processable_through,
    signatures,
)


def run_live_once(live_dir: Path, output_dir: Path) -> dict[str, Any]:
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
        before = signatures(live_dir)
        bars = read_live_bars(live_dir)
        after = signatures(live_dir)
        if before != after:
            raise DeferredRun(
                "INPUT_CHANGED_DURING_READ: retry on next BAT loop iteration"
            )

        state = load_state(state_path)
        registry = load_registry(registry_path)
        engine = LiveM1Engine(bars["M1"])
        latest_m15 = processable_through(bars["M15"], engine.latest_close)
        latest_h1 = processable_through(bars["H1"], engine.latest_close)

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
                "latest_closed": latest_closed(bars),
                "processable_through": {
                    "M15": latest_m15.strftime("%Y-%m-%d %H:%M:%S"),
                    "H1": latest_h1.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "hydration_proposal_counts": hydration_counts,
                "open_parent_positions": hydrated["open_parent_positions"],
                "b_state": state["b_state"],
                "new_candidate_count": 0,
                "controls": state["controls"],
            }
            append_jsonl(audit_jsonl, payload)
            atomic_write_text(
                latest_status_path,
                json.dumps(payload, ensure_ascii=False, indent=2),
            )
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
            "latest_closed": latest_closed(bars),
            "processable_through": {
                "M15": latest_m15.strftime("%Y-%m-%d %H:%M:%S"),
                "H1": latest_h1.strftime("%Y-%m-%d %H:%M:%S"),
            },
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
            "controls": state["controls"],
        }
        append_jsonl(audit_jsonl, payload)
        atomic_write_text(
            latest_status_path,
            json.dumps(payload, ensure_ascii=False, indent=2),
        )
        return payload
    finally:
        lock_path.unlink(missing_ok=True)
