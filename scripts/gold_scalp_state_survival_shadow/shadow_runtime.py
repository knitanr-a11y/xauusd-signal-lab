from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .common import (
    CANDIDATE_ID, CONTRACT_VERSION, RESEARCH_CUTOFF, RUNTIME_LABEL, SELECTED_STATE_ACTIONS,
    append_csv, load_config, lock_instance, logger_for, now_utc, read_csv_records,
    state_root, write_json,
)
from .discord_delivery import discord_settings, entry_message, make_chart, send
from .runtime_execution import (
    STATE_FILENAME, _advance_resolution, _initial_state, _levels, _load_state, _state_path,
    _new_resolution, _save_state,
)
from .runtime_policy import (
    ENTRY_EVENTS_FILENAME, HEALTH_DECISIONS_FILENAME, SUPPRESSION_EVENTS_FILENAME,
    TRADE_RESULTS_FILENAME, _advance_trades, _evaluate_row, _process_pending,
    _update_episode_absence,
)
from .state_engine import build_state_frame, load_market_data

DISCORD_LEDGER_FILENAME = "discord_send_ledger.csv"


def _sent_ids(root: Path) -> set[str]:
    return {record.get("event_id", "") for record in read_csv_records(root / DISCORD_LEDGER_FILENAME)}


def _deliver_discord_queue(
    state: dict[str, Any],
    config: Mapping[str, Any],
    config_path: Path,
    data: Mapping[str, pd.DataFrame],
    root: Path,
    logger,
) -> None:
    if not state.get("discord_queue"):
        return
    settings = discord_settings(config, config_path)
    sent_ids = _sent_ids(root)
    remaining = []
    for event in state["discord_queue"]:
        event_id = str(event["event_id"])
        if event_id in sent_ids:
            continue
        try:
            image = None
            if settings.get("attach_chart", True):
                image = make_chart(data["M15"], event, root, int(settings.get("chart_bars", 80)))
            send(settings["webhook_url"], settings["username"], entry_message(event), image)
            append_csv(
                root / DISCORD_LEDGER_FILENAME,
                {
                    "event_id": event_id,
                    "entry_time": event["entry_time"],
                    "state": event["state"],
                    "action": event["action"],
                    "sent_at_utc": now_utc(),
                },
            )
            sent_ids.add(event_id)
            logger.info("Discord entry notification sent: %s", event_id)
        except Exception as exc:  # fail closed and retry later
            logger.error("Discord delivery failed for %s: %s", event_id, exc)
            remaining.append(event)
    state["discord_queue"] = remaining


def bootstrap(config_path: Path, force: bool = False) -> dict[str, Any]:
    config = load_config(config_path)
    root = state_root(config, config_path)
    root.mkdir(parents=True, exist_ok=True)
    path = _state_path(root)
    if path.exists() and not force:
        raise RuntimeError(f"State already exists: {path}")
    data = load_market_data(config, config_path)
    states = build_state_frame(data["M15"], data["H1"], data["H4"])
    if states.empty:
        raise RuntimeError("No M15 state rows available")
    latest = pd.Timestamp(states["time"].iloc[-1])
    cursor = max(latest, RESEARCH_CUTOFF)
    state = _initial_state(cursor)
    _save_state(root, state)
    report = {
        "runtime_label": RUNTIME_LABEL,
        "candidate_id": CANDIDATE_ID,
        "contract_version": CONTRACT_VERSION,
        "formal_status": state["formal_status"],
        "bootstrapped_at_utc": now_utc(),
        "research_cutoff": str(RESEARCH_CUTOFF),
        "latest_existing_m15": str(latest),
        "cursor": str(cursor),
        "no_backfill": True,
        "selected_state_actions": SELECTED_STATE_ACTIONS,
        "data_source_audit": {key: value.attrs.get("source_audit", {}) for key, value in data.items()},
        "mt5_orders_enabled": False,
        "final_signal_enabled": False,
        "discord_entry_enabled": bool(config.get("discord", {}).get("enabled", True)),
    }
    write_json(root / "bootstrap_report.json", report)
    return report


