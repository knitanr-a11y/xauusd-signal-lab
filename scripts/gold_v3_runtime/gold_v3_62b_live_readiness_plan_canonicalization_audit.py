#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 62B live-readiness plan canonicalization audit-only.

Canonicalizes Stage62 plan into official 8-stage order and reference gap rows.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_62B_LIVE_READINESS_PLAN_CANONICALIZATION_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_62B_LIVE_READINESS_PLAN_CANONICALIZATION_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_62B_LIVE_READINESS_PLAN_CANONICALIZATION_BLOCKED_AUDIT_ONLY"
STAGE62_READY = "GOLD_V3_62_LIVE_READINESS_IMPLEMENTATION_PLANNING_READY_AUDIT_ONLY"

CANONICAL = [
    {
        "canonical_order": 1,
        "implementation_stage": "GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_AUDIT_ONLY",
        "source_gap_id": "live_input/h4_closed_bar_availability",
        "component": "live_input",
        "purpose": "Build closed H4 state from candle files only.",
        "input_artifacts": "goldsharp_h4.csv; Stage50 H4 closed state; Stage61 package",
        "planned_outputs": "h4_closed_live_state.csv; validation_matrix.csv; paste_me_summary.txt",
        "stop_conditions": "H4 file missing; last closed H4 cannot be determined; open H4 required; safety flag true",
    },
    {
        "canonical_order": 2,
        "implementation_stage": "GOLD_V3_64_M15_M5_ALIGNMENT_STATE_BUILDER_AUDIT_ONLY",
        "source_gap_id": "live_input/m15_m5_alignment",
        "component": "live_input",
        "purpose": "Align closed M15 opportunities with M5 adjudication windows.",
        "input_artifacts": "goldsharp_m15.csv; goldsharp_m5.csv; Stage51/53 ledgers",
        "planned_outputs": "m15_m5_alignment_state.csv; validation_matrix.csv; paste_me_summary.txt",
        "stop_conditions": "M15/M5 file missing; non-monotonic timestamps; insufficient M5 horizon; safety flag true",
    },
    {
        "canonical_order": 3,
        "implementation_stage": "GOLD_V3_65_ROLLING_PRIOR_60D_Q70_STATE_AUDIT_ONLY",
        "source_gap_id": "feature/rolling_prior_60d_q70",
        "component": "feature",
        "purpose": "Persist rolling prior-60D Q70 high-vol state.",
        "input_artifacts": "Stage50 Q70 state; closed M15/H4 candles",
        "planned_outputs": "rolling_prior_60d_q70_state.csv; validation_matrix.csv; paste_me_summary.txt",
        "stop_conditions": "insufficient lookback; open-asof required; mismatch with Stage50 anchor; safety flag true",
    },
    {
        "canonical_order": 4,
        "implementation_stage": "GOLD_V3_66_VIRTUAL_MONITORING_STATE_AUDIT_ONLY",
        "source_gap_id": "gate/virtual_monitoring_state",
        "component": "gate",
        "purpose": "Maintain virtual candidate monitoring without live orders.",
        "input_artifacts": "Stage51 virtual opportunity ledger; Stage46 contract; closed candles",
        "planned_outputs": "virtual_monitoring_state.csv; validation_matrix.csv; paste_me_summary.txt",
        "stop_conditions": "candidate contract missing; virtual opportunity parity mismatch; safety flag true",
    },
    {
        "canonical_order": 5,
        "implementation_stage": "GOLD_V3_67_HEALTH_GATE_REHYDRATION_AUDIT_ONLY",
        "source_gap_id": "gate/health_gate_rehydration",
        "component": "gate",
        "purpose": "Rehydrate rolling PF/loss-streak health gate state from virtual monitoring.",
        "input_artifacts": "Stage52 health gate state; virtual monitoring state",
        "planned_outputs": "health_gate_rehydrated_state.csv; validation_matrix.csv; paste_me_summary.txt",
        "stop_conditions": "min history unavailable; PF/loss-streak mismatch; manual candidate removal attempted; safety flag true",
    },
    {
        "canonical_order": 6,
        "implementation_stage": "GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_AUDIT_ONLY",
        "source_gap_id": "selection/rank_dedup_reproducibility",
        "component": "selection",
        "purpose": "Reproduce Stage52 rank-dedup selection audit-only.",
        "input_artifacts": "Stage52 selection ledger; health gate rehydrated state; Stage46 contract",
        "planned_outputs": "rank_dedup_selection_repro.csv; validation_matrix.csv; paste_me_summary.txt",
        "stop_conditions": "selection parity mismatch; duplicate conflict unresolved; safety flag true",
    },
    {
        "canonical_order": 7,
        "implementation_stage": "GOLD_V3_69_M5_TP_SL_HORIZON_ADJUDICATION_PARITY_AUDIT_ONLY",
        "source_gap_id": "adjudication/m5_tp_sl_horizon",
        "component": "adjudication",
        "purpose": "Reproduce Stage53 M5 TP/SL/horizon adjudication parity.",
        "input_artifacts": "Stage53 closed shadow ledger; goldsharp_m5.csv; selection repro ledger",
        "planned_outputs": "m5_adjudication_parity.csv; validation_matrix.csv; paste_me_summary.txt",
        "stop_conditions": "M5 horizon unavailable; same-bar SL priority mismatch; adjudication parity mismatch; safety flag true",
    },
    {
        "canonical_order": 8,
        "implementation_stage": "GOLD_V3_70_END_TO_END_SHADOW_LIVE_READINESS_REPLAY_AUDIT_ONLY",
        "source_gap_id": "shadow_live/e2e_replay",
        "component": "shadow_live",
        "purpose": "Run end-to-end audit-only replay of the live-readiness state chain without live execution.",
        "input_artifacts": "Stage63-69 outputs; Stage61 package; Stage60 prefix hash verification",
        "planned_outputs": "e2e_shadow_live_readiness_replay.csv; validation_matrix.csv; paste_me_summary.txt",
        "stop_conditions": "any upstream state blocked; any live flag true; final signal requested; safety flag true",
    },
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "62_live_readiness_implementation_planning_audit_only").exists():
            return d
    raise FileNotFoundError("Stage62 output directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage62-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s62 = Path(a.stage62_dir).expanduser().resolve() if a.stage62_dir else g / "62_live_readiness_implementation_planning_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "62b_live_readiness_plan_canonicalization_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p62s = s62 / "gold_v3_62_live_readiness_planning_summary.json"
    p62p = s62 / "gold_v3_62_gap_to_plan_matrix.csv"
    p62o = s62 / "gold_v3_62_stage_order_plan.csv"
    p62lock = s62 / "gold_v3_62_safety_lockout_matrix.csv"

    val: list[dict[str, Any]] = []
    for name, p in [("stage62_summary", p62s), ("stage62_gap_to_plan", p62p), ("stage62_order_plan", p62o), ("stage62_safety_lockout", p62lock)]:
        val.append(ok(f"{name}_present", p.exists(), str(p), "exists"))
    if any(v["result"] != "PASS" for v in val):
        pd.DataFrame(val).to_csv(out / "gold_v3_62b_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j62 = read_json(p62s)
    val.append(ok("stage62_status_ready", j62.get("status") == STAGE62_READY, j62.get("status"), STAGE62_READY))
    val.append(ok("stage62_planning_ready", j62.get("live_readiness_planning_ready") is True, j62.get("live_readiness_planning_ready"), True))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage62_{key}_false", j62.get(key) is False, j62.get(key), False))

    raw_plan = pd.read_csv(p62p, encoding="utf-8-sig")
    reference = raw_plan[raw_plan.get("implementation_stage_candidate", "").astype(str).str.contains("GOLD_V3_XX_ADDITIONAL", na=False)].copy()
    if reference.empty:
        # If Stage62 wording changes, treat any non-canonical source_gap_id as reference.
        canon_ids = {r["source_gap_id"] for r in CANONICAL}
        reference = raw_plan[~raw_plan["source_gap_id"].astype(str).isin(canon_ids)].copy()
    reference["reference_only"] = True
    reference["canonical_handling"] = "retained_for_traceability_not_official_order"
    reference.to_csv(out / "gold_v3_62b_reference_gap_rows.csv", index=False, encoding="utf-8-sig")

    canonical = pd.DataFrame(CANONICAL)
    for c in ["live_enablement_allowed", "mt5_execution_allowed", "discord_live_allowed", "final_signal_allowed"]:
        canonical[c] = False
    canonical.to_csv(out / "gold_v3_62b_canonical_stage_order_plan.csv", index=False, encoding="utf-8-sig")

    safety = pd.DataFrame([
        {"lockout": "audit_only", "value": True, "scope": "global_invariant", "reason": "GOLD V3 remains audit-only"},
        {"lockout": "live_allowed", "value": False, "scope": "global_invariant", "reason": "no live approval"},
        {"lockout": "mt5_execution_enabled", "value": False, "scope": "global_invariant", "reason": "no MT5 order BAT"},
        {"lockout": "discord_live_enabled", "value": False, "scope": "global_invariant", "reason": "no live notifications"},
        {"lockout": "ai_api_called", "value": False, "scope": "global_invariant", "reason": "no AI API"},
        {"lockout": "final_signal_enabled", "value": False, "scope": "global_invariant", "reason": "no final signal"},
        {"lockout": "live_hook_enabled", "value": False, "scope": "global_invariant", "reason": "no live hook"},
        {"lockout": "candidate_pool_mutation", "value": False, "scope": "global_invariant", "reason": "pool remains frozen"},
        {"lockout": "manual_candidate_demotion_or_removal", "value": False, "scope": "global_invariant", "reason": "HV/base candidates not manually removed"},
        {"lockout": "open_asof_allowed", "value": False, "scope": "global_invariant", "reason": "closed-asof only"},
    ])
    safety.to_csv(out / "gold_v3_62b_safety_lockout_matrix.csv", index=False, encoding="utf-8-sig")

    val.append(ok("canonical_plan_exactly_8_rows", len(canonical) == 8, len(canonical), 8))
    val.append(ok("canonical_has_no_xx_additional_rows", not canonical["implementation_stage"].astype(str).str.contains("GOLD_V3_XX_ADDITIONAL", na=False).any(), "none", "none"))
    val.append(ok("stage63_is_h4_closed_builder", canonical.iloc[0]["implementation_stage"] == "GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_AUDIT_ONLY", canonical.iloc[0]["implementation_stage"], "GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_AUDIT_ONLY"))
    val.append(ok("reference_rows_separated", len(reference) > 0, len(reference), ">0_reference_rows"))
    val.append(ok("canonical_no_live_enablement", not bool(canonical[["live_enablement_allowed", "mt5_execution_allowed", "discord_live_allowed", "final_signal_allowed"]].any().any()), "all_false", "all_false"))
    dangerous = safety[(safety["lockout"] != "audit_only") & (safety["value"] != False)]
    val.append(ok("safety_lockout_false_except_audit_only", dangerous.empty, dangerous.to_dict("records"), []))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_62b_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
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
        "plan_canonicalization_ready": failed.empty,
        "canonical_plan_rows": int(len(canonical)),
        "reference_gap_rows": int(len(reference)),
        "official_next_stage": "GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_AUDIT_ONLY",
        "safety_lockout_global": True,
        "live_enablement_blocked": True,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_62b_plan_canonicalization_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 62B PASTE_ME_CANONICAL_PLAN_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("plan_canonicalization_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append(f"canonical_plan_rows: {len(canonical)}")
    paste.append(f"reference_gap_rows: {len(reference)}")
    paste.append("official_next_stage: GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_AUDIT_ONLY")
    paste.append("stage62_unknown_rows: separated_as_reference_only")
    paste.append("safety_lockout: global_invariant_not_stage_number")
    paste.append("")
    paste.append("CANONICAL_STAGE_ORDER_PLAN")
    paste.append(canonical[["canonical_order", "implementation_stage", "source_gap_id", "component", "purpose"]].to_string(index=False))
    paste.append("")
    paste.append("REFERENCE_GAP_ROWS")
    if reference.empty:
        paste.append("none")
    else:
        cols = [c for c in ["source_gap_id", "gap_title", "implementation_stage_candidate", "canonical_handling"] if c in reference.columns]
        paste.append(reference[cols].to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_62b_canonical_stage_order_plan.csv")
    paste.append("gold_v3_62b_reference_gap_rows.csv")
    paste.append("gold_v3_62b_safety_lockout_matrix.csv")
    paste.append("gold_v3_62b_validation_matrix.csv")
    paste.append("gold_v3_62b_plan_canonicalization_summary.json")
    (out / "gold_v3_62b_PASTE_ME_CANONICAL_PLAN_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    (out / "GOLD_V3_62B_REPORT.md").write_text(f"# GOLD V3 62B live-readiness plan canonicalization audit-only report\n\nStatus: `{status}`\n\nOfficial next stage: `GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_AUDIT_ONLY`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_62b_PASTE_ME_CANONICAL_PLAN_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
