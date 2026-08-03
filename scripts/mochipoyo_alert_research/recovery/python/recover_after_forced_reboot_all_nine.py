from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import recover_after_forced_reboot as base

TARGETS: tuple[dict[str, Any], ...] = (
    {
        "name": "collector",
        "process_marker": "run_collect_events_forever.py",
        "lock_rel": Path("collector_loop.lock"),
    },
    {
        "name": "M7C",
        "process_marker": "run_m7c_prospective_shadow_forever_safe.py",
        "lock_rel": Path("m7c_shadow_loop.lock"),
    },
    {
        "name": "M9V",
        "process_marker": "run_m9v_shadow_forever_safe",
        "lock_rel": Path("m9v_runtime") / "m9v_shadow_loop.lock",
        "runtime_rel": Path("m9v_runtime") / "m9v_runtime_manifest.json",
        "expected_start": "2026.07.24 11:04:00",
    },
    {
        "name": "M9Y",
        "process_marker": "run_m9y_shadow_forever_safe.py",
        "lock_rel": Path("m9y_runtime") / "m9y_shadow_loop.lock",
        "runtime_rel": Path("m9y_runtime") / "m9y_runtime_manifest.json",
        "expected_start": "2026.07.24 12:45:00",
    },
    {
        "name": "M10B",
        "process_marker": "m10b_runtime.py",
        "lock_rel": Path("m10b_runtime") / "m10b_shadow_loop.lock",
        "runtime_rel": Path("m10b_runtime") / "m10b_runtime_manifest.json",
        "expected_start": "2026.07.24 20:54:00",
    },
    {
        "name": "M10E",
        "process_marker": "m10e_runtime.py",
        "lock_rel": Path("m10e_runtime") / "m10e_shadow_loop.lock",
        "runtime_rel": Path("m10e_runtime") / "m10e_runtime_manifest.json",
        "expected_start": "2026.07.24 22:06:00",
    },
    {
        "name": "M10P",
        "process_marker": "m10p_guarded_runtime.py",
        "lock_rel": Path("m10p_runtime") / "m10p_shadow_loop.lock",
        "runtime_rel": Path("m10p_runtime") / "m10p_runtime_manifest.json",
        "expected_start": "2026.07.24 23:56:00",
    },
    {
        "name": "M10P2",
        "process_marker": "m10p2_guarded_runtime.py",
        "lock_rel": Path("m10p2_runtime") / "m10p2_shadow_loop.lock",
        "runtime_rel": Path("m10p2_runtime") / "m10p2_runtime_manifest.json",
        "expected_start": "2026.07.27 01:39:00",
    },
    {
        "name": "M10W19",
        "process_marker": "m10w19_runtime.py",
        "lock_rel": Path("m10w19_runtime") / "m10w19_shadow_loop.lock",
        "runtime_rel": Path("m10w19_runtime") / "m10w19_runtime_manifest.json",
        "expected_start": "2026.07.28 02:31:00",
    },
    {
        "name": "M10W26",
        "process_marker": "run_m10w26_private_snapshot",
        "lock_rel": Path("m10w26_runtime") / "m10w26_shadow_loop.lock",
        "runtime_rel": Path("m10w26_runtime") / "m10w26_runtime_manifest.json",
        "expected_start": "2026.07.28 15:58:00",
    },
    {
        "name": "M10W34",
        "process_marker": "run_m10w34_private_snapshot.py",
        "lock_rel": Path("m10w34_runtime") / "m10w34_shadow_loop.lock",
        "runtime_rel": Path("m10w34_runtime") / "m10w34_runtime_manifest.json",
        "expected_start": "2026.07.28 18:19:00",
    },
)


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"cannot read protected runtime JSON: {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"protected runtime JSON is not an object: {path}")
    return payload


