from __future__ import annotations

import bisect
from datetime import datetime, timedelta
from typing import Any

import frozen_core as c

M5_ENTRY_OFFSET_ATR = 0.15
M5_ENTRY_WAIT_MINUTES = 6
H1_ENTRY_OFFSET_ATR = 0.05
H1_ENTRY_WAIT_MINUTES = 30
H4_ENTRY_OFFSET_ATR = 0.00
H4_ENTRY_WAIT_MINUTES = 60


def wilder_atr14(bars: list[c.Bar]) -> list[float | None]:
    tr: list[float] = []
    for index, bar in enumerate(bars):
        value = bar.high - bar.low if index == 0 else max(bar.high - bar.low, abs(bar.high - bars[index - 1].close), abs(bar.low - bars[index - 1].close))
        tr.append(value)
    output: list[float | None] = [None] * len(bars)
    if len(bars) >= 14:
        output[13] = sum(tr[:14]) / 14.0
        for index in range(14, len(bars)):
            previous = output[index - 1]
            assert previous is not None
            output[index] = ((13.0 * previous) + tr[index]) / 14.0
    return output


def metric_rows(rows: list[dict[str, Any]], *, value_key: str, time_key: str, extra_cost_bps: float = 0.0) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: c.parse_time(str(row[time_key])))
    return c.metrics_from_values([float(row[value_key]) - extra_cost_bps for row in ordered])


