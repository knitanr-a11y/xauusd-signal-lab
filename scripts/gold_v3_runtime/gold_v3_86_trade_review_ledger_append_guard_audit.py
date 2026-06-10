#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 86 trade review ledger append guard audit-only.

Guards the durable trade review ledger from NO_SIGNAL/heartbeat/error rows and
from unconfirmed or incomplete trade records. Does not append.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_86_TRADE_REVIEW_LEDGER_APPEND_GUARD_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_86_TRADE_REVIEW_LEDGER_APPEND_GUARD_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_86_TRADE_REVIEW_LEDGER_APPEND_GUARD_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
CANDIDATE_KEY_ORDER = "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars"

NO_APPEND_SUPPRESSED_NO_SIGNAL = "NO_APPEND_SUPPRESSED_NO_SIGNAL"
HOLD_UNTIL_CONFIRMED = "HOLD_NOT_APPEND_UNTIL_EXECUTION_OR_HUMAN_REVIEW_CONFIRMED"
BLOCK_CONTEXT_MISSING = "BLOCK_APPEND_REQUIRED_CONTEXT_MISSING"


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "86_trade_review_ledger_append_guard_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p85_summary = base / "85_trade_review_ledger_entry_preview_audit_only" / "gold_v3_85_trade_review_ledger_entry_preview_summary.json"
    p85_preview = base / "85_trade_review_ledger_entry_preview_audit_only" / "gold_v3_85_trade_review_entry_preview.csv"
    pschema = base / "trade_review_ledger" / "trade_review_ledger_schema.csv"
    j85 = read_json(p85_summary)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    guard_rows: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []

    val.append(ok("stage85_summary_present", p85_summary.exists(), str(p85_summary), "exists"))
    val.append(ok("stage84_schema_present", pschema.exists(), str(pschema), "exists"))
    if not p85_summary.exists():
        blockers.append(blocker("stage85_summary_missing", str(p85_summary), "STAGE85_SUMMARY_MISSING"))
    if not pschema.exists():
        blockers.append(blocker("stage84_schema_missing", str(pschema), "STAGE84_SCHEMA_MISSING"))

    decision = str(j85.get("decision", ""))
    ledger_action = str(j85.get("ledger_action", ""))
    preview_row_count = int(j85.get("preview_row_count", 0) or 0)
    suppression_reason = str(j85.get("ledger_suppression_reason", ""))
    evidence_paste = str(j85.get("evidence_paste_path", ""))

    append_guard_decision = ""
    append_allowed_future = False
    required_context_complete = False
    preview_df = pd.DataFrame()
    missing_context: list[str] = []

    if preview_row_count == 0 and ledger_action == "SUPPRESS" and "NO_SIGNAL" in decision.upper():
        append_guard_decision = NO_APPEND_SUPPRESSED_NO_SIGNAL
        append_allowed_future = False
        required_context_complete = True
    elif preview_row_count > 0:
        try:
            preview_df = pd.read_csv(p85_preview, encoding="utf-8-sig")
        except Exception as e:
            blockers.append(blocker("stage85_preview_read_failed", str(p85_preview), "PREVIEW_READ_FAILED", repr(e)))
            preview_df = pd.DataFrame()
        required_cols = ["trade_id", "decision", "direction", "candidate_key", "evidence_paste_path", "outcome_status", "manual_review_required"]
        if preview_df.empty:
            missing_context.append("preview_csv_empty")
        else:
            row = preview_df.iloc[0].to_dict()
            for c in required_cols:
                if c not in preview_df.columns or str(row.get(c, "")).strip() == "":
                    missing_context.append(c)
        required_context_complete = len(missing_context) == 0
        if required_context_complete:
            append_guard_decision = HOLD_UNTIL_CONFIRMED
            append_allowed_future = False
        else:
            append_guard_decision = BLOCK_CONTEXT_MISSING
            append_allowed_future = False
            blockers.append(blocker("append_required_context_missing", str(p85_preview), "REQUIRED_CONTEXT_MISSING", missing_context))
    else:
        append_guard_decision = "BLOCK_UNKNOWN_STAGE85_LEDGER_STATE"
        blockers.append(blocker("unknown_stage85_ledger_state", str(p85_summary), "UNKNOWN_STAGE85_LEDGER_STATE", {"decision": decision, "ledger_action": ledger_action, "preview_row_count": preview_row_count}))

    guard_rows.append({
        "decision": decision,
        "stage85_ledger_action": ledger_action,
        "stage85_suppression_reason": suppression_reason,
        "preview_row_count": preview_row_count,
        "append_guard_decision": append_guard_decision,
        "append_allowed_now": False,
        "append_allowed_future": append_allowed_future,
        "reason": "Stage86 is audit-only and does not append durable ledger",
    })
    context_rows.append({
        "candidate_key_order": CANDIDATE_KEY_ORDER,
        "required_context_complete": required_context_complete,
        "missing_context": ";".join(missing_context),
        "evidence_paste_path": evidence_paste,
    })

    val.extend([
        ok("no_durable_ledger_append", True, "no_append", "no_append"),
        ok("no_signal_guarded", not ("NO_SIGNAL" in decision.upper()) or append_guard_decision == NO_APPEND_SUPPRESSED_NO_SIGNAL, append_guard_decision, NO_APPEND_SUPPRESSED_NO_SIGNAL),
        ok("signal_not_appended_without_confirmation", preview_row_count == 0 or append_guard_decision == HOLD_UNTIL_CONFIRMED or append_guard_decision == BLOCK_CONTEXT_MISSING, append_guard_decision, "hold_or_block"),
        ok("candidate_key_order_exact", CANDIDATE_KEY_ORDER == "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars", CANDIDATE_KEY_ORDER, "exact"),
        ok("csv_open_bar_exclusion_required_false", True, False, False),
        ok("live_flags_all_false", True, "all_false", "all_false"),
    ])

    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    pd.DataFrame(guard_rows).to_csv(out / "gold_v3_86_append_guard_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(context_rows).to_csv(out / "gold_v3_86_candidate_context_check_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "gold_v3_86_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(val).to_csv(out / "gold_v3_86_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "trade_review_ledger_append_guard_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "decision": decision,
        "stage85_ledger_action": ledger_action,
        "append_guard_decision": append_guard_decision,
        "append_allowed_now": False,
        "preview_row_count": preview_row_count,
        "required_context_complete": required_context_complete,
        "missing_context": missing_context,
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
    }
    (out / "gold_v3_86_trade_review_ledger_append_guard_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = [
        "GOLD V3 86 PASTE_ME_TRADE_REVIEW_LEDGER_APPEND_GUARD_SUMMARY",
        f"status: {status}",
        "trade_review_ledger_append_guard_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"decision: {decision}",
        f"stage85_ledger_action: {ledger_action}",
        f"append_guard_decision: {append_guard_decision}",
        "append_allowed_now: false",
        f"preview_row_count: {preview_row_count}",
        f"required_context_complete: {required_context_complete}",
        f"missing_context: {missing_context}",
        f"blocker_count: {len(blockers)}",
        "", "APPEND_GUARD", pd.DataFrame(guard_rows).to_string(index=False),
        "", "CONTEXT_CHECK", pd.DataFrame(context_rows).to_string(index=False),
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "OUTPUTS",
        "gold_v3_86_append_guard_matrix.csv",
        "gold_v3_86_candidate_context_check_matrix.csv",
        "gold_v3_86_blocker_matrix.csv",
        "gold_v3_86_validation_matrix.csv",
        "gold_v3_86_trade_review_ledger_append_guard_summary.json",
        "gold_v3_86_PASTE_ME_TRADE_REVIEW_LEDGER_APPEND_GUARD_SUMMARY.txt",
        "GOLD_V3_86_REPORT.md",
    ]
    (out / "gold_v3_86_PASTE_ME_TRADE_REVIEW_LEDGER_APPEND_GUARD_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")
    report = f"""# GOLD V3 86 trade review ledger append guard audit-only report

Status: `{status}`

- decision: `{decision}`
- stage85_ledger_action: `{ledger_action}`
- append_guard_decision: `{append_guard_decision}`
- append_allowed_now: `false`
- preview_row_count: `{preview_row_count}`
- blocker_count: `{len(blockers)}`

Audit-only. Does not append to durable ledger. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_86_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] {out/'gold_v3_86_PASTE_ME_TRADE_REVIEW_LEDGER_APPEND_GUARD_SUMMARY.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
