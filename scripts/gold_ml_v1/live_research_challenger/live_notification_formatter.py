from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from live_win_rate import WinRateSummary

DISCORD_CONTENT_LIMIT = 2000

STRATEGY_NAMES = {
    "A_CORE": "4時間足環境＋15分足コア",
    "B_STATE": "日足環境＋1時間足ブレイク／再エントリー",
    "P18": "15分足スクイーズ上抜け",
    "W024A": "高ボラ反転ショート",
}

DIRECTION_NAMES = {"LONG": "買い", "SHORT": "売り"}
DIRECTION_TITLES = {"LONG": "LONG", "SHORT": "SELL"}

EXECUTION_STATUS_NAMES = {
    "PENDING": "処理待ち",
    "ORDER_FILLED": "約定済み",
    "ORDER_RECOVERED_OPEN": "保有ポジションを復旧",
    "ORDER_RECOVERED_HISTORY": "決済済み注文を復旧",
    "DRY_RUN": "テスト実行（注文なし）",
    "SIGNAL_ONLY": "通知のみ（注文なし）",
    "CONFIG_ERROR": "設定エラー",
    "MT5_ERROR": "MT5処理エラー",
    "SKIPPED_NOT_OPEN": "検出時点で終了済みのため見送り",
    "SKIPPED_FUTURE_TIME": "時刻不整合のため見送り",
    "SKIPPED_STALE": "検出遅延のため見送り",
    "SKIPPED_WIN_RATE_UNAVAILABLE": "成績情報不足のため見送り",
    "SKIPPED_POSITION_LIMIT": "同時保有上限のため見送り",
    "SKIPPED_SLEEVE_POSITION_OPEN": "同一戦略を保有中のため見送り",
    "INITIALIZED_NO_BACKFILL": "初期登録（過去注文なし）",
    "TIME_EXIT_FILLED": "保有期限による決済注文を受付",
    "TIME_EXIT_REJECTED": "保有期限による決済に失敗",
    "CLOSED_BY_SL_TP_OR_MANUAL": "決済済み",
}

CLOSE_REASON_NAMES = {
    "SL": "損切り",
    "STOP_LOSS": "損切り",
    "TP": "利益確定",
    "TAKE_PROFIT": "利益確定",
    "TIME": "保有期限による決済",
    "TIME_EXIT": "保有期限による決済",
    "MANUAL": "手動決済",
    "CLIENT": "手動決済",
    "MOBILE": "手動決済",
    "WEB": "手動決済",
    "EXPERT": "システムによる決済",
    "UNKNOWN": "SL・TP・手動決済のいずれか",
}


def _value(row: pd.Series | Mapping[str, Any], key: str) -> Any:
    if isinstance(row, pd.Series):
        return row.get(key, "")
    return row.get(key, "")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return str(value).strip()


def _number(value: Any) -> float | None:
    text = _text(value)
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _price(value: Any) -> str | None:
    number = _number(value)
    return None if number is None else f"{number:,.3f}"


def _strategy_name(row: pd.Series | Mapping[str, Any]) -> str:
    explicit = _text(_value(row, "strategy_name"))
    if explicit:
        return explicit
    comp = _text(_value(row, "comp"))
    return STRATEGY_NAMES.get(comp, "GOLD自動売買戦略")


def _direction_raw(row: pd.Series | Mapping[str, Any]) -> str:
    return _text(_value(row, "direction")).upper()


def _direction(row: pd.Series | Mapping[str, Any]) -> str:
    return DIRECTION_NAMES.get(_direction_raw(row), "不明")


def _direction_title(row: pd.Series | Mapping[str, Any]) -> str:
    return DIRECTION_TITLES.get(_direction_raw(row), "UNKNOWN")


def _direction_icon(row: pd.Series | Mapping[str, Any]) -> str:
    raw = _direction_raw(row)
    return "🟢" if raw == "LONG" else "🔴" if raw == "SHORT" else "⚪"


def _live_performance(summary: WinRateSummary) -> str:
    if not summary.available or summary.win_rate is None or summary.trades <= 0:
        return "集計前（決済済み0件）"
    losses = max(int(summary.trades) - int(summary.wins), 0)
    return f"{summary.wins}勝{losses}敗 / 勝率 {summary.win_rate * 100:.2f}%"


def _time_text(value: Any) -> str:
    text = _text(value)
    return text or "不明"


def _horizon_text(row: pd.Series | Mapping[str, Any]) -> str | None:
    decision_text = _text(_value(row, "decision_time"))
    horizon_text = _text(_value(row, "horizon_end_time"))
    hours = _number(_value(row, "horizon_hours"))
    if hours is None and decision_text and horizon_text:
        decision = pd.to_datetime(decision_text, errors="coerce")
        horizon = pd.to_datetime(horizon_text, errors="coerce")
        if not pd.isna(decision) and not pd.isna(horizon):
            hours = float((horizon - decision).total_seconds() / 3600.0)
    if hours is None and not horizon_text:
        return None
    if hours is None:
        return f"{horizon_text}まで"
    hour_label = f"{hours:g}時間"
    return f"{hour_label}（{horizon_text}まで）" if horizon_text else hour_label


