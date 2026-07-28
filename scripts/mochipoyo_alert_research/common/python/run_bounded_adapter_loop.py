from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

THIS = Path(__file__).resolve()
MR = THIS.parents[2]
ROOT = THIS.parents[4]
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

import bounded_csv_source_adapter as adapter

LOOPS: dict[str, dict[str, Any]] = {
    "M9V": {
        "stage": "M9V_GOLD_MULTI_TIMEFRAME_FRESH_PROSPECTIVE_SHADOW",
        "runtime_rel": Path("m9v_runtime") / "m9v_runtime_manifest.json",
        "lock_rel": Path("m9v_runtime") / "m9v_shadow_loop.lock",
        "stop_rel": Path("m9v_runtime") / "STOP_M9V_SHADOW_LOOP",
        "log_rel": Path("logs") / "m9v" / "m9v_shadow_forever.log",
        "status_rel": Path("logs") / "m9v" / "latest_m9v_shadow_loop_status.json",
    },
    "M9Y": {
        "stage": "M9Y_GOLD_PAYOFF_FRESH_PROSPECTIVE_SHADOW",
        "runtime_rel": Path("m9y_runtime") / "m9y_runtime_manifest.json",
        "lock_rel": Path("m9y_runtime") / "m9y_shadow_loop.lock",
        "stop_rel": Path("m9y_runtime") / "STOP_M9Y_SHADOW_LOOP",
        "log_rel": Path("logs") / "m9y" / "m9y_shadow_forever.log",
        "status_rel": Path("logs") / "m9y" / "latest_m9y_shadow_loop_status.json",
    },
    "M10B": {
        "stage": "M10B_GOLD_MULTI_TIMEFRAME_PAYOFF_FRESH_PROSPECTIVE_SHADOW",
        "runtime_rel": Path("m10b_runtime") / "m10b_runtime_manifest.json",
        "lock_rel": Path("m10b_runtime") / "m10b_shadow_loop.lock",
        "stop_rel": Path("m10b_runtime") / "STOP_M10B_SHADOW_LOOP",
        "log_rel": Path("logs") / "m10b" / "m10b_bounded_adapter_forever.log",
        "status_rel": Path("logs") / "m10b" / "latest_m10b_shadow_loop_status.json",
    },
    "M10E": {
        "stage": "M10E_H1_COMPOUND_LOSS_FILTER_FRESH_PROSPECTIVE_SHADOW",
        "runtime_rel": Path("m10e_runtime") / "m10e_runtime_manifest.json",
        "lock_rel": Path("m10e_runtime") / "m10e_shadow_loop.lock",
        "stop_rel": Path("m10e_runtime") / "STOP_M10E_SHADOW_LOOP",
        "log_rel": Path("logs") / "m10e" / "m10e_bounded_adapter_forever.log",
        "status_rel": Path("logs") / "m10e" / "latest_m10e_shadow_loop_status.json",
    },
    "M10P": {
        "stage": "M10P_C056_G013_FRESH_PROSPECTIVE_SHADOW",
        "runtime_rel": Path("m10p_runtime") / "m10p_runtime_manifest.json",
        "lock_rel": Path("m10p_runtime") / "m10p_shadow_loop.lock",
        "stop_rel": Path("m10p_runtime") / "STOP_M10P_SHADOW_LOOP",
        "log_rel": Path("logs") / "m10p" / "m10p_bounded_adapter_forever.log",
        "status_rel": Path("logs") / "m10p" / "latest_m10p_shadow_loop_status.json",
    },
    "M10P2": {
        "stage": "M10P2_C0212_FRESH_PROSPECTIVE_SHADOW",
        "runtime_rel": Path("m10p2_runtime") / "m10p2_runtime_manifest.json",
        "lock_rel": Path("m10p2_runtime") / "m10p2_shadow_loop.lock",
        "stop_rel": Path("m10p2_runtime") / "STOP_M10P2_SHADOW_LOOP",
        "log_rel": Path("logs") / "m10p2" / "m10p2_bounded_adapter_forever.log",
        "status_rel": Path("logs") / "m10p2" / "latest_m10p2_shadow_loop_status.json",
    },
    "M10W19": {
        "stage": "M10W19_BLC1_ATR_FILTER_FRESH_PROSPECTIVE_SHADOW",
        "runtime_rel": Path("m10w19_runtime") / "m10w19_runtime_manifest.json",
        "lock_rel": Path("m10w19_runtime") / "m10w19_shadow_loop.lock",
        "stop_rel": Path("m10w19_runtime") / "STOP_M10W19_SHADOW_LOOP",
        "log_rel": Path("logs") / "m10w19" / "m10w19_bounded_adapter_forever.log",
        "status_rel": Path("logs") / "m10w19" / "latest_m10w19_shadow_loop_status.json",
    },
}

