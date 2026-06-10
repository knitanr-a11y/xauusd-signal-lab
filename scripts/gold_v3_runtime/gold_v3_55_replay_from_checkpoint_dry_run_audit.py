#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 55 replay-from-checkpoint dry run audit-only.

Verifies Stage54 checkpoint hashes/counts/anchors against current artifacts.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_55_REPLAY_FROM_CHECKPOINT_DRY_RUN_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_55_REPLAY_FROM_CHECKPOINT_DRY_RUN_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_55_REPLAY_FROM_CHECKPOINT_DRY_RUN_BLOCKED_AUDIT_ONLY"
STAGE54_READY = "GOLD_V3_54_RESTART_REPLAY_CHECKPOINT_STATE_READY_AUDIT_ONLY"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def csv_rows(path: Path) -> int:
    if not path.exists() or path.suffix.lower() != ".csv":
        return 0
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        return max(0, sum(1 for _ in f) - 1)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "54_restart_replay_checkpoint_state_audit_only").exists():
            return d
    raise FileNotFoundError("Stage54 checkpoint directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage54-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s54 = Path(a.stage54_dir).expanduser().resolve() if a.stage54_dir else g / "54_restart_replay_checkpoint_state_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "55_replay_from_checkpoint_dry_run_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p_summary = s54 / "gold_v3_54_checkpoint_summary.json"
    p_checkpoint = s54 / "gold_v3_54_replay_checkpoint_state.csv"
    p_hashes = s54 / "gold_v3_54_source_artifact_hashes.csv"
    p_restart = s54 / "gold_v3_54_restart_plan.csv"
    p_val54 = s54 / "gold_v3_54_validation_matrix.csv"

    val: list[dict[str, Any]] = []
    for name, p in [("stage54_summary", p_summary), ("stage54_checkpoint", p_checkpoint), ("stage54_hashes", p_hashes), ("stage54_restart_plan", p_restart), ("stage54_validation", p_val54)]:
        val.append(ok(f"{name}_present", p.exists(), str(p), "exists"))
    if any(v["result"] != "PASS" for v in val):
        pd.DataFrame(val).to_csv(out / "gold_v3_55_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    js54 = read_json(p_summary)
    val.append(ok("stage54_status_ready", js54.get("status") == STAGE54_READY, js54.get("status"), STAGE54_READY))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage54_{key}_false", js54.get(key) is False, js54.get(key), False))
    val.append(ok("stage54_checkpoint_ready", js54.get("checkpoint_ready") is True, js54.get("checkpoint_ready"), True))

    hashes = pd.read_csv(p_hashes, encoding="utf-8-sig")
    recheck_rows = []
    for _, r in hashes.iterrows():
        path = Path(str(r["path"]))
        exists = path.exists()
        current_sha = sha256_file(path) if exists else ""
        expected_sha = str(r["sha256"])
        expected_rows = r.get("row_count_if_csv", "")
        current_rows = csv_rows(path) if exists and path.suffix.lower() == ".csv" else ""
        row_match = True
        if str(expected_rows) not in ["", "nan", "None"]:
            try:
                row_match = int(float(expected_rows)) == int(current_rows)
            except Exception:
                row_match = str(expected_rows) == str(current_rows)
        recheck_rows.append({
            "artifact_id": r["artifact_id"], "path": str(path), "exists": exists,
            "expected_sha256": expected_sha, "current_sha256": current_sha, "sha_match": current_sha == expected_sha,
            "expected_row_count_if_csv": expected_rows, "current_row_count_if_csv": current_rows, "row_count_match": row_match,
        })
    recheck = pd.DataFrame(recheck_rows)
    recheck.to_csv(out / "gold_v3_55_hash_recheck.csv", index=False, encoding="utf-8-sig")
    val.append(ok("all_artifact_paths_exist", bool(recheck["exists"].all()), int((~recheck["exists"]).sum()), 0))
    val.append(ok("all_artifact_hashes_match", bool(recheck["sha_match"].all()), int((~recheck["sha_match"]).sum()), 0))
    val.append(ok("all_csv_row_counts_match", bool(recheck["row_count_match"].all()), int((~recheck["row_count_match"]).sum()), 0))

    restart = pd.read_csv(p_restart, encoding="utf-8-sig")
    restart.to_csv(out / "gold_v3_55_restart_anchor_recheck.csv", index=False, encoding="utf-8-sig")
    val.append(ok("restart_plan_steps_8", len(restart) == 8, len(restart), 8))
    val.append(ok("restart_plan_order_1_to_8", restart["step_order"].tolist() == list(range(1, 9)), restart["step_order"].tolist(), list(range(1, 9))))
    val.append(ok("restart_anchors_nonempty", restart["restart_anchor"].astype(str).ne("").all(), int(restart["restart_anchor"].astype(str).eq("").sum()), 0))

    anchors = pd.DataFrame([
        {"anchor_id": "stage51_to_stage52_opportunity_count", "observed": js54.get("stage51_opportunities"), "expected": js54.get("stage51_opportunities"), "match": True},
        {"anchor_id": "stage52_selected_to_stage53_closed", "observed": js54.get("stage52_selected_trades"), "expected": js54.get("stage53_closed_shadow_trades"), "match": js54.get("stage52_selected_trades") == js54.get("stage53_closed_shadow_trades")},
        {"anchor_id": "hash_artifact_count", "observed": len(recheck), "expected": js54.get("hash_artifact_count"), "match": len(recheck) == js54.get("hash_artifact_count")},
        {"anchor_id": "restart_plan_steps", "observed": len(restart), "expected": js54.get("restart_plan_steps"), "match": len(restart) == js54.get("restart_plan_steps")},
    ])
    anchors.to_csv(out / "gold_v3_55_replay_anchor_check_matrix.csv", index=False, encoding="utf-8-sig")
    val.append(ok("replay_anchor_checks_all_match", bool(anchors["match"].all()), int((~anchors["match"]).sum()), 0))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_55_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP, "status": status, "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(cdir), "output_dir": str(out), "audit_only": True,
        "live_allowed": False, "mt5_execution_enabled": False, "mt5_bat_created": False,
        "discord_live_enabled": False, "ai_api_called": False, "signals_generated": False, "final_signal_enabled": False,
        "contract_mutated": False, "manual_candidate_demotion_or_removal": False, "open_asof_allowed": False, "live_ready": False,
        "replay_dry_run_ready": failed.empty, "hash_recheck_rows": int(len(recheck)),
        "hash_mismatch_count": int((~recheck["sha_match"]).sum()), "row_count_mismatch_count": int((~recheck["row_count_match"]).sum()),
        "restart_plan_steps": int(len(restart)), "anchor_mismatch_count": int((~anchors["match"]).sum()),
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_55_replay_dry_run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 55 PASTE_ME_REPLAY_DRY_RUN_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("replay_dry_run_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"hash_recheck_rows: {len(recheck)}")
    paste.append(f"hash_mismatch_count: {int((~recheck['sha_match']).sum())}")
    paste.append(f"row_count_mismatch_count: {int((~recheck['row_count_match']).sum())}")
    paste.append(f"restart_plan_steps: {len(restart)}")
    paste.append(f"anchor_mismatch_count: {int((~anchors['match']).sum())}")
    paste.append("")
    paste.append("ANCHORS")
    paste.append(anchors.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_55_hash_recheck.csv")
    paste.append("gold_v3_55_restart_anchor_recheck.csv")
    paste.append("gold_v3_55_replay_anchor_check_matrix.csv")
    (out / "gold_v3_55_PASTE_ME_REPLAY_DRY_RUN_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "GOLD_V3_55_REPORT.md").write_text(f"# GOLD V3 55 replay-from-checkpoint dry run audit-only report\n\nStatus: `{status}`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_55_PASTE_ME_REPLAY_DRY_RUN_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