def _entry_title(row: pd.Series | Mapping[str, Any]) -> str:
    icon = _direction_icon(row)
    direction = _direction_title(row)
    status = _text(_value(row, "execution_status")).upper()
    if status == "ORDER_RECOVERED_OPEN":
        return f"{icon} **GOLD {direction}（復旧）**"
    if status == "ORDER_RECOVERED_HISTORY":
        return f"{icon} **GOLD {direction}（決済済み復旧）**"
    if status == "DRY_RUN":
        return f"{icon} **GOLD {direction}（テスト）**"
    if status.startswith("SKIPPED_"):
        return "⚪ **GOLD 見送り**"
    if status in {"CONFIG_ERROR", "MT5_ERROR", "TIME_EXIT_REJECTED"}:
        return "⚠️ **GOLD 注文エラー**"
    return f"{icon} **GOLD {direction}**"


def _close_reason(row: pd.Series | Mapping[str, Any]) -> tuple[str, str]:
    raw = _text(_value(row, "close_reason")).upper()
    status = _text(_value(row, "execution_status")).upper()
    if not raw and status == "TIME_EXIT_FILLED":
        raw = "TIME"
    if not raw:
        raw = "UNKNOWN"
    label = CLOSE_REASON_NAMES.get(raw, CLOSE_REASON_NAMES["UNKNOWN"])
    return raw, label


def _bounded(lines: list[str]) -> str:
    content = "\n".join(lines)
    if len(content) <= DISCORD_CONTENT_LIMIT:
        return content
    suffix = "\n\n※表示上限のため一部を省略しました。詳細は実行ログを確認してください。"
    return content[: DISCORD_CONTENT_LIMIT - len(suffix)] + suffix


def format_entry_message(
    row: pd.Series | Mapping[str, Any],
    live: WinRateSummary,
) -> str:
    status_raw = _text(_value(row, "execution_status")).upper()
    lines = [_entry_title(row)]

    fill = _price(_value(row, "fill_price"))
    stop = _price(_value(row, "stop_price"))
    target = _price(_value(row, "target_price"))
    if any(value is not None for value in (fill, target, stop)):
        lines.append("")
        if fill is not None:
            label = "予定価格" if status_raw in {"DRY_RUN", "SIGNAL_ONLY"} else "約定価格"
            lines.append(f"{label}：{fill}")
        if target is not None:
            lines.append(f"TP　　　：{target}")
        if stop is not None:
            lines.append(f"SL　　　：{stop}")

    lines.extend(
        [
            "",
            f"戦略　　：{_strategy_name(row)}",
            f"判定時刻：{_time_text(_value(row, 'decision_time'))}（MT5サーバー時刻）",
        ]
    )
    horizon = _horizon_text(row)
    if horizon:
        lines.append(f"保有期限：{horizon}")

    signal_reason = _text(_value(row, "signal_reason"))
    higher_context = _text(_value(row, "higher_timeframe_context"))
    if signal_reason or higher_context:
        lines.append("")
        if signal_reason:
            lines.append(f"検出条件：{signal_reason}")
        if higher_context:
            lines.append(f"上位環境：{higher_context}")

    lines.extend(["", f"実運用成績：{_live_performance(live)}"])
    if status_raw in {"CONFIG_ERROR", "MT5_ERROR", "TIME_EXIT_REJECTED"}:
        lines.append("確認事項：詳細は実行ログを確認してください。")
    return _bounded(lines)


def format_exit_message(
    row: pd.Series | Mapping[str, Any],
    live: WinRateSummary,
) -> str:
    _reason_raw, reason_label = _close_reason(row)
    title = (
        f"{_direction_icon(row)} **GOLD {_direction_title(row)} "
        f"決済：{reason_label}**"
    )
    lines = [title]

    fill = _price(_value(row, "fill_price"))
    close = _price(_value(row, "close_price"))
    if fill is not None or close is not None:
        lines.append("")
        if fill is not None:
            lines.append(f"約定価格：{fill}")
        if close is not None:
            lines.append(f"決済価格：{close}")

    net = _number(_value(row, "net_profit"))
    net_text = "不明" if net is None else f"{net:+,.2f}"
    lines.extend(
        [
            "",
            f"戦略　　：{_strategy_name(row)}",
            f"決済時刻：{_time_text(_value(row, 'closed_at'))}（MT5サーバー時刻）",
            f"実損益　：{net_text}（口座通貨）",
            "",
            f"実運用成績：{_live_performance(live)}",
        ]
    )
    return _bounded(lines)
