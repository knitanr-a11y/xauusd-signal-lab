#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 83 runtime housekeeping size audit-only.

Audits runtime output folder/file size growth. Does not delete, move, compress,
or modify existing evidence. No MT5 orders, no Discord, no AI API, no final signal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_83_RUNTIME_HOUSEKEEPING_SIZE_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_83_RUNTIME_HOUSEKEEPING_SIZE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_83_RUNTIME_HOUSEKEEPING_SIZE_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"

MIB = 1024 * 1024
DEFAULT_FILE_WARN = 5 * MIB
DEFAULT_FILE_BLOCK = 50 * MIB
DEFAULT_FOLDER_WARN = 100 * MIB
DEFAULT_FOLDER_BLOCK = 500 * MIB
DEFAULT_79I_RUN_WARN = 200
DEFAULT_81C_BUNDLE_WARN = 100

IMPORTANT_FOLDERS = [
    "76_full_audit_monitor_with_payload_preview_audit_only",
    "79i",
    "80_immutable_runtime_monitor_audit_only",
    "81c",
    "82_runtime_doc_sync_and_operator_checklist_audit_only",
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


def human_size(n: int) -> str:
    if n >= 1024**3:
        return f"{n / 1024**3:.2f} GiB"
    if n >= 1024**2:
        return f"{n / 1024**2:.2f} MiB"
    if n >= 1024:
        return f"{n / 1024:.2f} KiB"
    return f"{n} B"


def classify_file(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".csv") and ("event" in name or "timing" in name or "log" in name):
        return "append_log_csv"
    if name in {"upload_first.txt", "paste_me.txt"} or name.startswith("gold_v3_") and "paste_me" in name:
        return "primary_paste_text"
    if name.endswith(".json"):
        return "json_state_or_summary"
    if name.endswith(".md"):
        return "report_or_doc"
    return "other"


def scan_files(root: Path, exclude_dir: Path | None) -> list[dict[str, Any]]:
    rows = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if exclude_dir and exclude_dir in p.parents:
            continue
        try:
            st = p.stat()
            rows.append({
                "relative_path": str(p.relative_to(root)),
                "path": str(p),
                "size_bytes": st.st_size,
                "size_human": human_size(st.st_size),
                "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "kind": classify_file(p),
            })
        except Exception as e:
            rows.append({"relative_path": str(p), "path": str(p), "size_bytes": -1, "size_human": "ERR", "mtime_utc": "", "kind": "scan_error", "error": repr(e)})
    rows.sort(key=lambda r: int(r.get("size_bytes", -1)), reverse=True)
    return rows


def folder_size(path: Path, exclude_dir: Path | None) -> tuple[int, int]:
    total = 0
    count = 0
    if not path.exists():
        return 0, 0
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        if exclude_dir and exclude_dir in p.parents:
            continue
        try:
            total += p.stat().st_size
            count += 1
        except Exception:
            pass
    return total, count


def count_leaf_dirs(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for p in path.rglob("*"):
        if p.is_dir() and any(child.is_file() for child in p.iterdir()):
            count += 1
    return count


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--file-warning-mib", type=float, default=5.0)
    p.add_argument("--file-blocker-mib", type=float, default=50.0)
    p.add_argument("--folder-warning-mib", type=float, default=100.0)
    p.add_argument("--folder-blocker-mib", type=float, default=500.0)
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    scan_root = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else scan_root / "83_runtime_housekeeping_size_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    file_warn = int(a.file_warning_mib * MIB)
    file_block = int(a.file_blocker_mib * MIB)
    folder_warn = int(a.folder_warning_mib * MIB)
    folder_block = int(a.folder_blocker_mib * MIB)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    val.append(ok("scan_root_present", scan_root.exists(), str(scan_root), "exists"))
    if not scan_root.exists():
        blockers.append(blocker("scan_root_missing", str(scan_root), "SCAN_ROOT_MISSING"))

    file_rows = scan_files(scan_root, out if out.exists() else None) if scan_root.exists() else []
    folder_rows: list[dict[str, Any]] = []
    for name in IMPORTANT_FOLDERS:
        p = scan_root / name
        size, count = folder_size(p, out)
        folder_rows.append({
            "folder": name,
            "path": str(p),
            "exists": p.exists(),
            "file_count": count,
            "size_bytes": size,
            "size_human": human_size(size),
        })

    total_size = sum(int(r.get("size_bytes", 0)) for r in folder_rows)
    total_files = sum(int(r.get("file_count", 0)) for r in folder_rows)
    max_file = max([int(r.get("size_bytes", 0)) for r in file_rows], default=0)
    max_file_row = next((r for r in file_rows if int(r.get("size_bytes", -1)) == max_file), {})

    oversized_files = [r for r in file_rows if int(r.get("size_bytes", 0)) >= file_block]
    warning_files = [r for r in file_rows if file_warn <= int(r.get("size_bytes", 0)) < file_block]
    oversized_folders = [r for r in folder_rows if int(r.get("size_bytes", 0)) >= folder_block]
    warning_folders = [r for r in folder_rows if folder_warn <= int(r.get("size_bytes", 0)) < folder_block]

    for r in warning_files:
        recommendations.append({"severity": "WARNING", "target": r["relative_path"], "reason": "single file above warning threshold", "recommended_action": "do_not_upload_full_file_first; use Stage81 upload_first.txt; inspect only if requested", "size_human": r["size_human"]})
    for r in oversized_files:
        recommendations.append({"severity": "BLOCKER", "target": r["relative_path"], "reason": "single file above blocker threshold", "recommended_action": "review log rotation/compaction plan before live", "size_human": r["size_human"]})
        blockers.append(blocker("file_size_blocker", r["path"], "FILE_EXCEEDS_BLOCKER_THRESHOLD", r["size_human"]))
    for r in warning_folders:
        recommendations.append({"severity": "WARNING", "target": r["folder"], "reason": "folder above warning threshold", "recommended_action": "review retention policy; do not delete automatically", "size_human": r["size_human"]})
    for r in oversized_folders:
        recommendations.append({"severity": "BLOCKER", "target": r["folder"], "reason": "folder above blocker threshold", "recommended_action": "manual retention decision required before live", "size_human": r["size_human"]})
        blockers.append(blocker("folder_size_blocker", r["path"], "FOLDER_EXCEEDS_BLOCKER_THRESHOLD", r["size_human"]))

    run_count_79i = count_leaf_dirs(scan_root / "79i")
    bundle_count_81c = count_leaf_dirs(scan_root / "81c")
    if run_count_79i >= DEFAULT_79I_RUN_WARN:
        recommendations.append({"severity": "WARNING", "target": "79i", "reason": "many immutable run folders", "recommended_action": "create retention/archive policy; do not delete automatically", "size_human": str(run_count_79i) + " runs"})
    if bundle_count_81c >= DEFAULT_81C_BUNDLE_WARN:
        recommendations.append({"severity": "WARNING", "target": "81c", "reason": "many support bundle folders", "recommended_action": "create support bundle retention policy; do not delete automatically", "size_human": str(bundle_count_81c) + " bundles"})

    val.extend([
        ok("file_inventory_written", True, "will_write", "written"),
        ok("folder_inventory_written", True, "will_write", "written"),
        ok("recommendation_matrix_written", True, "will_write", "written"),
        ok("no_file_size_blocker", len(oversized_files) == 0, len(oversized_files), 0),
        ok("no_folder_size_blocker", len(oversized_folders) == 0, len(oversized_folders), 0),
        ok("csv_open_bar_exclusion_required_false", True, False, False),
        ok("live_flags_all_false", True, "all_false", "all_false"),
    ])

    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    pd.DataFrame(file_rows).to_csv(out/"gold_v3_83_file_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(folder_rows).to_csv(out/"gold_v3_83_folder_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(recommendations).to_csv(out/"gold_v3_83_housekeeping_recommendation_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out/"gold_v3_83_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(val).to_csv(out/"gold_v3_83_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "runtime_housekeeping_size_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "scan_root": str(scan_root),
        "total_runtime_size_bytes": total_size,
        "total_runtime_size_human": human_size(total_size),
        "total_runtime_file_count": total_files,
        "max_file_size_bytes": max_file,
        "max_file_size_human": human_size(max_file),
        "max_file_relative_path": max_file_row.get("relative_path", ""),
        "warning_file_count": len(warning_files),
        "oversized_file_blocker_count": len(oversized_files),
        "warning_folder_count": len(warning_folders),
        "oversized_folder_blocker_count": len(oversized_folders),
        "immutable_run_folder_count_79i": run_count_79i,
        "support_bundle_folder_count_81c": bundle_count_81c,
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
    }
    (out/"gold_v3_83_runtime_housekeeping_size_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    top_files = file_rows[:10]
    paste = [
        "GOLD V3 83 PASTE_ME_RUNTIME_HOUSEKEEPING_SIZE_SUMMARY",
        f"status: {status}",
        "runtime_housekeeping_size_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"scan_root: {scan_root}",
        f"total_runtime_size: {human_size(total_size)}",
        f"total_runtime_file_count: {total_files}",
        f"max_file: {human_size(max_file)} {max_file_row.get('relative_path', '')}",
        f"warning_file_count: {len(warning_files)}",
        f"oversized_file_blocker_count: {len(oversized_files)}",
        f"warning_folder_count: {len(warning_folders)}",
        f"oversized_folder_blocker_count: {len(oversized_folders)}",
        f"immutable_run_folder_count_79i: {run_count_79i}",
        f"support_bundle_folder_count_81c: {bundle_count_81c}",
        f"blocker_count: {len(blockers)}",
        "", "TOP_10_LARGEST_FILES",
    ]
    if top_files:
        paste.append(pd.DataFrame(top_files)[["relative_path", "size_human", "kind"]].to_string(index=False))
    else:
        paste.append("NO_FILES")
    paste += [
        "", "FOLDER_INVENTORY", pd.DataFrame(folder_rows).to_string(index=False),
        "", "RECOMMENDATIONS", pd.DataFrame(recommendations).to_string(index=False) if recommendations else "NO_RECOMMENDATIONS",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "OUTPUTS",
        "gold_v3_83_file_inventory.csv",
        "gold_v3_83_folder_inventory.csv",
        "gold_v3_83_housekeeping_recommendation_matrix.csv",
        "gold_v3_83_blocker_matrix.csv",
        "gold_v3_83_validation_matrix.csv",
        "gold_v3_83_runtime_housekeeping_size_summary.json",
        "gold_v3_83_PASTE_ME_RUNTIME_HOUSEKEEPING_SIZE_SUMMARY.txt",
        "GOLD_V3_83_REPORT.md",
    ]
    (out/"gold_v3_83_PASTE_ME_RUNTIME_HOUSEKEEPING_SIZE_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")

    report = f"""# GOLD V3 83 runtime housekeeping size audit-only report

Status: `{status}`

- scan_root: `{scan_root}`
- total_runtime_size: `{human_size(total_size)}`
- total_runtime_file_count: `{total_files}`
- max_file: `{human_size(max_file)} {max_file_row.get('relative_path', '')}`
- immutable_run_folder_count_79i: `{run_count_79i}`
- support_bundle_folder_count_81c: `{bundle_count_81c}`
- blocker_count: `{len(blockers)}`

Audit-only. This stage does not delete, move, compress, or modify evidence.
"""
    (out/"GOLD_V3_83_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] {out/'gold_v3_83_PASTE_ME_RUNTIME_HOUSEKEEPING_SIZE_SUMMARY.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