def run_once(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    root = state_root(config, config_path)
    root.mkdir(parents=True, exist_ok=True)
    logger = logger_for(root, "gold_state_survival_shadow_once", "shadow_runtime.log")
    state = _load_state(root)
    data = load_market_data(config, config_path)
    state_rows = build_state_frame(data["M15"], data["H1"], data["H4"])

    _advance_trades(state, data, root)
    _process_pending(state, data, root)

    cursor = pd.Timestamp(state["last_processed_m15_time"])
    new_rows = state_rows[state_rows["time"] > cursor].sort_values("time")
    if not new_rows.empty:
        recovery_rows = new_rows.iloc[:-1]
        for _, row in recovery_rows.iterrows():
            _update_episode_absence(state, str(row["fine"]))
            state["last_processed_m15_time"] = str(pd.Timestamp(row["time"]))
            state["statistics"]["recovery_rows_skipped"] = int(state["statistics"].get("recovery_rows_skipped", 0)) + 1
            append_csv(
                root / SUPPRESSION_EVENTS_FILENAME,
                {
                    "signal_time": str(pd.Timestamp(row["time"])),
                    "entry_time": str(pd.Timestamp(row["time"]) + pd.Timedelta(minutes=15)),
                    "state": str(row["fine"]),
                    "action": SELECTED_STATE_ACTIONS.get(str(row["fine"]), ""),
                    "reason": "RECOVERY_NO_BACKFILL",
                    "created_at_utc": now_utc(),
                },
            )
        _evaluate_row(state, new_rows.iloc[-1], root)
        _process_pending(state, data, root)

    _advance_trades(state, data, root)
    _save_state(root, state)
    if config.get("discord", {}).get("enabled", True):
        _deliver_discord_queue(state, config, config_path, data, root, logger)
        _save_state(root, state)

    summary = {
        "runtime_label": RUNTIME_LABEL,
        "candidate_id": CANDIDATE_ID,
        "formal_status": state["formal_status"],
        "cursor": state["last_processed_m15_time"],
        "new_m15_rows": int(len(new_rows)),
        "pending_signal": state.get("pending_signal"),
        "open_trade_id": state.get("open_trade_id"),
        "total_trades": len(state.get("trades", {})),
        "discord_queue": len(state.get("discord_queue", [])),
        "suspended_states": list(state.get("health", {}).get("suspended", {})),
        "statistics": state.get("statistics", {}),
        "data_source_audit": {key: value.attrs.get("source_audit", {}) for key, value in data.items()},
        "mt5_orders_enabled": False,
        "final_signal_enabled": False,
    }
    write_json(root / "latest_cycle_summary.json", summary)
    return summary


def run_loop(config_path: Path) -> None:
    config = load_config(config_path)
    root = state_root(config, config_path)
    logger = logger_for(root, "gold_state_survival_shadow_loop", "shadow_runtime.log")
    lock = lock_instance(root, "shadow_runtime.lock", "State Survival Shadow is already running")
    poll_seconds = max(2, int(config.get("poll_seconds", 10)))
    logger.info("P75 State Survival observation-only loop started; orders are disabled")
    try:
        while True:
            if not config_path.exists():
                logger.error(
                    "CONFIG_MISSING_STOP path=%s; repository branch or checkout likely changed. "
                    "The P75 loop is stopping to avoid repeated failed cycles.",
                    config_path,
                )
                break
            try:
                summary = run_once(config_path)
                logger.info(
                    "cycle cursor=%s entries=%s open=%s",
                    summary["cursor"],
                    summary["total_trades"],
                    summary["open_trade_id"],
                )
            except Exception:
                logger.exception("P75 State Survival Shadow cycle failed")
            time.sleep(poll_seconds)
    finally:
        logger.info("P75 State Survival observation loop stopped")
        lock.close()


def status(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    root = state_root(config, config_path)
    state = _load_state(root)
    result = {
        "runtime_label": RUNTIME_LABEL,
        "candidate_id": CANDIDATE_ID,
        "contract_version": CONTRACT_VERSION,
        "formal_status": state.get("formal_status"),
        "state_root": str(root),
        "cursor": state.get("last_processed_m15_time"),
        "pending_signal": state.get("pending_signal"),
        "open_trade_id": state.get("open_trade_id"),
        "total_trades": len(state.get("trades", {})),
        "finalized_trades": sum(1 for trade in state.get("trades", {}).values() if trade.get("finalized")),
        "discord_queue": len(state.get("discord_queue", [])),
        "health": state.get("health"),
        "episodes": state.get("episodes"),
        "statistics": state.get("statistics"),
        "mt5_orders_enabled": False,
        "final_signal_enabled": False,
    }
    return result


def test_discord(config_path: Path) -> None:
    config = load_config(config_path)
    settings = discord_settings(config, config_path)
    content = "\n".join(
        [
            "✅ **GOLD State Survival Shadow Discord 接続テスト**",
            f"候補: `{CANDIDATE_ID}`",
            "通知対象: 新しく受理された疑似エントリーのみ",
            "状態: 観測専用・実注文なし",
            "MT5発注 / final_signal / live_ready: OFF",
        ]
    )
    send(settings["webhook_url"], settings["username"], content)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GOLD State Survival P75 prospective Shadow")
    parser.add_argument("command", choices=("bootstrap", "run-once", "run-loop", "status", "test-discord"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--force", action="store_true", help="Replace an existing bootstrap state")
    return parser


def main() -> None:
    args = _parser().parse_args()
    config_path = args.config.resolve()
    if args.command == "bootstrap":
        print(json.dumps(bootstrap(config_path, force=args.force), ensure_ascii=False, indent=2))
    elif args.command == "run-once":
        print(json.dumps(run_once(config_path), ensure_ascii=False, indent=2, default=str))
    elif args.command == "run-loop":
        run_loop(config_path)
    elif args.command == "status":
        print(json.dumps(status(config_path), ensure_ascii=False, indent=2, default=str))
    elif args.command == "test-discord":
        test_discord(config_path)
        print(f"[{RUNTIME_LABEL}] Discord test sent")


if __name__ == "__main__":
    main()
