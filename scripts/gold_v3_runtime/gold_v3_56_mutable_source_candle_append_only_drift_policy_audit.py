#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 56 mutable source candle append-only drift policy audit-only.

Classifies Stage55 strict checkpoint replay BLOCKED causes.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_56_MUTABLE_SOURCE_CANDLE_APPEND_ONLY_DRIFT_POLICY_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_56_MUTABLE_SOURCE_CANDLE_APPEND_ONLY_DRIFT_POLICY_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_56_MUTABLE_SOURCE_CANDLE_APPEND_ONLY_DRIFT_POLICY_BLOCKED_AUDIT_ONLY"
STAGE55_BLOCKED = "GOLD_V3_55_REPLAY_FROM_CHECKPOINT_DRY_RUN_BLOCKED_AUDIT_ONLY"
MUTABLE = {"m5_csv", "m15_csv", "h4_csv"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "55_replay_from_checkpoint_dry_run_audit_only").exists():
            return d
    raise FileNotFoundError("Stage55 output directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage55-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def classify(row: pd.Series) -> str:
    aid = str(row.get("artifact_id", ""))
    exists = bool(row.get("exists", False))
    sha_match = bool(row.get("sha_match", False))
    row_match = bool(row.get("row_count_match", False))
    if not exists:
        return "MISSING_ARTIFACT_BLOCKER"
    if sha_match and row_match:
        return "STABLE_OK"
    exp = row.get("expected_row_count_if_csv", "")
    cur = row.get("current_row_count_if_csv", "")
    try:
        exp_i = int(float(exp))
        cur_i = int(float(cur))
        has_rows = True
    except Exception:
        exp_i = cur_i = 0
        has_rows = False
    if aid in MUTABLE:
        if has_rows and cur_i > exp_i:
            return "MUTABLE_SOURCE_ADVANCED_APPEND_LIKELY"
        if has_rows and cur_i < exp_i:
            return "MUTABLE_SOURCE_TRUNCATION_BLOCKER"
        return "MUTABLE_SOURCE_REWRITE_BLOCKER"
    return "IMMUTABLE_STATE_DRIFT_BLOCKER"


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s55 = Path(a.stage55_dir).expanduser().resolve() if a.stage55_dir else g / "55_replay_from_checkpoint_dry_run_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "56_mutable_source_candle_append_only_drift_policy_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p_summary = s55 / "gold_v3_55_replay_dry_run_summary.json"
    p_recheck = s55 / "gold_v3_55_hash_recheck.csv"
    p_mismatch = s55 / "gold_v3_55_hash_mismatch_details.csv"
    p_val55 = s55 / "gold_v3_55_validation_matrix.csv"

    val: list[dict[str, Any]] = []
    for name, p in [("stage55_summary", p_summary), ("stage55_hash_recheck", p_recheck), ("stage55_hash_mismatch_details", p_mismatch), ("stage55_validation", p_val55)]:
        val.append(ok(f"{name}_present", p.exists(), str(p), "exists"))
    if any(v["result"] != "PASS" for v in val):
        pd.DataFrame(val).to_csv(out / "gold_v3_56_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    js55 = read_json(p_summary)
    val.append(ok("stage55_status_blocked_expected", js55.get("status") == STAGE55_BLOCKED, js55.get("status"), STAGE55_BLOCKED))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage55_{key}_false", js55.get(key) is False, js55.get(key), False))

    recheck = pd.read_csv(p_recheck, encoding="utf-8-sig")
    recheck["artifact_id"] = recheck["artifact_id"].astype(str)
    recheck["artifact_role"] = recheck["artifact_id"].apply(lambda x: "mutable_source_candle" if x in MUTABLE else "immutable_state_artifact")
    recheck["policy_classification"] = recheck.apply(classify, axis=1)
    recheck["policy_ready_allowed"] = recheck["policy_classification"].isin(["STABLE_OK", "MUTABLE_SOURCE_ADVANCED_APPEND_LIKELY"])
    recheck.to_csv(out / "gold_v3_56_drift_policy_matrix.csv", index=False, encoding="utf-8-sig")

    mutable_advanced = int(recheck["policy_classification"].eq("MUTABLE_SOURCE_ADVANCED_APPEND_LIKELY").sum())
    immutable_drift = int(recheck["policy_classification"].eq("IMMUTABLE_STATE_DRIFT_BLOCKER").sum())
    missing = int(recheck["policy_classification"].eq("MISSING_ARTIFACT_BLOCKER").sum())
    rewrite = int(recheck["policy_classification"].eq("MUTABLE_SOURCE_REWRITE_BLOCKER").sum())
    trunc = int(recheck["policy_classification"].eq("MUTABLE_SOURCE_TRUNCATION_BLOCKER").sum())
    val.append(ok("hash_recheck_rows_present", len(recheck) > 0, len(recheck), ">0"))
    val.append(ok("immutable_state_drift_count_zero", immutable_drift == 0, immutable_drift, 0))
    val.append(ok("missing_artifact_count_zero", missing == 0, missing, 0))
    val.append(ok("mutable_rewrite_count_zero", rewrite == 0, rewrite, 0))
    val.append(ok("mutable_truncation_count_zero", trunc == 0, trunc, 0))
    val.append(ok("policy_all_rows_allowed", bool(recheck["policy_ready_allowed"].all()), int((~recheck["policy_ready_allowed"]).sum()), 0))
    val.append(ok("stage55_anchor_mismatch_zero", js55.get("anchor_mismatch_count") == 0, js55.get("anchor_mismatch_count"), 0))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_56_validation_matrix.csv", index=False, encoding="utf-8-sig")

    mismatch_ids = recheck.loc[recheck["policy_classification"].ne("STABLE_OK"), "artifact_id"].astype(str).tolist()
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
        "live_ready": False,
        "policy_ready": failed.empty,
        "stage55_strict_replay_ready": False,
        "stage55_status": js55.get("status"),
        "mutable_source_advanced_append_likely_count": mutable_advanced,
        "immutable_state_drift_blocker_count": immutable_drift,
        "missing_artifact_blocker_count": missing,
        "mutable_source_rewrite_blocker_count": rewrite,
        "mutable_source_truncation_blocker_count": trunc,
        "mismatch_artifact_ids": mismatch_ids,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_56_policy_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 56 PASTE_ME_DRIFT_POLICY_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("policy_ready: " + str(failed.empty).lower())
    paste.append("stage55_strict_replay_ready: false")
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"stage55_status: {js55.get('status')}")
    paste.append(f"mutable_source_advanced_append_likely_count: {mutable_advanced}")
    paste.append(f"immutable_state_drift_blocker_count: {immutable_drift}")
    paste.append(f"missing_artifact_blocker_count: {missing}")
    paste.append(f"mutable_source_rewrite_blocker_count: {rewrite}")
    paste.append(f"mutable_source_truncation_blocker_count: {trunc}")
    paste.append("mismatch_artifact_ids: " + json.dumps(mismatch_ids, ensure_ascii=False))
    paste.append("")
    paste.append("DRIFT_POLICY_MATRIX_NON_STABLE")
    non_stable = recheck[recheck["policy_classification"].ne("STABLE_OK")]
    paste.append("NONE" if non_stable.empty else non_stable.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_56_drift_policy_matrix.csv")
    paste.append("gold_v3_56_validation_matrix.csv")
    paste.append("gold_v3_56_policy_summary.json")
    (out / "gold_v3_56_PASTE_ME_DRIFT_POLICY_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "GOLD_V3_56_REPORT.md").write_text(f"# GOLD V3 56 mutable source candle append-only drift policy audit-only report\n\nStatus: `{status}`\n\nStage55 strict replay remains not-ready. Audit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_56_PASTE_ME_DRIFT_POLICY_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
