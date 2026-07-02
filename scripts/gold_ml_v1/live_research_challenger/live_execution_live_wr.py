from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

import live_execution as core
import live_execution_supervisor as supervisor
from live_log_manager import (
    append_notification_log,
    combined_live_trade_frame,
    known_candidate_keys,
    maintain_logs_and_trades,
)
from live_mt5 import MetaTrader5Client
from live_notification_formatter import format_entry_message, format_exit_message
from live_settings import RuntimeSettings, SLEEVES
from live_store import atomic_write_csv, json_value
from live_win_rate import WinRateSummary

_BASE_LEDGER_COLUMNS = tuple(core.LEDGER_COLUMNS)
_OPTIONAL_LEDGER_COLUMNS = (
    "source_timeframe",
    "higher_timeframe",
    "features_json",
    "atr",
    "target_r",
    "horizon_hours",
    "strategy_name",
    "signal_reason",
    "higher_timeframe_context",
    "close_reason",
    "close_price",
)
_BASE_ROW_FACTORY = core._base_row


def _unused_history(
    _results_dir: Path,
    comps: Iterable[str],
) -> dict[str, WinRateSummary]:
    return {
        comp: WinRateSummary(
            trades=0,
            wins=0,
            losses_or_flat=0,
            win_rate=None,
            source="disabled",
            available=False,
            reason="historical performance is not used",
        )
        for comp in comps
    }


def _entry_message(
    row: pd.Series | dict[str, Any],
    _historical: WinRateSummary,
    live: WinRateSummary,
) -> str:
    return format_entry_message(row, live)


def _exit_message(
    row: pd.Series | dict[str, Any],
    _historical: WinRateSummary,
    live: WinRateSummary,
) -> str:
    return format_exit_message(row, live)


def _ledger_columns(path: Path) -> list[str]:
    existing: list[str] = []
    if path.is_file():
        existing = list(pd.read_csv(path, nrows=0).columns)
        missing_required = [
            column for column in _BASE_LEDGER_COLUMNS if column not in existing
        ]
        if missing_required:
            raise core.ExecutionCycleError(
                f"execution ledger missing columns: {missing_required}"
            )
    extras = [
        column
        for column in existing
        if column not in _BASE_LEDGER_COLUMNS
        and column not in _OPTIONAL_LEDGER_COLUMNS
    ]
    return [*_BASE_LEDGER_COLUMNS, *_OPTIONAL_LEDGER_COLUMNS, *extras]


