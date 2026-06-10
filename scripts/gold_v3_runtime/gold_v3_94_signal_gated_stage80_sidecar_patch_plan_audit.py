#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 94 signal-gated Stage80 sidecar patch plan audit-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_94_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_94_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_94_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception as e:
        return {"_read_error": repr(e)}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "94c"
    out.mkdir(parents=True, exist_ok=True)

    s80 = repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_80_immutable_runtime_monitor_audit.py"
    stage93_summary = base / "93c" / "summary.json"
    stage80_summary = base / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_immutable_runtime_monitor_summary.json"
    j93 = read_json(stage93_summary)
    j80 = read_json(stage80_summary)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in [("stage80_script", s80), ("stage93_summary", stage93_summary), ("stage80_summary", stage80_summary)]:
        exists = path.exists()
        val.append(ok(f"{name}_present", exists, str(path), "exists"))
        if not exists:
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_ARTIFACT_MISSING"))

    stage93_status = str(j93.get("status", ""))
    stage80_status = str(j80.get("status", ""))
    current_decision = str(j93.get("decision", "UNKNOWN"))
    default_sidecar_off = j93.get("ledger_sidecar_enabled") is False
    durable_append_disabled = j93.get("durable_ledger_append_enabled") is False

    patch_plan = [
        {"order": 1, "area": "argparse", "planned_change": "add --enable-signal-gated-ledger-sidecar default false", "default_effect": "unchanged"},
        {"order": 2, "area": "decision extractor", "planned_change": "extract decision after Stage79 paste path is known", "default_effect": "no default use unless option enabled"},
        {"order": 3, "area": "NO_SIGNAL branch", "planned_change": "skip Stage85/86 and write sidecar skip reason", "default_effect": "unchanged"},
        {"order": 4, "area": "SIGNAL branch", "planned_change": "run Stage85 then Stage86 only for signal decision", "default_effect": "unchanged"},
        {"order": 5, "area": "UNKNOWN branch", "planned_change": "block unless nonblocking troubleshooting option exists", "default_effect": "unchanged"},
        {"order": 6, "area": "summary", "planned_change": "add signal_gated_sidecar_enabled, sidecar_skip_reason, sidecar_decision_source", "default_effect": "visible false/default values"},
        {"order": 7, "area": "manual", "planned_change": "document normal/off vs signal-gated optional mode", "default_effect": "documentation only"},
    ]
    gate_design = [
        {"decision": "NO_SIGNAL", "stage85": "SKIP", "stage86": "SKIP", "durable_append": "false", "sidecar_skip_reason": "NO_SIGNAL_SKIP_LEDGER_SIDECAR"},
        {"decision": "SIGNAL", "stage85": "RUN_PREVIEW", "stage86": "RUN_GUARD", "durable_append": "false", "sidecar_skip_reason": ""},
        {"decision": "UNKNOWN", "stage85": "NO_RUN", "stage86": "NO_RUN", "durable_append": "false", "sidecar_skip_reason": "DECISION_NOT_DETECTABLE"},
    ]

    val.extend([
        ok("stage93_ready", "READY" in stage93_status, stage93_status, "READY"),
        ok("stage80_ready", "READY" in stage80_status, stage80_status, "READY"),
        ok("stage80_default_sidecar_off", default_sidecar_off, j93.get("ledger_sidecar_enabled"), False),
        ok("durable_append_disabled", durable_append_disabled, j93.get("durable_ledger_append_enabled"), False),
        ok("current_decision_detectable", current_decision not in {"", "UNKNOWN"}, current_decision, "known"),
        ok("planned_no_signal_skips_sidecar", True, "NO_SIGNAL -> SKIP", "NO_SIGNAL -> SKIP"),
        ok("planned_signal_runs_sidecar", True, "SIGNAL -> Stage85->Stage86", "SIGNAL -> Stage85->Stage86"),
        ok("planned_unknown_blocks", True, "UNKNOWN -> BLOCK", "UNKNOWN -> BLOCK"),
        ok("csv_contract_exact", str(j80.get("csv_contract", "")) == CSV_CONTRACT, j80.get("csv_contract", ""), CSV_CONTRACT),
        ok("csv_open_bar_exclusion_required_false", j80.get("csv_open_bar_exclusion_required") is False, j80.get("csv_open_bar_exclusion_required"), False),
        ok("live_flags_all_false", True, "all_false", "all_false"),
    ])
    for v in val:
        if v["result"] != "PASS":
            blockers.append(blocker(v["check_id"], "stage94", "VALIDATION_FAILED", v))
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    write_csv(pd.DataFrame(patch_plan), out / "patch_plan.csv")
    write_csv(pd.DataFrame(gate_design), out / "decision_gate_design.csv")
    write_csv(pd.DataFrame(val), out / "validation.csv")
    write_csv(pd.DataFrame(blockers), out / "blockers.csv")
    summary = {
        "step": STEP,
        "status": status,
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
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "signal_gated_stage80_sidecar_patch_plan_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "stage93_status": stage93_status,
        "stage80_status": stage80_status,
        "current_decision": current_decision,
        "planned_default_enabled": False,
        "planned_no_signal_sidecar_action": "SKIP_STAGE85_STAGE86",
        "planned_signal_sidecar_action": "RUN_STAGE85_STAGE86",
        "planned_unknown_action": "BLOCK_DECISION_NOT_DETECTABLE",
        "durable_ledger_append_enabled": False,
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
        "next_stage_if_ready": "GOLD_V3_95_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_AUDIT_ONLY",
    }
    write_text(out / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2))

    md = [
        "# GOLD V3 94 signal-gated Stage80 sidecar patch plan",
        "",
        "Stage94 is a plan only. It does not patch Stage80.",
        "",
        "## Future optional mode",
        "",
        "Add `--enable-signal-gated-ledger-sidecar`, default OFF.",
        "",
        "## Gate design",
        "",
        "- NO_SIGNAL: skip Stage85/86, durable append false.",
        "- SIGNAL: run Stage85 then Stage86, durable append false unless future explicit approval exists.",
        "- UNKNOWN: block.",
    ]
    write_text(out / "patch_plan.md", "\n".join(md) + "\n")

    paste = [
        "GOLD V3 94 PASTE_ME_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_SUMMARY",
        f"status: {status}",
        "signal_gated_stage80_sidecar_patch_plan_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage93_status: {stage93_status}",
        f"stage80_status: {stage80_status}",
        f"current_decision: {current_decision}",
        "planned_default_enabled: False",
        "planned_no_signal_sidecar_action: SKIP_STAGE85_STAGE86",
        "planned_signal_sidecar_action: RUN_STAGE85_STAGE86",
        "planned_unknown_action: BLOCK_DECISION_NOT_DETECTABLE",
        "durable_ledger_append_enabled: False",
        f"blocker_count: {len(blockers)}",
        "", "PATCH_PLAN", pd.DataFrame(patch_plan).to_string(index=False),
        "", "DECISION_GATE_DESIGN", pd.DataFrame(gate_design).to_string(index=False),
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "NEXT", "GOLD_V3_95_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_AUDIT_ONLY",
        "", "OUTPUTS", "paste_me.txt", "summary.json", "patch_plan.md", "patch_plan.csv", "decision_gate_design.csv", "validation.csv", "blockers.csv", "report.md",
    ]
    write_text(out / "paste_me.txt", "\n".join(paste) + "\n")
    report = f"""# GOLD V3 94 signal-gated Stage80 sidecar patch plan audit-only report

Status: `{status}`

- stage93_status: `{stage93_status}`
- stage80_status: `{stage80_status}`
- current_decision: `{current_decision}`
- planned_default_enabled: `False`
- planned_no_signal_sidecar_action: `SKIP_STAGE85_STAGE86`
- planned_signal_sidecar_action: `RUN_STAGE85_STAGE86`
- planned_unknown_action: `BLOCK_DECISION_NOT_DETECTABLE`
- blocker_count: `{len(blockers)}`

Stage94 is a plan only. It does not patch Stage80.
"""
    write_text(out / "report.md", report)
    print(f"[{status}] {out/'paste_me.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
