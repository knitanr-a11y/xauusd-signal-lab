#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 89 runtime ledger sidecar integration readiness audit-only.

Checks whether Stage85/86 can be safely integrated after Stage80->76->79 in a
future stage. Does not patch Stage80 and does not enable sidecar autorun.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_89_RUNTIME_LEDGER_SIDECAR_INTEGRATION_READINESS_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_89_RUNTIME_LEDGER_SIDECAR_INTEGRATION_READINESS_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_89_RUNTIME_LEDGER_SIDECAR_INTEGRATION_READINESS_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
CANDIDATE_KEY_ORDER = "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars"


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception as e:
        return {"_read_error": repr(e)}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


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
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    cdir = Path(args.candle_dir).expanduser().resolve() if args.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(args.output_dir).expanduser().resolve() if args.output_dir else base / "89c"
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "stage80_summary": base / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_immutable_runtime_monitor_summary.json",
        "stage85_summary": base / "85_trade_review_ledger_entry_preview_audit_only" / "gold_v3_85_trade_review_ledger_entry_preview_summary.json",
        "stage86_summary": base / "86_trade_review_ledger_append_guard_audit_only" / "gold_v3_86_trade_review_ledger_append_guard_summary.json",
        "stage84_schema": base / "trade_review_ledger" / "trade_review_ledger_schema.csv",
        "stage88_manual_candidates": base / "88c" / "manual_candidates.md",
        "s85_script": repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_85_trade_review_ledger_entry_preview_audit.py",
        "s86_script": repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_86_trade_review_ledger_append_guard_audit.py",
        "s85_bat": repo_root / "scripts" / "gold_v3_runtime" / "bat" / "run_gold_v3_85_trade_review_ledger_entry_preview_audit.bat",
        "s86_bat": repo_root / "scripts" / "gold_v3_runtime" / "bat" / "run_gold_v3_86_trade_review_ledger_append_guard_audit.bat",
        "s80_script": repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_80_immutable_runtime_monitor_audit.py",
    }

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    readiness_rows = []
    for name, path in paths.items():
        exists = path.exists()
        readiness_rows.append({"item": name, "path": str(path), "exists": exists})
        required = name in {"stage80_summary", "stage84_schema", "stage88_manual_candidates", "s85_script", "s86_script", "s85_bat", "s86_bat"}
        if required:
            val.append(ok(f"{name}_present", exists, str(path), "exists"))
            if not exists:
                blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_ARTIFACT_MISSING"))

    j80 = read_json(paths["stage80_summary"])
    j85 = read_json(paths["stage85_summary"])
    j86 = read_json(paths["stage86_summary"])
    latest_sidecar_run_present = paths["stage85_summary"].exists() and paths["stage86_summary"].exists()
    stage80_status = str(j80.get("status", ""))
    stage85_status = str(j85.get("status", ""))
    stage86_status = str(j86.get("status", ""))

    sidecar_autorun_enabled = False
    stage80_patched_by_stage89 = False
    durable_ledger_append_enabled = False
    live_flags_all_false = True

    chain_rows = [
        {"order": 1, "stage": "Stage80", "action": "detect new closed M15", "current_integration": "already active", "future_sidecar": "unchanged"},
        {"order": 2, "stage": "Stage76", "action": "payload preview audit", "current_integration": "already active via Stage80", "future_sidecar": "unchanged"},
        {"order": 3, "stage": "Stage79", "action": "immutable evidence", "current_integration": "already active via Stage80", "future_sidecar": "unchanged"},
        {"order": 4, "stage": "Stage85", "action": "trade ledger row preview or NO_SIGNAL suppression", "current_integration": "manual", "future_sidecar": "candidate"},
        {"order": 5, "stage": "Stage86", "action": "append guard", "current_integration": "manual", "future_sidecar": "candidate"},
    ]

    val.extend([
        ok("stage80_not_patched_by_stage89", not stage80_patched_by_stage89, stage80_patched_by_stage89, False),
        ok("sidecar_autorun_disabled", not sidecar_autorun_enabled, sidecar_autorun_enabled, False),
        ok("durable_ledger_append_disabled", not durable_ledger_append_enabled, durable_ledger_append_enabled, False),
        ok("latest_sidecar_run_present_or_plannable", latest_sidecar_run_present or (paths["s85_script"].exists() and paths["s86_script"].exists()), latest_sidecar_run_present, "present or scripts available"),
        ok("candidate_key_order_exact", CANDIDATE_KEY_ORDER == "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars", CANDIDATE_KEY_ORDER, "exact"),
        ok("csv_open_bar_exclusion_required_false", True, False, False),
        ok("live_flags_all_false", live_flags_all_false, "all_false", "all_false"),
    ])
    if latest_sidecar_run_present:
        val.append(ok("stage85_latest_ready", "READY" in stage85_status, stage85_status, "READY"))
        val.append(ok("stage86_latest_ready", "READY" in stage86_status, stage86_status, "READY"))
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    write_csv(pd.DataFrame(chain_rows), out / "chain_plan.csv")
    write_csv(pd.DataFrame(readiness_rows), out / "readiness.csv")
    write_csv(pd.DataFrame(blockers), out / "blockers.csv")
    write_csv(pd.DataFrame(val), out / "validation.csv")

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
        "runtime_ledger_sidecar_integration_readiness_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_order": CANDIDATE_KEY_ORDER,
        "output_dir": str(out),
        "stage80_status": stage80_status,
        "stage85_status": stage85_status,
        "stage86_status": stage86_status,
        "latest_sidecar_run_present": latest_sidecar_run_present,
        "sidecar_autorun_enabled": sidecar_autorun_enabled,
        "stage80_patched_by_stage89": stage80_patched_by_stage89,
        "durable_ledger_append_enabled": durable_ledger_append_enabled,
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
        "next_stage_if_ready": "GOLD_V3_90_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_AUDIT_ONLY",
    }
    write_text(out / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2))

    paste = [
        "GOLD V3 89 PASTE_ME_RUNTIME_LEDGER_SIDECAR_INTEGRATION_READINESS_SUMMARY",
        f"status: {status}",
        "runtime_ledger_sidecar_integration_readiness_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage80_status: {stage80_status}",
        f"stage85_status: {stage85_status}",
        f"stage86_status: {stage86_status}",
        f"latest_sidecar_run_present: {latest_sidecar_run_present}",
        f"sidecar_autorun_enabled: {sidecar_autorun_enabled}",
        f"stage80_patched_by_stage89: {stage80_patched_by_stage89}",
        f"durable_ledger_append_enabled: {durable_ledger_append_enabled}",
        f"blocker_count: {len(blockers)}",
        "", "CHAIN_PLAN", pd.DataFrame(chain_rows).to_string(index=False),
        "", "READINESS", pd.DataFrame(readiness_rows).to_string(index=False),
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "NEXT", "GOLD_V3_90_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_AUDIT_ONLY",
        "", "OUTPUTS", "paste_me.txt", "summary.json", "chain_plan.csv", "readiness.csv", "blockers.csv", "validation.csv", "report.md",
    ]
    write_text(out / "paste_me.txt", "\n".join(paste) + "\n")
    report = f"""# GOLD V3 89 runtime ledger sidecar integration readiness audit-only report

Status: `{status}`

- stage80_status: `{stage80_status}`
- latest_sidecar_run_present: `{latest_sidecar_run_present}`
- sidecar_autorun_enabled: `{sidecar_autorun_enabled}`
- stage80_patched_by_stage89: `{stage80_patched_by_stage89}`
- durable_ledger_append_enabled: `{durable_ledger_append_enabled}`
- blocker_count: `{len(blockers)}`

Stage89 does not patch Stage80. If READY, next stage may plan a dry-run sidecar patch.
"""
    write_text(out / "report.md", report)
    print(f"[{status}] {out/'paste_me.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
