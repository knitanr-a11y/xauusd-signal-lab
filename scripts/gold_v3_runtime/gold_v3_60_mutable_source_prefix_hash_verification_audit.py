#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 60 mutable source prefix-hash verification audit-only.

Recomputes Stage59 mutable source prefix hashes and verifies frozen-prefix identity.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_60_MUTABLE_SOURCE_PREFIX_HASH_VERIFICATION_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_60_MUTABLE_SOURCE_PREFIX_HASH_VERIFICATION_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_60_MUTABLE_SOURCE_PREFIX_HASH_VERIFICATION_BLOCKED_AUDIT_ONLY"
STAGE59_READY = "GOLD_V3_59_MUTABLE_SOURCE_PREFIX_HASH_SUPPORT_READY_AUDIT_ONLY"


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
        if (d / "FX_OUTPUTS" / "gold_v3" / "59_mutable_source_prefix_hash_support_audit_only").exists():
            return d
    raise FileNotFoundError("Stage59 output directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage59-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s59 = Path(a.stage59_dir).expanduser().resolve() if a.stage59_dir else g / "59_mutable_source_prefix_hash_support_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "60_mutable_source_prefix_hash_verification_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p59s = s59 / "gold_v3_59_prefix_hash_summary.json"
    p59snap = s59 / "gold_v3_59_mutable_source_prefix_hash_snapshot.csv"

    val: list[dict[str, Any]] = []
    for name, p in [("stage59_summary", p59s), ("stage59_prefix_snapshot", p59snap)]:
        val.append(ok(f"{name}_present", p.exists(), str(p), "exists"))
    if any(v["result"] != "PASS" for v in val):
        pd.DataFrame(val).to_csv(out / "gold_v3_60_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j59 = read_json(p59s)
    val.append(ok("stage59_status_ready", j59.get("status") == STAGE59_READY, j59.get("status"), STAGE59_READY))
    val.append(ok("stage59_prefix_hash_support_ready", j59.get("prefix_hash_support_ready") is True, j59.get("prefix_hash_support_ready"), True))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage59_{key}_false", j59.get(key) is False, j59.get(key), False))

    snap = pd.read_csv(p59snap, encoding="utf-8-sig")
    rows = []
    for _, r in snap.iterrows():
        aid = str(r["artifact_id"])
        path = Path(str(r["path"]))
        checkpoint_rows = int(float(r["checkpoint_row_count"]))
        expected_prefix = str(r["prefix_sha256"])
        exists = path.exists()
        current_rows = csv_rows_bytes(path) if exists else 0
        long_enough = exists and current_rows >= checkpoint_rows
        if long_enough:
            current_prefix, rows_used, bytes_used = prefix_hash_csv(path, checkpoint_rows)
        else:
            current_prefix, rows_used, bytes_used = "", 0, 0
        rows.append({
            "artifact_id": aid,
            "path": str(path),
            "exists": exists,
            "checkpoint_row_count": checkpoint_rows,
            "current_row_count": current_rows,
            "outside_frozen_window_rows": max(0, current_rows - checkpoint_rows),
            "expected_prefix_sha256": expected_prefix,
            "current_prefix_sha256": current_prefix,
            "prefix_hash_match": current_prefix == expected_prefix,
            "prefix_rows_used": rows_used,
            "prefix_bytes_used": bytes_used,
            "current_long_enough": long_enough,
            "verification_pass": exists and long_enough and rows_used == checkpoint_rows and current_prefix == expected_prefix,
        })
    mat = pd.DataFrame(rows)
    mat.to_csv(out / "gold_v3_60_prefix_hash_verification_matrix.csv", index=False, encoding="utf-8-sig")

    val.append(ok("prefix_snapshot_rows_present", len(mat) == len(snap), len(mat), len(snap)))
    val.append(ok("all_source_files_exist", bool(mat["exists"].all()) if not mat.empty else False, int((~mat["exists"]).sum()) if not mat.empty else len(snap), 0))
    val.append(ok("all_source_files_long_enough", bool(mat["current_long_enough"].all()) if not mat.empty else False, int((~mat["current_long_enough"]).sum()) if not mat.empty else len(snap), 0))
    val.append(ok("all_prefix_rows_equal_checkpoint", bool((mat["prefix_rows_used"] == mat["checkpoint_row_count"]).all()) if not mat.empty else False, mat[["artifact_id", "prefix_rows_used", "checkpoint_row_count"]].to_dict("records") if not mat.empty else [], "all_equal"))
    val.append(ok("all_prefix_hashes_match", bool(mat["prefix_hash_match"].all()) if not mat.empty else False, int((~mat["prefix_hash_match"]).sum()) if not mat.empty else len(snap), 0))
    val.append(ok("all_verification_pass", bool(mat["verification_pass"].all()) if not mat.empty else False, int((~mat["verification_pass"]).sum()) if not mat.empty else len(snap), 0))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_60_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "prefix_hash_verification_ready": failed.empty,
        "verification_rows": int(len(mat)),
        "prefix_hash_mismatch_count": int((~mat["prefix_hash_match"]).sum()) if not mat.empty else 0,
        "source_not_long_enough_count": int((~mat["current_long_enough"]).sum()) if not mat.empty else 0,
        "outside_frozen_window_rows_total": int(pd.to_numeric(mat["outside_frozen_window_rows"], errors="coerce").fillna(0).sum()) if not mat.empty else 0,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_60_prefix_hash_verification_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 60 PASTE_ME_PREFIX_HASH_VERIFY_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("prefix_hash_verification_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"verification_rows: {len(mat)}")
    paste.append(f"prefix_hash_mismatch_count: {int((~mat['prefix_hash_match']).sum()) if not mat.empty else 0}")
    paste.append(f"source_not_long_enough_count: {int((~mat['current_long_enough']).sum()) if not mat.empty else 0}")
    paste.append(f"outside_frozen_window_rows_total: {int(pd.to_numeric(mat['outside_frozen_window_rows'], errors='coerce').fillna(0).sum()) if not mat.empty else 0}")
    paste.append("")
    paste.append("PREFIX_HASH_VERIFICATION")
    paste.append(mat[["artifact_id", "checkpoint_row_count", "current_row_count", "outside_frozen_window_rows", "prefix_hash_match", "verification_pass"]].to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_60_prefix_hash_verification_matrix.csv")
    paste.append("gold_v3_60_validation_matrix.csv")
    paste.append("gold_v3_60_prefix_hash_verification_summary.json")
    (out / "gold_v3_60_PASTE_ME_PREFIX_HASH_VERIFY_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "GOLD_V3_60_REPORT.md").write_text(f"# GOLD V3 60 mutable source prefix-hash verification audit-only report\n\nStatus: `{status}`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_60_PASTE_ME_PREFIX_HASH_VERIFY_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
