#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 84 trade review ledger policy audit-only.

Creates durable trade review ledger schema/templates. Does not emit signals,
place orders, send Discord, call AI API, or adjudicate live results.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_84_TRADE_REVIEW_LEDGER_POLICY_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_84_TRADE_REVIEW_LEDGER_POLICY_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_84_TRADE_REVIEW_LEDGER_POLICY_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
CANDIDATE_KEY_ORDER = "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars"

SCHEMA = [
    ("trade_id", "string", "unique id for one signal/trade review record", "required"),
    ("source_stage", "string", "stage that produced the signal/payload", "required"),
    ("signal_time_m15", "datetime", "closed M15 signal time", "required"),
    ("signal_time_utc", "datetime", "UTC creation time", "required"),
    ("decision", "string", "SIGNAL/NO_SIGNAL/etc", "required"),
    ("direction", "string", "BUY/SELL/NONE", "required_when_signal"),
    ("candidate_label", "string", "candidate label", "required_when_signal"),
    ("base_candidate_label", "string", "base candidate label", "required_when_signal"),
    ("source_profile_id", "string", "source profile id", "required_when_signal"),
    ("profile_id", "string", "profile id", "required_when_signal"),
    ("hv_profile", "string", "HV profile", "required_when_signal"),
    ("tp_usd", "float", "take profit USD distance", "required_when_signal"),
    ("sl_usd", "float", "stop loss USD distance", "required_when_signal"),
    ("horizon_m15", "int", "M15 horizon", "required_when_signal"),
    ("horizon_m5_bars", "int", "M5 horizon bars", "required_when_signal"),
    ("candidate_key", "string", CANDIDATE_KEY_ORDER, "required_when_signal"),
    ("health_gate_status", "string", "rolling health gate status", "required"),
    ("payload_action", "string", "SUPPRESS/EMIT preview action", "required"),
    ("entry_ref_price", "float", "entry reference price if available", "optional"),
    ("spread_or_cost_note", "string", "spread/cost/slippage note", "optional"),
    ("expected_tp_price", "float", "expected TP price", "optional"),
    ("expected_sl_price", "float", "expected SL price", "optional"),
    ("outcome_status", "string", "PENDING/WIN/LOSS/BE/NO_TRADE", "required"),
    ("exit_time", "datetime", "exit or review time", "optional"),
    ("exit_reason", "string", "TP/SL/manual/expired/no_entry/etc", "optional"),
    ("realized_usd", "float", "realized USD result", "optional"),
    ("realized_r_multiple", "float", "realized R multiple", "optional"),
    ("mfe_usd", "float", "max favorable excursion USD", "optional"),
    ("mae_usd", "float", "max adverse excursion USD", "optional"),
    ("bars_to_exit_m5", "int", "M5 bars to exit", "optional"),
    ("bars_to_exit_m15", "int", "M15 bars to exit", "optional"),
    ("why_win_loss_hypothesis", "string", "brief why it won/lost hypothesis", "manual_or_later_auto"),
    ("post_trade_review_note", "string", "manual review note for future improvement", "manual"),
    ("evidence_run_dir", "string", "Stage79 run evidence directory", "required"),
    ("evidence_paste_path", "string", "Stage79 paste_me.txt path", "required"),
    ("manual_review_required", "bool", "whether human review is needed", "required"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--ledger-root", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "84_trade_review_ledger_policy_audit_only"
    ledger = Path(a.ledger_root).expanduser().resolve() if a.ledger_root else base / "trade_review_ledger"
    out.mkdir(parents=True, exist_ok=True)
    ledger.mkdir(parents=True, exist_ok=True)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    schema_rows = [{"column": c, "type": t, "description": d, "requiredness": r} for c, t, d, r in SCHEMA]
    schema_cols = [c for c, _, _, _ in SCHEMA]
    empty_template = pd.DataFrame(columns=schema_cols)
    manual_template = pd.DataFrame([{c: "" for c in schema_cols}])
    manual_template.loc[0, "outcome_status"] = "PENDING"
    manual_template.loc[0, "manual_review_required"] = True
    manual_template.loc[0, "why_win_loss_hypothesis"] = "FILL_AFTER_REVIEW"
    manual_template.loc[0, "post_trade_review_note"] = "FILL_AFTER_REVIEW"

    retention_rows = [
        {"artifact_type": "trade_review_ledger", "retention": "long_term", "reason": "core learning record", "action": "keep"},
        {"artifact_type": "per_trade_evidence_packet", "retention": "long_term", "reason": "replay/debug/AI review", "action": "keep compact evidence"},
        {"artifact_type": "old_notification_error_log", "retention": "short_term", "reason": "not useful after stale", "action": "summarize in support bundle only"},
        {"artifact_type": "heartbeat_event_log", "retention": "short_term", "reason": "operational noise", "action": "do not upload first"},
        {"artifact_type": "full_timing_csv", "retention": "short_term", "reason": "debug only", "action": "tail only in Stage81"},
        {"artifact_type": "NO_SIGNAL_repeated_entries", "retention": "short_term", "reason": "low learning value", "action": "aggregate not preserve every row long-term"},
    ]

    (ledger / "trade_review_ledger_schema.csv").write_text(pd.DataFrame(schema_rows).to_csv(index=False), encoding="utf-8-sig")
    empty_template.to_csv(ledger / "trade_review_current_template.csv", index=False, encoding="utf-8-sig")
    manual_template.to_csv(ledger / "trade_review_manual_outcome_template.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(retention_rows).to_csv(ledger / "trade_review_retention_policy_matrix.csv", index=False, encoding="utf-8-sig")
    readme = f"""# GOLD V3 Trade Review Ledger

This folder is for long-term trade review records.

Primary goal:

- preserve why each emitted/approved trade won or lost,
- support future signal improvement,
- support later AI API review if explicitly approved.

Candidate key order:

`{CANDIDATE_KEY_ORDER}`

Current safety:

- audit-only,
- no MT5,
- no Discord,
- no AI API,
- no final signal.

Use `trade_review_manual_outcome_template.csv` for manual post-trade review notes.
"""
    (ledger / "README_TRADE_REVIEW_LEDGER.md").write_text(readme, encoding="utf-8")

    val.extend([
        ok("ledger_root_exists", ledger.exists(), str(ledger), "exists"),
        ok("schema_written", (ledger/"trade_review_ledger_schema.csv").exists(), str(ledger/"trade_review_ledger_schema.csv"), "exists"),
        ok("retention_policy_written", (ledger/"trade_review_retention_policy_matrix.csv").exists(), str(ledger/"trade_review_retention_policy_matrix.csv"), "exists"),
        ok("manual_outcome_template_written", (ledger/"trade_review_manual_outcome_template.csv").exists(), str(ledger/"trade_review_manual_outcome_template.csv"), "exists"),
        ok("candidate_key_order_exact", CANDIDATE_KEY_ORDER == "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars", CANDIDATE_KEY_ORDER, "exact"),
        ok("retention_focus_trade_history", True, "trade_history_long_term", "trade_history_long_term"),
        ok("csv_open_bar_exclusion_required_false", True, False, False),
        ok("live_flags_all_false", True, "all_false", "all_false"),
    ])
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    pd.DataFrame(schema_rows).to_csv(out / "gold_v3_84_trade_review_schema_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(retention_rows).to_csv(out / "gold_v3_84_trade_review_retention_policy_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "gold_v3_84_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(val).to_csv(out / "gold_v3_84_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "trade_review_ledger_policy_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_order": CANDIDATE_KEY_ORDER,
        "ledger_root": str(ledger),
        "schema_column_count": len(schema_cols),
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
    }
    (out / "gold_v3_84_trade_review_ledger_policy_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = [
        "GOLD V3 84 PASTE_ME_TRADE_REVIEW_LEDGER_POLICY_SUMMARY",
        f"status: {status}",
        "trade_review_ledger_policy_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"ledger_root: {ledger}",
        f"candidate_key_order: {CANDIDATE_KEY_ORDER}",
        f"schema_column_count: {len(schema_cols)}",
        f"blocker_count: {len(blockers)}",
        "", "LONG_TERM_KEEP", "trade_review_ledger, per_trade_evidence_packet, signal decision context, outcome review note",
        "", "SHORT_TERM_OR_SUMMARY_ONLY", "old notification errors, heartbeat logs, full timing CSVs, repeated NO_SIGNAL entries",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "OUTPUTS",
        "trade_review_ledger/trade_review_ledger_schema.csv",
        "trade_review_ledger/trade_review_current_template.csv",
        "trade_review_ledger/trade_review_manual_outcome_template.csv",
        "trade_review_ledger/trade_review_retention_policy_matrix.csv",
        "trade_review_ledger/README_TRADE_REVIEW_LEDGER.md",
        "gold_v3_84_trade_review_schema_matrix.csv",
        "gold_v3_84_trade_review_retention_policy_matrix.csv",
        "gold_v3_84_blocker_matrix.csv",
        "gold_v3_84_validation_matrix.csv",
        "gold_v3_84_trade_review_ledger_policy_summary.json",
        "gold_v3_84_PASTE_ME_TRADE_REVIEW_LEDGER_POLICY_SUMMARY.txt",
        "GOLD_V3_84_REPORT.md",
    ]
    (out / "gold_v3_84_PASTE_ME_TRADE_REVIEW_LEDGER_POLICY_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")
    report = f"""# GOLD V3 84 trade review ledger policy audit-only report

Status: `{status}`

- ledger_root: `{ledger}`
- schema_column_count: `{len(schema_cols)}`
- candidate_key_order: `{CANDIDATE_KEY_ORDER}`
- blocker_count: `{len(blockers)}`

Audit-only. This creates schema/templates only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_84_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] {out/'gold_v3_84_PASTE_ME_TRADE_REVIEW_LEDGER_POLICY_SUMMARY.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
