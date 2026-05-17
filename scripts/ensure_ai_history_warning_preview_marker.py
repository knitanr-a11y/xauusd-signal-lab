#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensure AI-history warning preview marker files exist for a multi-strategy out-dir.

Use this when a multi-strategy guarded demo-send cycle has payload_rows_out=0.
In that case there is no signal payload to render, so no real Discord preview is
created. This helper writes explicit marker files so the operator can confirm the
AI-history warning stage was skipped safely rather than silently missing.

This helper never sends Discord, never calls AI, and never places orders.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def read_json(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def infer_payload_rows(summary: dict[str, Any]) -> int:
    for path in [
        ["key_metrics", "payload_rows_out"],
        ["ai_history_warning_preview", "payload_rows_out"],
    ]:
        cur: Any = summary
        ok = True
        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok:
            return safe_int(cur, 0)
    dry = summary.get("dry_run_summary", {}) if isinstance(summary.get("dry_run_summary"), dict) else {}
    metrics = dry.get("key_metrics", {}) if isinstance(dry.get("key_metrics"), dict) else {}
    return safe_int(metrics.get("payload_rows_out"), 0)


def build_marker(out_dir: Path, reason: str, force: bool) -> dict[str, Any]:
    preview_dir = out_dir / "ai_history_warning_preview"
    txt_path = preview_dir / "ai_history_warning_discord_preview.txt"
    json_path = preview_dir / "ai_history_warning_discord_preview.json"
    enriched_csv = preview_dir / "discord_input_with_ai_history_warning.csv"
    summary_path = out_dir / "latest_gold_multi_strategy_guarded_demo_send_once_result.json"
    summary = read_json(summary_path)
    payload_rows = infer_payload_rows(summary)

    marker = {
        "schema_version": "ai_history_warning_preview_skip_marker_v1",
        "created_at_utc": utc_now_text(),
        "status": reason,
        "reason": "No AI-history Discord preview was rendered because there were no payload rows to preview." if reason == "SKIPPED_NO_PAYLOAD_ROWS" else reason,
        "out_dir": str(out_dir),
        "summary_json": str(summary_path),
        "payload_rows_out": int(payload_rows),
        "preview_txt": str(txt_path),
        "preview_json": str(json_path),
        "enriched_csv": str(enriched_csv),
        "safety": {
            "discord_sent": False,
            "ai_api_called": False,
            "order_sent": False,
            "sender_input_modified": False,
        },
    }

    if not force and txt_path.exists() and json_path.exists():
        marker["status"] = "ALREADY_EXISTS"
        return marker

    text = (
        "AI履歴警告プレビュー: SKIPPED_NO_PAYLOAD_ROWS\n"
        "理由: このmulti-strategy cycleでは order_payloads.csv が0件だったため、表示対象のシグナルがありません。\n"
        "状態: 正常スキップ。Discord送信なし / AI API呼び出しなし / 注文変更なし。\n"
        f"out_dir: {out_dir}\n"
        f"summary_json: {summary_path}\n"
        f"payload_rows_out: {payload_rows}\n"
    )
    write_text(txt_path, text)
    write_json(json_path, {
        "source": "ensure_ai_history_warning_preview_marker.py",
        "ai_history_warning": {
            "ai_history_warning_enabled": True,
            "ai_history_warning_status": reason,
            "ai_history_warning_rows_warn": 0,
        },
        "records": [],
        "marker": marker,
    })
    return marker


def main() -> int:
    p = argparse.ArgumentParser(description="Create AI-history preview marker files for a skipped/no-payload multi out-dir.")
    p.add_argument("--out-dir", required=True, help="The once-wrapper out-dir, e.g. data/runtime_logs/trade_ai_review/multi_ai_warning_once_test")
    p.add_argument("--reason", default="SKIPPED_NO_PAYLOAD_ROWS")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    marker = build_marker(out_dir, str(args.reason), bool(args.force))
    print("ensure_ai_history_warning_preview_marker")
    print(f"out_dir: {out_dir}")
    print(f"status: {marker.get('status')}")
    print(f"payload_rows_out: {marker.get('payload_rows_out')}")
    print(f"preview_txt: {marker.get('preview_txt')}")
    print(f"preview_json: {marker.get('preview_json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
