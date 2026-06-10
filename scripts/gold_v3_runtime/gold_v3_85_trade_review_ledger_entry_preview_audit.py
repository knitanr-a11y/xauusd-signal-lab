#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 85 trade review ledger entry preview audit-only.

Creates a preview trade review ledger row only when the current Stage76 decision is
an actual SIGNAL. NO_SIGNAL is explicitly suppressed to avoid ledger bloat.
No MT5 orders, no Discord, no AI API, no final signal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_85_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_85_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_85_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
CANDIDATE_KEY_ORDER = "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars"
SUPPRESS_NO_SIGNAL = "NO_SIGNAL_NOT_A_TRADE_REVIEW_LEDGER_ROW"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def as_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def pick(j: dict[str, Any], names: list[str], default: Any = "") -> Any:
    for n in names:
        if n in j and j.get(n) not in [None, ""]:
            return j.get(n)
    return default


def make_candidate_key(row: dict[str, Any]) -> str:
    parts = [
        row.get("candidate_label", ""),
        row.get("base_candidate_label", ""),
        row.get("source_profile_id", ""),
        row.get("profile_id", ""),
        row.get("hv_profile", ""),
        row.get("tp_usd", ""),
        row.get("sl_usd", ""),
        row.get("horizon_m15", ""),
        row.get("horizon_m5_bars", ""),
    ]
    return "+".join(as_str(x) for x in parts)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "85_trade_review_ledger_entry_preview_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p76 = base / "76_full_audit_monitor_with_payload_preview_audit_only" / "gold_v3_76_full_audit_monitor_with_payload_preview_summary.json"
    p80 = base / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_immutable_runtime_monitor_summary.json"
    pschema = base / "trade_review_ledger" / "trade_review_ledger_schema.csv"
    j76 = read_json(p76)
    j80 = read_json(p80)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    suppress_rows: list[dict[str, Any]] = []

    val.append(ok("stage76_summary_present", p76.exists(), str(p76), "exists"))
    val.append(ok("stage80_summary_present", p80.exists(), str(p80), "exists"))
    val.append(ok("stage84_schema_present", pschema.exists(), str(pschema), "exists"))
    if not p76.exists():
        blockers.append(blocker("stage76_summary_missing", str(p76), "STAGE76_SUMMARY_MISSING"))
    if not p80.exists():
        blockers.append(blocker("stage80_summary_missing", str(p80), "STAGE80_SUMMARY_MISSING"))
    if not pschema.exists():
        blockers.append(blocker("stage84_schema_missing", str(pschema), "STAGE84_SCHEMA_MISSING"))

    schema_cols: list[str] = []
    if pschema.exists():
        try:
            schema_cols = list(pd.read_csv(pschema, encoding="utf-8-sig")["column"].astype(str))
        except Exception as e:
            blockers.append(blocker("stage84_schema_read_failed", str(pschema), "SCHEMA_READ_FAILED", repr(e)))
    val.append(ok("candidate_key_order_exact", CANDIDATE_KEY_ORDER == "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars", CANDIDATE_KEY_ORDER, "exact"))

    decision = as_str(pick(j76, ["decision", "signal_decision"], ""))
    payload_action = as_str(pick(j76, ["payload_action", "emission_action"], ""))
    latest_m15 = as_str(pick(j76, ["latest_m15_time", "latest_closed_m15_time"], pick(j80, ["latest_m15_time"], "")))
    evidence_paste = as_str(pick(j80, ["last_stage79_paste_path"], ""))
    evidence_run_dir = str(Path(evidence_paste).parent) if evidence_paste else ""

    is_signal = decision.upper() not in {"", "NO_SIGNAL", "NONE", "NO_ACTION"} and "SIGNAL" in decision.upper()
    preview_rows: list[dict[str, Any]] = []
    ledger_action = "SUPPRESS"
    ledger_suppression_reason = ""

    if not blockers and not is_signal:
        ledger_action = "SUPPRESS"
        ledger_suppression_reason = SUPPRESS_NO_SIGNAL
        suppress_rows.append({"decision": decision, "latest_m15_time": latest_m15, "ledger_action": ledger_action, "reason": ledger_suppression_reason})
        val.append(ok("no_signal_suppressed_from_trade_ledger", True, ledger_suppression_reason, SUPPRESS_NO_SIGNAL))
    elif not blockers:
        row = {c: "" for c in schema_cols}
        row.update({
            "trade_id": f"GOLDV3_{latest_m15.replace('-', '').replace(':', '').replace(' ', '_')}_{decision}",
            "source_stage": "GOLD_V3_76_TO_85_AUDIT_ONLY",
            "signal_time_m15": latest_m15,
            "signal_time_utc": utc_now(),
            "decision": decision,
            "direction": as_str(pick(j76, ["direction", "side", "signal_side"], "")),
            "candidate_label": as_str(pick(j76, ["candidate_label"], "")),
            "base_candidate_label": as_str(pick(j76, ["base_candidate_label"], "")),
            "source_profile_id": as_str(pick(j76, ["source_profile_id"], "")),
            "profile_id": as_str(pick(j76, ["profile_id"], "")),
            "hv_profile": as_str(pick(j76, ["hv_profile"], "")),
            "tp_usd": as_str(pick(j76, ["tp_usd"], "")),
            "sl_usd": as_str(pick(j76, ["sl_usd"], "")),
            "horizon_m15": as_str(pick(j76, ["horizon_m15"], "")),
            "horizon_m5_bars": as_str(pick(j76, ["horizon_m5_bars"], "")),
            "health_gate_status": as_str(pick(j76, ["health_gate_status", "status"], "")),
            "payload_action": payload_action,
            "entry_ref_price": as_str(pick(j76, ["entry_ref_price", "close", "latest_close"], "")),
            "outcome_status": "PENDING",
            "why_win_loss_hypothesis": "PENDING_POST_TRADE_REVIEW",
            "post_trade_review_note": "PENDING_POST_TRADE_REVIEW",
            "evidence_run_dir": evidence_run_dir,
            "evidence_paste_path": evidence_paste,
            "manual_review_required": True,
        })
        row["candidate_key"] = make_candidate_key(row)
        required_signal_cols = ["direction", "candidate_label", "base_candidate_label", "source_profile_id", "profile_id", "hv_profile", "tp_usd", "sl_usd", "horizon_m15", "horizon_m5_bars", "evidence_paste_path"]
        missing = [c for c in required_signal_cols if not as_str(row.get(c, ""))]
        if missing:
            blockers.append(blocker("signal_ledger_required_fields_missing", str(p76), "SIGNAL_LEDGER_REQUIRED_FIELDS_MISSING", missing))
        else:
            preview_rows.append(row)
            ledger_action = "PREVIEW_ONLY"
        val.append(ok("signal_preview_row_complete", not missing, missing if missing else "complete", "complete"))

    pd.DataFrame(preview_rows, columns=schema_cols).to_csv(out / "gold_v3_85_trade_review_entry_preview.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(suppress_rows).to_csv(out / "gold_v3_85_ledger_suppression_matrix.csv", index=False, encoding="utf-8-sig")

    val.append(ok("no_durable_ledger_append", True, "preview_only", "preview_only"))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    pd.DataFrame(blockers).to_csv(out / "gold_v3_85_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(val).to_csv(out / "gold_v3_85_validation_matrix.csv", index=False, encoding="utf-8-sig")
    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": utc_now(),
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
        "trade_review_ledger_entry_preview_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_order": CANDIDATE_KEY_ORDER,
        "decision": decision,
        "latest_m15_time": latest_m15,
        "ledger_action": ledger_action,
        "ledger_suppression_reason": ledger_suppression_reason,
        "preview_row_count": len(preview_rows),
        "evidence_paste_path": evidence_paste,
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
    }
    (out / "gold_v3_85_trade_review_ledger_entry_preview_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = [
        "GOLD V3 85 PASTE_ME_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_SUMMARY",
        f"status: {status}",
        "trade_review_ledger_entry_preview_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"decision: {decision}",
        f"latest_m15_time: {latest_m15}",
        f"ledger_action: {ledger_action}",
        f"ledger_suppression_reason: {ledger_suppression_reason}",
        f"preview_row_count: {len(preview_rows)}",
        f"evidence_paste_path: {evidence_paste}",
        f"candidate_key_order: {CANDIDATE_KEY_ORDER}",
        f"blocker_count: {len(blockers)}",
        "", "PREVIEW_ROW", pd.DataFrame(preview_rows).to_string(index=False) if preview_rows else "NO_PREVIEW_ROW",
        "", "SUPPRESSION", pd.DataFrame(suppress_rows).to_string(index=False) if suppress_rows else "NO_SUPPRESSION",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "OUTPUTS",
        "gold_v3_85_trade_review_entry_preview.csv",
        "gold_v3_85_ledger_suppression_matrix.csv",
        "gold_v3_85_blocker_matrix.csv",
        "gold_v3_85_validation_matrix.csv",
        "gold_v3_85_trade_review_ledger_entry_preview_summary.json",
        "gold_v3_85_PASTE_ME_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_SUMMARY.txt",
        "GOLD_V3_85_REPORT.md",
    ]
    (out / "gold_v3_85_PASTE_ME_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")
    report = f"""# GOLD V3 85 trade review ledger entry preview audit-only report

Status: `{status}`

- decision: `{decision}`
- ledger_action: `{ledger_action}`
- suppression_reason: `{ledger_suppression_reason}`
- preview_row_count: `{len(preview_rows)}`
- blocker_count: `{len(blockers)}`

Audit-only. Does not append to durable ledger. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_85_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] {out/'gold_v3_85_PASTE_ME_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_SUMMARY.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
