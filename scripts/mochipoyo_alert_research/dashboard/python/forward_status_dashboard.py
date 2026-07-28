from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

PROJECT = "MOCHIPOYO_ALERT_RESEARCH"
PASS_STATUS = "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY"


def local_root() -> Path:
    value = os.environ.get("LOCALAPPDATA", "").strip()
    if not value:
        raise RuntimeError("LOCALAPPDATA unavailable")
    return Path(value) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "MISSING"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON_NOT_OBJECT"
    return payload, None


def integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def nested(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text[:-1] + "+00:00").astimezone(UTC)
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def age_text(value: Any) -> str:
    parsed = parse_utc(value)
    if parsed is None:
        return "age=?"
    seconds = max(0.0, (datetime.now(UTC) - parsed).total_seconds())
    if seconds < 120:
        return f"age={int(seconds)}s"
    if seconds < 7200:
        return f"age={int(seconds // 60)}m"
    return f"age={int(seconds // 3600)}h"


def process_alive(pid: int | None) -> bool | None:
    if pid is None or pid <= 0:
        return None
    if os.name != "nt":
        return None
    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    error = ctypes.windll.kernel32.GetLastError()
    if error == 5:
        return True
    return False


def lock_pid(path: Path) -> int | None:
    payload, _ = read_json(path)
    if payload is None:
        return None
    value = payload.get("pid")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def gate_text(count: int, gates: tuple[int, ...]) -> str:
    reached = [gate for gate in gates if count >= gate]
    upcoming = next((gate for gate in gates if count < gate), None)
    if not reached:
        return f"WAIT -> {gates[0]}"
    if upcoming is None:
        return f"FORMAL {gates[-1]} REACHED"
    return f"REACHED {reached[-1]} -> NEXT {upcoming}"


def accepted(summary: dict[str, Any], arm: str) -> int:
    return integer(nested(summary, "arm_metrics", arm, "accepted_count"))


def m9v_progress(summary: dict[str, Any]) -> tuple[str, str]:
    counts = summary.get("arm_accepted_counts", {})
    if not isinstance(counts, dict):
        counts = {}
    v0 = integer(counts.get("V0_M15_ONLY"))
    v1 = integer(counts.get("V1_M15_PLUS_H1"))
    v2 = integer(counts.get("V2_ALL_TIMEFRAMES"))
    maximum = max(v0, v1, v2)
    return f"V0={v0} V1={v1} V2={v2} max={maximum}", gate_text(maximum, (20, 60, 120))


def m9y_progress(summary: dict[str, Any]) -> tuple[str, str]:
    y0 = accepted(summary, "Y0_W1_NATIVE_EXIT")
    w1 = integer(summary.get("w1_candidate_count"))
    pending = integer(summary.get("pending_count"))
    return f"Y0={y0} W1={w1} pending={pending}", gate_text(y0, (20, 60, 120))


def m10b_progress(summary: dict[str, Any]) -> tuple[str, str]:
    m5 = accepted(summary, "B0_M5_ENTRY_NATIVE")
    h1 = accepted(summary, "B2_H1_ENTRY_NATIVE")
    h4 = accepted(summary, "B4_H4_ENTRY_NATIVE")
    progress = f"M5={m5} H1={h1} H4={h4}"
    gate = f"M5:{gate_text(m5, (20, 60, 120))}; H1:{gate_text(h1, (5, 10, 20))}; H4:{'REACHED 5' if h4 >= 5 else 'WAIT -> 5'}"
    return progress, gate


def m10e_progress(summary: dict[str, Any]) -> tuple[str, str]:
    e0 = accepted(summary, "E0_H1_BASELINE_RUNNER50")
    e1 = accepted(summary, "E1_H1_FILTERED_RUNNER50")
    excluded = integer(summary.get("compound_excluded_before_one_position"))
    return f"E0={e0} E1={e1} excluded={excluded}", gate_text(e0, (5, 10, 20))


