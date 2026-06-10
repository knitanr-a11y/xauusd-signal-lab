#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 48 closed-asof pool contract live-readiness gap audit-only.

This script does not implement live trading. It reads Stage46/47 audit outputs,
inspects local candle files, and writes a gap matrix describing what is still
missing before any shadow/live evaluator could be considered.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_48_CLOSED_ASOF_POOL_CONTRACT_LIVE_READINESS_GAP_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_48_CLOSED_ASOF_POOL_CONTRACT_LIVE_READINESS_GAP_REPORT_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_48_CLOSED_ASOF_POOL_CONTRACT_LIVE_READINESS_GAP_REPORT_BLOCKED_AUDIT_ONLY"
STAGE46_READY = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY"
STAGE47_READY = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_READY_AUDIT_ONLY"

REQUIRED_HV = ["HV_TP180_SL70_H128", "HV_TP200_SL80_H128", "HV_TP220_SL90_H128"]
CANDLE_FILES = [
    ("M1", "goldsharp_m1.csv", False),
    ("M5", "goldsharp_m5.csv", True),
    ("M15", "goldsharp_m15.csv", True),
    ("H1", "goldsharp_h1.csv", False),
    ("H4", "goldsharp_h4.csv", True),
    ("D1", "goldsharp_d1.csv", False),
]

