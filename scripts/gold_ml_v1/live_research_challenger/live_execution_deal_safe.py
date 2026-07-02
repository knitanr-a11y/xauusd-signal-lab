from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pandas as pd

import live_execution as core
import live_execution_live_wr as policy
from live_deal_archive import (
    DealCapture,
    DealCapturingClient,
    archive_captures,
    completed_position_tickets,
)
from live_feature_archive import update_trade_feature_index
from live_log_manager import maintain_logs_and_trades as base_maintain_logs
from live_mt5 import MetaTrader5Client
from live_settings import RuntimeSettings, load_runtime_settings


def _ticket(value: Any) -> int | None:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _real_closed_rows(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return ledger.copy()
    tickets = ledger["position_ticket"].map(_ticket)
    return ledger[
        ledger["trade_state"].astype(str).eq("CLOSED") & tickets.notna()
    ].copy()


def _pending_deal_positions(output_dir: Path, ledger: pd.DataFrame) -> list[int]:
    complete = completed_position_tickets(output_dir)
    result: list[int] = []
    for value in _real_closed_rows(ledger)["position_ticket"].tolist():
        ticket = _ticket(value)
        if ticket is not None and ticket not in complete and ticket not in result:
            result.append(ticket)
    return result


def _capture_pending_positions(
    *,
    live_dir: Path,
    repo_root: Path,
    pending: list[int],
    base_factory: Callable[[RuntimeSettings], Any],
    captures: list[DealCapture],
) -> str | None:
    if not pending:
        return None
    settings = load_runtime_settings(live_dir, repo_root)
    if not settings.mt5_symbol:
        return "deal backfill skipped: MT5 symbol is unavailable"
    client = DealCapturingClient(base_factory(settings), captures)
    try:
        client.__enter__()
        for position_ticket in pending:
            client.capture_position(position_ticket)
    except Exception as exc:
        return f"deal backfill failed: {type(exc).__name__}: {exc}"
    finally:
        try:
            client.__exit__(None, None, None)
        except Exception:
            pass
    return None


def _mask_incomplete_deal_rows(
    output_dir: Path,
    ledger: pd.DataFrame,
) -> tuple[pd.DataFrame, set[str]]:
    complete = completed_position_tickets(output_dir)
    masked = ledger.copy()
    pending_keys: set[str] = set()
    for index, row in _real_closed_rows(ledger).iterrows():
        ticket = _ticket(row["position_ticket"])
        if ticket is not None and ticket not in complete:
            pending_keys.add(str(row["candidate_key"]))
            masked.loc[index, "trade_state"] = "DEAL_ARCHIVE_PENDING"
    return masked, pending_keys


def _restore_pending_states(
    compacted: pd.DataFrame,
    pending_keys: set[str],
) -> pd.DataFrame:
    if compacted.empty or not pending_keys:
        return compacted
    restored = compacted.copy()
    mask = restored["candidate_key"].astype(str).isin(pending_keys)
    restored.loc[mask, "trade_state"] = "CLOSED"
    return restored


def _read_frame(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=object) if path.is_file() else pd.DataFrame()


def process_execution_cycle(
    *,
    live_dir: Path,
    output_dir: Path,
    registry: pd.DataFrame,
    latest_m1_close: pd.Timestamp,
    now_text: str,
    repo_root: Path,
    client_factory: Callable[[RuntimeSettings], Any] | None = None,
    webhook_sender: Callable[..., Any] = core.send_webhook,
) -> dict[str, Any]:
    """Run execution with complete immutable MT5 deal retention."""

    base_factory = client_factory or MetaTrader5Client
    captures: list[DealCapture] = []

    def factory(settings: RuntimeSettings) -> DealCapturingClient:
        return DealCapturingClient(base_factory(settings), captures)

    original_maintain = policy.maintain_logs_and_trades
    deal_status: dict[str, Any] = {}
    maintenance_warning: str | None = None

    def maintain_with_deals(
        output: Path,
        *,
        ledger: pd.DataFrame,
        now_text: str,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        nonlocal deal_status, maintenance_warning

        deal_status = archive_captures(output, ledger, captures, now_text)
        pending = _pending_deal_positions(output, ledger)
        warning = _capture_pending_positions(
            live_dir=live_dir,
            repo_root=repo_root,
            pending=pending,
            base_factory=base_factory,
            captures=captures,
        )
        if warning:
            maintenance_warning = warning
        if pending:
            deal_status = archive_captures(output, ledger, captures, now_text)

        masked, pending_keys = _mask_incomplete_deal_rows(output, ledger)
        compacted, manifest = base_maintain_logs(
            output,
            ledger=masked,
            now_text=now_text,
        )
        compacted = _restore_pending_states(compacted, pending_keys)
        manifest["deal_archive"] = deal_status
        manifest["deal_archive_pending_positions"] = len(pending_keys)
        if maintenance_warning:
            manifest["deal_archive_warning"] = maintenance_warning
        return compacted, manifest

    try:
        policy.maintain_logs_and_trades = maintain_with_deals
        result = policy.process_execution_cycle(
            live_dir=live_dir,
            output_dir=output_dir,
            registry=registry,
            latest_m1_close=latest_m1_close,
            now_text=now_text,
            repo_root=repo_root,
            client_factory=factory,
            webhook_sender=webhook_sender,
        )
        operational = _read_frame(output_dir / "live_execution_ledger.csv")
        feature_index = update_trade_feature_index(
            output_dir,
            registry=registry,
            operational=operational,
            now_text=now_text,
        )
        result["trade_feature_index"] = {
            "path": "trades/trade_feature_index.csv",
            "rows": int(len(feature_index)),
            "entry_snapshot": "CLOSED_ENTRY_TIME_ONLY",
            "live_gate_usage": False,
        }
        result["deal_archive"] = deal_status
        result["autotrading_connection"] = "CONNECTED_WITH_EXISTING_FAIL_CLOSED_CONTROLS"
        if maintenance_warning:
            result["deal_archive_warning"] = maintenance_warning
        return result
    finally:
        policy.maintain_logs_and_trades = original_maintain
