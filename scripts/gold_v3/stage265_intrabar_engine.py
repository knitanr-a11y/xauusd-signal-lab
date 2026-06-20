from __future__ import annotations

import numpy as np
import pandas as pd


def source_for_time(t: pd.Timestamp) -> str | None:
    if pd.Timestamp("2025-01-02 08:00") <= t <= pd.Timestamp("2025-12-31 19:59"):
        return "GOLD_HASH_2025"
    if pd.Timestamp("2026-01-13 03:52") <= t <= pd.Timestamp("2026-06-19 19:53"):
        return "GOLDSHARP_2026"
    return None


def expected_minutes(start: pd.Timestamp, end_exclusive: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(start, end_exclusive - pd.Timedelta(minutes=1), freq="min")


def simulate(candidates: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    """Replay pre-created pending orders one minute at a time.

    Candidate rows must already contain entry-known values only:
    decision_time, order_expiry, direction, order_stop, atr14,
    hold_minutes, sl_mult and tp_mult.
    """
    books = {
        source: frame.set_index("time").sort_index()
        for source, frame in m1.groupby("source_id")
    }
    rows: list[dict] = []
    active_until = pd.Timestamp.min
    pending_until = pd.Timestamp.min

    for _, candidate in candidates.loc[candidates["candidate"]].sort_values("decision_time").iterrows():
        result = candidate.to_dict()
        decision_time = pd.Timestamp(candidate["decision_time"])
        expiry = pd.Timestamp(candidate["order_expiry"])
        source = source_for_time(decision_time)
        result.update(
            status=None,
            execution_source_id=source,
            fill_bar_time=pd.NaT,
            fill_price=np.nan,
            exit_time=pd.NaT,
            exit_price=np.nan,
            exit_reason=None,
            gross_pnl=np.nan,
            cost2_pnl=np.nan,
            cost5_pnl=np.nan,
            gap_fill=False,
            missing_order_minutes=0,
            missing_exit_minutes=0,
        )

        if decision_time < active_until:
            result["status"] = "ONE_ACTIVE_SUPPRESSED"
            rows.append(result)
            continue
        if decision_time < pending_until:
            result["status"] = "PENDING_ORDER_SUPPRESSED"
            rows.append(result)
            continue
        if source is None or source not in books:
            result["status"] = "NO_EXECUTION_SOURCE"
            rows.append(result)
            continue

        book = books[source]
        pending_until = expiry
        direction = str(candidate["direction"])
        stop = float(candidate["order_stop"])
        trigger_time = None
        fill_price = None
        gap_fill = False

        for minute in expected_minutes(decision_time, expiry):
            if source_for_time(minute) != source or minute not in book.index:
                result["status"] = "ORDER_STREAM_GAP_BEFORE_TRIGGER"
                result["missing_order_minutes"] = 1
                break
            bar = book.loc[minute]
            if direction == "LONG":
                if float(bar["open"]) >= stop:
                    trigger_time = minute
                    fill_price = float(bar["open"])
                    gap_fill = True
                    break
                if float(bar["high"]) >= stop:
                    trigger_time = minute
                    fill_price = stop
                    break
            else:
                if float(bar["open"]) <= stop:
                    trigger_time = minute
                    fill_price = float(bar["open"])
                    gap_fill = True
                    break
                if float(bar["low"]) <= stop:
                    trigger_time = minute
                    fill_price = stop
                    break

        if result["status"] == "ORDER_STREAM_GAP_BEFORE_TRIGGER":
            rows.append(result)
            continue
        if trigger_time is None:
            result["status"] = "EXPIRED"
            rows.append(result)
            continue

        result.update(
            fill_bar_time=trigger_time,
            fill_price=fill_price,
            gap_fill=gap_fill,
        )
        time_exit = trigger_time + pd.Timedelta(minutes=int(candidate["hold_minutes"]))
        if time_exit.date() != trigger_time.date() or time_exit.time() > pd.Timestamp("20:00").time():
            result["status"] = "SESSION_WINDOW_BLOCKED_AT_TRIGGER"
            rows.append(result)
            continue
        if source_for_time(time_exit) != source:
            result["status"] = "EXIT_SOURCE_BOUNDARY_BLOCKED"
            rows.append(result)
            continue

        atr = float(candidate["atr14"])
        if direction == "LONG":
            sl_price = fill_price - float(candidate["sl_mult"]) * atr
            tp_price = fill_price + float(candidate["tp_mult"]) * atr
        else:
            sl_price = fill_price + float(candidate["sl_mult"]) * atr
            tp_price = fill_price - float(candidate["tp_mult"]) * atr
        result.update(sl_price=sl_price, tp_price=tp_price)

        exit_reason = None
        exit_bar_time = None
        exit_price = None
        same_bar_tp_sl = False
        stream_gap = False

        for minute in expected_minutes(trigger_time, time_exit):
            if source_for_time(minute) != source or minute not in book.index:
                result["status"] = "EXIT_STREAM_GAP_AFTER_ENTRY"
                result["missing_exit_minutes"] = 1
                active_until = time_exit
                stream_gap = True
                break
            bar = book.loc[minute]
            if direction == "LONG":
                hit_sl = float(bar["low"]) <= sl_price
                hit_tp = float(bar["high"]) >= tp_price
            else:
                hit_sl = float(bar["high"]) >= sl_price
                hit_tp = float(bar["low"]) <= tp_price
            if hit_sl:
                exit_reason = "SL_EXIT"
                exit_bar_time = minute
                exit_price = sl_price
                same_bar_tp_sl = bool(hit_tp)
                break
            if hit_tp:
                exit_reason = "TP_EXIT"
                exit_bar_time = minute
                exit_price = tp_price
                break

        if stream_gap:
            rows.append(result)
            continue
        if exit_reason is None:
            if time_exit not in book.index:
                result["status"] = "EXIT_STREAM_GAP_AFTER_ENTRY"
                result["missing_exit_minutes"] = 1
                active_until = time_exit
                rows.append(result)
                continue
            exit_reason = "TIME_EXIT"
            exit_bar_time = time_exit
            exit_price = float(book.loc[time_exit, "open"])

        gross_pnl = (
            exit_price - fill_price
            if direction == "LONG"
            else fill_price - exit_price
        )
        result.update(
            status="RESOLVED",
            exit_time=exit_bar_time,
            exit_price=exit_price,
            exit_reason=exit_reason,
            same_bar_tp_sl=same_bar_tp_sl,
            gross_pnl=gross_pnl,
            cost2_pnl=gross_pnl - 2.0,
            cost5_pnl=gross_pnl - 5.0,
        )
        active_until = exit_bar_time + (
            pd.Timedelta(minutes=1) if exit_reason != "TIME_EXIT" else pd.Timedelta(0)
        )
        rows.append(result)

    return pd.DataFrame(rows)
