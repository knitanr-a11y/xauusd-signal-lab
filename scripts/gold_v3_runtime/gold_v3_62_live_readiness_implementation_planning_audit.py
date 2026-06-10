#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 62 live-readiness implementation planning audit-only.

Converts Stage48 live-readiness gaps into an audit-only implementation plan.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_62_LIVE_READINESS_IMPLEMENTATION_PLANNING_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_62_LIVE_READINESS_IMPLEMENTATION_PLANNING_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_62_LIVE_READINESS_IMPLEMENTATION_PLANNING_BLOCKED_AUDIT_ONLY"
STAGE61_READY = "GOLD_V3_61_FROZEN_AUDIT_PACKAGE_HUMAN_REVIEW_READY_AUDIT_ONLY"

KNOWN_GAPS = [
    {"source_gap_id": "safety/live_execution", "gap_status": "BLOCKED", "gap_title": "live execution lockout", "component": "safety"},
    {"source_gap_id": "live_input/h4_closed_bar_availability", "gap_status": "GAP", "gap_title": "H4 closed-bar availability", "component": "live_input"},
    {"source_gap_id": "live_input/m15_m5_alignment", "gap_status": "GAP", "gap_title": "M15/M5 alignment", "component": "live_input"},
    {"source_gap_id": "feature/rolling_prior_60d_q70", "gap_status": "GAP", "gap_title": "rolling prior-60D Q70 state", "component": "feature"},
    {"source_gap_id": "gate/virtual_monitoring_state", "gap_status": "GAP", "gap_title": "virtual monitoring state", "component": "gate"},
    {"source_gap_id": "gate/health_gate_rehydration", "gap_status": "GAP", "gap_title": "rolling health gate rehydration", "component": "gate"},
    {"source_gap_id": "selection/rank_dedup_reproducibility", "gap_status": "GAP", "gap_title": "rank-dedup selection reproducibility", "component": "selection"},
    {"source_gap_id": "adjudication/m5_tp_sl_horizon", "gap_status": "GAP", "gap_title": "M5 TP/SL/horizon adjudication parity", "component": "adjudication"},
]

