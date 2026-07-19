from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alert_function_context_builder import rebuild_alert_function_context_map
from db import open_database

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR / "schema.sql"
REPORT_NAME = "latest_alert_function_context_map.json"


def utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_local_root() -> Path:
    base = (
        os.environ.get("LOCALAPPDATA", "").strip()
        or os.environ.get("TEMP", "").strip()
        or tempfile.gettempdir()
    )
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    local = default_local_root()
    parser = argparse.ArgumentParser(
        description=(
            "Build the audit-only Mochipoyo alert function context map from "
            "entry-time M5 features and M6A outcome measurements."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=local / "mochipoyo_alerts.sqlite3",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=local / "logs" / REPORT_NAME,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.db.is_file():
        print("[ERROR] Mochipoyo database does not exist.")
        return 2

    built_at_utc = utc_now_text()
    try:
        connection = open_database(args.db, SCHEMA_PATH)
    except Exception as exc:
        print(f"[ERROR] Database open failed: {type(exc).__name__}: {exc}")
        return 2

    try:
        result = rebuild_alert_function_context_map(
            connection,
            built_at_utc=built_at_utc,
        )
        payload = {
            "status": "PASS",
            "stage": "M6B_ALERT_FUNCTION_CONTEXT_MAP",
            "audit_only": True,
            "dry_run": True,
            "database_write_performed": True,
            "derived_context_rows_rebuilt": True,
            "derived_cohort_rows_rebuilt": True,
            "raw_alerts_modified": False,
            "episodes_modified": False,
            "mt5_alignment_modified": False,
            "feature_snapshots_modified": False,
            "virtual_entries_modified": False,
            "outcomes_modified": False,
            "outcome_path_metrics_modified": False,
            "future_entry_fields_used": False,
            "post_entry_data_used_for_context_class": False,
            "post_entry_data_used_for_outcome_labels": True,
            "entry_gate_enabled": False,
            "automatic_trading_rule_approved": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "built_at_utc": built_at_utc,
            **result,
            "context_usage": "AUDIT_CONTEXT_ONLY",
            "database_path": str(args.db),
            "report_path": str(args.output),
        }
        atomic_write_json(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        print(
            f"[ERROR] Alert function context map failed: "
            f"{type(exc).__name__}: {exc}"
        )
        print(
            "[SAFE] Previous successful M6B context/cohort rows were preserved "
            "unless the failure occurred after the atomic transaction began."
        )
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
