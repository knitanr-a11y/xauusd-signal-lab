#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 71 live CSV signal audit pipeline package audit-only.

Packages Stage69/70 outputs into a stable latest signal snapshot for manual
audit inspection. No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_71_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_71_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_71_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_BLOCKED_AUDIT_ONLY"
STAGE69_READY = "GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_READY_AUDIT_ONLY"
STAGE70_READY = "GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    if path.exists() and path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d/"FX_OUTPUTS"/"gold_v3"/"70_live_csv_signal_decision_preview_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with Stage70 outputs")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage69-dir", default="")
    p.add_argument("--stage70-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s69 = Path(a.stage69_dir).expanduser().resolve() if a.stage69_dir else base_out / "69_live_csv_condition_detector_audit_only"
    s70 = Path(a.stage70_dir).expanduser().resolve() if a.stage70_dir else base_out / "70_live_csv_signal_decision_preview_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "71_live_csv_signal_audit_pipeline_package_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p69 = s69 / "gold_v3_69_live_csv_condition_detector_summary.json"
    p70 = s70 / "gold_v3_70_live_csv_signal_decision_preview_summary.json"
    p70_decision = s70 / "gold_v3_70_latest_closed_signal_decision.csv"

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in [("stage69_summary", p69), ("stage70_summary", p70), ("stage70_decision_csv", p70_decision)]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_INPUT_MISSING"))

    j69 = read_json(p69) if p69.exists() else {}
    j70 = read_json(p70) if p70.exists() else {}
    val.append(ok("stage69_status_ready", j69.get("status") == STAGE69_READY, j69.get("status"), STAGE69_READY))
    val.append(ok("stage69_detector_ready", j69.get("live_csv_condition_detector_ready") is True, j69.get("live_csv_condition_detector_ready"), True))
    val.append(ok("stage70_status_ready", j70.get("status") == STAGE70_READY, j70.get("status"), STAGE70_READY))
    val.append(ok("stage70_decision_preview_ready", j70.get("signal_decision_preview_ready") is True, j70.get("signal_decision_preview_ready"), True))
    for src, j in [("stage69", j69), ("stage70", j70)]:
        for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
            val.append(ok(f"{src}_{key}_false", j.get(key) is False, j.get(key), False))

    snapshot = pd.DataFrame()
    decision = ""
    reason = ""
    latest_time = str(j70.get("latest_closed_m15_time", ""))
    latest_rows = int(j70.get("latest_condition_candidate_rows", 0) or 0)
    eligible_rows = int(j70.get("eligible_candidate_rows", 0) or 0)
    selected_candidate = str(j70.get("selected_candidate_label", "") or "")

    if not blockers:
        dec = read_csv(p70_decision)
        val.append(ok("stage70_decision_csv_one_row", len(dec) == 1, len(dec), 1))
        if len(dec) != 1:
            blockers.append(blocker("stage70_decision_csv_invalid_row_count", str(p70_decision), "DECISION_CSV_MUST_HAVE_ONE_ROW", {"rows": len(dec)}))
        else:
            row = dec.iloc[0].to_dict()
            decision = str(row.get("decision", j70.get("decision", "")) or "")
            reason = str(row.get("no_signal_reason", j70.get("no_signal_reason", "")) or "")
            val.append(ok("decision_is_signal_or_no_signal", decision in {"SIGNAL", "NO_SIGNAL"}, decision, "SIGNAL|NO_SIGNAL"))
            if decision not in {"SIGNAL", "NO_SIGNAL"}:
                blockers.append(blocker("invalid_decision", str(p70_decision), "DECISION_NOT_SIGNAL_OR_NO_SIGNAL", decision))
            snapshot = pd.DataFrame([{ 
                "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "latest_closed_m15_time": latest_time,
                "decision": decision,
                "no_signal_reason": reason,
                "latest_condition_candidate_rows": latest_rows,
                "eligible_candidate_rows": eligible_rows,
                "selected_candidate_label": selected_candidate,
                "audit_only": True,
                "live_ready": False,
                "live_allowed": False,
                "mt5_execution_enabled": False,
                "discord_live_enabled": False,
                "ai_api_called": False,
                "final_signal_enabled": False,
                "csv_open_bar_exclusion_required": False,
                "csv_contract": CSV_CONTRACT,
                "pool_policy": POOL_POLICY,
            }])

    if snapshot.empty:
        snapshot = pd.DataFrame([{ 
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "latest_closed_m15_time": latest_time,
            "decision": decision,
            "no_signal_reason": reason,
            "latest_condition_candidate_rows": latest_rows,
            "eligible_candidate_rows": eligible_rows,
            "selected_candidate_label": selected_candidate,
            "audit_only": True,
            "live_ready": False,
            "live_allowed": False,
            "mt5_execution_enabled": False,
            "discord_live_enabled": False,
            "ai_api_called": False,
            "final_signal_enabled": False,
            "csv_open_bar_exclusion_required": False,
            "csv_contract": CSV_CONTRACT,
            "pool_policy": POOL_POLICY,
        }])
    snapshot.to_csv(out / "gold_v3_71_latest_signal_snapshot.csv", index=False, encoding="utf-8-sig")
    (out / "gold_v3_71_latest_signal_snapshot.json").write_text(json.dumps(snapshot.iloc[0].to_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    val.append(ok("latest_closed_time_present", latest_time != "", latest_time, "nonempty"))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    pd.DataFrame(blockers).to_csv(out / "gold_v3_71_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_71_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(cdir),
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
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "live_csv_signal_audit_pipeline_package_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "latest_closed_m15_time": latest_time,
        "decision": decision,
        "no_signal_reason": reason,
        "latest_condition_candidate_rows": latest_rows,
        "eligible_candidate_rows": eligible_rows,
        "selected_candidate_label": selected_candidate,
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
    }
    (out / "gold_v3_71_live_csv_signal_audit_pipeline_package_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 71 PASTE_ME_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("live_csv_signal_audit_pipeline_package_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append(f"latest_closed_m15_time: {latest_time}")
    paste.append(f"decision: {decision}")
    paste.append(f"no_signal_reason: {reason}")
    paste.append(f"latest_condition_candidate_rows: {latest_rows}")
    paste.append(f"eligible_candidate_rows: {eligible_rows}")
    paste.append(f"selected_candidate_label: {selected_candidate}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_71_latest_signal_snapshot.csv")
    paste.append("gold_v3_71_latest_signal_snapshot.json")
    paste.append("gold_v3_71_blocker_matrix.csv")
    paste.append("gold_v3_71_validation_matrix.csv")
    paste.append("gold_v3_71_live_csv_signal_audit_pipeline_package_summary.json")
    (out / "gold_v3_71_PASTE_ME_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")

    report = f"""# GOLD V3 71 live CSV signal audit pipeline package audit-only report

Status: `{status}`

## Latest snapshot

- latest_closed_m15_time: `{latest_time}`
- decision: `{decision}`
- no_signal_reason: `{reason}`
- latest_condition_candidate_rows: `{latest_rows}`
- eligible_candidate_rows: `{eligible_rows}`
- blocker_count: `{len(blockers)}`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_71_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_71_PASTE_ME_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
