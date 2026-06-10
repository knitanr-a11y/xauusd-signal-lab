#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 57 bounded replay window freeze decision audit-only.

Records human decision B and freezes mutable source replay to Stage54 checkpoint row-count bounds.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_57_BOUNDED_REPLAY_WINDOW_FREEZE_DECISION_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_57_BOUNDED_REPLAY_WINDOW_FREEZE_DECISION_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_57_BOUNDED_REPLAY_WINDOW_FREEZE_DECISION_BLOCKED_AUDIT_ONLY"
STAGE54_READY = "GOLD_V3_54_RESTART_REPLAY_CHECKPOINT_STATE_READY_AUDIT_ONLY"
STAGE55_BLOCKED = "GOLD_V3_55_REPLAY_FROM_CHECKPOINT_DRY_RUN_BLOCKED_AUDIT_ONLY"
STAGE56_READY = "GOLD_V3_56_MUTABLE_SOURCE_CANDLE_APPEND_ONLY_DRIFT_POLICY_READY_AUDIT_ONLY"
MUTABLE = {"m5_csv", "m15_csv", "h4_csv"}
DECISION = "B_BOUNDED_REPLAY_WINDOW_FREEZE"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "56_mutable_source_candle_append_only_drift_policy_audit_only").exists():
            return d
    raise FileNotFoundError("Stage56 output directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage54-dir", default="")
    p.add_argument("--stage55-dir", default="")
    p.add_argument("--stage56-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s54 = Path(a.stage54_dir).expanduser().resolve() if a.stage54_dir else g / "54_restart_replay_checkpoint_state_audit_only"
    s55 = Path(a.stage55_dir).expanduser().resolve() if a.stage55_dir else g / "55_replay_from_checkpoint_dry_run_audit_only"
    s56 = Path(a.stage56_dir).expanduser().resolve() if a.stage56_dir else g / "56_mutable_source_candle_append_only_drift_policy_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "57_bounded_replay_window_freeze_decision_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p54s = s54 / "gold_v3_54_checkpoint_summary.json"
    p54h = s54 / "gold_v3_54_source_artifact_hashes.csv"
    p54r = s54 / "gold_v3_54_restart_plan.csv"
    p55s = s55 / "gold_v3_55_replay_dry_run_summary.json"
    p55h = s55 / "gold_v3_55_hash_recheck.csv"
    p56s = s56 / "gold_v3_56_policy_summary.json"
    p56m = s56 / "gold_v3_56_drift_policy_matrix.csv"

    val: list[dict[str, Any]] = []
    for name, p in [("stage54_summary", p54s), ("stage54_hashes", p54h), ("stage54_restart", p54r), ("stage55_summary", p55s), ("stage55_hash_recheck", p55h), ("stage56_summary", p56s), ("stage56_policy_matrix", p56m)]:
        val.append(ok(f"{name}_present", p.exists(), str(p), "exists"))
    if any(v["result"] != "PASS" for v in val):
        pd.DataFrame(val).to_csv(out / "gold_v3_57_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j54, j55, j56 = read_json(p54s), read_json(p55s), read_json(p56s)
    for st, js, expected in [("54", j54, STAGE54_READY), ("55", j55, STAGE55_BLOCKED), ("56", j56, STAGE56_READY)]:
        val.append(ok(f"stage{st}_status_expected", js.get("status") == expected, js.get("status"), expected))
        for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
            val.append(ok(f"stage{st}_{key}_false", js.get(key) is False, js.get(key), False))

    val.append(ok("human_decision_b_recorded", DECISION == "B_BOUNDED_REPLAY_WINDOW_FREEZE", DECISION, "B_BOUNDED_REPLAY_WINDOW_FREEZE"))
    val.append(ok("stage56_policy_ready", j56.get("policy_ready") is True, j56.get("policy_ready"), True))
    val.append(ok("stage55_strict_replay_not_ready_expected", j56.get("stage55_strict_replay_ready") is False, j56.get("stage55_strict_replay_ready"), False))
    val.append(ok("immutable_state_drift_zero", j56.get("immutable_state_drift_blocker_count") == 0, j56.get("immutable_state_drift_blocker_count"), 0))
    val.append(ok("missing_artifact_zero", j56.get("missing_artifact_blocker_count") == 0, j56.get("missing_artifact_blocker_count"), 0))
    val.append(ok("mutable_rewrite_zero", j56.get("mutable_source_rewrite_blocker_count") == 0, j56.get("mutable_source_rewrite_blocker_count"), 0))
    val.append(ok("mutable_truncation_zero", j56.get("mutable_source_truncation_blocker_count") == 0, j56.get("mutable_source_truncation_blocker_count"), 0))

    policy = pd.read_csv(p56m, encoding="utf-8-sig")
    mutable_rows = policy[policy["artifact_id"].astype(str).isin(MUTABLE)].copy()
    mutable_rows["decision"] = DECISION
    mutable_rows["checkpoint_row_count"] = mutable_rows["expected_row_count_if_csv"]
    mutable_rows["current_row_count"] = mutable_rows["current_row_count_if_csv"]
    mutable_rows["outside_frozen_window_rows"] = pd.to_numeric(mutable_rows["current_row_count"], errors="coerce").fillna(0).astype(int) - pd.to_numeric(mutable_rows["checkpoint_row_count"], errors="coerce").fillna(0).astype(int)
    mutable_rows["bounded_replay_rule"] = "use_rows_1_to_checkpoint_row_count_only"
    mutable_rows["rows_after_checkpoint_policy"] = "outside_frozen_replay_window_do_not_delete_do_not_use_for_checkpoint_parity"
    mutable_rows["strict_stage55_status"] = "remains_blocked_by_full_file_hash"
    mutable_rows.to_csv(out / "gold_v3_57_mutable_source_window_freeze.csv", index=False, encoding="utf-8-sig")

    contract_rows = []
    for _, r in policy.iterrows():
        aid = str(r["artifact_id"])
        role = "mutable_source_candle" if aid in MUTABLE else "immutable_state_artifact"
        if role == "mutable_source_candle":
            rule = "bounded_replay_uses_checkpoint_row_count; appended rows excluded from checkpoint parity"
        else:
            rule = "strict_hash_and_row_count_must_match"
        contract_rows.append({
            "decision": DECISION,
            "artifact_id": aid,
            "artifact_role": role,
            "policy_classification": r.get("policy_classification", ""),
            "checkpoint_row_count": r.get("expected_row_count_if_csv", ""),
            "current_row_count": r.get("current_row_count_if_csv", ""),
            "bounded_replay_rule": rule,
            "live_ready": False,
            "mt5_execution_enabled": False,
            "final_signal_enabled": False,
        })
    contract = pd.DataFrame(contract_rows)
    contract.to_csv(out / "gold_v3_57_bounded_replay_window_contract.csv", index=False, encoding="utf-8-sig")

    val.append(ok("mutable_source_contract_rows_present", len(mutable_rows) == len(MUTABLE), len(mutable_rows), len(MUTABLE)))
    val.append(ok("outside_frozen_window_nonnegative", bool((mutable_rows["outside_frozen_window_rows"] >= 0).all()), mutable_rows["outside_frozen_window_rows"].tolist(), ">=0"))
    val.append(ok("contract_rows_match_policy_rows", len(contract) == len(policy), len(contract), len(policy)))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_57_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "human_decision": DECISION,
        "bounded_replay_contract_ready": failed.empty,
        "stage55_strict_replay_ready": False,
        "stage56_policy_ready": j56.get("policy_ready"),
        "mutable_source_contract_rows": int(len(mutable_rows)),
        "immutable_state_drift_blocker_count": j56.get("immutable_state_drift_blocker_count"),
        "mutable_source_rewrite_blocker_count": j56.get("mutable_source_rewrite_blocker_count"),
        "mutable_source_truncation_blocker_count": j56.get("mutable_source_truncation_blocker_count"),
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_57_bounded_replay_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 57 PASTE_ME_BOUNDED_REPLAY_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("bounded_replay_contract_ready: " + str(failed.empty).lower())
    paste.append(f"human_decision: {DECISION}")
    paste.append("stage55_strict_replay_ready: false")
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"mutable_source_contract_rows: {len(mutable_rows)}")
    paste.append(f"immutable_state_drift_blocker_count: {j56.get('immutable_state_drift_blocker_count')}")
    paste.append(f"mutable_source_rewrite_blocker_count: {j56.get('mutable_source_rewrite_blocker_count')}")
    paste.append(f"mutable_source_truncation_blocker_count: {j56.get('mutable_source_truncation_blocker_count')}")
    paste.append("")
    paste.append("MUTABLE_SOURCE_WINDOW_FREEZE")
    paste.append(mutable_rows[["artifact_id", "policy_classification", "checkpoint_row_count", "current_row_count", "outside_frozen_window_rows", "bounded_replay_rule"]].to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_57_bounded_replay_window_contract.csv")
    paste.append("gold_v3_57_mutable_source_window_freeze.csv")
    paste.append("gold_v3_57_validation_matrix.csv")
    (out / "gold_v3_57_PASTE_ME_BOUNDED_REPLAY_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "GOLD_V3_57_REPORT.md").write_text(f"# GOLD V3 57 bounded replay window freeze decision audit-only report\n\nStatus: `{status}`\n\nHuman decision: `{DECISION}`\n\nStage55 strict replay remains not-ready. Audit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_57_PASTE_ME_BOUNDED_REPLAY_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