def fixed_metrics_progress(summary: dict[str, Any]) -> tuple[str, str]:
    block = summary.get("metrics", {})
    if not isinstance(block, dict):
        block = {}
    resolved = integer(block.get("resolved_count"))
    accepted_count = integer(block.get("accepted_count"))
    open_count = integer(block.get("open_count"))
    return f"accepted={accepted_count} resolved={resolved} open={open_count}", gate_text(resolved, (5, 10, 20))


def m10w19_progress(summary: dict[str, Any]) -> tuple[str, str]:
    baseline = summary.get("W0_BLC1_BASELINE", {})
    filtered = summary.get("W1_BLC1_ATR_FILTERED", {})
    if not isinstance(baseline, dict):
        baseline = {}
    if not isinstance(filtered, dict):
        filtered = {}
    base_resolved = integer(baseline.get("resolved_count"))
    filtered_resolved = integer(filtered.get("resolved_count"))
    filtered_open = integer(filtered.get("open_count"))
    return f"base_res={base_resolved} filt_res={filtered_resolved} open={filtered_open}", gate_text(filtered_resolved, (20, 60, 120))


def named_block_progress(summary: dict[str, Any], key: str) -> tuple[str, str]:
    block = summary.get(key, {})
    if not isinstance(block, dict):
        block = {}
    candidate = integer(block.get("candidate_count"))
    accepted_count = integer(block.get("accepted_count"))
    resolved = integer(block.get("resolved_count"))
    open_count = integer(block.get("open_count"))
    return f"cand={candidate} acc={accepted_count} res={resolved} open={open_count}", gate_text(resolved, (20, 60, 120))


def m10w26_progress(summary: dict[str, Any]) -> tuple[str, str]:
    return named_block_progress(summary, "MMO1_CAUSAL_NEITHER")


def m10w34_progress(summary: dict[str, Any]) -> tuple[str, str]:
    return named_block_progress(summary, "SNDX1_CAUSAL_NEITHER")


ProgressReader = Callable[[dict[str, Any]], tuple[str, str]]

LOOPS: tuple[dict[str, Any], ...] = (
    {"name": "M9V", "progress": m9v_progress},
    {"name": "M9Y", "progress": m9y_progress},
    {"name": "M10B", "progress": m10b_progress},
    {"name": "M10E", "progress": m10e_progress},
    {"name": "M10P", "progress": fixed_metrics_progress},
    {"name": "M10P2", "progress": fixed_metrics_progress},
    {"name": "M10W19", "progress": m10w19_progress},
    {"name": "M10W26", "progress": m10w26_progress},
    {"name": "M10W34", "progress": m10w34_progress},
)


def loop_paths(root: Path, name: str) -> tuple[Path, Path, Path]:
    lower = name.lower()
    summary = root / "outputs" / name / "LATEST" / "01_summary.json"
    status = root / "logs" / lower / f"latest_{lower}_shadow_loop_status.json"
    lock = root / f"{lower}_runtime" / f"{lower}_shadow_loop.lock"
    return summary, status, lock


def health_text(status_payload: dict[str, Any] | None, lock_path: Path) -> tuple[str, str]:
    status = str((status_payload or {}).get("status", "NO_STATUS"))
    pid = integer((status_payload or {}).get("pid"), default=0) or lock_pid(lock_path)
    alive = process_alive(pid if pid > 0 else None)
    lock_exists = lock_path.is_file()
    if "BLOCKED" in status or "FAIL" in status:
        health = "BLOCKED"
    elif status == "WAITING_TRANSIENT_SOURCE":
        health = "WAITING"
    elif status == "RUNNING" and lock_exists and alive is not False:
        health = "RUNNING"
    elif status == "RUNNING":
        health = "CHECK"
    elif lock_exists and alive is True:
        health = "RUNNING?"
    else:
        health = status[:12]
    details = f"lock={'Y' if lock_exists else 'N'} pid={pid if pid > 0 else '-'}"
    return health, details


