#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find send_mt5_order_from_payload output directories under data/research_results.

Looks for directories containing:
- mt5_order_send_report.json
- mt5_order_send_results.csv

This is read-only and does not import MetaTrader5.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_SEARCH_ROOT = Path("data/research_results")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Find sender output dirs containing mt5_order_send_report.json and mt5_order_send_results.csv")
    p.add_argument("--search-root", type=Path, default=DEFAULT_SEARCH_ROOT)
    p.add_argument("--out-json", type=Path, default=None)
    p.add_argument("--out-csv", type=Path, default=None)
    p.add_argument("--limit", type=int, default=50)
    return p.parse_args()


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


def path_exists(path: Path) -> bool:
    try:
        return Path(windows_long_path(path)).exists()
    except Exception:
        return path.exists()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(windows_long_path(path)).read_text(encoding="utf-8"))
    except Exception as e:
        return {"_read_error": repr(e)}


def read_csv_len(path: Path) -> int:
    try:
        return int(len(pd.read_csv(windows_long_path(path), encoding="utf-8-sig")))
    except Exception:
        return 0


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def find_sender_dirs(search_root: Path, limit: int) -> list[dict[str, Any]]:
    if not path_exists(search_root):
        return []
    matches: list[dict[str, Any]] = []
    for report_path in Path(windows_long_path(search_root)).rglob("mt5_order_send_report.json"):
        # Convert long-path-ish Path back to normal display path when possible.
        report = Path(str(report_path))
        sender_dir = report.parent
        results = sender_dir / "mt5_order_send_results.csv"
        has_results = path_exists(results)
        report_json = read_json(report)
        row = {
            "sender_out_dir": str(sender_dir),
            "report_json": str(report),
            "results_csv": str(results),
            "has_results_csv": bool(has_results),
            "results_rows": read_csv_len(results) if has_results else 0,
            "input_csv": str(report_json.get("input_csv", "")),
            "send_requested": bool(report_json.get("send_requested", False)),
            "order_send_called_count": report_json.get("order_send_called_count", ""),
            "rows_in": report_json.get("rows_in", ""),
            "rows_out": report_json.get("rows_out", ""),
            "dry_run_check_ok_rows": report_json.get("dry_run_check_ok_rows", ""),
            "sent_rows": report_json.get("sent_rows", ""),
            "blocked_position_policy_rows": report_json.get("blocked_position_policy_rows", ""),
            "error_rows": report_json.get("error_rows", ""),
        }
        matches.append(row)
        if limit > 0 and len(matches) >= limit:
            break
    matches.sort(key=lambda r: str(r.get("sender_out_dir", "")))
    return matches


def main() -> int:
    args = parse_args()
    rows = find_sender_dirs(args.search_root, args.limit)
    summary = {
        "search_root": str(args.search_root),
        "found_count": int(len(rows)),
        "rows": rows,
    }
    if args.out_json:
        write_json(args.out_json, summary)
    if args.out_csv:
        write_csv(args.out_csv, rows)
    print("find_gold_multi_strategy_sender_report_outputs")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if rows:
        show_cols = [
            "sender_out_dir",
            "has_results_csv",
            "results_rows",
            "input_csv",
            "dry_run_check_ok_rows",
            "sent_rows",
            "blocked_position_policy_rows",
            "error_rows",
        ]
        print(pd.DataFrame(rows)[show_cols].to_string(index=False))
    else:
        print("[INFO] no sender output dirs found")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
