from __future__ import annotations

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
from live_settings import RuntimeSettings, SLEEVES
from live_store import atomic_write_csv
from live_win_rate import WinRateSummary


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


def _live_text(summary: WinRateSummary) -> str:
    if not summary.available or summary.win_rate is None or summary.trades <= 0:
        return "集計前（決済済み0件）"
    return f"{summary.win_rate * 100:.2f}%（{summary.wins}/{summary.trades}）"


def _entry_message(
    row: pd.Series | dict[str, Any],
    _historical: WinRateSummary,
    live: WinRateSummary,
) -> str:
    direction = core._text(row["direction"])
    icon = "🟢" if direction == "LONG" else "🔴"
    status = core._text(row["execution_status"])
    lines = [
        f"{icon} **GML1 XAUUSD 候補 / {status}**",
        f"軸: `{core._text(row['comp'])}`",
        f"候補: `{core._text(row['candidate_id'])}`",
        f"方向: **{direction}**",
        f"判定時刻（MT5 server）: `{core._text(row['decision_time'])}`",
        f"発注状態: **{status}**",
    ]
    volume = core._number(row.get("volume"))
    if volume is not None:
        lines.append(f"ロット: `{volume:g}`")
    if status in {"ORDER_FILLED", "ORDER_RECOVERED_OPEN", "DRY_RUN"}:
        lines.extend(
            [
                f"約定/予定価格: `{core._format_price(row['fill_price'])}`",
                f"SL: `{core._format_price(row['stop_price'])}`",
                f"TP: `{core._format_price(row['target_price'])}`",
            ]
        )
    lines.extend(
        [
            f"実運用WR（この軸）: **{_live_text(live)}**",
            f"注記: `{core._text(row['message'])[:300] or 'none'}`",
        ]
    )
    return "\n".join(lines)


def _exit_message(
    row: pd.Series | dict[str, Any],
    _historical: WinRateSummary,
    live: WinRateSummary,
) -> str:
    result = core._text(row["live_result"])
    icon = "✅" if result == "WIN" else "➖" if result == "BREAKEVEN" else "❌"
    net = core._number(row["net_profit"])
    net_text = "N/A" if net is None else f"{net:.2f}"
    return "\n".join(
        [
            f"{icon} **GML1 XAUUSD 決済 / {result or 'CLOSED'}**",
            f"軸: `{core._text(row['comp'])}`",
            f"候補: `{core._text(row['candidate_id'])}`",
            f"判定時刻（MT5 server）: `{core._text(row['decision_time'])}`",
            f"決済時刻: `{core._text(row['closed_at']) or 'unknown'}`",
            f"実損益（口座通貨）: **{net_text}**",
            f"実運用WR（この軸・更新後）: **{_live_text(live)}**",
        ]
    )


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
    original_core_loader = core.load_runtime_settings
    original_supervisor_loader = supervisor.load_runtime_settings
    original_history = core.load_historical_win_rates
    original_live_rates = core.load_live_win_rates
    original_entry = core._format_entry_message
    original_exit = core._format_exit_message

    def always_on_loader(*args: Any, **kwargs: Any) -> RuntimeSettings:
        settings = original_supervisor_loader(*args, **kwargs)
        return _always_on_settings(settings)

    def permanent_live_rates(
        operational: pd.DataFrame,
        comps: Iterable[str],
    ) -> dict[str, WinRateSummary]:
        combined = combined_live_trade_frame(output_dir, operational)
        return original_live_rates(combined, comps)

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
        core.load_runtime_settings = always_on_loader
        supervisor.load_runtime_settings = always_on_loader
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

        ledger_path = output_dir / "live_execution_ledger.csv"
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
        core.load_runtime_settings = original_core_loader
        supervisor.load_runtime_settings = original_supervisor_loader
        core.load_historical_win_rates = original_history
        core.load_live_win_rates = original_live_rates
        core._format_entry_message = original_entry
        core._format_exit_message = original_exit