TIME_CANDIDATES = ["time", "datetime", "date", "timestamp", "Time", "Date", "DateTime", "open_time", "Open time"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def smart_read_csv(path: Path, nrows: int | None = None) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig", sep=None, engine="python", nrows=nrows)
    except Exception:
        return pd.read_csv(path, encoding="utf-8-sig", nrows=nrows)


def detect_time_col(df: pd.DataFrame) -> str:
    for c in TIME_CANDIDATES:
        if c in df.columns:
            return c
    for c in df.columns:
        lc = str(c).lower()
        if "time" in lc or "date" in lc:
            return str(c)
    return ""


def file_inventory(candle_dir: Path) -> pd.DataFrame:
    rows = []
    for tf, fname, required in CANDLE_FILES:
        p = candle_dir / fname
        row = {
            "timeframe": tf,
            "file": fname,
            "required_for_stage48": required,
            "exists": p.exists(),
            "rows": 0,
            "time_col": "",
            "first_time": "",
            "last_time": "",
            "columns": "",
            "status": "MISSING_REQUIRED" if required else "MISSING_OPTIONAL",
        }
        if p.exists():
            try:
                df = smart_read_csv(p)
                row["rows"] = int(len(df))
                row["columns"] = ",".join(map(str, df.columns.tolist()))[:500]
                tcol = detect_time_col(df)
                row["time_col"] = tcol
                if tcol:
                    ts = pd.to_datetime(df[tcol], errors="coerce")
                    if ts.notna().any():
                        row["first_time"] = str(ts.dropna().iloc[0])
                        row["last_time"] = str(ts.dropna().iloc[-1])
                row["status"] = "PRESENT"
            except Exception as e:
                row["status"] = f"READ_ERROR:{type(e).__name__}:{e}"
        rows.append(row)
    return pd.DataFrame(rows)


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def gap(area: str, item: str, status: str, severity: str, observed: str, required_action: str) -> dict[str, str]:
    return {
        "area": area,
        "item": item,
        "status": status,
        "severity": severity,
        "observed": observed,
        "required_action": required_action,
    }


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "goldsharp_m5.csv").exists() and (d / "goldsharp_m15.csv").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with goldsharp_m5/m15.csv")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage46-dir", default="")
    p.add_argument("--stage47-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    candle_dir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    stage46_dir = Path(a.stage46_dir).expanduser().resolve() if a.stage46_dir else candle_dir / "FX_OUTPUTS" / "gold_v3" / "46_closed_asof_stage45_pool_contract_freeze_audit_only"
    stage47_dir = Path(a.stage47_dir).expanduser().resolve() if a.stage47_dir else candle_dir / "FX_OUTPUTS" / "gold_v3" / "47_closed_asof_pool_contract_forward_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else candle_dir / "FX_OUTPUTS" / "gold_v3" / "48_closed_asof_pool_contract_live_readiness_gap_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    stage46_path = stage46_dir / "gold_v3_46_closed_asof_stage45_pool_contract.json"
    stage47_path = stage47_dir / "gold_v3_47_forward_audit_summary.json"

    validation: list[dict[str, Any]] = []
    validation.append(ok("stage46_contract_present", stage46_path.exists(), str(stage46_path), "exists"))
    validation.append(ok("stage47_forward_summary_present", stage47_path.exists(), str(stage47_path), "exists"))

    contract: dict[str, Any] = {}
    forward: dict[str, Any] = {}
    if stage46_path.exists():
        contract = read_json(stage46_path)
    if stage47_path.exists():
        forward = read_json(stage47_path)

    if contract:
        frozen = contract.get("frozen_contract", {})
        validation.append(ok("stage46_status_ready", contract.get("status") == STAGE46_READY, contract.get("status"), STAGE46_READY))
        validation.append(ok("stage46_closed_asof", frozen.get("htf_asof") == "closed", frozen.get("htf_asof"), "closed"))
        validation.append(ok("stage46_open_asof_disallowed", frozen.get("open_asof_allowed") is False, frozen.get("open_asof_allowed"), False))
        validation.append(ok("stage46_no_manual_pool_mutation", "no_manual" in str(frozen.get("candidate_pool_policy", "")), frozen.get("candidate_pool_policy", ""), "no_manual..."))
        hv = list(frozen.get("hv_profiles_retained", []))
        for prof in REQUIRED_HV:
            validation.append(ok(f"stage46_retains_{prof}", prof in hv, prof if prof in hv else "missing", prof))
    if forward:
        validation.append(ok("stage47_status_ready", forward.get("status") == STAGE47_READY, forward.get("status"), STAGE47_READY))
        validation.append(ok("stage47_contract_reused", forward.get("contract_reused_without_candidate_changes") is True, forward.get("contract_reused_without_candidate_changes"), True))
        validation.append(ok("stage47_no_manual_demotion_or_removal", forward.get("manual_candidate_demotion_or_removal") is False, forward.get("manual_candidate_demotion_or_removal"), False))
        for flag in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "signals_generated", "final_signal_enabled"]:
            validation.append(ok(f"stage47_safety_{flag}_false", forward.get(flag) is False, forward.get(flag), False))

    inv = file_inventory(candle_dir)
    inv.to_csv(out / "gold_v3_48_input_candle_inventory.csv", index=False, encoding="utf-8-sig")
    for _, r in inv.iterrows():
        if bool(r["required_for_stage48"]):
            validation.append(ok(f"required_candle_{r['timeframe']}_present", bool(r["exists"]) and r["status"] == "PRESENT", r["status"], "PRESENT"))
            validation.append(ok(f"required_candle_{r['timeframe']}_has_time_col", bool(r["time_col"]), r["time_col"], "time column"))

    validation_df = pd.DataFrame(validation)
    hard_fail = not validation_df[validation_df["result"].ne("PASS")].empty

    gaps: list[dict[str, str]] = []
    gaps.append(gap("contract", "candidate_pool", "OK", "INFO", "Stage46/47 retain full base + HV sibling pool and no manual demotion/removal", "Do not change candidate pool in Stage48"))
    gaps.append(gap("contract", "closed_asof", "OK", "INFO", "Stage46/47 require closed asof and open_asof_allowed=false", "Continue using closed HTF values only"))
    gaps.append(gap("safety", "live_execution", "BLOCKED", "BLOCKER", "No live execution approval exists", "Keep MT5/Discord/final signal disabled until explicit later approval"))
    gaps.append(gap("live_input", "h4_closed_bar_availability", "GAP", "BLOCKER", "Backtest uses closed H4 asof; live must wait for confirmed H4 close-written file row", "Implement audit-only H4 closed-row readiness check before any evaluator decision"))
    gaps.append(gap("live_input", "m15_m5_alignment", "GAP", "BLOCKER", "Backtest enters on M15 and judges by M5 horizon; live must only create pending audit records, not know outcome immediately", "Design shadow ledger with entry_time, candidate_id, TP/SL profile, and pending horizon state"))
    gaps.append(gap("feature", "rolling_prior_60d_q70", "GAP", "BLOCKER", "High-vol rule must use prior 60D only; no persisted live state artifact is frozen yet", "Create audit-only rolling quantile state builder with no current-bar leakage"))
    gaps.append(gap("gate", "virtual_monitoring_state", "GAP", "BLOCKER", "Rolling health gate requires virtual results for all candidates, including unselected candidates", "Create persistent virtual opportunity/result ledger before any shadow evaluator"))
    gaps.append(gap("gate", "health_gate_rehydration", "GAP", "BLOCKER", "Gate window state must survive restarts and be replayable", "Freeze state schema and restart/replay rules"))
    gaps.append(gap("selection", "rank_dedup_reproducibility", "GAP", "BLOCKER", "Stage45 rank-dedup behavior must be reproduced exactly in any evaluator", "Write contract test comparing evaluator selected rows to Stage45 replay rows"))
    gaps.append(gap("adjudication", "m5_tp_sl_horizon", "GAP", "BLOCKER", "Backtest can judge future M5 bars; live/shadow must wait until TP/SL/timeout occurs", "Implement audit-only pending-to-closed trade adjudicator, still no order execution"))
    gaps.append(gap("outputs", "paste_me_monitoring", "OK", "INFO", "PASTE_ME summaries exist for Stage45-48", "Continue sharing compact PASTE_ME only when upload limit is reached"))

    gap_df = pd.DataFrame(gaps)
    blocker_gaps = gap_df[gap_df["severity"].eq("BLOCKER") & gap_df["status"].isin(["GAP", "BLOCKED"])]
    report_status = BLOCKED_STATUS if hard_fail else READY_STATUS

    validation_df.to_csv(out / "gold_v3_48_validation_matrix.csv", index=False, encoding="utf-8-sig")
    gap_df.to_csv(out / "gold_v3_48_live_readiness_gap_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": report_status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(candle_dir),
        "stage46_dir": str(stage46_dir),
        "stage47_dir": str(stage47_dir),
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
        "candidate_pool_policy": "retain_all_stage45_base_and_hv_sibling_candidates",
        "open_asof_allowed": False,
        "report_ready": not hard_fail,
        "live_ready": False,
        "deployment_blockers_present": True,
        "blocker_gap_count": int(len(blocker_gaps)),
        "validation_failure_count": int(len(validation_df[validation_df["result"].ne("PASS")])) if not validation_df.empty else 0,
    }
    (out / "gold_v3_48_live_readiness_gap_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 48 PASTE_ME_LIVE_READINESS_GAP_SUMMARY")
    paste.append(f"status: {report_status}")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("live_ready: false")
    paste.append(f"deployment_blockers_present: true")
    paste.append(f"blocker_gap_count: {len(blocker_gaps)}")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append("")
    paste.append("INPUT_CANDLE_INVENTORY")
    paste.append(inv[["timeframe", "file", "required_for_stage48", "exists", "rows", "time_col", "first_time", "last_time", "status"]].to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(validation_df.to_string(index=False))
    paste.append("")
    paste.append("BLOCKER_GAPS")
    paste.append(blocker_gaps.to_string(index=False) if not blocker_gaps.empty else "none")
    paste.append("")
    paste.append("NEXT_REQUIRED_AUDIT_ONLY_ARTIFACTS")
    paste.append("1. H4 closed-row readiness checker")
    paste.append("2. rolling prior-60D q70 state builder")
    paste.append("3. full-candidate virtual monitoring ledger")
    paste.append("4. health gate restart/replay state schema")
    paste.append("5. rank-dedup contract parity test")
    paste.append("6. M5 pending-to-closed horizon adjudicator")
    (out / "gold_v3_48_PASTE_ME_LIVE_READINESS_GAP_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 48 closed-asof pool contract live-readiness gap audit-only report

Status: `{report_status}`

## Meaning

This is a gap report. It does not approve live trading.

## Summary

- report_ready: `{not hard_fail}`
- live_ready: `false`
- deployment_blockers_present: `true`
- blocker_gap_count: `{len(blocker_gaps)}`
- contract_mutated: `false`
- manual_candidate_demotion_or_removal: `false`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, or final signal.
"""
    (out / "GOLD_V3_48_CLOSED_ASOF_POOL_CONTRACT_LIVE_READINESS_GAP_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{report_status}] output_dir={out}")
    print(out / "gold_v3_48_PASTE_ME_LIVE_READINESS_GAP_SUMMARY.txt")
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