def main() -> int:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if not local:
        print("[RECOVERY BLOCKED] LOCALAPPDATA unavailable", file=sys.stderr)
        return 2

    root = Path(local) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    archive = root / "reboot_recovery_all_nine" / utc_stamp()
    archive.mkdir(parents=True, exist_ok=False)

    try:
        running: dict[str, list[dict[str, Any]]] = {}
        for target in TARGETS:
            rows = base.running_processes(str(target["process_marker"]))
            if rows:
                running[str(target["name"])] = rows
        if running:
            (archive / "blocked_running_processes.json").write_text(
                json.dumps(running, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            raise RuntimeError(
                "one or more protected loops are still running; no lock was touched: "
                + ", ".join(sorted(running))
            )

        runtime_checks: dict[str, Any] = {}
        for target in TARGETS:
            runtime_rel = target.get("runtime_rel")
            if runtime_rel is None:
                continue
            name = str(target["name"])
            runtime_path = root / Path(runtime_rel)
            if not runtime_path.is_file():
                raise RuntimeError(f"protected runtime manifest is missing for {name}: {runtime_path}")
            runtime = read_json(runtime_path)
            actual_start = runtime.get("prospective_start_server_time")
            expected_start = target.get("expected_start")
            runtime_checks[name] = {
                "runtime": str(runtime_path),
                "prospective_start_server_time": actual_start,
                "expected_start": expected_start,
                "start_match": actual_start == expected_start,
            }
            if actual_start != expected_start:
                raise RuntimeError(
                    f"protected prospective start mismatch for {name}: "
                    f"expected={expected_start!r} actual={actual_start!r}"
                )

        planned: list[dict[str, Any]] = []
        for target in TARGETS:
            name = str(target["name"])
            lock = root / Path(target["lock_rel"])
            row: dict[str, Any] = {
                "name": name,
                "lock": str(lock),
                "lock_existed": lock.is_file(),
                "archived": False,
                "removed": False,
            }
            if lock.is_file():
                destination = archive / f"{name}_{lock.name}"
                shutil.copy2(lock, destination)
                row["archived"] = True
                row["archive_path"] = str(destination)
            planned.append(row)

        # Delete only after every existing lock has been copied successfully.
        for row in planned:
            if not row["lock_existed"]:
                continue
            lock = Path(str(row["lock"]))
            lock.unlink()
            row["removed"] = True

        receipt = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "ALL_NINE_FORWARD_LOOPS_FORCED_REBOOT_STALE_LOCK_RECOVERY",
            "status": "PASS_ALL_NINE_FORWARD_PLUS_BASE_STALE_LOCK_RECOVERY_ONLY",
            "created_at_utc": utc_text(),
            "root": str(root),
            "process_precheck_all_absent": True,
            "runtime_checks": runtime_checks,
            "actions": planned,
            "runtime_or_start_deleted": False,
            "runtime_or_start_reset": False,
            "state_or_history_modified": False,
            "database_deleted_or_reset": False,
            "journal_or_snapshot_modified": False,
            "process_started_or_killed": False,
            "prospective_starts_preserved": True,
            "next_restart_order": [
                "1) Ensure MT5 and the CSV-producing terminal/export are running and updating again.",
                "2) scripts/mochipoyo_alert_research/run_collect_events_cloudflare_forever.bat",
                "3) scripts/mochipoyo_alert_research/run_m7c_prospective_shadow_forever.bat",
                "4) scripts/mochipoyo_alert_research/m8c/bat/02_run_forward_shadow_forever.bat",
                "5) scripts/mochipoyo_alert_research/m9v/bat/03_run_shadow_forever.bat",
                "6) scripts/mochipoyo_alert_research/m9y/bat/03_run_shadow_forever.bat",
                "7) scripts/mochipoyo_alert_research/m10b/bat/03_run_shadow_forever.bat",
                "8) scripts/mochipoyo_alert_research/m10e/bat/03_run_shadow_forever.bat",
                "9) scripts/mochipoyo_alert_research/m10p/bat/03_run_shadow_forever.bat",
                "10) scripts/mochipoyo_alert_research/m10p2/bat/03_run_shadow_forever.bat",
                "11) scripts/mochipoyo_alert_research/m10w19/bat/03_run_shadow_forever.bat",
                "12) scripts/mochipoyo_alert_research/m10w26/bat/03_run_shadow_forever.bat",
                "13) scripts/mochipoyo_alert_research/m10w34/bat/03_run_shadow_forever.bat",
            ],
            "never_run_after_initialization": [
                "M7C initializer/runtime reset",
                "M8C initializer/runtime reset",
                "M9V BAT00/BAT01",
                "M9Y BAT01",
                "M10B BAT01",
                "M10E BAT01",
                "M10P BAT01",
                "M10P2 BAT01",
                "M10W19 BAT01",
                "M10W26 BAT01",
                "M10W34 BAT01",
            ],
            "post_restart_health_operator": (
                "scripts/mochipoyo_alert_research/recovery/bat/06_audit_all_nine_restart_health.bat"
            ),
            "data_gap_note": (
                "Permanent PC-off CSV gaps remain unobserved. Missing entry or exit bars are never "
                "reconstructed from later outcomes."
            ),
        }
        receipt_path = archive / "recovery_receipt.json"
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print("[REBOOT RECOVERY PASS] all protected processes were absent and stale-lock recovery completed")
        for row in planned:
            if row["removed"]:
                print(f"[RECOVERED] {row['name']}: archived and removed stale lock")
            else:
                print(f"[OK] {row['name']}: no stale lock present")
        print(f"[RECEIPT] {receipt_path}")
        print("[SAFE] No runtime, start, state/history, journal/snapshot or database was reset.")
        return 0
    except Exception as exc:
        print(f"[REBOOT RECOVERY BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No initializer was run and no runtime/start was intentionally changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
