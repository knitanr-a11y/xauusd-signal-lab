from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alert_trigger_signature_audit import audit_trigger_signatures, write_csv
from db import open_database

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR / "schema.sql"
REPORT_NAME = "latest_alert_trigger_signature_audit.json"
EVENT_CSV_NAME = "latest_alert_trigger_event_features.csv"
RULE_CSV_NAME = "latest_alert_trigger_candidate_rules.csv"


def utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    local = default_local_root()
    parser = argparse.ArgumentParser(
        description=(
            "Infer exploratory, causal alert-trigger signatures by comparing genuine "
            "Mochipoyo events with no-event M15 decision boundaries."
        )
    )
    parser.add_argument("--env", type=Path, default=local / ".env")
    parser.add_argument("--db", type=Path, default=local / "mochipoyo_alerts.sqlite3")
    parser.add_argument("--output", type=Path, default=local / "logs" / REPORT_NAME)
    parser.add_argument(
        "--event-csv", type=Path, default=local / "logs" / EVENT_CSV_NAME
    )
    parser.add_argument(
        "--rule-csv", type=Path, default=local / "logs" / RULE_CSV_NAME
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = load_env(args.env)
    root_text = env.get("MT5_FILES_ROOT", "").strip()
    if not root_text:
        print("[ERROR] MT5_FILES_ROOT is not configured.")
        return 2
    mt5_root = Path(root_text)
    if not mt5_root.is_dir():
        print("[ERROR] Configured MT5 Files folder does not exist.")
        return 2
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
        result = audit_trigger_signatures(
            connection,
            mt5_files_root=mt5_root,
            built_at_utc=built_at_utc,
        )
        event_rows = list(result.pop("event_csv_rows"))
        rule_rows = list(result.pop("rule_csv_rows"))
        write_csv(args.event_csv, event_rows)
        write_csv(args.rule_csv, rule_rows)
        payload = {
            "status": "PASS",
            "stage": "M7A_ALERT_TRIGGER_SIGNATURE_AUDIT",
            "audit_only": True,
            "dry_run": True,
            "database_write_performed": False,
            "csv_input_modified": False,
            "derived_report_files_written": True,
            "genuine_alert_labels_used": True,
            "no_event_controls_used": True,
            "controls_outside_verified_observation_window_used": False,
            "alert_bar_ohlc_used": False,
            "closed_m15_features_only": True,
            "future_entry_fields_used": False,
            "exact_proprietary_condition_claimed": False,
            "independent_proxy_only": True,
            "historical_candidate_extraction_approved": False,
            "cross_timeframe_candidate_extraction_approved": False,
            "entry_gate_enabled": False,
            "automatic_trading_rule_approved": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "built_at_utc": built_at_utc,
            **result,
            "usage": "DISCOVERY_AUDIT_ONLY",
            "mt5_files_root": "<configured-mt5-files-root>",
            "database_path": str(args.db),
            "report_path": str(args.output),
            "event_feature_csv_path": str(args.event_csv),
            "candidate_rule_csv_path": str(args.rule_csv),
        }
        atomic_write_json(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        print(
            f"[ERROR] Alert trigger signature audit failed: "
            f"{type(exc).__name__}: {exc}"
        )
        print("[SAFE] Raw alerts, SQLite derived stages, and MT5 CSVs were not modified.")
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