def _load_ledger_additive(
    path: Path,
    columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    effective_columns = list(columns or _ledger_columns(path))
    if not path.is_file():
        return pd.DataFrame(columns=effective_columns)
    frame = pd.read_csv(path, dtype=object)
    missing_required = [
        column for column in _BASE_LEDGER_COLUMNS if column not in frame.columns
    ]
    if missing_required:
        raise core.ExecutionCycleError(
            f"execution ledger missing columns: {missing_required}"
        )
    for column in effective_columns:
        if column not in frame.columns:
            frame[column] = ""
    if frame["candidate_key"].duplicated().any():
        raise core.ExecutionCycleError(
            "execution ledger contains duplicate candidate_key values"
        )
    return frame[effective_columns].copy()


def _json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _base_row_with_optional(record: dict[str, Any], now_text: str) -> dict[str, Any]:
    row = _BASE_ROW_FACTORY(record, now_text)
    row.update(
        {
            "source_timeframe": str(record.get("source_timeframe") or ""),
            "higher_timeframe": str(record.get("higher_timeframe") or ""),
            "features_json": _json_text(record.get("features_json")),
            "atr": json_value(record.get("atr")),
            "target_r": json_value(record.get("target_r")),
            "horizon_hours": json_value(record.get("horizon_hours")),
            "strategy_name": str(record.get("strategy_name") or ""),
            "signal_reason": str(record.get("signal_reason") or ""),
            "higher_timeframe_context": str(
                record.get("higher_timeframe_context") or ""
            ),
            "close_reason": "",
            "close_price": "",
        }
    )
    return row


def _deal_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    method = getattr(value, "_asdict", None)
    if callable(method):
        return dict(method())
    return {
        name: getattr(value, name)
        for name in ("ticket", "time_msc", "entry", "reason", "price")
        if hasattr(value, name)
    }


def _closing_deals(client: Any, position_ticket: int) -> list[dict[str, Any]]:
    try:
        capture = getattr(client, "capture_position", None)
        if callable(capture):
            raw = capture(int(position_ticket)) or ()
        else:
            custom = getattr(client, "position_deal_records", None)
            if callable(custom):
                raw = custom(int(position_ticket)) or ()
            else:
                mt5 = getattr(client, "mt5", None)
                raw = (
                    mt5.history_deals_get(position=int(position_ticket)) or ()
                    if mt5 is not None
                    else ()
                )
    except Exception:
        return []
    result: list[dict[str, Any]] = []
    for value in raw:
        deal = _deal_dict(value)
        try:
            entry = int(deal.get("entry", -1))
        except (TypeError, ValueError):
            continue
        if entry in {1, 2, 3}:
            result.append(deal)
    return result


def _deal_close_reason(client: Any, deal: dict[str, Any]) -> str:
    raw = deal.get("reason")
    text = str(raw).strip().upper() if raw is not None else ""
    text_aliases = {
        "SL": "SL",
        "STOP_LOSS": "SL",
        "TP": "TP",
        "TAKE_PROFIT": "TP",
        "CLIENT": "MANUAL",
        "MOBILE": "MANUAL",
        "WEB": "MANUAL",
        "MANUAL": "MANUAL",
        "EXPERT": "EXPERT",
    }
    if text in text_aliases:
        return text_aliases[text]
    try:
        reason = int(raw)
    except (TypeError, ValueError):
        return ""
    mt5 = getattr(client, "mt5", None)
    if mt5 is None:
        return ""
    for label, names in (
        ("SL", ("DEAL_REASON_SL",)),
        ("TP", ("DEAL_REASON_TP",)),
        (
            "MANUAL",
            ("DEAL_REASON_CLIENT", "DEAL_REASON_MOBILE", "DEAL_REASON_WEB"),
        ),
        ("EXPERT", ("DEAL_REASON_EXPERT",)),
    ):
        for name in names:
            value = getattr(mt5, name, None)
            if value is not None and int(value) == reason:
                return label
    return ""


def _enrich_closed_deal_metadata(ledger: pd.DataFrame, client: Any) -> None:
    required = {"trade_state", "execution_status", "close_reason", "close_price"}
    if ledger.empty or not required.issubset(ledger.columns):
        return
    closed = ledger[ledger["trade_state"].astype(str).eq("CLOSED")]
    for index, row in closed.iterrows():
        if core._text(row.get("close_reason")) and core._text(
            row.get("close_price")
        ):
            continue
        status = core._text(row.get("execution_status"))
        if status == "TIME_EXIT_FILLED" and not core._text(
            row.get("close_reason")
        ):
            ledger.loc[index, "close_reason"] = "TIME"
        ticket = core._ticket(row.get("position_ticket"))
        if ticket is None:
            continue
        deals = _closing_deals(client, ticket)
        if not deals:
            continue
        latest = max(
            deals,
            key=lambda deal: (
                int(deal.get("time_msc") or 0),
                int(deal.get("deal_ticket") or deal.get("ticket") or 0),
            ),
        )
        if not core._text(ledger.loc[index, "close_price"]):
            price = core._number(latest.get("price"))
            if price is not None:
                ledger.loc[index, "close_price"] = price
        if not core._text(ledger.loc[index, "close_reason"]):
            reason = _deal_close_reason(client, latest)
            if reason:
                ledger.loc[index, "close_reason"] = reason


def _unique_errors(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _always_on_settings(settings: RuntimeSettings) -> RuntimeSettings:
    """Keep configured delivery/execution on while preserving emergency recovery."""

    if not settings.env_path.is_file():
        return replace(settings, require_historical_win_rate=False)

    errors = list(settings.config_errors)
    if not settings.discord_webhook_url:
        errors.append("always-on Discord requires a webhook URL in Files/.env")
    if not settings.mt5_symbol:
        errors.append("always-on MT5 execution requires GML1_MT5_SYMBOL")
    missing_volumes = [
        comp
        for comp in SLEEVES
        if settings.volumes.get(comp) is None or float(settings.volumes[comp]) <= 0
    ]
    if missing_volumes:
        errors.append(
            "positive MT5 volume is required for: " + ", ".join(missing_volumes)
        )
    if not settings.mt5_dry_run and not settings.mt5_live_confirmed:
        errors.append(
            "real MT5 orders require the exact GML1_MT5_LIVE_CONFIRM token"
        )
    return replace(
        settings,
        discord_enabled=True,
        mt5_enabled=True,
        require_historical_win_rate=False,
        config_errors=_unique_errors(errors),
    )


def _registry_without_archived_duplicates(
    output_dir: Path,
    registry: pd.DataFrame,
) -> pd.DataFrame:
    state_path = output_dir / "live_execution_state.json"
    if not state_path.is_file() or registry.empty:
        return registry
    known = known_candidate_keys(output_dir)
    if not known:
        return registry
    ledger_path = output_dir / "live_execution_ledger.csv"
    current_keys: set[str] = set()
    if ledger_path.is_file():
        current = core._load_ledger(ledger_path)
        if not current.empty:
            current_keys = set(current["candidate_key"].astype(str))
    archived_only = known - current_keys
    if not archived_only:
        return registry
    return registry[
        ~registry["candidate_key"].astype(str).isin(archived_only)
    ].copy()


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
    original_core_settings_loader = core.load_runtime_settings
    original_supervisor_loader = supervisor.load_runtime_settings
    original_history = core.load_historical_win_rates
    original_live_rates = core.load_live_win_rates
    original_entry = core._format_entry_message
    original_exit = core._format_exit_message
    original_ledger_columns = core.LEDGER_COLUMNS
    original_ledger_loader = core._load_ledger
    original_base_row = core._base_row
    original_supervisor_reconcile = supervisor._safe_reconcile_open_orders

    ledger_path = output_dir / "live_execution_ledger.csv"
    effective_ledger_columns = _ledger_columns(ledger_path)

    def always_on_loader(*args: Any, **kwargs: Any) -> RuntimeSettings:
        settings = original_supervisor_loader(*args, **kwargs)
        return _always_on_settings(settings)

    def permanent_live_rates(
        operational: pd.DataFrame,
        comps: Iterable[str],
    ) -> dict[str, WinRateSummary]:
        combined = combined_live_trade_frame(output_dir, operational)
        return original_live_rates(combined, comps)

    def additive_ledger_loader(path: Path) -> pd.DataFrame:
        return _load_ledger_additive(path, effective_ledger_columns)

    def reconcile_with_notification_metadata(
        ledger: pd.DataFrame,
        client: MetaTrader5Client,
        latest_close: pd.Timestamp,
        check_time: str,
    ) -> list[str]:
        events = original_supervisor_reconcile(
            ledger, client, latest_close, check_time
        )
        _enrich_closed_deal_metadata(ledger, client)
        return events

    def logged_webhook_sender(
        url: str,
        *,
        content: str,
        username: str,
    ) -> Any:
        try:
            result = webhook_sender(url, content=content, username=username)
        except Exception as exc:
            append_notification_log(
                output_dir,
                now_text=now_text,
                status="FAILED",
                content=content,
                username=username,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        append_notification_log(
            output_dir,
            now_text=now_text,
            status="SENT",
            content=content,
            username=username,
        )
        return result

    try:
        core.LEDGER_COLUMNS = effective_ledger_columns
        core._load_ledger = additive_ledger_loader
        core._base_row = _base_row_with_optional
        core.load_runtime_settings = always_on_loader
        supervisor.load_runtime_settings = always_on_loader
        supervisor._safe_reconcile_open_orders = reconcile_with_notification_metadata
        core.load_historical_win_rates = _unused_history
        core.load_live_win_rates = permanent_live_rates
        core._format_entry_message = _entry_message
        core._format_exit_message = _exit_message

        effective_registry = _registry_without_archived_duplicates(
            output_dir, registry
        )
        result = supervisor.process_execution_cycle(
            live_dir=live_dir,
            output_dir=output_dir,
            registry=effective_registry,
            latest_m1_close=latest_m1_close,
            now_text=now_text,
            repo_root=repo_root,
            client_factory=client_factory,
            webhook_sender=logged_webhook_sender,
        )
        result.pop("historical_win_rate", None)
        result["win_rate_scope"] = "LIVE_MT5_CLOSED_ORDERS_ONLY_BY_SLEEVE"
        result["service_mode"] = "ALWAYS_ON_FAIL_CLOSED"

        if ledger_path.is_file():
            ledger = core._load_ledger(ledger_path)
            compacted, manifest = maintain_logs_and_trades(
                output_dir,
                ledger=ledger,
                now_text=now_text,
            )
            atomic_write_csv(ledger_path, compacted)
            result["log_management"] = manifest
        return result
    finally:
        core.load_runtime_settings = original_core_settings_loader
        supervisor.load_runtime_settings = original_supervisor_loader
        supervisor._safe_reconcile_open_orders = original_supervisor_reconcile
        core.load_historical_win_rates = original_history
        core.load_live_win_rates = original_live_rates
        core._format_entry_message = original_entry
        core._format_exit_message = original_exit
        core.LEDGER_COLUMNS = original_ledger_columns
        core._load_ledger = original_ledger_loader
        core._base_row = original_base_row