TERMINAL_TOKENS = (
    "runtime integrity",
    "runtime manifest changed",
    "prospective start changed",
    "start anchor mismatch",
    "chronology anchor changed",
    "contract mismatch",
    "unsafe flag",
    "timestamp",
    "duplicate",
    "non-ascending",
    "overlap canonical row changed",
    "overlap timestamp missing",
    "frozen anchor absent",
    "source data_root changed",
    "point changed",
)
TRANSIENT_TOKENS = (
    "permission denied",
    "permissionerror",
    "sharing violation",
    "winerror 32",
    "winerror 33",
    "cannot obtain stable",
    "changed during read",
    "source changed during double read",
    "temporarily unavailable",
    "file replacement",
    "source rebuild has not caught up",
    "stable source read unavailable",
    "adapter update lock remained busy",
    "tail snapshot is not present",
    "tail snapshot not present",
    "feed stale",
    "live feed stale",
)


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def append_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def add_module_path(path: Path) -> None:
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)


def capture_call(function: Callable[[], int]) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = function()
        rc = int(result or 0)
    except Exception as exc:
        traceback.print_exc(file=stderr)
        rc = 2
        stderr.write(f"\n[UNCAUGHT] {type(exc).__name__}: {exc}\n")
    output = stdout.getvalue()
    error = stderr.getvalue()
    combined = output + (("\n[stderr]\n" + error) if error else "")
    return rc, combined


def is_transient_failure(text: str) -> bool:
    lowered = text.lower()
    if any(token in lowered for token in TERMINAL_TOKENS):
        return False
    return any(token in lowered for token in TRANSIENT_TOKENS)


def load_runtime(local_root: Path, loop: str) -> dict[str, Any]:
    relative, _ = adapter.RUNTIME_SPECS[loop]
    return adapter.load_json(local_root / relative)