def group_metrics(rows: list[dict[str, Any]], *, value_key: str, time_key: str, mode: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        current = c.parse_time(str(row[time_key]))
        label = str(current.year) if mode == "year" else (f"{current.year}Q{(current.month - 1) // 3 + 1}" if mode == "quarter" else f"{current.year}-{current.month:02d}")
        groups.setdefault(label, []).append(row)
    return [{mode: label, **metric_rows(group, value_key=value_key, time_key=time_key)} for label, group in sorted(groups.items())]


def build_m5_reclaim(rows: list[dict[str, Any]], m1: list[c.Bar], m5: list[c.Bar], *, point: float) -> list[dict[str, Any]]:
    m1_index = {bar.time: i for i, bar in enumerate(m1)}
    m5_close_times = [bar.time + timedelta(minutes=5) for bar in m5]
    atr5 = wilder_atr14(m5)
    output: list[dict[str, Any]] = []
    for row in rows:
        proxy_time, first_time, exit_time = c.parse_time(str(row["proxy_entry_time"])), c.parse_time(str(row["turn_entry_time"])), c.parse_time(str(row["exit_time"]))
        proxy_index, first_index, exit_index = m1_index.get(proxy_time), m1_index.get(first_time), m1_index.get(exit_time)
        if proxy_index is None or first_index is None or exit_index is None or exit_index <= first_index:
            continue
        i5 = bisect.bisect_right(m5_close_times, first_time) - 1
        if i5 < 0 or atr5[i5] is None or float(atr5[i5]) <= 0:
            continue
        atr_value, primary_bid = float(atr5[i5]), m1[proxy_index].open
        level = primary_bid - M5_ENTRY_OFFSET_ATR * atr_value
        actual_index: int | None = first_index if m1[first_index].open >= level else None
        if actual_index is None:
            last_check_exclusive = min(exit_index - 1, first_index + M5_ENTRY_WAIT_MINUTES)
            for closed_index in range(first_index, last_check_exclusive):
                if m1[closed_index].close >= level:
                    candidate = closed_index + 1
                    if candidate < exit_index and candidate <= first_index + M5_ENTRY_WAIT_MINUTES:
                        actual_index = candidate
                    break
        if actual_index is None:
            continue
        actual_time = m1[actual_index].time
        entry_exec = m1[actual_index].open + m1[actual_index].spread * point
        native_return = (m1[exit_index].open - entry_exec) / abs(entry_exec) * 10000.0
        output.append({**row, "actual_entry_time": actual_time.strftime(c.TIME_FORMAT), "entry_delay_minutes": actual_index - first_index, "primary_bid": primary_bid, "atr_at_first_turn": atr_value, "reclaim_level": level, "reclaim_offset_atr": M5_ENTRY_OFFSET_ATR, "wait_minutes": M5_ENTRY_WAIT_MINUTES, "entry_exec": entry_exec, "native_return_bps": native_return})
    return output


def build_htf_reclaim(rows: list[dict[str, Any]], m1: list[c.Bar], signal_bars: list[c.Bar], confirm_bars: list[c.Bar], *, signal_delta: timedelta, confirm_delta: timedelta, offset_atr: float, wait_minutes: int, point: float, confirm_name: str) -> list[dict[str, Any]]:
    m1_index = {bar.time: i for i, bar in enumerate(m1)}
    signal_close_times = [bar.time + signal_delta for bar in signal_bars]
    confirm_close_times = [bar.time + confirm_delta for bar in confirm_bars]
    atr_values = wilder_atr14(signal_bars)
    output: list[dict[str, Any]] = []
    for row in rows:
        proxy_time, first_time, exit_time = c.parse_time(str(row["proxy_entry_time"])), c.parse_time(str(row["turn_entry_time"])), c.parse_time(str(row["exit_time"]))
        proxy_index, first_index, exit_index = m1_index.get(proxy_time), m1_index.get(first_time), m1_index.get(exit_time)
        if proxy_index is None or first_index is None or exit_index is None or exit_index <= first_index:
            continue
        signal_index = bisect.bisect_right(signal_close_times, first_time) - 1
        if signal_index < 0 or atr_values[signal_index] is None or float(atr_values[signal_index]) <= 0:
            continue
        atr_value, primary_bid = float(atr_values[signal_index]), m1[proxy_index].open
        level = primary_bid - offset_atr * atr_value
        confirm_index = bisect.bisect_right(confirm_close_times, first_time) - 1
        actual_time: datetime | None = first_time if confirm_index >= 0 and confirm_bars[confirm_index].close >= level else None
        if actual_time is None:
            deadline = first_time + timedelta(minutes=wait_minutes)
            next_index = confirm_index + 1
            while next_index < len(confirm_bars):
                close_time = confirm_close_times[next_index]
                if close_time > deadline or close_time >= exit_time:
                    break
                if confirm_bars[next_index].close >= level:
                    actual_time = close_time
                    break
                next_index += 1
        if actual_time is None or actual_time >= exit_time:
            continue
        actual_index = m1_index.get(actual_time)
        if actual_index is None or actual_index >= exit_index:
            continue
        entry_exec = m1[actual_index].open + m1[actual_index].spread * point
        native_return = (m1[exit_index].open - entry_exec) / abs(entry_exec) * 10000.0
        output.append({**row, "actual_entry_time": actual_time.strftime(c.TIME_FORMAT), "entry_delay_minutes": int((actual_time - first_time).total_seconds() // 60), "primary_bid": primary_bid, "atr_at_first_turn": atr_value, "reclaim_level": level, "reclaim_offset_atr": offset_atr, "wait_minutes": wait_minutes, "confirm_timeframe": confirm_name, "entry_exec": entry_exec, "native_return_bps": native_return})
    return output


def macd_line(bars: list[c.Bar]) -> list[float]:
    closes = [bar.close for bar in bars]
    fast, slow = c.ema(closes, 6), c.ema(closes, 13)
    return [a - b for a, b in zip(fast, slow)]


def rci_turn_down_decision_times(bars: list[c.Bar]) -> list[datetime]:
    rci9 = c.rci_series([bar.close for bar in bars], 9)
    output: list[datetime] = []
    for current_index in range(50, len(bars)):
        selected = current_index - 1
        current, previous, previous2 = rci9[selected], rci9[selected - 1], rci9[selected - 2]
        if current is not None and previous is not None and previous2 is not None and current < previous and previous >= previous2:
            output.append(bars[current_index].time)
    return output


def build_runner_meta(entry_rows: list[dict[str, Any]], m1: list[c.Bar], runner_bars: list[c.Bar], *, context_bars: tuple[list[c.Bar], ...], context_deltas: tuple[timedelta, ...]) -> list[dict[str, Any]]:
    m1_index = {bar.time: i for i, bar in enumerate(m1)}
    runner_times = rci_turn_down_decision_times(runner_bars)
    context_close_times = [[bar.time + delta for bar in bars] for bars, delta in zip(context_bars, context_deltas)]
    context_macd = [macd_line(bars) for bars in context_bars]
    output: list[dict[str, Any]] = []
    for row in entry_rows:
        native_exit_time = c.parse_time(str(row["exit_time"]))
        flags: list[bool] = []
        for close_times, macd_values in zip(context_close_times, context_macd):
            index = bisect.bisect_right(close_times, native_exit_time) - 1
            flags.append(index > 0 and macd_values[index] > macd_values[index - 1])
        position = bisect.bisect_left(runner_times, native_exit_time)
        runner_exit_time: datetime | None = None
        runner_return = float(row["native_return_bps"])
        if position < len(runner_times):
            candidate_time = runner_times[position]
            candidate_index = m1_index.get(candidate_time)
            if candidate_index is not None:
                runner_exit_time = candidate_time
                runner_return = (m1[candidate_index].open - float(row["entry_exec"])) / abs(float(row["entry_exec"])) * 10000.0
        output.append({**row, "runner_eligible": all(flags), "runner_context_flags": "|".join("1" if flag else "0" for flag in flags), "runner_exit_time": None if runner_exit_time is None else runner_exit_time.strftime(c.TIME_FORMAT), "runner_return_bps": runner_return})
    return output


def one_position_runner(rows: list[dict[str, Any]], *, runner_share: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: c.parse_time(str(row["actual_entry_time"])))
    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    active_until: datetime | None = None
    for row in ordered:
        entry_time = c.parse_time(str(row["actual_entry_time"]))
        if active_until is not None and entry_time < active_until:
            skipped.append(dict(row))
            continue
        runner_exit_raw = row.get("runner_exit_time")
        runner_exit = None if runner_exit_raw in (None, "") else c.parse_time(str(runner_exit_raw))
        use_runner = bool(row["runner_eligible"]) and runner_exit is not None
        if use_runner:
            active_until = runner_exit
            weighted_return = (1.0 - runner_share) * float(row["native_return_bps"]) + runner_share * float(row["runner_return_bps"])
        else:
            active_until = c.parse_time(str(row["exit_time"]))
            weighted_return = float(row["native_return_bps"])
        accepted.append({**row, "runner_used": use_runner, "runner_share": runner_share, "weighted_return_bps": weighted_return, "active_until": active_until.strftime(c.TIME_FORMAT)})
    return accepted, skipped
