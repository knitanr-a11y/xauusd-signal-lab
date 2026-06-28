from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from live_discord import DiscordError, send_webhook
from live_mt5 import MT5ExecutionError, MetaTrader5Client, OrderResult
from live_settings import SLEEVES, RuntimeSettings, load_runtime_settings
from live_store import atomic_write_csv, atomic_write_text, json_value
from live_win_rate import (
    WinRateSummary,
    load_historical_win_rates,
    load_live_win_rates,
)

LEDGER_COLUMNS = [
    "candidate_key",
    "candidate_id",
    "comp",
    "direction",
    "decision_time",
    "horizon_end_time",
    "execution_status",
    "trade_state",
    "live_result",
    "requested_at",
    "last_checked_at",
    "magic",
    "comment",
    "symbol",
    "volume",
    "order_ticket",
    "deal_ticket",
    "position_ticket",
    "fill_price",
    "stop_price",
    "target_price",
    "retcode",
    "message",
    "closed_at",
    "net_profit",
    "entry_discord_sent_at",
    "exit_discord_sent_at",
]


class ExecutionCycleError(RuntimeError):
    pass


def _blank_ledger() -> pd.DataFrame:
    return pd.DataFrame(columns=LEDGER_COLUMNS)


def _load_ledger(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return _blank_ledger()
    frame = pd.read_csv(path, dtype=object)
    missing = [column for column in LEDGER_COLUMNS if column not in frame.columns]
    if missing:
        raise ExecutionCycleError(f"execution ledger missing columns: {missing}")
    if frame["candidate_key"].duplicated().any():
        raise ExecutionCycleError(
            "execution ledger contains duplicate candidate_key values"
        )
    return frame[LEDGER_COLUMNS].copy()


def _is_blank(value: Any) -> bool:
    return (
        value is None
        or (isinstance(value, float) and np.isnan(value))
        or str(value).strip() == ""
    )


def _text(value: Any) -> str:
    return "" if _is_blank(value) else str(value)


def _number(value: Any) -> float | None:
    if _is_blank(value):
        return None
    converted = float(value)
    return converted if np.isfinite(converted) else None


def _ticket(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None and number > 0 else None


def _base_row(record: dict[str, Any], now_text: str) -> dict[str, Any]:
    decision = pd.Timestamp(record["decision_time"])
    horizon = decision + pd.Timedelta(hours=int(record["horizon_hours"]))
    return {
        "candidate_key": str(record["candidate_key"]),
        "candidate_id": str(record["candidate_id"]),
        "comp": str(record["comp"]),
        "direction": str(record["direction"]),
        "decision_time": decision.strftime("%Y-%m-%d %H:%M:%S"),
        "horizon_end_time": horizon.strftime("%Y-%m-%d %H:%M:%S"),
        "execution_status": "PENDING",
        "trade_state": "NOT_SENT",
        "live_result": "",
        "requested_at": now_text,
        "last_checked_at": now_text,
        "magic": "",
        "comment": "",
        "symbol": "",
        "volume": "",
        "order_ticket": "",
        "deal_ticket": "",
        "position_ticket": "",
        "fill_price": "",
        "stop_price": "",
        "target_price": "",
        "retcode": "",
        "message": "",
        "closed_at": "",
        "net_profit": "",
        "entry_discord_sent_at": "",
        "exit_discord_sent_at": "",
    }


def _apply_order_result(row: dict[str, Any], result: OrderResult) -> None:
    row.update(
        {
            "execution_status": result.status,
            "trade_state": (
                "OPEN"
                if result.status in {"ORDER_FILLED", "ORDER_RECOVERED_OPEN"}
                else "CLOSED"
                if result.status == "ORDER_RECOVERED_HISTORY"
                else "NOT_SENT"
            ),
            "magic": result.magic,
            "comment": result.comment,
            "symbol": result.symbol,
            "volume": json_value(result.volume),
            "order_ticket": json_value(result.order_ticket),
            "deal_ticket": json_value(result.deal_ticket),
            "position_ticket": json_value(result.position_ticket),
            "fill_price": json_value(result.fill_price),
            "stop_price": json_value(result.stop_price),
            "target_price": json_value(result.target_price),
            "retcode": json_value(result.retcode),
            "message": result.message,
        }
    )


def _historical_ready(summary: WinRateSummary) -> bool:
    return summary.available and summary.win_rate is not None and summary.trades > 0


def _format_price(value: Any) -> str:
    number = _number(value)
    return "N/A" if number is None else f"{number:.3f}"


def _format_entry_message(
    row: pd.Series | dict[str, Any],
    historical: WinRateSummary,
    live: WinRateSummary,
) -> str:
    direction = _text(row["direction"])
    icon = "🟢" if direction == "LONG" else "🔴"
    status = _text(row["execution_status"])
    lines = [
        f"{icon} **GML1 XAUUSD 候補 / {status}**",
        f"軸: `{_text(row['comp'])}`",
        f"候補: `{_text(row['candidate_id'])}`",
        f"方向: **{direction}**",
        f"判定時刻（MT5 server）: `{_text(row['decision_time'])}`",
        f"発注状態: **{status}**",
    ]
    volume = _number(row.get("volume") if isinstance(row, dict) else row["volume"])
    if volume is not None:
        lines.append(f"ロット: `{volume:g}`")
    if status in {"ORDER_FILLED", "ORDER_RECOVERED_OPEN", "DRY_RUN"}:
        lines.extend(
            [
                f"約定/予定価格: `{_format_price(row['fill_price'])}`",
                f"SL: `{_format_price(row['stop_price'])}`",
                f"TP: `{_format_price(row['target_price'])}`",
            ]
        )
    lines.extend(
        [
            f"過去自動売買WR: **{historical.display()}**",
            f"実運用WR: **{live.display()}**",
            f"注記: `{_text(row['message'])[:300] or 'none'}`",
        ]
    )
    return "\n".join(lines)


def _format_exit_message(
    row: pd.Series | dict[str, Any],
    historical: WinRateSummary,
    live: WinRateSummary,
) -> str:
    result = _text(row["live_result"])
    icon = "✅" if result == "WIN" else "➖" if result == "BREAKEVEN" else "❌"
    net = _number(row["net_profit"])
    net_text = "N/A" if net is None else f"{net:.2f}"
    return "\n".join(
        [
            f"{icon} **GML1 XAUUSD 決済 / {result or 'CLOSED'}**",
            f"軸: `{_text(row['comp'])}`",
            f"候補: `{_text(row['candidate_id'])}`",
            f"判定時刻（MT5 server）: `{_text(row['decision_time'])}`",
            f"決済時刻: `{_text(row['closed_at']) or 'unknown'}`",
            f"実損益（口座通貨）: **{net_text}**",
            f"過去自動売買WR: **{historical.display()}**",
            f"実運用WR（更新後）: **{live.display()}**",
        ]
    )


def _append_rows(ledger: pd.DataFrame, rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return ledger
    addition = pd.DataFrame(rows, columns=LEDGER_COLUMNS)
    combined = addition if ledger.empty else pd.concat([ledger, addition], ignore_index=True)
    if combined["candidate_key"].duplicated().any():
        raise ExecutionCycleError(
            "execution cycle would create duplicate candidate keys"
        )
    return (
        combined[LEDGER_COLUMNS]
        .sort_values(
            ["decision_time", "comp", "candidate_key"], kind="mergesort"
        )
        .reset_index(drop=True)
    )


def _active_real_rows(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return ledger
    return ledger[
        ledger["trade_state"].eq("OPEN")
        & ledger["execution_status"].isin(
            [
                "ORDER_FILLED",
                "ORDER_RECOVERED_OPEN",
                "TIME_EXIT_FILLED",
                "TIME_EXIT_REJECTED",
            ]
        )
    ].copy()


def _reconcile_open_orders(
    ledger: pd.DataFrame,
    client: MetaTrader5Client,
    latest_m1_close: pd.Timestamp,
    now_text: str,
) -> list[str]:
    events: list[str] = []
    for index, row in _active_real_rows(ledger).iterrows():
        ticket = _ticket(row["position_ticket"])
        if ticket is None:
            ledger.loc[index, "execution_status"] = "MT5_ERROR"
            ledger.loc[index, "message"] = "open ledger row has no position ticket"
            continue
        position = client.get_position(ticket)
        horizon = pd.Timestamp(row["horizon_end_time"])
        if position is not None and latest_m1_close >= horizon:
            try:
                result = client.close_position(
                    ticket,
                    comment=_text(row["comment"]),
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
                ledger.loc[index, "trade_state"] = "CLOSED"
                ledger.loc[index, "net_profit"] = net
                ledger.loc[index, "live_result"] = (
                    "WIN" if net > 0 else "LOSS" if net < 0 else "BREAKEVEN"
                )
                ledger.loc[index, "closed_at"] = (
                    closed_at.strftime("%Y-%m-%d %H:%M:%S")
                    if closed_at
                    else now_text
                )
                if _text(ledger.loc[index, "execution_status"]) not in {
                    "TIME_EXIT_FILLED",
                    "ORDER_RECOVERED_HISTORY",
                }:
                    ledger.loc[
                        index, "execution_status"
                    ] = "CLOSED_BY_SL_TP_OR_MANUAL"
                events.append(f"{row['candidate_key']}:CLOSED")
        ledger.loc[index, "last_checked_at"] = now_text
    return events


def _make_client(
    settings: RuntimeSettings,
    client_factory: Callable[[RuntimeSettings], MetaTrader5Client] | None,
) -> MetaTrader5Client:
    return (client_factory or MetaTrader5Client)(settings)


def process_execution_cycle(
    *,
    live_dir: Path,
    output_dir: Path,
    registry: pd.DataFrame,
    latest_m1_close: pd.Timestamp,
    now_text: str,
    repo_root: Path,
    client_factory: Callable[[RuntimeSettings], MetaTrader5Client] | None = None,
    webhook_sender: Callable[..., Any] = send_webhook,
) -> dict[str, Any]:
    ledger_path = output_dir / "live_execution_ledger.csv"
    state_path = output_dir / "live_execution_state.json"
    client_context: MetaTrader5Client | None = None
    try:
        settings = load_runtime_settings(live_dir, repo_root)
        requested = settings.discord_enabled or settings.mt5_enabled
        if not requested:
            return {
                "status": "DISABLED",
                "controls": settings.controls(),
                "new_execution_rows": 0,
                "open_live_orders": 0,
            }

        ledger = _load_ledger(ledger_path)
        historical = load_historical_win_rates(
            settings.historical_results_dir, SLEEVES
        )

        if not state_path.is_file():
            initial_rows: list[dict[str, Any]] = []
            already_recorded = (
                set(ledger["candidate_key"].astype(str))
                if not ledger.empty
                else set()
            )
            for record in registry.to_dict(orient="records"):
                if str(record["candidate_key"]) in already_recorded:
                    continue
                row = _base_row(record, now_text)
                row["execution_status"] = "INITIALIZED_NO_BACKFILL"
                row[
                    "message"
                ] = "existing candidate registered without order or notification"
                row["entry_discord_sent_at"] = "INITIALIZATION_NO_BACKFILL"
                row["exit_discord_sent_at"] = "INITIALIZATION_NO_BACKFILL"
                initial_rows.append(row)
            ledger = _append_rows(ledger, initial_rows)
            atomic_write_csv(ledger_path, ledger)
            atomic_write_text(
                state_path,
                json.dumps(
                    {
                        "schema_version": 1,
                        "initialized_at": now_text,
                        "initial_candidate_count": int(len(registry)),
                        "no_backfill": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            return {
                "status": "EXECUTION_INITIALIZED_NO_BACKFILL",
                "controls": settings.controls(),
                "config_errors": list(settings.config_errors),
                "new_execution_rows": int(len(initial_rows)),
                "open_live_orders": 0,
            }

        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("schema_version") != 1 or state.get("no_backfill") is not True:
            raise ExecutionCycleError(
                "unsupported or unsafe live_execution_state.json"
            )

        active_rows = _active_real_rows(ledger)
        if not settings.mt5_symbol and not active_rows.empty:
            symbols = sorted(
                {
                    _text(value)
                    for value in active_rows["symbol"].tolist()
                    if _text(value)
                }
            )
            if len(symbols) == 1:
                settings = replace(settings, mt5_symbol=symbols[0])
            elif len(symbols) > 1:
                raise ExecutionCycleError(
                    "open execution ledger rows contain multiple MT5 symbols"
                )

        client_error: str | None = None
        need_client = settings.real_orders_armed or not active_rows.empty
        if need_client:
            try:
                client_context = _make_client(settings, client_factory)
                client_context.__enter__()
            except (MT5ExecutionError, ModuleNotFoundError, ImportError) as exc:
                client_context = None
                client_error = str(exc)

        reconciliation_events: list[str] = []
        if client_context is not None:
            reconciliation_events = _reconcile_open_orders(
                ledger, client_context, pd.Timestamp(latest_m1_close), now_text
            )

        existing_keys = (
            set(ledger["candidate_key"].astype(str)) if not ledger.empty else set()
        )
        pending = registry[
            ~registry["candidate_key"].astype(str).isin(existing_keys)
        ].copy()
        pending = pending.sort_values(
            ["first_seen_at", "decision_time", "comp"], kind="mergesort"
        )
        new_rows: list[dict[str, Any]] = []
        for record in pending.to_dict(orient="records"):
            row = _base_row(record, now_text)
            comp = row["comp"]
            hist = historical[comp]
            decision = pd.Timestamp(row["decision_time"])
            lag_seconds = float(
                (pd.Timestamp(latest_m1_close) - decision).total_seconds()
            )
            volume = settings.volumes.get(comp)
            row["symbol"] = settings.mt5_symbol or ""
            row["volume"] = json_value(volume)

            if settings.config_errors:
                row["execution_status"] = "CONFIG_ERROR"
                row["message"] = "; ".join(settings.config_errors)
            elif _text(record.get("position_state")) != "OPEN":
                row["execution_status"] = "SKIPPED_NOT_OPEN"
                row[
                    "message"
                ] = "candidate was already resolved when the live adapter observed it"
            elif lag_seconds < 0:
                row["execution_status"] = "SKIPPED_FUTURE_TIME"
                row[
                    "message"
                ] = f"decision time is {abs(lag_seconds):.0f}s ahead of latest closed M1"
            elif lag_seconds > settings.mt5_max_entry_lag_seconds:
                row["execution_status"] = "SKIPPED_STALE"
                row["message"] = (
                    f"entry lag {lag_seconds:.0f}s exceeds limit "
                    f"{settings.mt5_max_entry_lag_seconds}s"
                )
            elif not settings.mt5_enabled:
                row["execution_status"] = "SIGNAL_ONLY"
                row[
                    "message"
                ] = "Discord notification only; MT5 execution is disabled"
            elif settings.require_historical_win_rate and not _historical_ready(hist):
                row["execution_status"] = "SKIPPED_WIN_RATE_UNAVAILABLE"
                row["message"] = (
                    hist.reason or "historical win-rate profile unavailable"
                )
            elif settings.mt5_dry_run:
                row["execution_status"] = "DRY_RUN"
                row["message"] = "MT5 dry-run; no order was sent"
                current_price = _number(record.get("current_price"))
                planned_price = (
                    current_price
                    if current_price is not None
                    else _number(record.get("entry_price"))
                )
                row["fill_price"] = json_value(planned_price)
                row["stop_price"] = json_value(record.get("stop_price"))
                row["target_price"] = json_value(record.get("target_price"))
            elif client_context is None:
                row["execution_status"] = "MT5_ERROR"
                row["message"] = client_error or "MT5 client unavailable"
            else:
                magic = client_context.magic(comp)
                comment = client_context.comment(row["candidate_key"], comp)
                recovered = client_context.recover_existing(
                    magic=magic, comment=comment
                )
                if recovered is not None:
                    _apply_order_result(row, recovered)
                    if (
                        recovered.status == "ORDER_RECOVERED_HISTORY"
                        and recovered.position_ticket
                    ):
                        closed = client_context.closed_position_profit(
                            recovered.position_ticket
                        )
                        if closed is not None:
                            net, closed_at = closed
                            row["trade_state"] = "CLOSED"
                            row["net_profit"] = net
                            row["live_result"] = (
                                "WIN"
                                if net > 0
                                else "LOSS"
                                if net < 0
                                else "BREAKEVEN"
                            )
                            row["closed_at"] = (
                                closed_at.strftime("%Y-%m-%d %H:%M:%S")
                                if closed_at
                                else now_text
                            )
                else:
                    positions = client_context.gml1_positions()
                    if len(positions) >= settings.mt5_max_total_positions:
                        row["execution_status"] = "SKIPPED_POSITION_LIMIT"
                        row["magic"] = magic
                        row["comment"] = comment
                        row["message"] = (
                            f"GML1 open position count {len(positions)} reached limit "
                            f"{settings.mt5_max_total_positions}"
                        )
                    elif any(
                        int(getattr(position, "magic", -1)) == magic
                        for position in positions
                    ):
                        row[
                            "execution_status"
                        ] = "SKIPPED_SLEEVE_POSITION_OPEN"
                        row["magic"] = magic
                        row["comment"] = comment
                        row[
                            "message"
                        ] = "one-position-per-sleeve guard blocked the order"
                    else:
                        try:
                            result = client_context.open_market_order(
                                record, float(volume)
                            )
                            _apply_order_result(row, result)
                        except MT5ExecutionError as exc:
                            row["execution_status"] = "MT5_ERROR"
                            row["magic"] = magic
                            row["comment"] = comment
                            row["message"] = str(exc)

            if not settings.discord_enabled:
                row["entry_discord_sent_at"] = "DISCORD_DISABLED_AT_EVENT"
            new_rows.append(row)

        ledger = _append_rows(ledger, new_rows)
        live_rates = load_live_win_rates(ledger, SLEEVES)
        discord_errors: list[str] = []
        if settings.discord_enabled and settings.discord_webhook_url:
            for index, row in ledger.iterrows():
                if row["execution_status"] == "INITIALIZED_NO_BACKFILL":
                    continue
                if _is_blank(row["entry_discord_sent_at"]):
                    comp = _text(row["comp"])
                    try:
                        webhook_sender(
                            settings.discord_webhook_url,
                            content=_format_entry_message(
                                row, historical[comp], live_rates[comp]
                            ),
                            username=settings.discord_username,
                        )
                        ledger.loc[index, "entry_discord_sent_at"] = now_text
                    except (DiscordError, OSError, ValueError) as exc:
                        discord_errors.append(f"entry {row['candidate_key']}: {exc}")
                if row["trade_state"] == "CLOSED" and _is_blank(
                    row["exit_discord_sent_at"]
                ):
                    live_rates = load_live_win_rates(ledger, SLEEVES)
                    comp = _text(row["comp"])
                    try:
                        webhook_sender(
                            settings.discord_webhook_url,
                            content=_format_exit_message(
                                row, historical[comp], live_rates[comp]
                            ),
                            username=settings.discord_username,
                        )
                        ledger.loc[index, "exit_discord_sent_at"] = now_text
                    except (DiscordError, OSError, ValueError) as exc:
                        discord_errors.append(f"exit {row['candidate_key']}: {exc}")

        atomic_write_csv(ledger_path, ledger)
        if client_context is not None:
            client_context.__exit__(None, None, None)
            client_context = None

        status = "PASS"
        if settings.config_errors or client_error or discord_errors:
            status = "PASS_WITH_EXECUTION_WARNINGS"
        return {
            "status": status,
            "controls": settings.controls(),
            "config_errors": list(settings.config_errors),
            "mt5_error": client_error,
            "discord_errors": discord_errors,
            "new_execution_rows": int(len(new_rows)),
            "new_execution_statuses": {
                status_name: int(
                    sum(row["execution_status"] == status_name for row in new_rows)
                )
                for status_name in sorted(
                    {row["execution_status"] for row in new_rows}
                )
            },
            "reconciliation_events": reconciliation_events,
            "open_live_orders": int(len(_active_real_rows(ledger))),
            "historical_win_rate": {
                comp: {
                    "available": historical[comp].available,
                    "trades": historical[comp].trades,
                    "wins": historical[comp].wins,
                    "win_rate": historical[comp].win_rate,
                    "reason": historical[comp].reason,
                }
                for comp in SLEEVES
            },
        }
    except Exception as exc:
        return {
            "status": "EXECUTION_CYCLE_ERROR",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "new_execution_rows": 0,
        }
    finally:
        if client_context is not None:
            try:
                client_context.__exit__(None, None, None)
            except Exception:
                pass
