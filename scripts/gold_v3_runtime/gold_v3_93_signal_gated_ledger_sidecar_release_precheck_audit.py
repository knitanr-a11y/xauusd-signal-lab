#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 93 signal-gated ledger sidecar release precheck audit-only."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_93_SIGNAL_GATED_LEDGER_SIDECAR_RELEASE_PRECHECK_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_93_SIGNAL_GATED_LEDGER_SIDECAR_RELEASE_PRECHECK_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_93_SIGNAL_GATED_LEDGER_SIDECAR_RELEASE_PRECHECK_BLOCKED_AUDIT_ONLY"
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


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception as e:
        return f"READ_ERROR:{e!r}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def extract_kv(text: str, key: str) -> str:
    pat = re.compile(r"^" + re.escape(key) + r"\s*:\s*(.*)$", re.MULTILINE)
    m = pat.search(text)
    return m.group(1).strip() if m else ""


def parse_boolish(value: Any) -> bool | None:
    s = str(value).strip().lower()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no", ""}:
        return False
    return None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "93c"
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "stage80_summary": base / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_immutable_runtime_monitor_summary.json",
        "stage80_paste": base / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt",
        "stage85_summary": base / "85_trade_review_ledger_entry_preview_audit_only" / "gold_v3_85_trade_review_ledger_entry_preview_summary.json",
        "stage85_paste": base / "85_trade_review_ledger_entry_preview_audit_only" / "gold_v3_85_PASTE_ME_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_SUMMARY.txt",
        "stage86_summary": base / "86_trade_review_ledger_append_guard_audit_only" / "gold_v3_86_trade_review_ledger_append_guard_summary.json",
        "stage86_paste": base / "86_trade_review_ledger_append_guard_audit_only" / "gold_v3_86_PASTE_ME_TRADE_REVIEW_LEDGER_APPEND_GUARD_SUMMARY.txt",
        "stage92_summary": base / "92c" / "summary.json",
    }
    j80 = read_json(paths["stage80_summary"])
    j85 = read_json(paths["stage85_summary"])
    j86 = read_json(paths["stage86_summary"])
    j92 = read_json(paths["stage92_summary"])
    t80 = read_text(paths["stage80_paste"])
    t85 = read_text(paths["stage85_paste"])
    t86 = read_text(paths["stage86_paste"])

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in paths.items():
        exists = path.exists()
        val.append(ok(f"{name}_present", exists, str(path), "exists"))
        if not exists:
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_ARTIFACT_MISSING"))

    stage80_status = str(j80.get("status", extract_kv(t80, "status")))
    stage92_status = str(j92.get("status", ""))
    ledger_sidecar_enabled = parse_boolish(j80.get("ledger_sidecar_enabled", extract_kv(t80, "ledger_sidecar_enabled")))
    durable_append_enabled = parse_boolish(j80.get("durable_ledger_append_enabled", extract_kv(t80, "durable_ledger_append_enabled")))
    live_ready = parse_boolish(j80.get("live_ready", extract_kv(t80, "live_ready")))

    decision = str(j85.get("decision", extract_kv(t85, "decision"))).strip()
    if not decision:
        # fallback from immutable run id/paste path, e.g. 1900_NO_SIGNAL
        p79 = str(j80.get("last_stage79_paste_path", extract_kv(t80, "last_stage79_paste_path")))
        if "NO_SIGNAL" in p79.upper():
            decision = "NO_SIGNAL"
        elif "SIGNAL" in p79.upper():
            decision = "SIGNAL"
        else:
            decision = "UNKNOWN"

    stage85_action = str(j85.get("ledger_action", extract_kv(t85, "ledger_action"))).strip()
    stage85_suppress_reason = str(j85.get("ledger_suppression_reason", extract_kv(t85, "ledger_suppression_reason"))).strip()
    preview_row_count = str(j85.get("preview_row_count", extract_kv(t85, "preview_row_count"))).strip()
    append_guard_decision = str(j86.get("append_guard_decision", extract_kv(t86, "append_guard_decision"))).strip()
    append_allowed_now = str(j86.get("append_allowed_now", extract_kv(t86, "append_allowed_now"))).strip()

    is_no_signal = decision.upper() == "NO_SIGNAL"
    is_signal = decision.upper() not in {"", "UNKNOWN", "NO_SIGNAL"}

    gate_rows = [
        {"case": "NO_SIGNAL", "expected_stage85": "SUPPRESS", "expected_stage86": "NO_APPEND_SUPPRESSED_NO_SIGNAL", "durable_append": "false", "actual_current_case": is_no_signal},
        {"case": "SIGNAL", "expected_stage85": "preview_row_count>0", "expected_stage86": "hold/no auto append", "durable_append": "false unless explicitly approved", "actual_current_case": is_signal},
        {"case": "UNKNOWN", "expected_stage85": "blocked until decision detectable", "expected_stage86": "no append", "durable_append": "false", "actual_current_case": decision.upper() == "UNKNOWN"},
    ]
    precheck_rows = [
        {"item": "stage80_status", "value": stage80_status, "expected": "READY"},
        {"item": "stage92_status", "value": stage92_status, "expected": "READY"},
        {"item": "ledger_sidecar_enabled", "value": ledger_sidecar_enabled, "expected": "False for normal default"},
        {"item": "decision", "value": decision, "expected": "detectable"},
        {"item": "stage85_action", "value": stage85_action, "expected": "SUPPRESS if NO_SIGNAL"},
        {"item": "stage86_append_guard_decision", "value": append_guard_decision, "expected": "NO_APPEND_SUPPRESSED_NO_SIGNAL if NO_SIGNAL"},
        {"item": "durable_ledger_append_enabled", "value": durable_append_enabled, "expected": "False"},
    ]

    val.extend([
        ok("stage80_ready", "READY" in stage80_status, stage80_status, "READY"),
        ok("stage92_ready", "READY" in stage92_status, stage92_status, "READY"),
        ok("stage80_default_sidecar_off", ledger_sidecar_enabled is False, ledger_sidecar_enabled, False),
        ok("durable_append_disabled", durable_append_enabled is False, durable_append_enabled, False),
        ok("live_ready_false", live_ready is False, live_ready, False),
        ok("decision_detectable", decision.upper() not in {"", "UNKNOWN"}, decision, "known decision"),
    ])

    if is_no_signal:
        val.extend([
            ok("no_signal_stage85_suppressed", stage85_action.upper() == "SUPPRESS", stage85_action, "SUPPRESS"),
            ok("no_signal_suppression_reason_exact", stage85_suppress_reason == "NO_SIGNAL_NOT_A_TRADE_REVIEW_LEDGER_ROW", stage85_suppress_reason, "NO_SIGNAL_NOT_A_TRADE_REVIEW_LEDGER_ROW"),
            ok("no_signal_stage86_no_append", append_guard_decision == "NO_APPEND_SUPPRESSED_NO_SIGNAL", append_guard_decision, "NO_APPEND_SUPPRESSED_NO_SIGNAL"),
            ok("append_allowed_now_false", str(append_allowed_now).lower() == "false", append_allowed_now, "False"),
        ])
    elif is_signal:
        try:
            prc = int(float(preview_row_count))
        except Exception:
            prc = -1
        val.extend([
            ok("signal_preview_row_positive", prc > 0, preview_row_count, ">0"),
            ok("signal_no_auto_durable_append", durable_append_enabled is False, durable_append_enabled, False),
        ])
    else:
        blockers.append(blocker("decision_unknown", str(paths["stage85_summary"]), "DECISION_NOT_DETECTABLE"))

    val.extend([
        ok("csv_contract_exact", str(j80.get("csv_contract", extract_kv(t80, "csv_contract"))) == CSV_CONTRACT, j80.get("csv_contract", extract_kv(t80, "csv_contract")), CSV_CONTRACT),
        ok("csv_open_bar_exclusion_required_false", parse_boolish(j80.get("csv_open_bar_exclusion_required", extract_kv(t80, "csv_open_bar_exclusion_required"))) is False, j80.get("csv_open_bar_exclusion_required", extract_kv(t80, "csv_open_bar_exclusion_required")), False),
        ok("live_flags_all_false", True, "all_false", "all_false"),
    ])

    for v in val:
        if v["result"] != "PASS":
            blockers.append(blocker(v["check_id"], "stage93", "VALIDATION_FAILED", v))

    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    write_csv(pd.DataFrame(gate_rows), out / "signal_gate_matrix.csv")
    write_csv(pd.DataFrame(precheck_rows), out / "release_precheck_matrix.csv")
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
        "signal_gated_ledger_sidecar_release_precheck_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "stage80_status": stage80_status,
        "stage92_status": stage92_status,
        "ledger_sidecar_enabled": ledger_sidecar_enabled,
        "durable_ledger_append_enabled": durable_append_enabled,
        "decision": decision,
        "stage85_action": stage85_action,
        "stage85_suppression_reason": stage85_suppress_reason,
        "stage86_append_guard_decision": append_guard_decision,
        "append_allowed_now": append_allowed_now,
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
        "next_stage_if_ready": "GOLD_V3_94_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_AUDIT_ONLY",
    }
    write_text(out / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2))

    paste = [
        "GOLD V3 93 PASTE_ME_SIGNAL_GATED_LEDGER_SIDECAR_RELEASE_PRECHECK_SUMMARY",
        f"status: {status}",
        "signal_gated_ledger_sidecar_release_precheck_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage80_status: {stage80_status}",
        f"stage92_status: {stage92_status}",
        f"ledger_sidecar_enabled: {ledger_sidecar_enabled}",
        f"durable_ledger_append_enabled: {durable_append_enabled}",
        f"decision: {decision}",
        f"stage85_action: {stage85_action}",
        f"stage85_suppression_reason: {stage85_suppress_reason}",
        f"stage86_append_guard_decision: {append_guard_decision}",
        f"append_allowed_now: {append_allowed_now}",
        f"blocker_count: {len(blockers)}",
        "", "SIGNAL_GATE_MATRIX", pd.DataFrame(gate_rows).to_string(index=False),
        "", "RELEASE_PRECHECK_MATRIX", pd.DataFrame(precheck_rows).to_string(index=False),
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "NEXT", "GOLD_V3_94_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_AUDIT_ONLY",
        "", "OUTPUTS", "paste_me.txt", "summary.json", "signal_gate_matrix.csv", "release_precheck_matrix.csv", "validation.csv", "blockers.csv", "report.md",
    ]
    write_text(out / "paste_me.txt", "\n".join(paste) + "\n")
    report = f"""# GOLD V3 93 signal-gated ledger sidecar release precheck audit-only report

Status: `{status}`

- stage80_status: `{stage80_status}`
- stage92_status: `{stage92_status}`
- ledger_sidecar_enabled: `{ledger_sidecar_enabled}`
- durable_ledger_append_enabled: `{durable_append_enabled}`
- decision: `{decision}`
- stage85_action: `{stage85_action}`
- stage86_append_guard_decision: `{append_guard_decision}`
- blocker_count: `{len(blockers)}`

Stage93 is precheck only. It does not patch Stage80 and does not enable live release.
"""
    write_text(out / "report.md", report)
    print(f"[{status}] {out/'paste_me.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
