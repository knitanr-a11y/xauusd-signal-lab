from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import m10w26_runtime as base
from m10w26_runtime import *

RUNTIME_VERSION = "M10W26_RUNTIME_V2_PRESTART_CAUSAL_ENGINE_AUDITED"
base.RUNTIME_VERSION = RUNTIME_VERSION


def initialize(snapshot_root: Path, point: float) -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    paths = base.runtime_paths(local_root)
    contract = base.load_json(base.CONTRACT)
    base.validate_contract(contract)
    if paths["lock"].exists():
        raise base.M10W26Error("M10W26 loop lock exists; stop loop before initialization")
    if paths["runtime"].exists() or paths["state"].exists() or paths["receipt"].exists():
        raise base.M10W26Error("M10W26 runtime already exists; reinitialize/reset is forbidden")

    snapshot = base.snapshot_info(snapshot_root)
    start = base.parse_time(str(snapshot["M1"]["last_server_open"]))
    bars = base.load_bars(snapshot_root)
    candidates, decisions, diagnostics = base.build_candidates(bars, start)
    if decisions or candidates:
        raise base.M10W26Error(
            f"prestart dry run unexpectedly produced post-start rows: decisions={len(decisions)} candidates={len(candidates)}"
        )
    short_diagnostics = diagnostics.get("short_family", {})
    if int(short_diagnostics.get("source_timing_violation_count", -1)) != 0:
        raise base.M10W26Error("prestart short-family causal source timing audit failed")
    long_diagnostics = diagnostics.get("long_family", {})
    expected_long = {"LONG_M5_S1", "LONG_M15_S2", "LONG_H1_S3", "LONG_H4_S4"}
    if set(long_diagnostics) != expected_long:
        raise base.M10W26Error(f"prestart long-family audit incomplete: {sorted(long_diagnostics)}")
    for family, row in long_diagnostics.items():
        if row.get("future_exit_reference") is not False or row.get("completed_pair_required") is not False:
            raise base.M10W26Error(f"unsafe causal long diagnostic: {family}")

    result = base.initialize(snapshot_root, point)
    if result != 0:
        return result
    audit_path = paths["directory"] / "m10w26_prestart_causal_engine_audit.json"
    payload: dict[str, Any] = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": base.STAGE,
        "status": "PASS_PRESTART_CAUSAL_ENGINE_AUDIT",
        "prospective_start_server_time": base.fmt_time(start),
        "runtime_contract_version": RUNTIME_VERSION,
        "private_snapshot": snapshot,
        "long_family_diagnostics": long_diagnostics,
        "short_family_diagnostics": short_diagnostics,
        "post_start_decision_count_in_dry_run": 0,
        "post_start_candidate_count_in_dry_run": 0,
        "formula_change": False,
        "threshold_change": False,
        "future_reference": False,
        "runtime_or_existing_start_modified_by_audit": False,
        "discord_send": False,
        "mt5_order": False,
    }
    base.atomic_json(audit_path, payload)
    print("[M10W26 PRESTART ENGINE PASS] six causal coverage families verified before start freeze")
    return 0


def once(snapshot_root: Path, point: float) -> int:
    base.RUNTIME_VERSION = RUNTIME_VERSION
    return base.once(snapshot_root, point)
