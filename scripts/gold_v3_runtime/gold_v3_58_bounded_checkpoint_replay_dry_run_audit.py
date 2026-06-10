#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 58 bounded checkpoint replay dry run audit-only.

Applies Stage57 bounded replay contract: mutable source candles use checkpoint row-count window,
immutable state artifacts remain strict hash/row-count checked.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_58_BOUNDED_CHECKPOINT_REPLAY_DRY_RUN_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_58_BOUNDED_CHECKPOINT_REPLAY_DRY_RUN_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_58_BOUNDED_CHECKPOINT_REPLAY_DRY_RUN_BLOCKED_AUDIT_ONLY"
STAGE54_READY = "GOLD_V3_54_RESTART_REPLAY_CHECKPOINT_STATE_READY_AUDIT_ONLY"
STAGE55_BLOCKED = "GOLD_V3_55_REPLAY_FROM_CHECKPOINT_DRY_RUN_BLOCKED_AUDIT_ONLY"
STAGE56_READY = "GOLD_V3_56_MUTABLE_SOURCE_CANDLE_APPEND_ONLY_DRIFT_POLICY_READY_AUDIT_ONLY"
STAGE57_READY = "GOLD_V3_57_BOUNDED_REPLAY_WINDOW_FREEZE_DECISION_READY_AUDIT_ONLY"
MUTABLE = {"m5_csv", "m15_csv", "h4_csv"}


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
        if (d / "FX_OUTPUTS" / "gold_v3" / "57_bounded_replay_window_freeze_decision_audit_only").exists():
            return d
    raise FileNotFoundError("Stage57 output directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage54-dir", default="")
    p.add_argument("--stage55-dir", default="")
    p.add_argument("--stage56-dir", default="")
    p.add_argument("--stage57-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s54 = Path(a.stage54_dir).expanduser().resolve() if a.stage54_dir else g / "54_restart_replay_checkpoint_state_audit_only"
    s55 = Path(a.stage55_dir).expanduser().resolve() if a.stage55_dir else g / "55_replay_from_checkpoint_dry_run_audit_only"
    s56 = Path(a.stage56_dir).expanduser().resolve() if a.stage56_dir else g / "56_mutable_source_candle_append_only_drift_policy_audit_only"
    s57 = Path(a.stage57_dir).expanduser().resolve() if a.stage57_dir else g / "57_bounded_replay_window_freeze_decision_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "58_bounded_checkpoint_replay_dry_run_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "stage54_summary": s54 / "gold_v3_54_checkpoint_summary.json",
        "stage54_hashes": s54 / "gold_v3_54_source_artifact_hashes.csv",
        "stage55_summary": s55 / "gold_v3_55_replay_dry_run_summary.json",
        "stage56_summary": s56 / "gold_v3_56_policy_summary.json",
        "stage57_summary": s57 / "gold_v3_57_bounded_replay_summary.json",
        "stage57_contract": s57 / "gold_v3_57_bounded_replay_window_contract.csv",
        "stage57_mutable_window": s57 / "gold_v3_57_mutable_source_window_freeze.csv",
    }
    val: list[dict[str, Any]] = []
    for name, p in paths.items():
        val.append(ok(f"{name}_present", p.exists(), str(p), "exists"))
    if any(v["result"] != "PASS" for v in val):
        pd.DataFrame(val).to_csv(out / "gold_v3_58_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j54 = read_json(paths["stage54_summary"])
    j55 = read_json(paths["stage55_summary"])
    j56 = read_json(paths["stage56_summary"])
    j57 = read_json(paths["stage57_summary"])
    for st, js, expected in [("54", j54, STAGE54_READY), ("55", j55, STAGE55_BLOCKED), ("56", j56, STAGE56_READY), ("57", j57, STAGE57_READY)]:
        val.append(ok(f"stage{st}_status_expected", js.get("status") == expected, js.get("status"), expected))
        for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
            val.append(ok(f"stage{st}_{key}_false", js.get(key) is False, js.get(key), False))

    hashes = pd.read_csv(paths["stage54_hashes"], encoding="utf-8-sig")
    contract = pd.read_csv(paths["stage57_contract"], encoding="utf-8-sig")
    merged = contract.merge(hashes[["artifact_id", "path", "sha256", "row_count_if_csv"]], on="artifact_id", how="left", suffixes=("_contract", "_checkpoint"))

    check_rows = []
    for _, r in merged.iterrows():
        aid = str(r["artifact_id"])
        role = str(r.get("artifact_role", ""))
        path = Path(str(r["path"]))
        exists = path.exists()
        current_sha = sha256_file(path) if exists else ""
        current_rows = csv_rows(path) if exists and path.suffix.lower() == ".csv" else ""
        checkpoint_rows = r.get("row_count_if_csv", "")
        expected_sha = str(r.get("sha256", ""))
        try:
            cur_i = int(current_rows)
            chk_i = int(float(checkpoint_rows))
        except Exception:
            cur_i = chk_i = None
        if aid in MUTABLE or role == "mutable_source_candle":
            pass_policy = exists and cur_i is not None and chk_i is not None and cur_i >= chk_i
            replay_scope = "bounded_rows_1_to_checkpoint_row_count"
            strict_hash_required = False
            sha_match = current_sha == expected_sha
            row_count_match = cur_i == chk_i if cur_i is not None and chk_i is not None else False
            classification = "MUTABLE_BOUNDED_WINDOW_OK" if pass_policy else "MUTABLE_BOUNDED_WINDOW_BLOCKED"
            outside_rows = cur_i - chk_i if cur_i is not None and chk_i is not None else ""
        else:
            sha_match = exists and current_sha == expected_sha
            row_count_match = True
            if str(checkpoint_rows) not in ["", "nan", "None"]:
                try:
                    row_count_match = int(float(checkpoint_rows)) == int(current_rows)
                except Exception:
                    row_count_match = str(checkpoint_rows) == str(current_rows)
            pass_policy = exists and sha_match and row_count_match
            replay_scope = "strict_full_artifact"
            strict_hash_required = True
            classification = "IMMUTABLE_STRICT_OK" if pass_policy else "IMMUTABLE_STRICT_BLOCKED"
            outside_rows = 0
        check_rows.append({
            "artifact_id": aid,
            "artifact_role": role,
            "path": str(path),
            "exists": exists,
            "checkpoint_row_count": checkpoint_rows,
            "current_row_count": current_rows,
            "outside_frozen_window_rows": outside_rows,
            "checkpoint_sha256": expected_sha,
            "current_sha256": current_sha,
            "sha_match": sha_match,
            "row_count_match": row_count_match,
            "strict_hash_required": strict_hash_required,
            "replay_scope": replay_scope,
            "bounded_replay_pass": pass_policy,
            "classification": classification,
        })
    matrix = pd.DataFrame(check_rows)
    matrix.to_csv(out / "gold_v3_58_bounded_replay_check_matrix.csv", index=False, encoding="utf-8-sig")
    matrix[matrix["artifact_id"].isin(MUTABLE)].to_csv(out / "gold_v3_58_mutable_source_bounded_window.csv", index=False, encoding="utf-8-sig")
    matrix[~matrix["artifact_id"].isin(MUTABLE)].to_csv(out / "gold_v3_58_immutable_state_recheck.csv", index=False, encoding="utf-8-sig")

    mutable_blocked = int(matrix[matrix["artifact_id"].isin(MUTABLE)]["bounded_replay_pass"].eq(False).sum())
    immutable_blocked = int(matrix[~matrix["artifact_id"].isin(MUTABLE)]["bounded_replay_pass"].eq(False).sum())
    mutable_outside_rows = int(pd.to_numeric(matrix[matrix["artifact_id"].isin(MUTABLE)]["outside_frozen_window_rows"], errors="coerce").fillna(0).sum())
    val.append(ok("stage57_bounded_contract_ready", j57.get("bounded_replay_contract_ready") is True, j57.get("bounded_replay_contract_ready"), True))
    val.append(ok("stage55_strict_replay_not_ready_expected", j57.get("stage55_strict_replay_ready") is False, j57.get("stage55_strict_replay_ready"), False))
    val.append(ok("mutable_bounded_window_blocked_count_zero", mutable_blocked == 0, mutable_blocked, 0))
    val.append(ok("immutable_strict_blocked_count_zero", immutable_blocked == 0, immutable_blocked, 0))
    val.append(ok("bounded_check_rows_match_contract", len(matrix) == len(contract), len(matrix), len(contract)))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_58_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "bounded_replay_ready": failed.empty,
        "stage55_strict_replay_ready": False,
        "bounded_check_rows": int(len(matrix)),
        "mutable_bounded_window_blocked_count": mutable_blocked,
        "immutable_strict_blocked_count": immutable_blocked,
        "mutable_outside_frozen_window_rows_total": mutable_outside_rows,
        "prefix_hash_available": False,
        "prefix_hash_limitation": "Stage54 did not store source-candle prefix hashes; Stage58 verifies row-bound availability and immutable state stability only.",
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_58_bounded_replay_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 58 PASTE_ME_BOUNDED_REPLAY_DRY_RUN_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("bounded_replay_ready: " + str(failed.empty).lower())
    paste.append("stage55_strict_replay_ready: false")
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"bounded_check_rows: {len(matrix)}")
    paste.append(f"mutable_bounded_window_blocked_count: {mutable_blocked}")
    paste.append(f"immutable_strict_blocked_count: {immutable_blocked}")
    paste.append(f"mutable_outside_frozen_window_rows_total: {mutable_outside_rows}")
    paste.append("prefix_hash_available: false")
    paste.append("prefix_hash_limitation: Stage54 did not store source-candle prefix hashes; row-bound + immutable-state verification only.")
    paste.append("")
    paste.append("MUTABLE_SOURCE_BOUNDED_WINDOW")
    paste.append(matrix[matrix["artifact_id"].isin(MUTABLE)][["artifact_id", "checkpoint_row_count", "current_row_count", "outside_frozen_window_rows", "replay_scope", "bounded_replay_pass", "classification"]].to_string(index=False))
    paste.append("")
    paste.append("IMMUTABLE_STATE_RECHECK_SUMMARY")
    imm = matrix[~matrix["artifact_id"].isin(MUTABLE)]
    paste.append(imm[["artifact_id", "sha_match", "row_count_match", "bounded_replay_pass", "classification"]].to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_58_bounded_replay_check_matrix.csv")
    paste.append("gold_v3_58_mutable_source_bounded_window.csv")
    paste.append("gold_v3_58_immutable_state_recheck.csv")
    (out / "gold_v3_58_PASTE_ME_BOUNDED_REPLAY_DRY_RUN_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "GOLD_V3_58_REPORT.md").write_text(f"# GOLD V3 58 bounded checkpoint replay dry run audit-only report\n\nStatus: `{status}`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_58_PASTE_ME_BOUNDED_REPLAY_DRY_RUN_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
