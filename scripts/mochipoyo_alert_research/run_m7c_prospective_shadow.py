from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import m7c_prospective_shadow as core


def utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="M7C prospective Mochipoyo proxy shadow reproduction (audit-only)."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--mt5-files-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--built-at-utc", default=utc_now_text())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = core.load_manifest(args.manifest)
        if not args.database.is_file():
            raise core.M7CContractError("Mochipoyo SQLite database was not found")
        if not args.mt5_files_root.is_dir():
            raise core.M7CContractError("configured MT5 Files root was not found")
        connection = sqlite3.connect(args.database)
        connection.row_factory = sqlite3.Row
        try:
            report = core.audit_m7c(
                connection,
                mt5_files_root=args.mt5_files_root,
                manifest=manifest,
                built_at_utc=args.built_at_utc,
            )
        finally:
            connection.close()
        paths = core.write_outputs(args.output_dir, report)
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "stage": report["stage"],
                    "prospective_start_utc": report["prospective_start_utc"],
                    "comparison_summary": report["comparison_summary"],
                    "readiness": report["readiness"],
                    "outputs": paths,
                },
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        )
        return 0
    except core.M7CUpstreamStaleError as exc:
        print(f"[UPSTREAM_STALE] {exc}")
        return 3
    except (core.M7CContractError, core.TriggerSignatureContractError) as exc:
        print(f"[M7C_FAIL_CLOSED] {exc}")
        return 2
    except Exception as exc:
        print(f"[M7C_ERROR] {type(exc).__name__}: {exc}")
        print(
            "[SAFE] Raw alerts, MT5 CSVs, Discord settings, MT5 order settings, "
            "entry gate, live-ready, and final signal were not modified."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
