from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alert_entry_timing_builder import rebuild_m5_entry_timing_audit
from db import open_database

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR / "schema.sql"
REPORT_NAME = "latest_m5_entry_timing_audit.json"


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
        description="Build the audit-only causal M5 entry timing comparison."
    )
    parser.add_argument("--env", type=Path, default=local / ".env")
    parser.add_argument("--db", type=Path, default=local / "mochipoyo_alerts.sqlite3")
    parser.add_argument("--output", type=Path, default=local / "logs" / REPORT_NAME)
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
        result = rebuild_m5_entry_timing_audit(
            connection,
            mt5_files_root=mt5_root,
            built_at_utc=built_at_utc,
        )
        payload = {
            "status": "PASS",
            "stage": "M6C_M5_ENTRY_TIMING_AUDIT",
            "audit_only": True,
            "dry_run": True,
            "database_write_performed": True,
            "derived_candidate_rows_rebuilt": True,
            "derived_timing_outcome_rows_rebuilt": True,
            "derived_cohort_rows_rebuilt": True,
            "raw_alerts_modified": False,
            "episodes_modified": False,
            "mt5_alignment_modified": False,
            "feature_snapshots_modified": False,
            "virtual_entries_modified": False,
            "source_outcomes_modified": False,
            "future_entry_fields_used": False,
            "post_entry_data_used_for_candidate_detection": False,
            "post_entry_data_used_for_outcome_measurement": True,
            "entry_gate_enabled": False,
            "automatic_trading_rule_approved": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "built_at_utc": built_at_utc,
            **result,
            "usage": "AUDIT_CONTEXT_ONLY",
            "mt5_files_root": "<configured-mt5-files-root>",
            "database_path": str(args.db),
            "report_path": str(args.output),
        }
        atomic_write_json(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        print(
            f"[ERROR] M5 entry timing audit failed: "
            f"{type(exc).__name__}: {exc}"
        )
        print(
            "[SAFE] Previous successful M6C derived rows were preserved "
            "unless failure occurred after the atomic transaction began."
        )
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