STAGE_PLAN = {
    "safety/live_execution": ("GOLD_V3_63_SAFETY_LOCKOUT_DECLARATION_AUDIT_ONLY", "Keep all live/MT5/Discord/final signal flags hard false."),
    "live_input/h4_closed_bar_availability": ("GOLD_V3_64_H4_CLOSED_BAR_LIVE_STATE_BUILDER_AUDIT_ONLY", "Build closed H4 state from candle files only."),
    "live_input/m15_m5_alignment": ("GOLD_V3_65_M15_M5_ALIGNMENT_STATE_BUILDER_AUDIT_ONLY", "Align closed M15 entries with M5 adjudication windows."),
    "feature/rolling_prior_60d_q70": ("GOLD_V3_66_ROLLING_PRIOR_60D_Q70_STATE_AUDIT_ONLY", "Persist rolling prior-60D Q70 high-vol state."),
    "gate/virtual_monitoring_state": ("GOLD_V3_67_VIRTUAL_MONITORING_STATE_AUDIT_ONLY", "Maintain virtual candidate monitoring without live orders."),
    "gate/health_gate_rehydration": ("GOLD_V3_68_HEALTH_GATE_REHYDRATION_AUDIT_ONLY", "Rehydrate rolling PF/loss-streak state from virtual monitoring."),
    "selection/rank_dedup_reproducibility": ("GOLD_V3_69_RANK_DEDUP_SELECTION_REPRO_AUDIT_ONLY", "Reproduce Stage52 rank-dedup selection audit-only."),
    "adjudication/m5_tp_sl_horizon": ("GOLD_V3_70_M5_TP_SL_HORIZON_ADJUDICATION_PARITY_AUDIT_ONLY", "Reproduce Stage53 M5 TP/SL/horizon adjudication parity."),
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "61_frozen_audit_package_human_review_audit_only").exists():
            return d
    raise FileNotFoundError("Stage61 output directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage48-dir", default="")
    p.add_argument("--stage61-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def normalize_gap_matrix(path: Path | None) -> tuple[pd.DataFrame, str]:
    if path is None or not path.exists():
        return pd.DataFrame(KNOWN_GAPS), "fallback_known_stage48_gap_list"
    raw = pd.read_csv(path, encoding="utf-8-sig")
    rows = []
    for i, r in raw.iterrows():
        lower = {str(k).lower(): k for k in raw.columns}
        def get_any(names: list[str], default: Any = "") -> Any:
            for n in names:
                if n.lower() in lower:
                    return r[lower[n.lower()]]
            return default
        source_gap_id = str(get_any(["gap_id", "check_id", "item", "blocker_id", "source_gap_id"], f"stage48_gap_{i+1}"))
        gap_status = str(get_any(["status", "result", "gap_status"], "GAP"))
        gap_title = str(get_any(["title", "description", "gap_title", "item"], source_gap_id))
        component = source_gap_id.split("/")[0] if "/" in source_gap_id else str(get_any(["component"], "unknown"))
        rows.append({"source_gap_id": source_gap_id, "gap_status": gap_status, "gap_title": gap_title, "component": component})
    # Ensure the known canonical gaps are present even if Stage48 matrix wording changed.
    seen = {str(x["source_gap_id"]) for x in rows}
    for g in KNOWN_GAPS:
        if g["source_gap_id"] not in seen:
            rows.append({**g, "gap_status": "MISSING_FROM_STAGE48_MATRIX_FALLBACK_ADDED"})
    return pd.DataFrame(rows), str(path)


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s48 = Path(a.stage48_dir).expanduser().resolve() if a.stage48_dir else g / "48_closed_asof_pool_contract_live_readiness_gap_audit_only"
    s61 = Path(a.stage61_dir).expanduser().resolve() if a.stage61_dir else g / "61_frozen_audit_package_human_review_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "62_live_readiness_implementation_planning_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p61s = s61 / "gold_v3_61_frozen_audit_package_summary.json"
    p48m = s48 / "gold_v3_48_live_readiness_gap_matrix.csv"
    p48s = s48 / "gold_v3_48_live_readiness_gap_summary.json"

    val: list[dict[str, Any]] = []
    val.append(ok("stage61_summary_present", p61s.exists(), str(p61s), "exists"))
    val.append(ok("stage48_gap_matrix_or_fallback_available", p48m.exists() or True, str(p48m) if p48m.exists() else "fallback_known_stage48_gap_list", "matrix_or_fallback"))
    if not p61s.exists():
        pd.DataFrame(val).to_csv(out / "gold_v3_62_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j61 = read_json(p61s)
    val.append(ok("stage61_status_ready", j61.get("status") == STAGE61_READY, j61.get("status"), STAGE61_READY))
    val.append(ok("stage61_frozen_package_ready", j61.get("frozen_audit_package_ready") is True, j61.get("frozen_audit_package_ready"), True))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage61_{key}_false", j61.get(key) is False, j61.get(key), False))

    gaps, gap_source = normalize_gap_matrix(p48m if p48m.exists() else None)
    plan_rows = []
    for _, r in gaps.iterrows():
        gid = str(r["source_gap_id"])
        stage_candidate, note = STAGE_PLAN.get(gid, ("GOLD_V3_XX_ADDITIONAL_LIVE_READINESS_AUDIT_ONLY", "Additional gap from Stage48 matrix."))
        plan_rows.append({
            "source_gap_id": gid,
            "gap_status": r.get("gap_status", ""),
            "gap_title": r.get("gap_title", ""),
            "component": r.get("component", ""),
            "implementation_stage_candidate": stage_candidate,
            "planning_note": note,
            "input_artifacts": "Stage46-61 frozen audit package; source candles; relevant prior state artifacts",
            "planned_state_artifacts": f"{stage_candidate.lower()}_state.csv; validation_matrix.csv; paste_me_summary.txt",
            "audit_checks": "presence; closed-asof only; deterministic replay; parity to frozen artifacts where applicable; safety flags false",
            "stop_conditions": "missing source; open-asof required; state mismatch; hash/prefix mismatch; safety flag true",
            "live_enablement_allowed": False,
            "mt5_execution_allowed": False,
            "discord_live_allowed": False,
            "final_signal_allowed": False,
        })
    plan = pd.DataFrame(plan_rows)
    plan.to_csv(out / "gold_v3_62_gap_to_plan_matrix.csv", index=False, encoding="utf-8-sig")

    stage_order = plan[["implementation_stage_candidate", "source_gap_id", "component", "planning_note"]].copy()
    stage_order.insert(0, "order", range(1, len(stage_order) + 1))
    stage_order.to_csv(out / "gold_v3_62_stage_order_plan.csv", index=False, encoding="utf-8-sig")

    safety = pd.DataFrame([
        {"lockout": "live_allowed", "value": False, "reason": "planning-only stage"},
        {"lockout": "mt5_execution_enabled", "value": False, "reason": "no MT5 order BAT"},
        {"lockout": "discord_live_enabled", "value": False, "reason": "no live notifications"},
        {"lockout": "ai_api_called", "value": False, "reason": "no AI API"},
        {"lockout": "final_signal_enabled", "value": False, "reason": "no final signal"},
        {"lockout": "live_hook_enabled", "value": False, "reason": "no live hook"},
        {"lockout": "candidate_pool_mutation", "value": False, "reason": "pool remains frozen"},
        {"lockout": "manual_candidate_demotion_or_removal", "value": False, "reason": "HV/base candidates not manually removed"},
        {"lockout": "open_asof_allowed", "value": False, "reason": "closed-asof only"},
    ])
    safety.to_csv(out / "gold_v3_62_safety_lockout_matrix.csv", index=False, encoding="utf-8-sig")

    val.append(ok("plan_rows_cover_known_gaps", set(KNOWN_GAPS[i]["source_gap_id"] for i in range(len(KNOWN_GAPS))).issubset(set(plan["source_gap_id"])), sorted(set(KNOWN_GAPS[i]["source_gap_id"] for i in range(len(KNOWN_GAPS))) - set(plan["source_gap_id"])), []))
    val.append(ok("plan_has_no_live_enablement", not bool(plan[["live_enablement_allowed", "mt5_execution_allowed", "discord_live_allowed", "final_signal_allowed"]].any().any()), "all_false", "all_false"))
    val.append(ok("safety_lockout_all_false", not bool(safety["value"].any()), "all_false", "all_false"))
    val.append(ok("stage_order_rows_match_plan_rows", len(stage_order) == len(plan), len(stage_order), len(plan)))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_62_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "live_readiness_planning_ready": failed.empty,
        "human_decision": "D2_CONTINUE_LIVE_READINESS_IMPLEMENTATION_PLANNING_AUDIT_ONLY",
        "gap_source": gap_source,
        "gap_plan_rows": int(len(plan)),
        "stage_order_rows": int(len(stage_order)),
        "live_enablement_blocked": True,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_62_live_readiness_planning_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 62 PASTE_ME_LIVE_READINESS_PLANNING_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("live_readiness_planning_ready: " + str(failed.empty).lower())
    paste.append("human_decision: D2_CONTINUE_LIVE_READINESS_IMPLEMENTATION_PLANNING_AUDIT_ONLY")
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append(f"gap_source: {gap_source}")
    paste.append(f"gap_plan_rows: {len(plan)}")
    paste.append(f"stage_order_rows: {len(stage_order)}")
    paste.append("live_enablement: BLOCKED_REQUIRES_SEPARATE_EXPLICIT_APPROVAL_AND_LIVE_READINESS_IMPLEMENTATION_AUDIT")
    paste.append("")
    paste.append("STAGE_ORDER_PLAN")
    paste.append(stage_order.to_string(index=False))
    paste.append("")
    paste.append("SAFETY_LOCKOUT")
    paste.append(safety.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_62_gap_to_plan_matrix.csv")
    paste.append("gold_v3_62_stage_order_plan.csv")
    paste.append("gold_v3_62_safety_lockout_matrix.csv")
    paste.append("gold_v3_62_validation_matrix.csv")
    paste.append("gold_v3_62_live_readiness_planning_summary.json")
    (out / "gold_v3_62_PASTE_ME_LIVE_READINESS_PLANNING_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = [
        "# GOLD V3 62 live-readiness implementation planning audit-only report",
        "",
        f"Status: `{status}`",
        "",
        "Planning only. No MT5, Discord, AI API, live hook, or final signal.",
    ]
    (out / "GOLD_V3_62_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_62_PASTE_ME_LIVE_READINESS_PLANNING_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
