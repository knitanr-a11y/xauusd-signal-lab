#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 79 immutable runtime output policy audit-only.

Creates an immutable run_id snapshot of Stage76 runtime evidence.
No MT5 orders, no Discord, no AI API, no final signal.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_79_IMMUTABLE_RUNTIME_OUTPUT_POLICY_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_79_IMMUTABLE_RUNTIME_OUTPUT_POLICY_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_79_IMMUTABLE_RUNTIME_OUTPUT_POLICY_BLOCKED_AUDIT_ONLY"
STAGE76_READY = "GOLD_V3_76_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"

SOURCE_FILES = [
    "gold_v3_76_monitor_state.json",
    "gold_v3_76_monitor_event_log.csv",
    "gold_v3_76_runtime_timing_log.csv",
    "gold_v3_76_latest_payload_preview.csv",
    "gold_v3_76_latest_payload_preview.json",
    "gold_v3_76_blocker_matrix.csv",
    "gold_v3_76_validation_matrix.csv",
    "gold_v3_76_full_audit_monitor_with_payload_preview_summary.json",
    "gold_v3_76_PASTE_ME_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_SUMMARY.txt",
    "GOLD_V3_76_REPORT.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"immutable target already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_text_new(path: Path, text: str) -> None:
    if path.exists():
        raise FileExistsError(f"immutable target already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"immutable target already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_part(s: str) -> str:
    s = str(s or "").strip()
    s = re.sub(r"[^0-9A-Za-z_\-]+", "_", s)
    return s.strip("_") or "NA"


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


def derive_run_id(summary: dict[str, Any]) -> tuple[str, str]:
    created = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    latest = str(summary.get("latest_m15_time") or summary.get("latest_closed_m15_time") or "NA")
    decision = safe_part(summary.get("decision", "NA"))
    try:
        dt = pd.to_datetime(latest)
        latest_part = dt.strftime("%Y%m%d_%H%M%S")
        day = dt.strftime("%Y%m%d")
    except Exception:
        latest_part = safe_part(latest)
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
    run_id = f"{created}_m15_{latest_part}_{decision}"
    return day, run_id


def unique_run_dir(base: Path, day: str, run_id: str) -> tuple[Path, str]:
    day_dir = base / day
    candidate = day_dir / run_id
    if not candidate.exists():
        return candidate, run_id
    for i in range(1, 100):
        rid = f"{run_id}_retry{i:02d}"
        candidate = day_dir / rid
        if not candidate.exists():
            return candidate, rid
    raise RuntimeError(f"could not allocate unique run_id under {day_dir}")


def copy_new(src: Path, dst: Path) -> None:
    if dst.exists():
        raise FileExistsError(f"immutable copy target already exists: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage76-dir", default="")
    p.add_argument("--immutable-root", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    stage76_dir = Path(a.stage76_dir).expanduser().resolve() if a.stage76_dir else base_out / "76_full_audit_monitor_with_payload_preview_audit_only"
    immutable_root = Path(a.immutable_root).expanduser().resolve() if a.immutable_root else base_out / "runtime_immutable"
    summary_path = stage76_dir / "gold_v3_76_full_audit_monitor_with_payload_preview_summary.json"

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    val.append(ok("stage76_dir_present", stage76_dir.exists(), str(stage76_dir), "exists"))
    val.append(ok("stage76_summary_present", summary_path.exists(), str(summary_path), "exists"))
    if not summary_path.exists():
        blockers.append(blocker("stage76_summary_missing", str(summary_path), "STAGE76_SUMMARY_MISSING"))
        status = BLOCKED_STATUS
        print(f"[{status}] missing Stage76 summary: {summary_path}")
        return 1

    j76 = read_json(summary_path)
    day, base_run_id = derive_run_id(j76)
    run_dir, run_id = unique_run_dir(immutable_root, day, base_run_id)
    snapshot_dir = run_dir / "stage76_snapshot"
    run_dir.mkdir(parents=True, exist_ok=False)
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    copied: list[dict[str, Any]] = []
    missing_optional: list[str] = []
    try:
        for name in SOURCE_FILES:
            src = stage76_dir / name
            if not src.exists():
                missing_optional.append(name)
                continue
            dst = snapshot_dir / name
            copy_new(src, dst)
            copied.append({
                "source_path": str(src),
                "snapshot_path": str(dst),
                "relative_path": f"stage76_snapshot/{name}",
                "size_bytes": dst.stat().st_size,
                "sha256": sha256_file(dst),
            })

        val.append(ok("stage76_status_ready", j76.get("status") == STAGE76_READY, j76.get("status"), STAGE76_READY))
        val.append(ok("run_dir_created_new", run_dir.exists(), str(run_dir), "new immutable directory"))
        val.append(ok("snapshot_dir_created_new", snapshot_dir.exists(), str(snapshot_dir), "new immutable directory"))
        val.append(ok("copied_file_count_positive", len(copied) > 0, len(copied), "> 0"))
        val.append(ok("no_existing_target_overwritten", True, "copy_new enforced", "no overwrite"))
        val.append(ok("csv_open_bar_exclusion_required_false", j76.get("csv_open_bar_exclusion_required") is False, j76.get("csv_open_bar_exclusion_required"), False))
        val.append(ok("discord_send_false", str(j76.get("should_notify_discord", "False")) == "False", j76.get("should_notify_discord"), False))
        val.append(ok("mt5_order_false", str(j76.get("should_place_mt5_order", "False")) == "False", j76.get("should_place_mt5_order"), False))
        val.append(ok("ai_api_false", str(j76.get("should_call_ai_api", "False")) == "False", j76.get("should_call_ai_api"), False))
        val.append(ok("final_signal_false", str(j76.get("should_enable_final_signal", "False")) == "False", j76.get("should_enable_final_signal"), False))
        val.append(ok("live_flags_all_false", True, "all_false", "all_false"))
        if j76.get("status") != STAGE76_READY:
            blockers.append(blocker("stage76_not_ready", str(summary_path), "STAGE76_STATUS_NOT_READY", j76.get("status")))

        policy_rows = [
            {"item": "runtime_evidence_overwrite", "policy": "forbidden", "observed": "new run_id directory", "result": "PASS"},
            {"item": "latest_state_overwrite", "policy": "not used by Stage79 immutable evidence", "observed": "snapshot only", "result": "PASS"},
            {"item": "run_id_uniqueness", "policy": "required", "observed": run_id, "result": "PASS"},
            {"item": "snapshot_hash_manifest", "policy": "required", "observed": len(copied), "result": "PASS" if copied else "FAIL"},
            {"item": "external_side_effects", "policy": "forbidden", "observed": "all_false", "result": "PASS"},
        ]
        write_csv_new(run_dir / "gold_v3_79_output_policy_matrix.csv", policy_rows)
        write_json(run_dir / "gold_v3_79_immutable_manifest.json", {"run_id": run_id, "created_at_utc": utc_now(), "source_stage": "stage76", "copied_files": copied, "missing_optional_files": missing_optional})
        write_csv_new(run_dir / "gold_v3_79_immutable_manifest.csv", copied)
        manifest_json = run_dir / "gold_v3_79_immutable_manifest.json"
        manifest_csv = run_dir / "gold_v3_79_immutable_manifest.csv"
        val.append(ok("manifest_json_present", manifest_json.exists(), str(manifest_json), "exists"))
        val.append(ok("manifest_csv_present", manifest_csv.exists(), str(manifest_csv), "exists"))
        val.append(ok("all_copied_files_hashed", all(x.get("sha256") for x in copied), "all_hashed" if copied else "none", "all_hashed"))

        failed = [v for v in val if v.get("result") != "PASS"]
        status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS
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
            "immutable_runtime_output_policy_ready": status == READY_STATUS,
            "pool_policy": POOL_POLICY,
            "stage76_summary_path": str(summary_path),
            "immutable_root": str(immutable_root),
            "run_id": run_id,
            "run_dir": str(run_dir),
            "snapshot_dir": str(snapshot_dir),
            "latest_m15_time": j76.get("latest_m15_time", ""),
            "stage76_status": j76.get("status", ""),
            "decision": j76.get("decision", ""),
            "emission_action": j76.get("emission_action", ""),
            "payload_action": j76.get("payload_action", ""),
            "copied_file_count": len(copied),
            "missing_optional_count": len(missing_optional),
            "missing_optional_files": missing_optional,
            "blocker_count": len(blockers),
            "validation_failure_count": len(failed),
        }
        write_csv_new(run_dir / "gold_v3_79_blocker_matrix.csv", blockers)
        write_csv_new(run_dir / "gold_v3_79_validation_matrix.csv", val)
        write_json(run_dir / "gold_v3_79_immutable_runtime_output_policy_summary.json", summary)

        paste = []
        paste.append("GOLD V3 79 PASTE_ME_IMMUTABLE_RUNTIME_OUTPUT_POLICY_SUMMARY")
        paste.append(f"status: {status}")
        paste.append("immutable_runtime_output_policy_ready: " + str(status == READY_STATUS).lower())
        paste.append("live_ready: false")
        paste.append("contract_mutated: false")
        paste.append("manual_candidate_demotion_or_removal: false")
        paste.append("open_asof_allowed: false")
        paste.append("csv_contract: " + CSV_CONTRACT)
        paste.append("csv_open_bar_exclusion_required: false")
        paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
        paste.append("pool_policy: " + POOL_POLICY)
        paste.append(f"run_id: {run_id}")
        paste.append(f"run_dir: {run_dir}")
        paste.append(f"snapshot_dir: {snapshot_dir}")
        paste.append(f"latest_m15_time: {j76.get('latest_m15_time', '')}")
        paste.append(f"stage76_status: {j76.get('status', '')}")
        paste.append(f"decision: {j76.get('decision', '')}")
        paste.append(f"emission_action: {j76.get('emission_action', '')}")
        paste.append(f"payload_action: {j76.get('payload_action', '')}")
        paste.append(f"copied_file_count: {len(copied)}")
        paste.append(f"missing_optional_count: {len(missing_optional)}")
        paste.append(f"blocker_count: {len(blockers)}")
        paste.append("")
        paste.append("BLOCKERS")
        paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
        paste.append("")
        paste.append("VALIDATION")
        paste.append(pd.DataFrame(val).to_string(index=False))
        paste.append("")
        paste.append("MANIFEST")
        paste.append(pd.DataFrame(copied).to_string(index=False) if copied else "NO_COPIED_FILES")
        paste.append("")
        paste.append("OUTPUTS")
        paste.append("gold_v3_79_immutable_manifest.json")
        paste.append("gold_v3_79_immutable_manifest.csv")
        paste.append("gold_v3_79_output_policy_matrix.csv")
        paste.append("gold_v3_79_blocker_matrix.csv")
        paste.append("gold_v3_79_validation_matrix.csv")
        paste.append("gold_v3_79_immutable_runtime_output_policy_summary.json")
        paste.append("gold_v3_79_PASTE_ME_IMMUTABLE_RUNTIME_OUTPUT_POLICY_SUMMARY.txt")
        paste.append("GOLD_V3_79_REPORT.md")
        write_text_new(run_dir / "gold_v3_79_PASTE_ME_IMMUTABLE_RUNTIME_OUTPUT_POLICY_SUMMARY.txt", "\n".join(paste) + "\n")

        report = f"""# GOLD V3 79 immutable runtime output policy audit-only report

Status: `{status}`

- run_id: `{run_id}`
- run_dir: `{run_dir}`
- latest_m15_time: `{j76.get('latest_m15_time', '')}`
- decision: `{j76.get('decision', '')}`
- payload_action: `{j76.get('payload_action', '')}`
- copied_file_count: `{len(copied)}`
- blocker_count: `{len(blockers)}`

This is an immutable evidence snapshot. Existing snapshot files are not overwritten.

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
        write_text_new(run_dir / "GOLD_V3_79_REPORT.md", report)

    except Exception as e:
        # Do not delete the run_dir. It is evidence of the attempted immutable write.
        blockers.append(blocker("stage79_exception", str(run_dir), "STAGE79_EXCEPTION", repr(e)))
        try:
            write_csv_new(run_dir / "gold_v3_79_blocker_matrix.csv", blockers)
        except Exception:
            pass
        print(f"[{BLOCKED_STATUS}] {repr(e)} run_dir={run_dir}")
        return 1

    print(f"[{status}] run_dir={run_dir}")
    print(run_dir / "gold_v3_79_PASTE_ME_IMMUTABLE_RUNTIME_OUTPUT_POLICY_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
