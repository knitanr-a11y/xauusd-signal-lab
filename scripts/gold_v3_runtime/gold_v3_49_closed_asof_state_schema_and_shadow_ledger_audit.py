#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 49 closed-asof state schema and shadow ledger audit-only.

Freezes schema definitions for audit-only shadow state management. This does not
implement a shadow evaluator, does not emit live signals, and does not change the
Stage46/47 candidate pool or gate contract.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_BLOCKED_AUDIT_ONLY"
STAGE46_READY = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY"
STAGE47_READY = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_READY_AUDIT_ONLY"
STAGE48_READY = "GOLD_V3_48_CLOSED_ASOF_POOL_CONTRACT_LIVE_READINESS_GAP_REPORT_READY_AUDIT_ONLY"

REQUIRED_HV = ["HV_TP180_SL70_H128", "HV_TP200_SL80_H128", "HV_TP220_SL90_H128"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "46_closed_asof_stage45_pool_contract_freeze_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with GOLD V3 outputs")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage46-dir", default="")
    p.add_argument("--stage47-dir", default="")
    p.add_argument("--stage48-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def schema_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(artifact: str, field: str, dtype: str, required: bool, desc: str) -> None:
        rows.append({"artifact": artifact, "field": field, "dtype": dtype, "required": str(required).lower(), "description": desc})

    add("h4_closed_readiness_state", "state_time_jst", "datetime", True, "Audit state creation/update time")
    add("h4_closed_readiness_state", "latest_h4_open_time_jst", "datetime", True, "Latest H4 candle open time present in source CSV")
    add("h4_closed_readiness_state", "latest_h4_close_time_jst", "datetime", True, "Expected close time for latest H4 candle")
    add("h4_closed_readiness_state", "is_closed_safe", "bool", True, "Whether latest H4 row is safe under closed-asof contract")
    add("h4_closed_readiness_state", "source_file", "string", True, "H4 CSV source path")
    add("h4_closed_readiness_state", "source_row_hash", "string", True, "Hash of latest H4 row used for audit reproducibility")

    add("rolling_prior_60d_q70_state", "m15_time_jst", "datetime", True, "M15 decision time")
    add("rolling_prior_60d_q70_state", "lookback_start_jst", "datetime", True, "Prior 60D start exclusive/inclusive per implementation contract")
    add("rolling_prior_60d_q70_state", "lookback_end_jst", "datetime", True, "End before current M15 bar to prevent leakage")
    add("rolling_prior_60d_q70_state", "atr28_q70", "float", True, "Prior-only M15 ATR28 q70 threshold")
    add("rolling_prior_60d_q70_state", "m15_atr28", "float", True, "Current M15 ATR28 used only for comparison")
    add("rolling_prior_60d_q70_state", "high_vol_pass", "bool", True, "m15_atr28 >= prior q70")

    add("virtual_opportunity_ledger", "opportunity_id", "string", True, "Deterministic candidate opportunity id")
    add("virtual_opportunity_ledger", "m15_time_jst", "datetime", True, "M15 decision time")
    add("virtual_opportunity_ledger", "candidate_label", "string", True, "Base or HV candidate label")
    add("virtual_opportunity_ledger", "base_candidate_label", "string", True, "Original base candidate label")
    add("virtual_opportunity_ledger", "hv_sibling", "bool", True, "Whether opportunity is HV sibling")
    add("virtual_opportunity_ledger", "hv_profile", "string", False, "HV profile if hv_sibling=true")
    add("virtual_opportunity_ledger", "tp_usd", "float", True, "TP profile in USD")
    add("virtual_opportunity_ledger", "sl_usd", "float", True, "SL profile in USD")
    add("virtual_opportunity_ledger", "horizon_m5_bars", "int", True, "M5 adjudication horizon")
    add("virtual_opportunity_ledger", "source_rank", "int", True, "Stage45 source/rank priority")
    add("virtual_opportunity_ledger", "gate_evaluated", "bool", True, "Whether rolling gate was evaluated")
    add("virtual_opportunity_ledger", "gate_pass", "bool", True, "Whether gate passed at decision time")
    add("virtual_opportunity_ledger", "selected_after_rank_dedup", "bool", True, "Whether selected after rank-dedup")

    add("health_gate_state", "candidate_label", "string", True, "Candidate label")
    add("health_gate_state", "asof_m15_time_jst", "datetime", True, "Gate state as of decision time")
    add("health_gate_state", "window", "int", True, "Rolling health window, frozen at 30")
    add("health_gate_state", "min_history", "int", True, "Minimum history, frozen at 20")
    add("health_gate_state", "pf_threshold", "float", True, "PF threshold, frozen at 1.1")
    add("health_gate_state", "loss_streak_lt", "int", True, "Loss streak must be less than this, frozen at 3")
    add("health_gate_state", "history_count", "int", True, "Closed virtual results available before current opportunity")
    add("health_gate_state", "rolling_pf", "float", False, "Prior rolling PF")
    add("health_gate_state", "loss_streak", "int", True, "Prior consecutive losses")
    add("health_gate_state", "eligible", "bool", True, "Gate eligibility decision")

    add("rank_dedup_selection_ledger", "m15_time_jst", "datetime", True, "M15 decision time")
    add("rank_dedup_selection_ledger", "candidate_count_before_dedup", "int", True, "Number of passing candidates before dedup")
    add("rank_dedup_selection_ledger", "selected_candidate_label", "string", False, "Selected label after deterministic priority")
    add("rank_dedup_selection_ledger", "selected_opportunity_id", "string", False, "Selected opportunity id")
    add("rank_dedup_selection_ledger", "dedup_priority_rule", "string", True, "Frozen deterministic priority rule name")
    add("rank_dedup_selection_ledger", "no_signal_reason", "string", False, "Reason if nothing selected")

    add("pending_shadow_trade_ledger", "shadow_trade_id", "string", True, "Deterministic shadow trade id")
    add("pending_shadow_trade_ledger", "opportunity_id", "string", True, "Linked opportunity id")
    add("pending_shadow_trade_ledger", "entry_time_jst", "datetime", True, "Audit-only entry time")
    add("pending_shadow_trade_ledger", "direction", "string", True, "BUY/SELL if available from candidate")
    add("pending_shadow_trade_ledger", "entry_price", "float", True, "Audit-only entry price")
    add("pending_shadow_trade_ledger", "tp_price", "float", True, "Derived TP price")
    add("pending_shadow_trade_ledger", "sl_price", "float", True, "Derived SL price")
    add("pending_shadow_trade_ledger", "timeout_time_jst", "datetime", True, "M5 horizon timeout")
    add("pending_shadow_trade_ledger", "status", "string", True, "PENDING only for this ledger")

    add("closed_shadow_trade_ledger", "shadow_trade_id", "string", True, "Linked shadow trade id")
    add("closed_shadow_trade_ledger", "close_time_jst", "datetime", True, "Outcome time")
    add("closed_shadow_trade_ledger", "outcome", "string", True, "TP/SL/TIMEOUT")
    add("closed_shadow_trade_ledger", "result_usd", "float", True, "Audit-only result in USD")
    add("closed_shadow_trade_ledger", "same_bar_priority", "string", True, "SL priority when same M5 bar touches TP and SL")
    add("closed_shadow_trade_ledger", "adjudication_source", "string", True, "M5 CSV source and row range")

    add("replay_checkpoint_state", "checkpoint_time_utc", "datetime", True, "Checkpoint creation time")
    add("replay_checkpoint_state", "last_processed_m15_time_jst", "datetime", True, "Replay anchor")
    add("replay_checkpoint_state", "source_file_hashes_json", "json", True, "Hash map for source files")
    add("replay_checkpoint_state", "state_schema_version", "string", True, "Schema version")
    add("replay_checkpoint_state", "contract_version", "string", True, "Stage46/47 contract id")

    return rows


def manifest_rows() -> list[dict[str, str]]:
    return [
        {"artifact": "h4_closed_readiness_state", "file": "gold_v3_shadow_h4_closed_readiness_state.csv", "purpose": "confirm H4 closed-asof row readiness", "stage48_gap": "h4_closed_bar_availability"},
        {"artifact": "rolling_prior_60d_q70_state", "file": "gold_v3_shadow_rolling_prior_60d_q70_state.csv", "purpose": "persist prior-only high-vol threshold", "stage48_gap": "rolling_prior_60d_q70"},
        {"artifact": "virtual_opportunity_ledger", "file": "gold_v3_shadow_virtual_opportunity_ledger.csv", "purpose": "record every candidate opportunity for virtual monitoring", "stage48_gap": "virtual_monitoring_state"},
        {"artifact": "health_gate_state", "file": "gold_v3_shadow_health_gate_state.csv", "purpose": "persist per-candidate rolling health eligibility", "stage48_gap": "health_gate_rehydration"},
        {"artifact": "rank_dedup_selection_ledger", "file": "gold_v3_shadow_rank_dedup_selection_ledger.csv", "purpose": "record deterministic selection per M15 time", "stage48_gap": "rank_dedup_reproducibility"},
        {"artifact": "pending_shadow_trade_ledger", "file": "gold_v3_shadow_pending_trade_ledger.csv", "purpose": "track pending M5 TP/SL/timeout adjudication", "stage48_gap": "m15_m5_alignment"},
        {"artifact": "closed_shadow_trade_ledger", "file": "gold_v3_shadow_closed_trade_ledger.csv", "purpose": "record completed audit-only outcomes", "stage48_gap": "m5_tp_sl_horizon"},
        {"artifact": "replay_checkpoint_state", "file": "gold_v3_shadow_replay_checkpoint_state.csv", "purpose": "support deterministic restart/replay", "stage48_gap": "health_gate_rehydration"},
    ]


def transition_rows() -> list[dict[str, str]]:
    return [
        {"from_state": "new_m15_closed_bar", "to_state": "h4_closed_readiness_state", "trigger": "M15 decision time reached", "guard": "latest usable H4 row must be closed", "output": "h4_closed_readiness_state row"},
        {"from_state": "h4_closed_readiness_state", "to_state": "rolling_prior_60d_q70_state", "trigger": "H4 readiness pass", "guard": "use prior M15 bars only", "output": "q70 high-vol state row"},
        {"from_state": "rolling_prior_60d_q70_state", "to_state": "virtual_opportunity_ledger", "trigger": "candidate rules evaluated", "guard": "full candidate pool retained", "output": "all candidate opportunity rows"},
        {"from_state": "virtual_opportunity_ledger", "to_state": "health_gate_state", "trigger": "opportunity available", "guard": "use closed prior virtual results only", "output": "per-candidate eligibility row"},
        {"from_state": "health_gate_state", "to_state": "rank_dedup_selection_ledger", "trigger": "gate pass set known", "guard": "deterministic rank priority", "output": "selected/no-signal row"},
        {"from_state": "rank_dedup_selection_ledger", "to_state": "pending_shadow_trade_ledger", "trigger": "candidate selected", "guard": "audit-only, no order", "output": "pending shadow trade row"},
        {"from_state": "pending_shadow_trade_ledger", "to_state": "closed_shadow_trade_ledger", "trigger": "M5 TP/SL/timeout known", "guard": "same-bar SL priority", "output": "closed shadow trade outcome"},
        {"from_state": "closed_shadow_trade_ledger", "to_state": "health_gate_state", "trigger": "virtual result closed", "guard": "all candidates update virtual monitoring", "output": "next gate state input"},
        {"from_state": "any", "to_state": "replay_checkpoint_state", "trigger": "end of run or checkpoint interval", "guard": "source file hashes captured", "output": "restart/replay checkpoint"},
    ]


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    s46 = Path(a.stage46_dir).expanduser().resolve() if a.stage46_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "46_closed_asof_stage45_pool_contract_freeze_audit_only"
    s47 = Path(a.stage47_dir).expanduser().resolve() if a.stage47_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "47_closed_asof_pool_contract_forward_audit_only"
    s48 = Path(a.stage48_dir).expanduser().resolve() if a.stage48_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "48_closed_asof_pool_contract_live_readiness_gap_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "49_closed_asof_state_schema_and_shadow_ledger_audit_only"
    tmpl_dir = out / "gold_v3_49_empty_schema_templates"
    out.mkdir(parents=True, exist_ok=True)
    tmpl_dir.mkdir(parents=True, exist_ok=True)

    p46 = s46 / "gold_v3_46_closed_asof_stage45_pool_contract.json"
    p47 = s47 / "gold_v3_47_forward_audit_summary.json"
    p48 = s48 / "gold_v3_48_live_readiness_gap_summary.json"

    val: list[dict[str, Any]] = []
    val.append(ok("stage46_contract_present", p46.exists(), str(p46), "exists"))
    val.append(ok("stage47_forward_summary_present", p47.exists(), str(p47), "exists"))
    val.append(ok("stage48_gap_summary_present", p48.exists(), str(p48), "exists"))

    j46: dict[str, Any] = read_json(p46) if p46.exists() else {}
    j47: dict[str, Any] = read_json(p47) if p47.exists() else {}
    j48: dict[str, Any] = read_json(p48) if p48.exists() else {}

    if j46:
        frozen = j46.get("frozen_contract", {})
        val.append(ok("stage46_status_ready", j46.get("status") == STAGE46_READY, j46.get("status"), STAGE46_READY))
        val.append(ok("stage46_closed_asof", frozen.get("htf_asof") == "closed", frozen.get("htf_asof"), "closed"))
        val.append(ok("stage46_open_asof_disallowed", frozen.get("open_asof_allowed") is False, frozen.get("open_asof_allowed"), False))
        val.append(ok("stage46_no_manual_pool_mutation", "no_manual" in str(frozen.get("candidate_pool_policy", "")), frozen.get("candidate_pool_policy", ""), "no_manual..."))
        hv = list(frozen.get("hv_profiles_retained", []))
        for prof in REQUIRED_HV:
            val.append(ok(f"stage46_retains_{prof}", prof in hv, prof if prof in hv else "missing", prof))
    if j47:
        val.append(ok("stage47_status_ready", j47.get("status") == STAGE47_READY, j47.get("status"), STAGE47_READY))
        val.append(ok("stage47_contract_reused", j47.get("contract_reused_without_candidate_changes") is True, j47.get("contract_reused_without_candidate_changes"), True))
        val.append(ok("stage47_no_manual_demotion", j47.get("manual_candidate_demotion_or_removal") is False, j47.get("manual_candidate_demotion_or_removal"), False))
    if j48:
        val.append(ok("stage48_report_ready", j48.get("status") == STAGE48_READY, j48.get("status"), STAGE48_READY))
        val.append(ok("stage48_contract_not_mutated", j48.get("contract_mutated") is False, j48.get("contract_mutated"), False))
        val.append(ok("stage48_no_manual_demotion", j48.get("manual_candidate_demotion_or_removal") is False, j48.get("manual_candidate_demotion_or_removal"), False))
        val.append(ok("stage48_open_asof_disallowed", j48.get("open_asof_allowed") is False, j48.get("open_asof_allowed"), False))
        for flag in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "signals_generated", "final_signal_enabled"]:
            val.append(ok(f"stage48_safety_{flag}_false", j48.get(flag) is False, j48.get(flag), False))

    schema_df = pd.DataFrame(schema_rows())
    manifest_df = pd.DataFrame(manifest_rows())
    transition_df = pd.DataFrame(transition_rows())

    schema_df.to_csv(out / "gold_v3_49_shadow_ledger_schema.csv", index=False, encoding="utf-8-sig")
    manifest_df.to_csv(out / "gold_v3_49_state_artifact_manifest.csv", index=False, encoding="utf-8-sig")
    transition_df.to_csv(out / "gold_v3_49_state_transition_matrix.csv", index=False, encoding="utf-8-sig")

    # Empty templates with schema columns.
    for artifact, sub in schema_df.groupby("artifact", sort=False):
        cols = sub["field"].tolist()
        pd.DataFrame(columns=cols).to_csv(tmpl_dir / f"{artifact}.csv", index=False, encoding="utf-8-sig")

    val.append(ok("schema_artifact_count", len(manifest_df) == 8, len(manifest_df), 8, "BLOCKER"))
    val.append(ok("schema_field_count_nonzero", len(schema_df) > 0, len(schema_df), ">0", "BLOCKER"))
    val.append(ok("transition_count_nonzero", len(transition_df) > 0, len(transition_df), ">0", "BLOCKER"))
    for artifact in manifest_df["artifact"].tolist():
        val.append(ok(f"template_created_{artifact}", (tmpl_dir / f"{artifact}.csv").exists(), str(tmpl_dir / f"{artifact}.csv"), "exists", "BLOCKER"))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_49_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(cdir),
        "stage46_dir": str(s46),
        "stage47_dir": str(s47),
        "stage48_dir": str(s48),
        "output_dir": str(out),
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "live_ready": False,
        "schema_ready": failed.empty,
        "artifact_count": int(len(manifest_df)),
        "schema_field_count": int(len(schema_df)),
        "transition_count": int(len(transition_df)),
        "template_dir": str(tmpl_dir),
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_49_state_schema_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 49 PASTE_ME_STATE_SCHEMA_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("schema_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"artifact_count: {len(manifest_df)}")
    paste.append(f"schema_field_count: {len(schema_df)}")
    paste.append(f"transition_count: {len(transition_df)}")
    paste.append("")
    paste.append("STATE_ARTIFACT_MANIFEST")
    paste.append(manifest_df.to_string(index=False))
    paste.append("")
    paste.append("STATE_TRANSITION_MATRIX")
    paste.append(transition_df.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    (out / "gold_v3_49_PASTE_ME_STATE_SCHEMA_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 49 closed-asof state schema and shadow ledger audit-only report

Status: `{status}`

## Meaning

State schemas and empty templates are frozen for future audit-only shadow evaluator stages.
This does not implement live trading.

## Summary

- schema_ready: `{failed.empty}`
- live_ready: `false`
- contract_mutated: `false`
- manual_candidate_demotion_or_removal: `false`
- artifact_count: `{len(manifest_df)}`
- schema_field_count: `{len(schema_df)}`
- transition_count: `{len(transition_df)}`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, or final signal.
"""
    (out / "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_49_PASTE_ME_STATE_SCHEMA_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
