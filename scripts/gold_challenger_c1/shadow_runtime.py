from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .shadow_common import (
    CANDIDATE_ID, CONTRACT_VERSION, HORIZON_M1, RUNTIME_LABEL, append_csv, load_config,
    lock_instance, logger_for, now_utc, parse_dt, read_csv_records, read_json, state_root,
    write_json,
)
from .shadow_data import load_m1, load_wave_data, peek_latest_m1, research_timeline, resolve_data_sources, validate_base_sources
from .shadow_engine import _entry_prices, default_state, process_new_decisions, process_open_trade
from .v19_readonly import V19Interval, V19View, load_v19_view


def health_payload(state: Mapping[str, Any], v19: V19View | None, status: str, message: str | None = None) -> dict[str, Any]:
    return {
        "runtime_label": RUNTIME_LABEL,
        "candidate_id": CANDIDATE_ID,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "activated": bool(state.get("activated")),
        "observation_only": True,
        "retrospective_formal_status": "RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_FAILED",
        "user_authorization": "USER_AUTHORIZED_PROSPECTIVE_SHADOW_AND_DISCORD_2026-08-01",
        "v19_frozen_and_read_only": True,
        "v19_status": None if v19 is None else v19.status,
        "v19_parity": None if v19 is None else v19.parity,
        "v19_last_processed": None if v19 is None else v19.last_processed,
        "last_processed_decision_dt": state.get("last_processed_decision_dt"),
        "open_trade": state.get("open_trade"),
        "counters": state.get("counters", {}),
        "message": message,
        "updated_at_utc": now_utc(),
    }


def bootstrap(config_path: Path, activate: bool) -> None:
    config = load_config(config_path)
    root = state_root(config)
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / "runtime_state.json"
    if state_path.exists() and read_json(state_path).get("activated"):
        print(f"[{RUNTIME_LABEL}] Already activated; bootstrap did not reset the no-backfill baseline.")
        return
    sources = resolve_data_sources(config)
    validation = validate_base_sources(sources)
    v19 = load_v19_view(config)
    if not v19.ready:
        raise RuntimeError(f"V19_NOT_READY status={v19.status} activated={v19.activated} parity={v19.parity}")
    data = load_wave_data(sources)
    timeline = research_timeline(data, v19.score_ledger)
    if timeline.empty:
        raise RuntimeError("No Challenger decision rows were reproduced")
    latest = pd.Timestamp(timeline.decision_dt.iloc[-1])
    if v19.last_processed is None or v19.last_processed < latest:
        raise RuntimeError(f"V19_NOT_CAUGHT_UP: v19={v19.last_processed} challenger={latest}")
    state = default_state()
    state.update(
        {
            "activated": bool(activate),
            "activated_at_utc": now_utc() if activate else None,
            "baseline_decision_dt": latest,
            "last_processed_decision_dt": latest,
            "last_seen_m1_dt": pd.Timestamp(data["M1"].time.iloc[-1]),
            "source_validation": validation,
            "startup_policy": "NO_BACKFILL_BASELINE_CURRENT_DECISION_AND_CURRENT_EVENT_STATE",
        }
    )
    status = "READY" if activate else "BOOTSTRAPPED_NOT_ACTIVATED"
    write_json(state_path, state)
    write_json(root / "runtime_health.json", health_payload(state, v19, status))
    append_csv(root / "outputs" / "runtime_event_ledger.csv", {"event": "BOOTSTRAP_BASELINE", "decision_dt": latest, "activated": activate, "at_utc": now_utc()})
    print(json.dumps(health_payload(state, v19, status), ensure_ascii=False, indent=2, default=str))


