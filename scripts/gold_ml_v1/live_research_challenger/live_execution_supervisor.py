from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pandas as pd

import live_execution as core
from live_mt5 import MT5ExecutionError, MetaTrader5Client
from live_settings import RuntimeSettings, SLEEVES, load_runtime_settings
from live_store import json_value


def _ledger_symbol(active: pd.DataFrame) -> str | None:
    if active.empty or "symbol" not in active.columns:
        return None
    symbols = sorted(
        {
            core._text(value)
            for value in active["symbol"].tolist()
            if core._text(value)
        }
    )
    if len(symbols) > 1:
        raise core.ExecutionCycleError(
            "open execution ledger rows contain multiple MT5 symbols"
        )
    return symbols[0] if symbols else None


def _management_settings(
    *,
    live_dir: Path,
    repo_root: Path,
    active: pd.DataFrame,
    base: RuntimeSettings | None,
) -> RuntimeSettings:
    symbol = _ledger_symbol(active)
    if not symbol:
        raise core.ExecutionCycleError(
            "an open execution ledger exists but its MT5 symbol is unavailable"
        )
    if base is not None:
        return replace(
            base,
            discord_enabled=False,
            discord_webhook_url=None,
            mt5_enabled=True,
            mt5_dry_run=False,
            mt5_live_confirmed=True,
            mt5_symbol=symbol,
            volumes={comp: 0.01 for comp in SLEEVES},
            config_errors=(),
        )
    return RuntimeSettings(
        env_path=live_dir / ".env",
        discord_enabled=False,
        discord_webhook_url=None,
        discord_username="GML1 XAUUSD",
        mt5_enabled=True,
        mt5_dry_run=False,
        mt5_live_confirmed=True,
        mt5_symbol=symbol,
        mt5_terminal_path=None,
        mt5_login=None,
        mt5_password=None,
        mt5_server=None,
        mt5_deviation_points=50,
        mt5_max_entry_lag_seconds=180,
        mt5_max_total_positions=1,
        mt5_magic_base=982200,
        mt5_require_hedging=True,
        mt5_filling_mode="AUTO",
        volumes={comp: 0.01 for comp in SLEEVES},
        historical_results_dir=(
            repo_root / "outputs/gold_ml_v1/research_challenger_local_runtime"
        ).resolve(),
        require_historical_win_rate=True,
        config_errors=(),
    )


def _mark_closed(
    ledger: pd.DataFrame,
    index: Any,
    *,
    net: float,
    closed_at: Any,
    now_text: str,
) -> None:
    ledger.loc[index, "trade_state"] = "CLOSED"
    ledger.loc[index, "net_profit"] = net
    ledger.loc[index, "live_result"] = (
        "WIN" if net > 0 else "LOSS" if net < 0 else "BREAKEVEN"
    )
    ledger.loc[index, "closed_at"] = (
        closed_at.strftime("%Y-%m-%d %H:%M:%S")
        if closed_at is not None
        else now_text
    )
    if core._text(ledger.loc[index, "execution_status"]) not in {
        "TIME_EXIT_FILLED",
        "ORDER_RECOVERED_HISTORY",
    }:
        ledger.loc[index, "execution_status"] = "CLOSED_BY_SL_TP_OR_MANUAL"


def _recover_missing_ticket(
    ledger: pd.DataFrame,
    index: Any,
    row: pd.Series,
    client: MetaTrader5Client,
    now_text: str,
) -> tuple[int | None, Any | None, bool]:
    magic_text = core._text(row["magic"])
    comment = core._text(row["comment"])
    if not magic_text or not comment:
        ledger.loc[index, "execution_status"] = "MT5_ERROR"
        ledger.loc[index, "message"] = (
            "open ledger row has no position ticket and lacks magic/comment recovery keys"
        )
        return None, None, False
    magic = int(float(magic_text))

    position = None
    finder = getattr(client, "find_position", None)
    if callable(finder):
        position = finder(magic=magic, comment=comment)
    if position is not None:
        ticket = int(getattr(position, "ticket", 0)) or None
        if ticket is not None:
            ledger.loc[index, "position_ticket"] = ticket
            ledger.loc[index, "execution_status"] = "ORDER_RECOVERED_OPEN"
            ledger.loc[index, "message"] = (
                "missing position ticket recovered from open MT5 position"
            )
            return ticket, position, True

    recover = getattr(client, "recover_existing", None)
    recovered = recover(magic=magic, comment=comment) if callable(recover) else None
    if recovered is not None and recovered.position_ticket:
        ticket = int(recovered.position_ticket)
        ledger.loc[index, "position_ticket"] = ticket
        ledger.loc[index, "deal_ticket"] = json_value(recovered.deal_ticket)
        ledger.loc[index, "execution_status"] = recovered.status
        ledger.loc[index, "message"] = recovered.message
        if recovered.status == "ORDER_RECOVERED_OPEN":
            return ticket, client.get_position(ticket), True
        closed = client.closed_position_profit(ticket)
        if closed is not None:
            net, closed_at = closed
            _mark_closed(
                ledger,
                index,
                net=net,
                closed_at=closed_at,
                now_text=now_text,
            )
            return ticket, None, True

    ledger.loc[index, "execution_status"] = "MT5_ERROR"
    ledger.loc[index, "message"] = (
        "open ledger row has no position ticket and MT5 recovery found no position or deal"
    )
    return None, None, False


