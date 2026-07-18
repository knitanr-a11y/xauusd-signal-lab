from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mt5_csv_contract import FILE_MAP, inspect_csv, load_m1_bars, provisional_offset, score_offsets


def utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip() or tempfile.gettempdir()
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_eligible_alerts(database: Path) -> list[dict[str, Any]]:
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        annotations_exist = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='raw_alert_annotations'"
        ).fetchone() is not None
        exclusion = ""
        if annotations_exist:
            exclusion = """
                WHERE NOT EXISTS (
                    SELECT 1 FROM raw_alert_annotations a
                    WHERE a.raw_alert_id = r.cloudflare_id
                      AND a.annotation_type = 'CONNECTION_TEST'
                )
            """
        rows = connection.execute(
            f"""
            SELECT r.cloudflare_id, r.ticker, r.event, r.fired_at_utc,
                   r.bar_time_utc, r.close_price
            FROM raw_alerts r
            {exclusion}
            ORDER BY r.cloudflare_id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    local = default_local_root()
    parser = argparse.ArgumentParser(description="Audit MT5 CSV inventory and infer broker clock offset without writing the database.")
    parser.add_argument("--env", type=Path, default=local / ".env")
    parser.add_argument("--db", type=Path, default=local / "mochipoyo_alerts.sqlite3")
    parser.add_argument("--output", type=Path, default=local / "logs" / "latest_mt5_csv_contract_audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = load_env(args.env)
    root_text = env.get("MT5_FILES_ROOT", "").strip()
    if not root_text:
        print("[ERROR] MT5_FILES_ROOT is not configured. Run run_configure_mt5_csv_root.bat first.")
        return 2
    root = Path(root_text)
    if not root.is_dir():
        print("[ERROR] Configured MT5 Files folder does not exist.")
        return 2
    if not args.db.is_file():
        print("[ERROR] Mochipoyo database does not exist.")
        return 2
    try:
        inventories = []
        for ticker, timeframes in FILE_MAP.items():
            for timeframe, filename in timeframes.items():
                inventories.append(inspect_csv(root / filename, ticker=ticker, timeframe=timeframe))
        alerts = read_eligible_alerts(args.db)
        m1 = {ticker: load_m1_bars(root / files["M1"]) for ticker, files in FILE_MAP.items()}
        scores = score_offsets(alerts, m1)
        selected = provisional_offset(scores)
        max_path_length = max(item.path_length for item in inventories)
        payload = {
            "status": "PASS",
            "stage": "M4_MT5_CSV_CONTRACT_AUDIT",
            "audit_only": True,
            "dry_run": True,
            "database_write_performed": False,
            "csv_write_performed": False,
            "future_entry_fields_used": False,
            "generated_at_utc": utc_now_text(),
            "mt5_files_root": "<configured-mt5-files-root>",
            "configured_root_length": len(str(root)),
            "maximum_input_path_length": max_path_length,
            "legacy_path_limit_risk": max_path_length >= 240,
            "inventory": [item.__dict__ for item in inventories],
            "eligible_alert_count": len(alerts),
            "offset_scoring_contract": {
                "candidate_offsets_hours": [-1, 0, 1, 2, 3, 4, 5],
                "source": "exact M1 minute at fired_at_utc plus candidate offset",
                "price_range_hit_tolerance_bps": 1.0,
                "fixed_offset_hardcoded": False,
                "dst_recheck_required": True,
            },
            "offset_scores": scores,
            "provisional_broker_offset": selected,
            "closed_bar_alignment_contract": {
                "csv_timestamp_meaning": "MT5 server-time bar open",
                "server_open_to_utc": "utc_open = server_open - inferred_offset",
                "utc_close": "utc_close = utc_open + timeframe duration",
                "selection_rule": "latest row with utc_close <= decision_time_utc",
                "same_printed_hour_join_forbidden": True,
                "h4_d1_note": "TradingView and MT5 bar boundaries may differ; align by closed interval/as-of, not matching labels.",
                "m15_note": "Source alert timestamps remain TradingView UTC; MT5 M15 is comparison context only.",
            },
            "database_path": str(args.db),
            "report_path": str(args.output),
        }
        atomic_write_json(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
