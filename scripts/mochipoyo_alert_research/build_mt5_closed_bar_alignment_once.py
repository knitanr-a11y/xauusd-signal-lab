from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db import open_database
from mt5_alignment_builder import build_mt5_closed_bar_alignment

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR / "schema.sql"
REPORT_NAME = "latest_mt5_closed_bar_alignment_result.json"


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_local_root() -> Path:
    base = (
        os.environ.get("LOCALAPPDATA", "").strip()
        or os.environ.get("TEMP", "").strip()
        or tempfile.gettempdir()
    )
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
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    local_root = default_local_root()
    parser = argparse.ArgumentParser(
        description=(
            "Build audit-only MT5 M5/M15/H1/H4/D1 closed-bar as-of "
            "alignment for eligible Mochipoyo alerts."
        )
    )
    parser.add_argument("--env", type=Path, default=local_root / ".env")
    parser.add_argument(
        "--db",
        type=Path,
        default=local_root / "mochipoyo_alerts.sqlite3",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=local_root / "logs" / REPORT_NAME,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = load_env(args.env)
    root_text = env.get("MT5_FILES_ROOT", "").strip()
    if not root_text:
        print(
            "[ERROR] MT5_FILES_ROOT is not configured. "
            "Run run_configure_mt5_csv_root.bat first."
        )
        return 2

    mt5_files_root = Path(root_text)
    if not mt5_files_root.is_dir():
        print("[ERROR] Configured MT5 Files folder does not exist.")
        return 2
    if not args.db.is_file():
        print("[ERROR] Mochipoyo database does not exist.")
        return 2

    built_at_utc = utc_now_text()
    try:
        connection = open_database(args.db, SCHEMA_PATH)
    except Exception as exc:
        print(f"[ERROR] Failed to open database: {type(exc).__name__}: {exc}")
        return 2

    try:
        result = build_mt5_closed_bar_alignment(
            connection,
            mt5_files_root=mt5_files_root,
            built_at_utc=built_at_utc,
        )

        by_ticker_timeframe = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    r.ticker,
                    a.timeframe,
                    COUNT(*) AS alignment_count,
                    MIN(a.time_diff_seconds) AS minimum_bar_age_seconds,
                    MAX(a.time_diff_seconds) AS maximum_bar_age_seconds
                FROM mt5_alignment a
                JOIN raw_alerts r ON r.cloudflare_id = a.raw_alert_id
                GROUP BY r.ticker, a.timeframe
                ORDER BY r.ticker, a.timeframe
                """
            ).fetchall()
        ]
        by_event = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    r.event,
                    COUNT(DISTINCT a.raw_alert_id) AS alert_count,
                    COUNT(*) AS alignment_count
                FROM mt5_alignment a
                JOIN raw_alerts r ON r.cloudflare_id = a.raw_alert_id
                GROUP BY r.event
                ORDER BY r.event
                """
            ).fetchall()
        ]

        payload = {
            "status": "PASS",
            "stage": "M4_MT5_CLOSED_BAR_ALIGNMENT",
            "audit_only": True,
            "dry_run": True,
            "database_write_performed": True,
            "derived_alignment_table_rebuilt": True,
            "raw_alerts_modified": False,
            "episodes_modified": False,
            "csv_write_performed": False,
            "future_entry_fields_used": False,
            "entry_gate_enabled": False,
            "live_ready": False,
            "final_signal": False,
            "discord_send": False,
            "mt5_order": False,
            "built_at_utc": built_at_utc,
            **result,
            "by_ticker_timeframe": by_ticker_timeframe,
            "by_event": by_event,
            "alignment_contract": {
                "offset_fixed_hardcoded": False,
                "offset_source": "M1 price-range audit over eligible alerts",
                "dst_recheck_required": True,
                "csv_timestamp_meaning": "MT5 server-time bar open",
                "selected_value_meaning": (
                    "estimated_mt5_time_utc stores selected bar UTC close"
                ),
                "selection_rule": (
                    "latest estimated UTC close <= TradingView fired_at_utc"
                ),
                "same_printed_hour_join_forbidden": True,
                "h4_d1_boundary_equivalence_assumed": False,
                "usage": "AUDIT_CONTEXT_ONLY",
            },
            "mt5_files_root": "<configured-mt5-files-root>",
            "database_path": str(args.db),
            "report_path": str(args.output),
        }
        atomic_write_json(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(
            "[ERROR] MT5 closed-bar alignment failed; previous derived "
            f"alignment was preserved: {type(exc).__name__}: {exc}"
        )
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