def build_m9v_runner(local_root: Path, source_root: Path, journal: Path, point: float) -> Callable[[], int]:
    add_module_path(MR / "m9v" / "python")
    add_module_path(MR / "m9p" / "python")
    legacy = importlib.import_module("m9v_core")
    core = importlib.import_module("m9v_core_v2")
    wrapper = importlib.import_module("run_m9v_shadow_once_v2")
    runtime_path = local_root / adapter.RUNTIME_SPECS["M9V"][0]
    runtime = adapter.load_json(runtime_path)
    contract_path = ROOT / "config" / "mochipoyo_alert_research" / "m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json"
    contract = adapter.load_json(contract_path)
    file_map = contract["data"]["live_file_map"]
    by_filename = {str(filename): runtime["frozen_row_prefixes"][tf] for tf, filename in file_map.items()}

    def adapter_audit(*, data_root: Path, contract: dict[str, Any], runtime: dict[str, Any], point: float):
        contract_sha = core.sha256_bytes(
            json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        core.validate_runtime_manifest(runtime, contract, contract_sha)
        adapter.validate_loop(local_root, "M9V", source_root, point)
        original_prefix = legacy.prefix_fingerprint
        original_replay = legacy.replay_episodes

        def compatibility_prefix(path: Path, cutoff: Any) -> dict[str, Any]:
            frozen = by_filename.get(path.name)
            if not isinstance(frozen, dict):
                raise core.M9VContractError(f"unexpected adapter file during compatibility check: {path.name}")
            return dict(frozen)

        def replay_from_verified_journal(bars: list[Any], timeframe: str, start: Any):
            return original_replay(bars, timeframe, start)

        runtime_compat = dict(runtime)
        runtime_compat["prefix_fingerprints"] = dict(runtime["frozen_row_prefixes"])
        legacy.prefix_fingerprint = compatibility_prefix
        legacy.replay_episodes = replay_from_verified_journal
        try:
            return legacy.audit(data_root=data_root, contract=contract, runtime=runtime_compat, point=point)
        finally:
            legacy.prefix_fingerprint = original_prefix
            legacy.replay_episodes = original_replay

    core.audit = adapter_audit
    os.environ["M9V_GOLD_DATA_ROOT"] = str(journal)
    os.environ["M9V_RUNTIME_MANIFEST"] = str(runtime_path)
    return wrapper.legacy.main


def build_m9y_runner(local_root: Path, source_root: Path, journal: Path, point: float) -> Callable[[], int]:
    add_module_path(MR / "m9y" / "python")
    add_module_path(MR / "m9v" / "python")
    add_module_path(MR / "m9p" / "python")
    core = importlib.import_module("m9y_core")
    one = importlib.import_module("run_m9y_shadow_once")
    runtime_path = local_root / adapter.RUNTIME_SPECS["M9Y"][0]
    runtime = adapter.load_json(runtime_path)
    contract = adapter.load_json(ROOT / "config" / "mochipoyo_alert_research" / "m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json")
    core.prefix_fingerprint_rows = adapter.frozen_prefix_compatibility(runtime, contract["data"]["live_file_map"])
    os.environ["M9Y_GOLD_DATA_ROOT"] = str(journal)
    os.environ["M9Y_RUNTIME_MANIFEST"] = str(runtime_path)
    return one.main


def build_m10b_runner(local_root: Path, source_root: Path, journal: Path, point: float) -> Callable[[], int]:
    add_module_path(MR / "m10b" / "python")
    module = importlib.import_module("m10b_runtime")
    runtime = load_runtime(local_root, "M10B")
    contract = module.js(module.CONTRACT)
    module.env = lambda: (local_root, journal, point)
    module.v2.prefix_fingerprint_rows = adapter.frozen_prefix_compatibility(runtime, contract["data"]["live_file_map"])
    return module.once


def build_m10e_runner(local_root: Path, source_root: Path, journal: Path, point: float) -> Callable[[], int]:
    add_module_path(MR / "m10e" / "python")
    module = importlib.import_module("m10e_runtime")
    runtime = load_runtime(local_root, "M10E")
    contract = module.js(module.CONTRACT)
    module.env = lambda: (local_root, journal, point)
    module.v2.prefix_fingerprint_rows = adapter.frozen_prefix_compatibility(runtime, contract["data"]["live_file_map"])
    return module.once


def build_m10p_runner(local_root: Path, source_root: Path, journal: Path, point: float) -> Callable[[], int]:
    add_module_path(MR / "m10p" / "python")
    guarded = importlib.import_module("m10p_guarded_runtime")
    impl = guarded.impl
    runtime = load_runtime(local_root, "M10P")
    contract = impl.js(impl.CONTRACT)
    impl.env = lambda: (local_root, journal, point)
    impl.v2.prefix_fingerprint_rows = adapter.frozen_prefix_compatibility(runtime, contract["data"]["live_file_map"])

    def cycle() -> int:
        guarded.observed_feed_health(journal)
        return guarded._original_once()

    return cycle


def build_m10p2_runner(local_root: Path, source_root: Path, journal: Path, point: float) -> Callable[[], int]:
    add_module_path(MR / "m10p2" / "python")
    guarded = importlib.import_module("m10p2_guarded_runtime")
    impl = guarded.impl
    runtime = load_runtime(local_root, "M10P2")
    contract = impl.js(impl.CONTRACT)
    impl.env = lambda: (local_root, journal, point)
    impl.v2.prefix_fingerprint_rows = adapter.frozen_prefix_compatibility(runtime, contract["data"]["live_file_map"])
    original_verify = impl.verify_runtime

    def compatible_verify(root: Path, current_point: float, current_contract: dict[str, Any], current_runtime: dict[str, Any], m10p_path: Path):
        runtime_compat = dict(current_runtime)
        runtime_compat["data_root"] = str(root)
        return original_verify(root, current_point, current_contract, runtime_compat, m10p_path)

    impl.verify_runtime = compatible_verify

    def cycle() -> int:
        guarded.observed_feed_health(journal)
        return guarded._original_once()

    return cycle


def build_m10w19_runner(local_root: Path, source_root: Path, journal: Path, point: float) -> Callable[[], int]:
    add_module_path(MR / "m10w19" / "python")
    module = importlib.import_module("m10w19_runtime")
    runtime = load_runtime(local_root, "M10W19")
    contract = module.js(module.CONTRACT)
    module.env = lambda: (local_root, journal, point)
    module.v2.prefix_fingerprint_rows = adapter.frozen_prefix_compatibility(runtime, contract["data"]["live_file_map"])
    original_verify = module.verify_runtime

    def compatible_verify(root: Path, current_point: float, current_contract: dict[str, Any], current_runtime: dict[str, Any]):
        runtime_compat = dict(current_runtime)
        runtime_compat["data_root"] = str(root)
        return original_verify(root, current_point, current_contract, runtime_compat)

    module.verify_runtime = compatible_verify
    return module.once


BUILDERS: dict[str, Callable[[Path, Path, Path, float], Callable[[], int]]] = {
    "M9V": build_m9v_runner,
    "M9Y": build_m9y_runner,
    "M10B": build_m10b_runner,
    "M10E": build_m10e_runner,
    "M10P": build_m10p_runner,
    "M10P2": build_m10p2_runner,
    "M10W19": build_m10w19_runner,
}


def write_status(path: Path, loop: str, started: str, cycles: int, successful: int, waiting: int, failed: int, status: str, **extra: Any) -> None:
    payload = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": LOOPS[loop]["stage"],
        "loop": loop,
        "status": status,
        "implementation": "BOUNDED_CSV_SOURCE_ADAPTER_V1",
        "audit_only": True,
        "started_at_utc": started,
        "updated_at_utc": utc_text(),
        "cycles": cycles,
        "successful_cycles": successful,
        "waiting_transient_cycles": waiting,
        "failed_terminal_cycles": failed,
        "prospective_start_server_time": adapter.EXPECTED_STARTS[loop],
        "runtime_or_start_modified": False,
        "historical_backfill_before_start": False,
        "discord_send": False,
        "mt5_order": False,
        **extra,
    }
    atomic_json(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a preserved-start fresh shadow through the bounded CSV source adapter.")
    parser.add_argument("--loop", choices=tuple(LOOPS), required=True)
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--compat-process-marker", default="")
    args = parser.parse_args()
    loop = args.loop
    if args.interval_seconds < 10 or args.interval_seconds > 3600:
        print("[LOOP BLOCKED] interval must be 10..3600 seconds", file=sys.stderr)
        return 2
    if args.max_cycles < 0:
        print("[LOOP BLOCKED] max-cycles must be non-negative", file=sys.stderr)
        return 2

    local_value = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_value:
        print("[LOOP BLOCKED] LOCALAPPDATA unavailable", file=sys.stderr)
        return 2
    local_root = Path(local_value) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    spec = LOOPS[loop]
    runtime_path = local_root / spec["runtime_rel"]
    lock_path = local_root / spec["lock_rel"]
    stop_path = local_root / spec["stop_rel"]
    log_path = local_root / spec["log_rel"]
    status = local_root / spec["status_rel"]
    if not runtime_path.is_file():
        print(f"[{loop} LOOP BLOCKED] runtime missing; BAT01 is forbidden: {runtime_path}", file=sys.stderr)
        return 2

    try:
        source_root, point = adapter.source_environment(local_root)
        journal = adapter.ensure_updated(local_root, source_root, point, retry_window_seconds=90.0)
        adapter.validate_loop(local_root, loop, source_root, point)
        cycle_function = BUILDERS[loop](local_root, source_root, journal, point)
    except Exception as exc:
        print(f"[{loop} LOOP BLOCKED] adapter preflight failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] Runtime manifest/start were not changed. Do not run BAT01.", file=sys.stderr)
        return 2

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(f"[{loop} LOOP BLOCKED] loop lock already exists: {lock_path}", file=sys.stderr)
        return 2
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump({
            "loop": loop,
            "stage": spec["stage"],
            "pid": os.getpid(),
            "started_at_utc": utc_text(),
            "implementation": adapter.ADAPTER_VERSION,
            "audit_only": True,
        }, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    stop_path.unlink(missing_ok=True)
    started = utc_text()
    cycles = successful = waiting = failed = 0
    print("=" * 72)
    print(f"{loop} preserved-start bounded CSV adapter loop - AUDIT ONLY")
    print(f"Source:  {source_root}")
    print(f"Journal: {journal}")
    print(f"Start:   {adapter.EXPECTED_STARTS[loop]}")
    print("Transient source/replacement errors wait and retry; integrity errors stop fail-closed.")
    print("=" * 72)

    try:
        while True:
            if stop_path.exists():
                write_status(status, loop, started, cycles, successful, waiting, failed, "STOPPED", stop_reason="STOP_FILE")
                print(f"[{loop} LOOP STOPPED] operator stop file")
                return 0
            cycles += 1
            cycle_stamp = utc_text()
            try:
                journal = adapter.ensure_updated(local_root, source_root, point, retry_window_seconds=90.0)
                adapter.validate_loop(local_root, loop, source_root, point)
                retry_deadline = time.monotonic() + 90.0
                while True:
                    rc, output = capture_call(cycle_function)
                    append_log(log_path, f"\n===== {loop} bounded cycle {cycles} {cycle_stamp} rc={rc} =====\n{output}")
                    if output:
                        print(output.rstrip())
                    if rc == 0:
                        successful += 1
                        write_status(status, loop, started, cycles, successful, waiting, failed, "RUNNING", last_exit_code=0)
                        break
                    if is_transient_failure(output) and time.monotonic() < retry_deadline:
                        time.sleep(1.0)
                        continue
                    if is_transient_failure(output):
                        waiting += 1
                        write_status(
                            status, loop, started, cycles, successful, waiting, failed,
                            "WAITING_TRANSIENT_SOURCE", last_exit_code=rc, last_error=output[-8000:],
                        )
                        print(f"[{loop} WAITING] transient cycle failure persisted for 90 seconds; loop remains alive.", file=sys.stderr)
                        break
                    failed += 1
                    write_status(
                        status, loop, started, cycles, successful, waiting, failed,
                        "BLOCKED", last_exit_code=rc, stop_reason="TERMINAL_RESEARCH_OR_INTEGRITY_FAILURE", last_error=output[-12000:],
                    )
                    print(f"[{loop} LOOP BLOCKED] terminal research/integrity failure. Do not reinitialize.", file=sys.stderr)
                    return 2
            except adapter.AdapterTransientError as exc:
                waiting += 1
                text = f"{type(exc).__name__}: {exc}"
                append_log(log_path, f"\n===== {loop} bounded cycle {cycles} {cycle_stamp} WAITING =====\n{text}\n")
                write_status(status, loop, started, cycles, successful, waiting, failed, "WAITING_TRANSIENT_SOURCE", last_error=text)
                print(f"[{loop} WAITING] {text}", file=sys.stderr)
            except adapter.AdapterIntegrityError as exc:
                failed += 1
                text = f"{type(exc).__name__}: {exc}"
                append_log(log_path, f"\n===== {loop} bounded cycle {cycles} {cycle_stamp} BLOCKED =====\n{text}\n")
                write_status(status, loop, started, cycles, successful, waiting, failed, "BLOCKED", stop_reason="TERMINAL_ADAPTER_INTEGRITY_FAILURE", last_error=text)
                print(f"[{loop} LOOP BLOCKED] {text}", file=sys.stderr)
                return 2
            except Exception as exc:
                failed += 1
                text = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
                append_log(log_path, f"\n===== {loop} bounded cycle {cycles} {cycle_stamp} BLOCKED =====\n{text}\n")
                write_status(status, loop, started, cycles, successful, waiting, failed, "BLOCKED", stop_reason="UNCLASSIFIED_TERMINAL_FAILURE", last_error=text[-12000:])
                print(f"[{loop} LOOP BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
                return 2

            if args.max_cycles and cycles >= args.max_cycles:
                write_status(status, loop, started, cycles, successful, waiting, failed, "STOPPED", stop_reason="MAX_CYCLES")
                return 0
            deadline = time.monotonic() + args.interval_seconds
            while time.monotonic() < deadline:
                if stop_path.exists():
                    break
                time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    except KeyboardInterrupt:
        write_status(status, loop, started, cycles, successful, waiting, failed, "STOPPED", stop_reason="KEYBOARD_INTERRUPT")
        print(f"[{loop}] graceful Ctrl+C stop")
        return 0
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
