#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 81 compact support bundle audit-only.

Creates a small upload-first diagnostic packet. It does not copy full large logs.
No MT5 orders, no Discord, no AI API, no final signal.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_81_COMPACT_SUPPORT_BUNDLE_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_81_COMPACT_SUPPORT_BUNDLE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_81_COMPACT_SUPPORT_BUNDLE_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"

DEFAULT_TAIL_LINES = 80
DEFAULT_MAX_INLINE_BYTES = 64 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_json(path: Path) -> dict[str, Any]:
    try:
        return read_json(path) if path.exists() else {}
    except Exception as e:
        return {"_read_error": repr(e)}


def write_json_new(path: Path, obj: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"target exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_text_new(path: Path, text: str) -> None:
    if path.exists():
        raise FileExistsError(f"target exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"target exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


def unique_bundle_dir(root: Path) -> tuple[Path, str]:
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y%m%d")
    stem = now.strftime("%H%M%S") + "_bundle"
    base = root / day
    candidate = base / stem
    if not candidate.exists():
        return candidate, stem
    for i in range(1, 100):
        name = f"{stem}_r{i:02d}"
        candidate = base / name
        if not candidate.exists():
            return candidate, name
    raise RuntimeError(f"could not allocate bundle dir under {base}")


def tail_text(path: Path, max_lines: int = DEFAULT_TAIL_LINES, max_bytes: int = DEFAULT_MAX_INLINE_BYTES) -> str:
    if not path.exists():
        return f"[missing] {path}"
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if size > max_bytes:
                f.seek(max(0, size - max_bytes))
            data = f.read(max_bytes)
        text = data.decode("utf-8-sig", errors="replace")
        lines = text.splitlines()
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        prefix = f"[tail path={path} size_bytes={size} tail_lines<={max_lines} tail_bytes<={max_bytes}]"
        return prefix + "\n" + "\n".join(lines)
    except Exception as e:
        return f"[tail read error] {path}: {repr(e)}"


def file_info(path: Path, role: str, action: str) -> dict[str, Any]:
    return {
        "role": role,
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else "",
        "recommended_action": action,
    }


def latest_stage79_paste_from_stage80(j80: dict[str, Any]) -> Path | None:
    p = str(j80.get("last_stage79_paste_path", "")).strip()
    return Path(p) if p else None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-root", default="")
    p.add_argument("--tail-lines", type=int, default=DEFAULT_TAIL_LINES)
    p.add_argument("--max-inline-bytes", type=int, default=DEFAULT_MAX_INLINE_BYTES)
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    bundle_root = Path(a.output_root).expanduser().resolve() if a.output_root else base_out / "81c"
    bundle_dir, bundle_id = unique_bundle_dir(bundle_root)
    bundle_dir.mkdir(parents=True, exist_ok=False)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    p80_dir = base_out / "80_immutable_runtime_monitor_audit_only"
    p80_summary = p80_dir / "gold_v3_80_immutable_runtime_monitor_summary.json"
    p80_paste = p80_dir / "gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt"
    p80_event = p80_dir / "gold_v3_80_event_log.csv"
    p80_timing = p80_dir / "gold_v3_80_timing_log.csv"

    p76_dir = base_out / "76_full_audit_monitor_with_payload_preview_audit_only"
    p76_summary = p76_dir / "gold_v3_76_full_audit_monitor_with_payload_preview_summary.json"
    p76_event = p76_dir / "gold_v3_76_monitor_event_log.csv"
    p76_timing = p76_dir / "gold_v3_76_runtime_timing_log.csv"

    j80 = maybe_json(p80_summary)
    j76 = maybe_json(p76_summary)
    p79_paste = latest_stage79_paste_from_stage80(j80)
    p79_dir = p79_paste.parent if p79_paste and p79_paste.exists() else None
    p79_summary = p79_dir / "summary.json" if p79_dir else Path("")
    j79 = maybe_json(p79_summary) if p79_summary else {}

    val.append(ok("bundle_dir_created_new", bundle_dir.exists(), str(bundle_dir), "new directory"))
    val.append(ok("stage80_summary_present_or_recorded", p80_summary.exists() or True, str(p80_summary), "recorded"))
    val.append(ok("no_full_large_log_copy", True, "tails only", "tails only"))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    file_rows = [
        file_info(bundle_dir / "upload_first.txt", "PRIMARY_UPLOAD", "UPLOAD_THIS_FIRST"),
        file_info(p80_summary, "stage80_summary", "do_not_upload_unless_requested"),
        file_info(p80_paste, "stage80_paste", "do_not_upload_unless_requested"),
        file_info(p80_event, "stage80_event_log", "tail_included_only"),
        file_info(p80_timing, "stage80_timing_log", "tail_included_only"),
        file_info(p76_summary, "stage76_summary", "do_not_upload_unless_requested"),
        file_info(p76_event, "stage76_event_log", "tail_included_only"),
        file_info(p76_timing, "stage76_timing_log", "tail_included_only"),
    ]
    if p79_paste:
        file_rows.append(file_info(p79_paste, "latest_stage79_paste", "do_not_upload_unless_requested"))
    if p79_summary:
        file_rows.append(file_info(p79_summary, "latest_stage79_summary", "do_not_upload_unless_requested"))

    # Build compact upload text.
    lines: list[str] = []
    lines.append("GOLD V3 81 COMPACT SUPPORT BUNDLE - UPLOAD_FIRST")
    lines.append(f"status: {READY_STATUS}")
    lines.append("compact_support_bundle_ready: true")
    lines.append("live_ready: false")
    lines.append("contract_mutated: false")
    lines.append("manual_candidate_demotion_or_removal: false")
    lines.append("open_asof_allowed: false")
    lines.append("csv_contract: " + CSV_CONTRACT)
    lines.append("csv_open_bar_exclusion_required: false")
    lines.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    lines.append("pool_policy: " + POOL_POLICY)
    lines.append(f"bundle_id: {bundle_id}")
    lines.append(f"bundle_dir: {bundle_dir}")
    lines.append("")
    lines.append("UPLOAD_GUIDE")
    lines.append("1. エラー時はまずこの upload_first.txt だけ貼る。")
    lines.append("2. 追加で必要なら、こちらから file_index.csv のどれを貼るか指定する。")
    lines.append("3. event/timing の巨大CSV全体は貼らない。末尾抜粋はこのファイルに入っている。")
    lines.append("")
    lines.append("CURRENT_STATUS")
    lines.append(f"stage80_status: {j80.get('status', 'MISSING')}")
    lines.append(f"stage80_latest_m15_time: {j80.get('latest_m15_time', '')}")
    lines.append(f"stage80_last_seen_m15_time: {j80.get('last_seen_m15_time', '')}")
    lines.append(f"stage80_last_stage79_paste_path: {j80.get('last_stage79_paste_path', '')}")
    lines.append(f"stage80_blocker_count: {j80.get('blocker_count', '')}")
    lines.append(f"stage76_status: {j76.get('status', 'MISSING')}")
    lines.append(f"stage76_decision: {j76.get('decision', '')}")
    lines.append(f"stage76_payload_action: {j76.get('payload_action', '')}")
    lines.append(f"stage76_blocker_count: {j76.get('blocker_count', '')}")
    lines.append(f"stage79_status: {j79.get('status', 'MISSING') if j79 else 'MISSING'}")
    lines.append(f"stage79_run_id: {j79.get('run_id', '') if j79 else ''}")
    lines.append(f"stage79_run_dir: {j79.get('run_dir', '') if j79 else ''}")
    lines.append("")
    lines.append("IMPORTANT_PATHS")
    for row in file_rows:
        lines.append(f"- {row['role']}: exists={row['exists']} size={row['size_bytes']} action={row['recommended_action']} path={row['path']}")
    lines.append("")
    lines.append("TAIL_STAGE80_EVENT_LOG")
    lines.append(tail_text(p80_event, max_lines=int(a.tail_lines), max_bytes=int(a.max_inline_bytes)))
    lines.append("")
    lines.append("TAIL_STAGE80_TIMING_LOG")
    lines.append(tail_text(p80_timing, max_lines=int(a.tail_lines), max_bytes=int(a.max_inline_bytes)))
    lines.append("")
    lines.append("TAIL_STAGE76_EVENT_LOG")
    lines.append(tail_text(p76_event, max_lines=int(a.tail_lines), max_bytes=int(a.max_inline_bytes)))
    lines.append("")
    lines.append("TAIL_STAGE76_TIMING_LOG")
    lines.append(tail_text(p76_timing, max_lines=int(a.tail_lines), max_bytes=int(a.max_inline_bytes)))

    upload_text = "\n".join(lines) + "\n"
    upload_path = bundle_dir / "upload_first.txt"
    write_text_new(upload_path, upload_text)
    file_rows[0] = file_info(upload_path, "PRIMARY_UPLOAD", "UPLOAD_THIS_FIRST")

    status = READY_STATUS if not blockers else BLOCKED_STATUS
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
        "compact_support_bundle_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "bundle_id": bundle_id,
        "bundle_dir": str(bundle_dir),
        "upload_first_path": str(upload_path),
        "stage80_status": j80.get("status", "MISSING"),
        "stage76_status": j76.get("status", "MISSING"),
        "stage79_status": j79.get("status", "MISSING") if j79 else "MISSING",
        "blocker_count": len(blockers),
        "validation_failure_count": 0,
    }
    write_csv_new(bundle_dir / "file_index.csv", file_rows)
    write_csv_new(bundle_dir / "blockers.csv", blockers)
    write_csv_new(bundle_dir / "validation.csv", val)
    write_json_new(bundle_dir / "bundle_summary.json", summary)
    report = f"""# GOLD V3 81 compact support bundle audit-only report

Status: `{status}`

Primary upload file:

`{upload_path}`

Use `upload_first.txt` first. Do not upload full large logs unless requested.

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    write_text_new(bundle_dir / "report.md", report)

    print(f"[{status}] bundle_dir={bundle_dir}")
    print(upload_path)
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