def _safe_reconcile_open_orders(
    ledger: pd.DataFrame,
    client: MetaTrader5Client,
    latest_m1_close: pd.Timestamp,
    now_text: str,
) -> list[str]:
    events: list[str] = []
    for index, row in core._active_real_rows(ledger).iterrows():
        ticket = core._ticket(row["position_ticket"])
        position = None
        if ticket is None:
            ticket, position, recovered = _recover_missing_ticket(
                ledger, index, row, client, now_text
            )
            if not recovered or ticket is None:
                ledger.loc[index, "last_checked_at"] = now_text
                continue
            if ledger.loc[index, "trade_state"] == "CLOSED":
                events.append(f"{row['candidate_key']}:RECOVERED_CLOSED")
                ledger.loc[index, "last_checked_at"] = now_text
                continue
        if position is None:
            position = client.get_position(ticket)

        horizon = pd.Timestamp(row["horizon_end_time"])
        if position is not None and latest_m1_close >= horizon:
            try:
                result = client.close_position(
                    ticket,
                    comment=core._text(row["comment"]),
                    magic=int(float(row["magic"])),
                )
                ledger.loc[index, "execution_status"] = result.status
                ledger.loc[index, "retcode"] = json_value(result.retcode)
                ledger.loc[index, "deal_ticket"] = json_value(result.deal_ticket)
                ledger.loc[index, "message"] = result.message
                events.append(f"{row['candidate_key']}:{result.status}")
            except MT5ExecutionError as exc:
                ledger.loc[index, "execution_status"] = "TIME_EXIT_REJECTED"
                ledger.loc[index, "message"] = str(exc)

        position = client.get_position(ticket)
        if position is None:
            closed = client.closed_position_profit(ticket)
            if closed is not None:
                net, closed_at = closed
                _mark_closed(
                    ledger,
                    index,
                    net=net,
                    closed_at=closed_at,
                    now_text=now_text,
                )
                events.append(f"{row['candidate_key']}:CLOSED")
        ledger.loc[index, "last_checked_at"] = now_text
    return events


def process_execution_cycle(
    *,
    live_dir: Path,
    output_dir: Path,
    registry: pd.DataFrame,
    latest_m1_close: pd.Timestamp,
    now_text: str,
    repo_root: Path,
    client_factory: Callable[[RuntimeSettings], MetaTrader5Client] | None = None,
    webhook_sender: Callable[..., Any] = core.send_webhook,
) -> dict[str, Any]:
    """Run v1 with two additional fail-safe guarantees.

    1. Existing real MT5 positions remain managed even after all new-entry and
       Discord settings are disabled or the .env file becomes malformed.
    2. A filled order whose position ticket was not immediately returned is
       recovered from MT5 magic/comment identity before it can be abandoned.
    """

    ledger_path = output_dir / "live_execution_ledger.csv"
    try:
        ledger = core._load_ledger(ledger_path)
        active = core._active_real_rows(ledger)
    except Exception:
        return core.process_execution_cycle(
            live_dir=live_dir,
            output_dir=output_dir,
            registry=registry,
            latest_m1_close=latest_m1_close,
            now_text=now_text,
            repo_root=repo_root,
            client_factory=client_factory,
            webhook_sender=webhook_sender,
        )

    settings: RuntimeSettings | None = None
    settings_error: Exception | None = None
    try:
        settings = load_runtime_settings(live_dir, repo_root)
    except Exception as exc:
        settings_error = exc

    forced_management = False
    if not active.empty and (
        settings is None
        or not (settings.discord_enabled or settings.mt5_enabled)
    ):
        forced_management = True
        settings = _management_settings(
            live_dir=live_dir,
            repo_root=repo_root,
            active=active,
            base=settings,
        )

    if settings_error is not None and not forced_management:
        return core.process_execution_cycle(
            live_dir=live_dir,
            output_dir=output_dir,
            registry=registry,
            latest_m1_close=latest_m1_close,
            now_text=now_text,
            repo_root=repo_root,
            client_factory=client_factory,
            webhook_sender=webhook_sender,
        )

    original_loader = core.load_runtime_settings
    original_reconcile = core._reconcile_open_orders
    try:
        core._reconcile_open_orders = _safe_reconcile_open_orders
        effective_registry = registry
        if forced_management:
            recorded_keys = set(ledger["candidate_key"].astype(str))
            effective_registry = registry[
                registry["candidate_key"].astype(str).isin(recorded_keys)
            ].copy()
            core.load_runtime_settings = lambda *_args, **_kwargs: settings
        result = core.process_execution_cycle(
            live_dir=live_dir,
            output_dir=output_dir,
            registry=effective_registry,
            latest_m1_close=latest_m1_close,
            now_text=now_text,
            repo_root=repo_root,
            client_factory=client_factory,
            webhook_sender=webhook_sender,
        )
        if forced_management:
            result["forced_open_position_management"] = True
            if settings_error is not None:
                result["settings_warning"] = (
                    f"{type(settings_error).__name__}: {settings_error}"
                )
        return result
    finally:
        core.load_runtime_settings = original_loader
        core._reconcile_open_orders = original_reconcile
