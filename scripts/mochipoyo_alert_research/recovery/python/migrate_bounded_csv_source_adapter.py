from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
COMMON = THIS.parents[2] / "common" / "python"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

import bounded_csv_source_adapter as adapter

PROCESS_MARKERS = {
    "M9V": "run_m9v_shadow_forever_safe",
    "M9Y": "run_m9y_shadow_forever_safe.py",
    "M10B": "m10b_runtime.py",
    "M10E": "m10e_runtime.py",
    "M10P": "m10p_guarded_runtime.py",
    "M10P2": "m10p2_guarded_runtime.py",
    "M10W19": "m10w19_runtime.py",
}
LOCKS = {
    "M9V": Path("m9v_runtime") / "m9v_shadow_loop.lock",
    "M9Y": Path("m9y_runtime") / "m9y_shadow_loop.lock",
    "M10B": Path("m10b_runtime") / "m10b_shadow_loop.lock",
    "M10E": Path("m10e_runtime") / "m10e_shadow_loop.lock",
    "M10P": Path("m10p_runtime") / "m10p_shadow_loop.lock",
    "M10P2": Path("m10p2_runtime") / "m10p2_shadow_loop.lock",
    "M10W19": Path("m10w19_runtime") / "m10w19_shadow_loop.lock",
}


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def running_processes(marker: str) -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    escaped = marker.replace("'", "''")
    command = (
        "$self=$PID; $rows=Get-CimInstance Win32_Process | Where-Object { "
        "$_.ProcessId -ne $self -and $_.CommandLine -and $_.CommandLine -like '*"
        + escaped
        + "*' }; $rows | Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"process inspection failed for {marker}: {completed.stderr.strip()}")
    text = completed.stdout.strip()
    if not text:
        return []
    payload = json.loads(text)
    return [payload] if isinstance(payload, dict) else list(payload)


def main() -> int:
    try:
        local_value = os.environ.get("LOCALAPPDATA", "").strip()
        if not local_value:
            raise RuntimeError("LOCALAPPDATA unavailable")
        local_root = Path(local_value) / "xauusd_signal_lab" / "mochipoyo_alert_research"
        source_root, point = adapter.source_environment(local_root)

        running: dict[str, Any] = {}
        for loop, marker in PROCESS_MARKERS.items():
            rows = running_processes(marker)
            if rows:
                running[loop] = rows
        if running:
            raise RuntimeError(f"protected loop processes are still running: {sorted(running)}")
        existing_locks = {loop: str(local_root / relative) for loop, relative in LOCKS.items() if (local_root / relative).is_file()}
        if existing_locks:
            raise RuntimeError(f"protected loop locks are present; do not delete manually: {existing_locks}")

        before_hashes = {
            loop: adapter.sha256_file(local_root / relative)
            for loop, (relative, _) in adapter.RUNTIME_SPECS.items()
        }
        existing_manifest = adapter.manifest_path(local_root).is_file()
        existing_receipt = adapter.receipt_path(local_root).is_file()
        if existing_manifest != existing_receipt:
            raise RuntimeError(
                "partial adapter migration evidence exists; do not delete it manually. "
                "Send the screen output to ChatGPT."
            )
        migration_reused = existing_manifest and existing_receipt
        if migration_reused:
            receipt = adapter.load_json(adapter.receipt_path(local_root))
            if receipt.get("status") != "PASS_MIGRATION_READY_FOR_REVIEW":
                raise RuntimeError("existing bounded CSV migration receipt is not PASS")
            for loop in adapter.RUNTIME_SPECS:
                adapter.validate_loop(local_root, loop, source_root, point)
            adapter.ensure_updated(local_root, source_root, point, retry_window_seconds=90.0)
        else:
            receipt = adapter.migrate(local_root, source_root, point)

        after_hashes = {
            loop: adapter.sha256_file(local_root / relative)
            for loop, (relative, _) in adapter.RUNTIME_SPECS.items()
        }
        if before_hashes != after_hashes:
            raise RuntimeError("runtime manifest hash changed during adapter migration/package rebuild")

        output_root = local_root / "outputs" / "BOUNDED_CSV_SOURCE_ADAPTER_MIGRATION"
        archive = output_root / "archive" / utc_stamp()
        archive.mkdir(parents=True, exist_ok=False)
        manifest = adapter.load_json(adapter.manifest_path(local_root))
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "FRESH_LOOP_BOUNDED_CSV_PRESERVED_START_MIGRATION_AUDIT_ONLY",
            "status": "PASS_READY_FOR_CHATGPT_REVIEW",
            "built_at_utc": utc_text(),
            "source_root": str(source_root),
            "xauusd_point": point,
            "adapter_version": adapter.ADAPTER_VERSION,
            "immutable_starts": adapter.EXPECTED_STARTS,
            "runtime_hashes_before": before_hashes,
            "runtime_hashes_after": after_hashes,
            "runtime_hashes_unchanged": before_hashes == after_hashes,
            "loop_coverage": receipt.get("loop_coverage"),
            "journal_fingerprints": manifest.get("journals"),
            "migration_reused_for_package_rebuild": migration_reused,
            "processes_started_or_stopped": False,
            "locks_removed": False,
            "runtime_or_start_modified": False,
            "historical_backfill_before_starts": False,
            "candidate_eligibility_before_start": False,
            "restart_authorized": False,
        }
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "One-time audit-only migration for bounded MT5 CSV sources.\n"
            "It seeded or revalidated verified append-only journals from the current bounded source, preserved all seven runtime manifests and starts, and did not restart any loop.\n"
            "Upload this ZIP for review before running any BAT03.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "02_adapter_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "03_migration_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "04_runtime_hashes.json").write_text(json.dumps({"before": before_hashes, "after": after_hashes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "05_audit.log").write_text("\n".join([
            "status=PASS_READY_FOR_CHATGPT_REVIEW",
            f"adapter_version={adapter.ADAPTER_VERSION}",
            f"source_root={source_root}",
            "all_loop_processes_absent=true",
            "all_loop_locks_absent=true",
            f"migration_reused_for_package_rebuild={str(migration_reused).lower()}",
            "runtime_hashes_unchanged=true",
            "prospective_starts_unchanged=true",
            "historical_backfill_before_starts=false",
            "candidate_eligibility_before_start=false",
            "restart_authorized=false",
            "",
        ]), encoding="utf-8")
        names = [path.name for path in archive.iterdir() if path.is_file()]
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(names):
                zf.write(archive / name, name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        action = "revalidated and package rebuilt" if migration_reused else "seeded"
        print(f"[MIGRATION PASS] Bounded CSV adapter journals are {action}; all starts/runtime hashes are preserved.")
        print("[OUTPUT]", latest)
        print("[NEXT] Upload 99_UPLOAD_PACKAGE.zip. Do not run any BAT03 until reviewed.")
        return 0
    except Exception as exc:
        print(f"[MIGRATION BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No initializer was run. No runtime manifest or prospective start was intentionally changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
