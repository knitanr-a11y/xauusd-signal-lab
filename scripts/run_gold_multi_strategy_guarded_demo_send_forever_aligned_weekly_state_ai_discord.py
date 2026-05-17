#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

import run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state as base  # type: ignore
from ensure_ai_history_warning_preview_marker import build_marker  # type: ignore

_ORIGINAL_RUN_ONCE = base.run_once
SUMMARY_NAME = "latest_gold_multi_strategy_guarded_demo_send_once_result.json"
PAYLOAD_CSV_REL = Path("dry_run_stage") / "payload" / "order_payloads.csv"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def _payload_rows_from_summary(summary: dict[str, Any]) -> int:
    metrics = summary.get("key_metrics", {}) if isinstance(summary.get("key_metrics"), dict) else {}
    if "payload_rows_out" in metrics:
        return _safe_int(metrics.get("payload_rows_out"), 0)
    return _safe_int(summary.get("payload_rows_out"), 0)


def _read_csv_rows(path: Path) -> int:
    if not base.path_exists(path):
        return 0
    try:
        return int(len(pd.read_csv(base.windows_long_path(path), encoding="utf-8-sig")))
    except EmptyDataError:
        return 0
    except Exception:
        return 0


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    base.write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def _run_cmd(label: str, cmd: list[str], cwd: Path) -> tuple[int, float]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


def _ensure_marker_when_no_payload(cycle_dir: Path) -> None:
    summary_path = cycle_dir / SUMMARY_NAME
    summary = base.read_json_or_empty(summary_path)
    payload_rows = _payload_rows_from_summary(summary)
    preview_json = cycle_dir / "ai_history_warning_preview" / "ai_history_warning_discord_preview.json"
    if payload_rows > 0 or base.path_exists(preview_json):
        return
    marker = build_marker(cycle_dir, "SKIPPED_NO_PAYLOAD_ROWS", force=True)
    print(
        "[INFO] AI-history warning preview marker ensured: "
        f"status={marker.get('status')} payload_rows_out={marker.get('payload_rows_out')} "
        f"preview_txt={marker.get('preview_txt')}",
        flush=True,
    )


def _discord_send_paths(cycle_dir: Path, persistent_ledger: Path) -> dict[str, Path]:
    preview_dir = cycle_dir / "ai_history_warning_discord_send"
    return {
        "preview_dir": preview_dir,
        "send_ledger_csv": persistent_ledger.parent / "multi_ai_history_discord_send_ledger.csv",
        "preview_txt": preview_dir / "ai_history_warning_discord_preview.txt",
        "preview_json": preview_dir / "ai_history_warning_discord_preview.json",
        "result_json": preview_dir / "multi_ai_history_discord_send_result.json",
        "payload_csv": cycle_dir / PAYLOAD_CSV_REL,
    }


def _read_send_result(preview_json: Path) -> dict[str, Any]:
    obj = base.read_json_or_empty(preview_json)
    records = obj.get("records", []) if isinstance(obj.get("records"), list) else []
    sent = sum(1 for r in records if isinstance(r, dict) and bool(r.get("sent")))
    errors = sum(1 for r in records if isinstance(r, dict) and str(r.get("send_status", "")).startswith("ERROR"))
    would = sum(1 for r in records if isinstance(r, dict) and str(r.get("send_status", "")) == "DRY_RUN_WOULD_SEND")
    warn = 0
    for r in records:
        if isinstance(r, dict) and str(r.get("ai_history_warning_status", "")).upper() == "WARN":
            warn += 1
    return {
        "records": len(records),
        "sent": sent,
        "errors": errors,
        "dry_run_would_send": would,
        "warning_rows": warn,
        "raw": obj,
    }


def _send_multi_ai_discord(cycle_dir: Path, persistent_ledger: Path) -> None:
    paths = _discord_send_paths(cycle_dir, persistent_ledger)
    payload_rows = _read_csv_rows(paths["payload_csv"])
    if payload_rows <= 0:
        _ensure_marker_when_no_payload(cycle_dir)
        return

    cmd = [
        sys.executable,
        str(base.REPO_ROOT / "scripts" / "send_mochipoyo_discord_messages.py"),
        "--input-csv", str(paths["payload_csv"]),
        "--send-ledger-csv", str(paths["send_ledger_csv"]),
        "--preview-txt", str(paths["preview_txt"]),
        "--preview-json", str(paths["preview_json"]),
        "--symbol", "GOLD",
        "--max-rows", str(max(1, payload_rows)),
        "--style", "compact",
        "--send",
    ]
    rc, elapsed = _run_cmd("multi_ai_history_discord_send", cmd, base.REPO_ROOT)
    parsed = _read_send_result(paths["preview_json"])
    result = {
        "schema_version": "gold_multi_ai_history_discord_send_result_v1",
        "created_at_utc": base.utc_text(),
        "cycle_dir": str(cycle_dir),
        "payload_csv": str(paths["payload_csv"]),
        "payload_rows": int(payload_rows),
        "returncode": int(rc),
        "elapsed_seconds": float(elapsed),
        "send_ledger_csv": str(paths["send_ledger_csv"]),
        "preview_txt": str(paths["preview_txt"]),
        "preview_json": str(paths["preview_json"]),
        "records": parsed.get("records", 0),
        "sent": parsed.get("sent", 0),
        "errors": parsed.get("errors", 0),
        "warning_rows": parsed.get("warning_rows", 0),
        "safety": {
            "mt5_order_payload_modified": False,
            "mt5_order_send_called_by_this_step": False,
            "ai_api_called": False,
            "discord_send_requested": True,
            "duplicate_prevention_ledger": str(paths["send_ledger_csv"]),
        },
    }
    _write_json(paths["result_json"], result)
    print(
        "[INFO] multi AI Discord send result: "
        f"returncode={rc} payload_rows={payload_rows} sent={result['sent']} "
        f"errors={result['errors']} warning_rows={result['warning_rows']} "
        f"preview_txt={paths['preview_txt']}",
        flush=True,
    )


def run_once(cycle_index: int, args: Any, out_dir: Path, persistent_ledger: Path):
    result = _ORIGINAL_RUN_ONCE(cycle_index, args, out_dir, persistent_ledger)
    try:
        cycle_dir = Path(result[6])
        _send_multi_ai_discord(cycle_dir, persistent_ledger)
    except Exception as exc:
        print(f"[WARN] failed to run multi AI Discord step: {exc!r}", flush=True)
    return result


base.run_once = run_once


if __name__ == "__main__":
    raise SystemExit(base.main())
