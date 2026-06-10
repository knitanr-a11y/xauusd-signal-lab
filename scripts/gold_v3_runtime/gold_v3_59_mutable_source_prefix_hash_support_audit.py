#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 59 mutable source prefix-hash support audit-only.

Creates first prefix-hash baseline for mutable source candle CSVs.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_59_MUTABLE_SOURCE_PREFIX_HASH_SUPPORT_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_59_MUTABLE_SOURCE_PREFIX_HASH_SUPPORT_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_59_MUTABLE_SOURCE_PREFIX_HASH_SUPPORT_BLOCKED_AUDIT_ONLY"
STAGE57_READY = "GOLD_V3_57_BOUNDED_REPLAY_WINDOW_FREEZE_DECISION_READY_AUDIT_ONLY"
STAGE58_READY = "GOLD_V3_58_BOUNDED_CHECKPOINT_REPLAY_DRY_RUN_READY_AUDIT_ONLY"
MUTABLE = {"m5_csv", "m15_csv", "h4_csv"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def csv_rows_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("rb") as f:
        first = True
        for _ in f:
            if first:
                first = False
                continue
            count += 1
    return count


def prefix_hash_csv(path: Path, data_rows: int) -> tuple[str, int, int]:
    h = hashlib.sha256()
    lines_used = 0
    bytes_used = 0
    with path.open("rb") as f:
        for i, line in enumerate(f):
            if i == 0 or lines_used < data_rows:
                h.update(line)
                bytes_used += len(line)
                if i > 0:
                    lines_used += 1
            else:
                break
    return h.hexdigest(), lines_used, bytes_used


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "58_bounded_checkpoint_replay_dry_run_audit_only").exists():
            return d
    raise FileNotFoundError("Stage58 output directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage57-dir", default="")
    p.add_argument("--stage58-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s57 = Path(a.stage57_dir).expanduser().resolve() if a.stage57_dir else g / "57_bounded_replay_window_freeze_decision_audit_only"
    s58 = Path(a.stage58_dir).expanduser().resolve() if a.stage58_dir else g / "58_bounded_checkpoint_replay_dry_run_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "59_mutable_source_prefix_hash_support_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p57s = s57 / "gold_v3_57_bounded_replay_summary.json"
    p57w = s57 / "gold_v3_57_mutable_source_window_freeze.csv"
    p58s = s58 / "gold_v3_58_bounded_replay_summary.json"
    p58w = s58 / "gold_v3_58_mutable_source_bounded_window.csv"

    val: list[dict[str, Any]] = []
    for name, p in [("stage57_summary", p57s), ("stage57_mutable_window", p57w), ("stage58_summary", p58s), ("stage58_mutable_window", p58w)]:
        val.append(ok(f"{name}_present", p.exists(), str(p), "exists"))
    if any(v["result"] != "PASS" for v in val):
        pd.DataFrame(val).to_csv(out / "gold_v3_59_prefix_hash_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j57, j58 = read_json(p57s), read_json(p58s)
    for st, js, expected in [("57", j57, STAGE57_READY), ("58", j58, STAGE58_READY)]:
        val.append(ok(f"stage{st}_status_expected", js.get("status") == expected, js.get("status"), expected))
        for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
            val.append(ok(f"stage{st}_{key}_false", js.get(key) is False, js.get(key), False))

    win = pd.read_csv(p58w, encoding="utf-8-sig")
    rows = []
    for _, r in win.iterrows():
        aid = str(r["artifact_id"])
        if aid not in MUTABLE:
            continue
        path = Path(str(r["path"])) if "path" in r and str(r["path"]) not in ["", "nan"] else None
        if path is None or not path.exists():
            # Stage58 matrix contains path; fallback by id.
            fname = {"m5_csv": "goldsharp_m5.csv", "m15_csv": "goldsharp_m15.csv", "h4_csv": "goldsharp_h4.csv"}[aid]
            path = cdir / fname
        checkpoint_rows = int(float(r["checkpoint_row_count"]))
        current_rows = csv_rows_bytes(path) if path.exists() else 0
        can_hash = path.exists() and current_rows >= checkpoint_rows
        if can_hash:
            prefix_sha, prefix_rows_used, prefix_bytes_used = prefix_hash_csv(path, checkpoint_rows)
        else:
            prefix_sha, prefix_rows_used, prefix_bytes_used = "", 0, 0
        rows.append({
            "artifact_id": aid,
            "path": str(path),
            "checkpoint_row_count": checkpoint_rows,
            "current_row_count": current_rows,
            "outside_frozen_window_rows": max(0, current_rows - checkpoint_rows),
            "prefix_hash_available": can_hash,
            "prefix_hash_algorithm": "sha256(header_plus_first_N_data_rows_raw_bytes)",
            "prefix_sha256": prefix_sha,
            "prefix_rows_used": prefix_rows_used,
            "prefix_bytes_used": prefix_bytes_used,
            "baseline_stage": "GOLD_V3_59",
            "baseline_limitation": "first prefix baseline; cannot prove Stage54-time prefix identity because Stage54 did not store prefix hashes",
        })
    snap = pd.DataFrame(rows)
    snap.to_csv(out / "gold_v3_59_mutable_source_prefix_hash_snapshot.csv", index=False, encoding="utf-8-sig")

    val.append(ok("mutable_prefix_rows_present", len(snap) == len(MUTABLE), len(snap), len(MUTABLE)))
    val.append(ok("all_mutable_sources_exist_and_long_enough", bool(snap["prefix_hash_available"].all()) if not snap.empty else False, int((~snap["prefix_hash_available"]).sum()) if not snap.empty else len(MUTABLE), 0))
    val.append(ok("prefix_rows_equal_checkpoint_rows", bool((snap["prefix_rows_used"] == snap["checkpoint_row_count"]).all()) if not snap.empty else False, snap[["artifact_id", "prefix_rows_used", "checkpoint_row_count"]].to_dict("records") if not snap.empty else [], "all_equal"))
    val.append(ok("stage58_bounded_replay_ready", j58.get("bounded_replay_ready") is True, j58.get("bounded_replay_ready"), True))
    val.append(ok("stage58_immutable_blocked_zero", j58.get("immutable_strict_blocked_count") == 0, j58.get("immutable_strict_blocked_count"), 0))
    val.append(ok("stage58_mutable_blocked_zero", j58.get("mutable_bounded_window_blocked_count") == 0, j58.get("mutable_bounded_window_blocked_count"), 0))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_59_prefix_hash_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "prefix_hash_support_ready": failed.empty,
        "prefix_hash_snapshot_rows": int(len(snap)),
        "prefix_hash_available_count": int(snap["prefix_hash_available"].sum()) if not snap.empty else 0,
        "prefix_hash_baseline_stage": "GOLD_V3_59",
        "prefix_hash_limitation": "first prefix baseline; cannot prove Stage54-time prefix identity because Stage54 did not store prefix hashes",
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_59_prefix_hash_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 59 PASTE_ME_PREFIX_HASH_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("prefix_hash_support_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"prefix_hash_snapshot_rows: {len(snap)}")
    paste.append(f"prefix_hash_available_count: {int(snap['prefix_hash_available'].sum()) if not snap.empty else 0}")
    paste.append("prefix_hash_baseline_stage: GOLD_V3_59")
    paste.append("prefix_hash_limitation: first prefix baseline; cannot prove Stage54-time prefix identity because Stage54 did not store prefix hashes")
    paste.append("")
    paste.append("PREFIX_HASH_SNAPSHOT")
    paste.append(snap[["artifact_id", "checkpoint_row_count", "current_row_count", "outside_frozen_window_rows", "prefix_hash_available", "prefix_rows_used", "prefix_sha256"]].to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_59_mutable_source_prefix_hash_snapshot.csv")
    paste.append("gold_v3_59_prefix_hash_validation_matrix.csv")
    paste.append("gold_v3_59_prefix_hash_summary.json")
    (out / "gold_v3_59_PASTE_ME_PREFIX_HASH_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "GOLD_V3_59_REPORT.md").write_text(f"# GOLD V3 59 mutable source prefix-hash support audit-only report\n\nStatus: `{status}`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_59_PASTE_ME_PREFIX_HASH_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
