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
MR = THIS.parents[2]
for directory in (MR / "m10p" / "python", MR / "m10p2" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import m10p_guarded_runtime as pg
import m10p2_guarded_runtime as p2g

STAGE = "M10W10_M10P_M10P2_RUNTIME_FRESHNESS_DIAGNOSTIC_AUDIT_ONLY"
STALE_TOLERANCE_MINUTES = 5.0


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"_non_object": True}
    except Exception as exc:
        return {"_read_error": f"{type(exc).__name__}: {exc}"}


def file_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    stat = path.stat()
    return {
        "exists": True,
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def pid_exists_windows(pid: int | None) -> dict[str, Any]:
    if pid is None:
        return {"checked": False, "exists": None, "reason": "no_pid_in_lock"}
    if os.name != "nt":
        return {"checked": False, "exists": None, "reason": "non_windows_runtime"}
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        text = (proc.stdout or "").strip()
        exists = bool(text) and not text.upper().startswith("INFO:") and f'"{pid}"' in text
        return {
            "checked": True,
            "exists": exists,
            "returncode": proc.returncode,
            "tasklist_output": text[:1000],
        }
    except Exception as exc:
        return {"checked": False, "exists": None, "reason": f"{type(exc).__name__}: {exc}"}


def iso_error(fn) -> dict[str, Any]:
    try:
        value = fn()
        return {"pass": True, "value": value}
    except Exception as exc:
        return {"pass": False, "error": f"{type(exc).__name__}: {exc}"}


def classify(lock_exists: bool, pid_status: dict[str, Any], stale_minutes: float | None, guard_pass: bool) -> str:
    stale = stale_minutes is not None and stale_minutes > STALE_TOLERANCE_MINUTES
    if not guard_pass:
        return "CURRENT_GUARD_BLOCKED_DIAGNOSE_ERROR_BEFORE_RESTART"
    if stale and not lock_exists:
        return "LIKELY_LOOP_EXITED_OR_NOT_RUNNING_LOCK_ABSENT"
    if stale and lock_exists and pid_status.get("checked") is True and pid_status.get("exists") is False:
        return "STALE_LOCK_WITH_NO_LIVE_PID"
    if stale and lock_exists and pid_status.get("exists") is True:
        return "LIVE_PID_PRESENT_BUT_LATEST_OUTPUT_STALE_REVIEW_CONSOLE_OR_HANG"
    if stale:
        return "OUTPUT_STALE_RUNTIME_STATUS_UNCONFIRMED"
    if lock_exists and pid_status.get("exists") is True:
        return "OUTPUT_CURRENT_AND_LOOP_PID_PRESENT"
    return "OUTPUT_CURRENT_LOOP_STATUS_NOT_PROVEN"


def raw_snapshots(root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for tf, filename in pg.EXPECTED_LIVE_FILE_MAP.items():
        out[tf] = pg.impl.v.tail_snapshot(root / filename)
    return out


def monitor_detail(name: str, local_root: Path, root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    if name == "M10P":
        impl = pg.impl
        runtime_dir, runtime_path, state_path, lock_path = impl.runtime_paths(local_root)
        latest_dir = local_root / "outputs" / "M10P" / "LATEST"
        summary_path = latest_dir / "01_summary.json"
        runtime = read_json(runtime_path)
        state = read_json(state_path)
        summary = read_json(summary_path)
        lock = read_json(lock_path)
        integrity = iso_error(lambda: impl.verify_runtime(
            root,
            impl.js(impl.CONTRACT),
            impl.js(runtime_path),
            local_root / "m10e_runtime" / "m10e_runtime_manifest.json",
        ))
        feed_guard = iso_error(lambda: pg.observed_feed_health(root))
    else:
        impl = p2g.impl
        runtime_dir, runtime_path, state_path, lock_path = impl.runtime_paths(local_root)
        latest_dir = local_root / "outputs" / "M10P2" / "LATEST"
        summary_path = latest_dir / "01_summary.json"
        runtime = read_json(runtime_path)
        state = read_json(state_path)
        summary = read_json(summary_path)
        lock = read_json(lock_path)
        integrity = iso_error(lambda: impl.verify_runtime(
            root,
            float(impl.env()[2]),
            impl.js(impl.CONTRACT),
            impl.js(runtime_path),
            local_root / "m10p_runtime" / "m10p_runtime_manifest.json",
        ))
        feed_guard = iso_error(lambda: p2g.observed_feed_health(root))

    pid = None
    if isinstance(lock, dict) and isinstance(lock.get("pid"), int):
        pid = int(lock["pid"])
    pid_status = pid_exists_windows(pid)

    raw_m1_text = str(raw.get("M1", {}).get("last_server_open", ""))
    summary_m1_text = ""
    if isinstance(summary, dict):
        summary_m1_text = str(summary.get("latest_server_open", {}).get("M1", ""))
    stale_minutes: float | None = None
    if raw_m1_text and summary_m1_text:
        try:
            stale_minutes = (impl.pt(raw_m1_text) - impl.pt(summary_m1_text)).total_seconds() / 60.0
        except Exception:
            stale_minutes = None

    classification = classify(lock_path.exists(), pid_status, stale_minutes, bool(integrity.get("pass") and feed_guard.get("pass")))
    return {
        "name": name,
        "runtime_dir": str(runtime_dir),
        "runtime_manifest": runtime,
        "runtime_state": state,
        "latest_summary": summary,
        "runtime_manifest_file": file_meta(runtime_path),
        "runtime_state_file": file_meta(state_path),
        "latest_summary_file": file_meta(summary_path),
        "latest_package_file": file_meta(latest_dir / "99_UPLOAD_PACKAGE.zip"),
        "lock_file": file_meta(lock_path),
        "lock_payload": lock,
        "pid_status": pid_status,
        "runtime_integrity_check": integrity,
        "current_observed_feed_guard": feed_guard,
        "raw_latest_M1_mt5_server": raw_m1_text,
        "summary_latest_M1_mt5_server": summary_m1_text,
        "output_stale_minutes_vs_raw_M1": stale_minutes,
        "classification": classification,
    }


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> int:
    local_root, root, point = pg.impl.env()
    local_root2, root2, point2 = p2g.impl.env()
    if str(local_root) != str(local_root2) or str(root) != str(root2):
        raise RuntimeError("M10P and M10P2 resolve different local/data roots")
    if abs(float(point) - float(point2)) > 1e-12:
        raise RuntimeError("M10P and M10P2 point mismatch")

    raw = raw_snapshots(root)
    p_detail = monitor_detail("M10P", local_root, root, raw)
    p2_detail = monitor_detail("M10P2", local_root, root, raw)

    status = "PASS_READ_ONLY_DIAGNOSTIC"
    attention = any("STALE" in str(item["classification"]) or "BLOCKED" in str(item["classification"]) or "EXITED" in str(item["classification"])
                    for item in (p_detail, p2_detail))
    if attention:
        status = "PASS_READ_ONLY_DIAGNOSTIC_ATTENTION_REQUIRED"

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": status,
        "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "XAUUSD_GOLD_ONLY",
        "point": point,
        "raw_latest_server_open": {tf: item.get("last_server_open") for tf, item in raw.items()},
        "M10P": {
            "classification": p_detail["classification"],
            "raw_latest_M1": p_detail["raw_latest_M1_mt5_server"],
            "summary_latest_M1": p_detail["summary_latest_M1_mt5_server"],
            "stale_minutes": p_detail["output_stale_minutes_vs_raw_M1"],
            "lock_exists": p_detail["lock_file"]["exists"],
            "pid_status": p_detail["pid_status"],
            "runtime_integrity_pass": p_detail["runtime_integrity_check"]["pass"],
            "current_feed_guard_pass": p_detail["current_observed_feed_guard"]["pass"],
            "cycle_count": (p_detail.get("runtime_state") or {}).get("cycle_count"),
            "last_cycle_at_utc": (p_detail.get("runtime_state") or {}).get("last_cycle_at_utc"),
            "immutable_start": (p_detail.get("runtime_manifest") or {}).get("prospective_start_server_time"),
        },
        "M10P2": {
            "classification": p2_detail["classification"],
            "raw_latest_M1": p2_detail["raw_latest_M1_mt5_server"],
            "summary_latest_M1": p2_detail["summary_latest_M1_mt5_server"],
            "stale_minutes": p2_detail["output_stale_minutes_vs_raw_M1"],
            "lock_exists": p2_detail["lock_file"]["exists"],
            "pid_status": p2_detail["pid_status"],
            "runtime_integrity_pass": p2_detail["runtime_integrity_check"]["pass"],
            "current_feed_guard_pass": p2_detail["current_observed_feed_guard"]["pass"],
            "cycle_count": (p2_detail.get("runtime_state") or {}).get("cycle_count"),
            "last_cycle_at_utc": (p2_detail.get("runtime_state") or {}).get("last_cycle_at_utc"),
            "immutable_start": (p2_detail.get("runtime_manifest") or {}).get("prospective_start_server_time"),
        },
        "guardrails": {
            "read_only_sources": True,
            "runtime_modified": False,
            "lock_modified": False,
            "monitor_restarted": False,
            "historical_backfill": False,
            "threshold_refit": False,
            "start_modified": False,
            "M10V_executed": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        },
        "next": "Upload this diagnostic package. Do not restart BAT03 or delete locks until the diagnostic is reviewed.",
    }

    output_root = local_root / "outputs" / "M10W10"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = output_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10W10 read-only diagnostic for stale M10P/M10P2 outputs.\n"
        "Do not reset/reinitialize either monitor. Do not delete lock files. Do not restart BAT03 until reviewed.\n",
        encoding="utf-8",
    )
    (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "02_M10P_detail.json").write_text(json.dumps(p_detail, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "03_M10P2_detail.json").write_text(json.dumps(p2_detail, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "04_raw_tail_snapshots.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "05_audit.log").write_text(
        "\n".join([
            f"status={status}",
            f"M10P_classification={p_detail['classification']}",
            f"M10P_stale_minutes={p_detail['output_stale_minutes_vs_raw_M1']}",
            f"M10P_lock_exists={p_detail['lock_file']['exists']}",
            f"M10P_integrity_pass={p_detail['runtime_integrity_check']['pass']}",
            f"M10P_feed_guard_pass={p_detail['current_observed_feed_guard']['pass']}",
            f"M10P2_classification={p2_detail['classification']}",
            f"M10P2_stale_minutes={p2_detail['output_stale_minutes_vs_raw_M1']}",
            f"M10P2_lock_exists={p2_detail['lock_file']['exists']}",
            f"M10P2_integrity_pass={p2_detail['runtime_integrity_check']['pass']}",
            f"M10P2_feed_guard_pass={p2_detail['current_observed_feed_guard']['pass']}",
            "runtime_modified=false",
            "lock_modified=false",
            "monitor_restarted=false",
            "historical_backfill=false",
            "threshold_refit=false",
            "",
        ]),
        encoding="utf-8",
    )

    source_copy = archive / "06_source_state_copies"
    for name, runtime_dir, latest_dir in (
        ("M10P", local_root / "m10p_runtime", local_root / "outputs" / "M10P" / "LATEST"),
        ("M10P2", local_root / "m10p2_runtime", local_root / "outputs" / "M10P2" / "LATEST"),
    ):
        for src in runtime_dir.glob("*.json"):
            copy_if_exists(src, source_copy / name / "runtime" / src.name)
        copy_if_exists(latest_dir / "01_summary.json", source_copy / name / "latest" / "01_summary.json")
        for lock_name in ("m10p_shadow_loop.lock", "m10p2_shadow_loop.lock"):
            copy_if_exists(runtime_dir / lock_name, source_copy / name / "runtime" / lock_name)

    latest = output_root / "LATEST"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    package = latest / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(latest.rglob("*")):
            if path.is_file() and path != package:
                zf.write(path, path.relative_to(latest))

    print(f"[M10W10 {status}]")
    print(f"[M10P] {p_detail['classification']} stale_minutes={p_detail['output_stale_minutes_vs_raw_M1']} lock={p_detail['lock_file']['exists']}")
    print(f"[M10P2] {p2_detail['classification']} stale_minutes={p2_detail['output_stale_minutes_vs_raw_M1']} lock={p2_detail['lock_file']['exists']}")
    print(f"[PACKAGE] {package}")
    print("[SAFE] No runtime, lock, start, threshold, ledger, or monitor was modified/restarted.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[M10W10 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No monitor should be reset/reinitialized to force a pass.", file=sys.stderr)
        raise SystemExit(2)
