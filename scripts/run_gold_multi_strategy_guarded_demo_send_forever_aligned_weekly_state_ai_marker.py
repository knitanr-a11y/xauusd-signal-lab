#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any

import run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state as base  # type: ignore
from ensure_ai_history_warning_preview_marker import build_marker  # type: ignore

_ORIGINAL_RUN_ONCE = base.run_once
SUMMARY_NAME = "latest_gold_multi_strategy_guarded_demo_send_once_result.json"


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


def run_once(cycle_index: int, args: Any, out_dir: Path, persistent_ledger: Path):
    result = _ORIGINAL_RUN_ONCE(cycle_index, args, out_dir, persistent_ledger)
    try:
        cycle_dir = Path(result[6])
        _ensure_marker_when_no_payload(cycle_dir)
    except Exception as exc:
        print(f"[WARN] failed to ensure AI-history warning preview marker: {exc!r}", flush=True)
    return result


base.run_once = run_once


if __name__ == "__main__":
    raise SystemExit(base.main())