def fit(text: str, width: int) -> str:
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def render(root: Path) -> None:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    width = 170
    print("=" * width)
    print(f"MOCHIPOYO M9V+ FORWARD MONITOR DASHBOARD  [READ ONLY]   {now}")
    print("Reads summaries/status/locks only. It does not initialize, stop, restart, reset, edit, delete, tune, notify, or place orders.")
    print("=" * width)
    header = (
        fit("LOOP", 8)
        + fit("HEALTH", 12)
        + fit("LOCK/PID", 22)
        + fit("START (MT5 SERVER)", 22)
        + fit("PROGRESS", 48)
        + fit("REVIEW GATE", 42)
        + fit("UPDATED", 16)
    )
    print(header)
    print("-" * width)

    problems: list[str] = []
    reached: list[str] = []
    for item in LOOPS:
        name = str(item["name"])
        reader: ProgressReader = item["progress"]
        summary_path, status_path, lock_path = loop_paths(root, name)
        summary, summary_error = read_json(summary_path)
        status_payload, status_error = read_json(status_path)
        health, lock_details = health_text(status_payload, lock_path)

        if summary is None:
            progress = f"SUMMARY {summary_error or 'UNAVAILABLE'}"
            gate = "UNKNOWN"
            start = "-"
            updated = age_text((status_payload or {}).get("updated_at_utc"))
            problems.append(f"{name}: summary {summary_error}")
        else:
            try:
                progress, gate = reader(summary)
            except Exception as exc:
                progress = f"PARSE {type(exc).__name__}"
                gate = "UNKNOWN"
                problems.append(f"{name}: progress parse {type(exc).__name__}: {exc}")
            start = str(summary.get("prospective_start_server_time", "-"))
            updated_source = (status_payload or {}).get("updated_at_utc") or summary.get("built_at_utc")
            updated = age_text(updated_source)
            if str(summary.get("status", "")) != PASS_STATUS:
                problems.append(f"{name}: summary status={summary.get('status')}")

        if health in {"BLOCKED", "CHECK", "NO_STATUS"}:
            problems.append(f"{name}: health={health}; status_error={status_error}")
        if "REACHED" in gate:
            reached.append(f"{name}: {gate}")

        row = (
            fit(name, 8)
            + fit(health, 12)
            + fit(lock_details, 22)
            + fit(start, 22)
            + fit(progress, 48)
            + fit(gate, 42)
            + fit(updated, 16)
        )
        print(row)

    print("-" * width)
    if reached:
        print("REVIEW THRESHOLD REACHED (send this dashboard screenshot before running any checkpoint BAT):")
        for item in reached:
            print(f"  - {item}")
    else:
        print("No displayed review threshold has been reached yet.")
    if problems:
        print("CHECK ITEMS:")
        for item in problems:
            print(f"  - {item}")
    else:
        print("All nine summaries report PASS and no terminal dashboard health problem was detected.")
    print("Ctrl+C closes only this dashboard. All monitor windows remain unchanged.")
    print("=" * width)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only dashboard for M9V and later forward monitors")
    parser.add_argument("--once", action="store_true", help="render once and exit")
    parser.add_argument("--interval-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.interval_seconds < 10 or args.interval_seconds > 3600:
        print("[DASHBOARD BLOCKED] interval must be 10..3600 seconds", file=sys.stderr)
        return 2
    try:
        root = local_root()
        if args.once:
            render(root)
            return 0
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            render(root)
            time.sleep(args.interval_seconds)
    except KeyboardInterrupt:
        print("\n[DASHBOARD CLOSED] Read-only dashboard stopped. Monitor loops were not changed.")
        return 0
    except Exception as exc:
        print(f"[DASHBOARD BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No monitor, runtime, start, lock, journal, output, Discord, or MT5 order was changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
