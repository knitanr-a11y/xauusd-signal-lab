from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import m10w26_runtime as base
from m10w26_runtime import *

RUNTIME_VERSION = "M10W26_RUNTIME_V2_PRESTART_CAUSAL_ENGINE_AUDITED"
base.RUNTIME_VERSION = RUNTIME_VERSION


def implementation_paths() -> dict[str, Path]:
    return {
        "m10w26_runtime_base": base.THIS,
        "m10w26_runtime_v2": Path(__file__).resolve(),
        "m10w26_operator_base": base.MR / "m10w26" / "python" / "run_m10w26_private_snapshot.py",
        "m10w26_operator_v2": base.MR / "m10w26" / "python" / "run_m10w26_private_snapshot_v2.py",
        "m10w22_feature_core": base.MR / "m10w22" / "python" / "run_high_atr_bullish_new_causal_information_availability_audit.py",
        "m10w25_coverage_core": base.MR / "m10w25" / "python" / "run_m10w25_neither_prefix_causal_live_parity_audit.py",
        "m10w13_short_core": base.MR / "m10w13" / "python" / "run_m10w13_frozen_historical_short_activation_interval_calibration.py",
        "m10a_frozen_core": base.MR / "m10a" / "python" / "frozen_core.py",
        "m10a_payoff_rules": base.MR / "m10a" / "python" / "payoff_rules.py",
        "bounded_csv_adapter": base.MR / "common" / "python" / "bounded_csv_source_adapter.py",
        "bounded_csv_integrity": base.MR / "common" / "python" / "bounded_csv_journal_integrity.py",
    }


def implementation_sha256s() -> dict[str, str]:
    output: dict[str, str] = {}
    for name, path in implementation_paths().items():
        if not path.is_file():
            raise base.M10W26Error(f"required frozen implementation missing: {name}: {path}")
        output[name] = base.adapter.sha256_file(path)
    return output


def verify_implementation_freeze(runtime_payload: dict[str, Any]) -> None:
    expected = runtime_payload.get("implementation_sha256")
    if not isinstance(expected, dict) or set(expected) != set(implementation_paths()):
        raise base.M10W26Error("M10W26 frozen implementation inventory missing or changed")
    current = implementation_sha256s()
    if current != expected:
        changed = sorted(name for name in current if current.get(name) != expected.get(name))
        raise base.M10W26Error(f"M10W26 implementation changed after start freeze: {changed}")


def initialize(snapshot_root: Path, point: float) -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    paths = base.runtime_paths(local_root)
    contract = base.load_json(base.CONTRACT)
    base.validate_contract(contract)
    if paths["lock"].exists():
        raise base.M10W26Error("M10W26 loop lock exists; stop loop before initialization")
    protected = (paths["runtime"], paths["state"], paths["receipt"])
    if any(path.exists() for path in protected):
        raise base.M10W26Error("M10W26 runtime already exists; reinitialize/reset is forbidden")

    frozen_implementation = implementation_sha256s()
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

    audit_path = paths["directory"] / "m10w26_prestart_causal_engine_audit.json"
    payload: dict[str, Any] = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": base.STAGE,
        "status": "PASS_PRESTART_CAUSAL_ENGINE_AUDIT_START_NOT_YET_FROZEN",
        "prospective_start_candidate_server_time": base.fmt_time(start),
        "runtime_contract_version": RUNTIME_VERSION,
        "implementation_sha256": frozen_implementation,
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

    original_atomic = base.atomic_json

    def atomic_with_implementation(path: Path, value: Any) -> None:
        if path == paths["runtime"]:
            if not isinstance(value, dict):
                raise base.M10W26Error("runtime payload must be an object")
            value = dict(value)
            value["implementation_sha256"] = frozen_implementation
            value["prestart_causal_engine_audit"] = str(audit_path)
        original_atomic(path, value)

    base.atomic_json = atomic_with_implementation
    try:
        result = base.initialize(snapshot_root, point)
    except Exception:
        for path in protected:
            path.unlink(missing_ok=True)
        raise
    finally:
        base.atomic_json = original_atomic
    if result != 0 or not all(path.is_file() for path in protected):
        for path in protected:
            path.unlink(missing_ok=True)
        raise base.M10W26Error("M10W26 initialization did not produce a complete runtime transaction")
    runtime_payload = base.load_json(paths["runtime"])
    verify_implementation_freeze(runtime_payload)
    return 0


def once(snapshot_root: Path, point: float) -> int:
    base.RUNTIME_VERSION = RUNTIME_VERSION
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    runtime_payload = base.load_json(base.runtime_paths(local_root)["runtime"])
    verify_implementation_freeze(runtime_payload)
    return base.once(snapshot_root, point)