def run_iteration(config_path: Path, allow_new_entries: bool) -> None:
    config = load_config(config_path)
    root = state_root(config)
    state_path = root / "runtime_state.json"
    if not state_path.exists():
        raise FileNotFoundError("Run bootstrap before starting the loop")
    state = read_json(state_path)
    if not state.get("activated"):
        raise RuntimeError("Challenger Shadow is not activated")
    sources = resolve_data_sources(config)
    latest_m1 = peek_latest_m1(sources)
    v19 = load_v19_view(config)
    if not v19.ready:
        raise RuntimeError(f"V19_NOT_READY status={v19.status} activated={v19.activated} parity={v19.parity}")
    latest_decision = v19.last_processed
    last_decision = parse_dt(state.get("last_processed_decision_dt"))
    last_seen_m1 = parse_dt(state.get("last_seen_m1_dt"))
    needs_m1 = last_seen_m1 is None or latest_m1 > last_seen_m1 or bool(state.get("open_trade"))
    needs_decision = latest_decision is not None and (last_decision is None or latest_decision > last_decision)
    if not needs_m1 and not needs_decision:
        state["last_iteration_utc"] = now_utc()
        state["last_error"] = None
        write_json(state_path, state)
        write_json(root / "runtime_health.json", health_payload(state, v19, "READY"))
        return
    data = load_wave_data(sources) if needs_decision else None
    m1 = data["M1"] if data is not None else load_m1(sources)
    process_open_trade(state, root, m1, v19)
    if data is not None:
        process_new_decisions(state, root, research_timeline(data, v19.score_ledger), m1, v19, allow_new_entries)
    state["last_seen_m1_dt"] = pd.Timestamp(m1.time.iloc[-1])
    state["last_iteration_utc"] = now_utc()
    state["last_error"] = None
    write_json(state_path, state)
    write_json(root / "runtime_health.json", health_payload(state, v19, "READY"))


def loop(config_path: Path) -> None:
    config = load_config(config_path)
    root = state_root(config)
    logger = logger_for(root, "gold_challenger_c1_shadow", "shadow_runtime.log")
    lock = lock_instance(root, "shadow_runtime.lock", "Challenger Shadow runtime is already running")
    delay = max(2, int(config.get("poll_seconds", 10)))
    first_iteration = True
    logger.info("Starting Challenger C1 observation-only loop session=%s", uuid.uuid4().hex)
    try:
        while True:
            try:
                run_iteration(config_path, allow_new_entries=not first_iteration)
                first_iteration = False
            except Exception as exc:
                state_path = root / "runtime_state.json"
                state = read_json(state_path) if state_path.exists() else default_state()
                state["last_error"] = {"at_utc": now_utc(), "message": str(exc)}
                state["last_iteration_utc"] = now_utc()
                write_json(state_path, state)
                write_json(root / "runtime_health.json", health_payload(state, None, "BLOCKED", str(exc)))
                logger.exception("Challenger C1 Shadow iteration failed")
            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        logger.info("Challenger C1 observation loop stopped")
        lock.close()


def status(config_path: Path) -> None:
    root = state_root(load_config(config_path))
    state = read_json(root / "runtime_state.json") if (root / "runtime_state.json").exists() else {"status": "NOT_BOOTSTRAPPED"}
    health = read_json(root / "runtime_health.json") if (root / "runtime_health.json").exists() else {"status": "NOT_BOOTSTRAPPED"}
    print(json.dumps({"runtime_label": RUNTIME_LABEL, "state": state, "health": health}, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GOLD Challenger C1 observation-only prospective Shadow")
    parser.add_argument("--config", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    boot = sub.add_parser("bootstrap")
    boot.add_argument("--activate", action="store_true")
    sub.add_parser("once")
    sub.add_parser("loop")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.command == "bootstrap":
            bootstrap(args.config, bool(args.activate))
        elif args.command == "once":
            run_iteration(args.config, allow_new_entries=False)
        elif args.command == "loop":
            loop(args.config)
        else:
            status(args.config)
        return 0
    except Exception as exc:
        print(f"[{RUNTIME_LABEL}] ERROR: {exc}", file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
