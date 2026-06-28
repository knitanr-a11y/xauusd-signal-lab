from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

import live_execution as core
import live_execution_supervisor as supervisor
from live_mt5 import MetaTrader5Client
from live_settings import RuntimeSettings
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
    original_entry = core._format_entry_message
    original_exit = core._format_exit_message

    def live_only_settings(*args: Any, **kwargs: Any) -> RuntimeSettings:
        settings = original_supervisor_loader(*args, **kwargs)
        return replace(settings, require_historical_win_rate=False)

    try:
        core.load_runtime_settings = live_only_settings
        supervisor.load_runtime_settings = live_only_settings
        core.load_historical_win_rates = _unused_history
        core._format_entry_message = _entry_message
        core._format_exit_message = _exit_message
        result = supervisor.process_execution_cycle(
            live_dir=live_dir,
            output_dir=output_dir,
            registry=registry,
            latest_m1_close=latest_m1_close,
            now_text=now_text,
            repo_root=repo_root,
            client_factory=client_factory,
            webhook_sender=webhook_sender,
        )
        result.pop("historical_win_rate", None)
        result["win_rate_scope"] = "LIVE_MT5_CLOSED_ORDERS_ONLY_BY_SLEEVE"
        return result
    finally:
        core.load_runtime_settings = original_core_loader
        supervisor.load_runtime_settings = original_supervisor_loader
        core.load_historical_win_rates = original_history
        core._format_entry_message = original_entry
        core._format_exit_message = original_exit
