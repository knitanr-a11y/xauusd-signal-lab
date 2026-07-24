from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
POINT = 0.01
LONG_EXIT_RCI9 = 78.333333333333
SHORT_EXIT_RCI9 = -75.0
TURN_LOOKBACK = 5
EXPECTED_FILES = {
    "M1": ("gold_v3_2023_2026_m1.csv", "dec61b435ceb1df687baced57862de214793e0270e30c67d84f510f9f119b9d2"),
    "M5": ("gold_v3_2023_2026_m5.csv", "c47c0a136e8a953bf219bfbcb80a79ccacac3afb04a0ed6e825843eba143948d"),
    "M15": ("gold_v3_2023_2026_m15.csv", "e327bedd180dae6429ed658ea714bc1229fb026262124248cdd5fff38fdeaa28"),
    "H1": ("gold_v3_2023_2026_h1.csv", "fb9d4ad228c02383a14ac86309f7306a799b0ef8d076f015a72b70daaddafc4a"),
    "H4": ("gold_v3_2023_2026_h4.csv", "5cd0d4427c752bd3feffd17b91fbd1ed3cd35ee5210887fa1726f01184367913"),
    "D1": ("gold_v3_2023_2026_d1.csv", "58d9b8e6716b3dedf4d310b3de5a914ab062c50578bae54dc85a2c8fddf689f6"),
}
HEADER = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]

@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread: int


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_bars(path: Path) -> list[Bar]:
    output: list[Bar] = []
    previous: datetime | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            raise RuntimeError(f"unexpected header: {path.name}")
        for row in reader:
            current = parse_time(row["time"])
            if previous is not None and current <= previous:
                raise RuntimeError(f"timestamp not strictly ascending: {path.name} {row['time']}")
            previous = current
            output.append(Bar(current, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]), int(row["tick_volume"]), int(row["spread"])))
    if not output:
        raise RuntimeError(f"empty CSV: {path.name}")
    return output


def quantile_sorted(values: list[float], q: float) -> float:
    position = q * (len(values) - 1)
    lower, upper = int(math.floor(position)), int(math.ceil(position))
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def ema(values: list[float], period: int) -> list[float]:
    alpha = 2.0 / (period + 1.0)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1.0 - alpha) * output[-1])
    return output


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    output = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        end = cursor + 1
        while end < len(indexed) and indexed[end][1] == indexed[cursor][1]:
            end += 1
        average = ((cursor + 1) + end) / 2.0
        for position in range(cursor, end):
            output[indexed[position][0]] = average
        cursor = end
    return output


def rci_series(values: list[float], period: int) -> list[float | None]:
    output: list[float | None] = [None] * len(values)
    denominator = period * (period * period - 1)
    for index in range(period - 1, len(values)):
        ranks = average_ranks(values[index - period + 1:index + 1])
        squared = sum(((position + 1) - ranks[position]) ** 2 for position in range(period))
        output[index] = (1.0 - 6.0 * squared / denominator) * 100.0
    return output


def replay_m7c(bars: list[Bar]) -> list[dict[str, Any]]:
    closes = [bar.close for bar in bars]
    rci9 = rci_series(closes, 9)
    ema20, ema30, ema40 = ema(closes, 20), ema(closes, 30), ema(closes, 40)
    pairs: list[dict[str, Any]] = []
    state = "IDLE"
    open_primary: tuple[str, datetime] | None = None
    for current_index in range(50, len(bars)):
        selected = current_index - 1
        current, previous, previous2 = rci9[selected], rci9[selected - 1], rci9[selected - 2]
        if current is None or previous is None or previous2 is None:
            continue
        turn_up = current > previous and previous <= previous2
        turn_down = current < previous and previous >= previous2
        bullish = ema20[selected] > ema30[selected] > ema40[selected]
        bearish = ema20[selected] < ema30[selected] < ema40[selected]
        if state == "IDLE":
            if turn_up and bullish:
                state, open_primary = "ACTIVE_LONG", ("LONG", bars[current_index].time)
            elif turn_down and bearish:
                state, open_primary = "ACTIVE_SHORT", ("SHORT", bars[current_index].time)
        elif state == "ACTIVE_LONG" and current >= LONG_EXIT_RCI9:
            if open_primary is None:
                raise RuntimeError("LONG exit without primary")
            pairs.append({"direction": open_primary[0], "entry_time": open_primary[1], "exit_time": bars[current_index].time})
            state, open_primary = "IDLE", None
        elif state == "ACTIVE_SHORT" and current <= SHORT_EXIT_RCI9:
            if open_primary is None:
                raise RuntimeError("SHORT exit without primary")
            pairs.append({"direction": open_primary[0], "entry_time": open_primary[1], "exit_time": bars[current_index].time})
            state, open_primary = "IDLE", None
    return pairs


def directional_return(direction: str, entry: float, exit_price: float) -> float:
    return ((exit_price - entry) if direction == "LONG" else (entry - exit_price)) / abs(entry) * 10000.0


def build_first_turns(pairs: list[dict[str, Any]], m1: list[Bar], point: float, prefix: str) -> list[dict[str, Any]]:
    index = {bar.time: position for position, bar in enumerate(m1)}
    output: list[dict[str, Any]] = []
    for trade_number, pair in enumerate(pairs, start=1):
        if pair["entry_time"] not in index or pair["exit_time"] not in index:
            continue
        entry_index, exit_index = index[pair["entry_time"]], index[pair["exit_time"]]
        if exit_index <= entry_index:
            continue
        direction = pair["direction"]
        signal_bid = m1[entry_index].open
        exit_exec = m1[exit_index].open + m1[exit_index].spread * point if direction == "SHORT" else m1[exit_index].open
        for current_index in range(entry_index + 1, exit_index):
            if current_index + 1 >= exit_index:
                break
            history = m1[max(0, current_index - TURN_LOOKBACK):current_index]
            if len(history) < TURN_LOOKBACK:
                continue
            previous, current = m1[current_index - 1], m1[current_index]
            if direction == "LONG":
                candidate = previous.low <= min(bar.low for bar in history) and previous.low < signal_bid and current.close > previous.close
            else:
                candidate = previous.high >= max(bar.high for bar in history) and previous.high > signal_bid and current.close < previous.close
            if not candidate:
                continue
            turn_bar = m1[current_index + 1]
            entry_exec = turn_bar.open + turn_bar.spread * point if direction == "LONG" else turn_bar.open
            output.append({"trade_id": f"{prefix}_T{trade_number:06d}", "direction": direction, "proxy_entry_time": pair["entry_time"].strftime(TIME_FORMAT), "turn_entry_time": turn_bar.time.strftime(TIME_FORMAT), "exit_time": pair["exit_time"].strftime(TIME_FORMAT), "return_bps": directional_return(direction, entry_exec, exit_exec)})
            break
    return output


def m5_ratio20(m5: list[Bar]) -> list[float | None]:
    output: list[float | None] = [None] * len(m5)
    rolling_sum = 0
    for index, bar in enumerate(m5):
        rolling_sum += bar.tick_volume
        if index >= 20:
            rolling_sum -= m5[index - 20].tick_volume
        if index >= 19:
            output[index] = bar.tick_volume / (rolling_sum / 20.0)
    return output


def selected_closed_index(close_times: list[datetime], decision: datetime) -> int:
    return bisect.bisect_right(close_times, decision) - 1


def window_quantile(values: list[float | None], index: int, window: int, q: float) -> float | None:
    start = index - window + 1
    if start < 0:
        return None
    selected = values[start:index + 1]
    if len(selected) != window or any(value is None or not math.isfinite(float(value)) for value in selected):
        return None
    return quantile_sorted(sorted(float(value) for value in selected if value is not None), q)


def macd_bps(bars: list[Bar]) -> list[float]:
    closes = [bar.close for bar in bars]
    fast, slow = ema(closes, 6), ema(closes, 13)
    return [(a - b) / abs(close) * 10000.0 for a, b, close in zip(fast, slow, closes)]


def build_timeframe_turns(bars: list[Bar], m1: list[Bar], point: float, prefix: str) -> list[dict[str, Any]]:
    return build_first_turns(replay_m7c(bars), m1, point, prefix)


def enrich_indices(rows: list[dict[str, Any]], close_times: dict[str, list[datetime]], timeframes: tuple[str, ...]) -> None:
    for row in rows:
        decision = parse_time(str(row["turn_entry_time"]))
        for timeframe in timeframes:
            row[f"{timeframe.lower()}_index"] = selected_closed_index(close_times[timeframe], decision)


def select_s1(long_m5: list[dict[str, Any]], ratio20_m5: list[float | None], macd: dict[str, list[float]], rci9_h1: list[float | None]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in long_m5:
        i5, i15, ih1 = int(row["m5_index"]), int(row["m15_index"]), int(row["h1_index"])
        q_m5_volume = window_quantile(ratio20_m5, i5, 200, 0.50)
        q_m5_macd = window_quantile(macd["M5"], i5, 200, 0.75)
        own_core = (q_m5_volume is not None and ratio20_m5[i5] is not None and float(ratio20_m5[i5]) <= q_m5_volume) or (q_m5_macd is not None and float(macd["M5"][i5]) >= q_m5_macd)
        q_m15 = window_quantile(macd["M15"], i15, 100, 0.75)
        q_h1_macd = window_quantile(macd["H1"], ih1, 100, 0.50)
        q_h1_rci = window_quantile(rci9_h1, ih1, 100, 0.50)
        if own_core and q_m15 is not None and q_h1_macd is not None and q_h1_rci is not None and float(macd["M15"][i15]) >= q_m15 and float(macd["H1"][ih1]) >= q_h1_macd and rci9_h1[ih1] is not None and float(rci9_h1[ih1]) >= q_h1_rci:
            selected.append({**row, "branch": "M5_S1"})
    return selected


def select_s2(long_m15: list[dict[str, Any]], ratio20_m5: list[float | None], macd_m15: list[float]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in long_m15:
        i5, i15 = int(row["m5_index"]), int(row["m15_index"])
        q1, q2 = window_quantile(ratio20_m5, i5, 200, 0.50), window_quantile(macd_m15, i15, 200, 0.75)
        n1 = q1 is not None and ratio20_m5[i5] is not None and float(ratio20_m5[i5]) <= q1
        n2 = q2 is not None and float(macd_m15[i15]) >= q2
        if n1 or n2:
            selected.append({**row, "branch": "M15_S2", "N1": n1, "N2": n2, "N3": True})
    return selected


def select_s3(long_h1: list[dict[str, Any]], macd_h4: list[float], macd_d1: list[float]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in long_h1:
        ih4, id1 = int(row["h4_index"]), int(row["d1_index"])
        q_h4, q_d1 = window_quantile(macd_h4, ih4, 100, 0.75), window_quantile(macd_d1, id1, 100, 0.50)
        if q_h4 is not None and q_d1 is not None and float(macd_h4[ih4]) >= q_h4 and float(macd_d1[id1]) >= q_d1:
            selected.append({**row, "branch": "H1_S3"})
    return selected


def select_s4(long_h4: list[dict[str, Any]], rci9_d1: list[float | None], ema20_d1: list[float], ema30_d1: list[float], ema40_d1: list[float]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in long_h4:
        id1 = int(row["d1_index"])
        q_d1 = window_quantile(rci9_d1, id1, 100, 0.50)
        if q_d1 is not None and rci9_d1[id1] is not None and float(rci9_d1[id1]) >= q_d1 and ema20_d1[id1] > ema30_d1[id1] > ema40_d1[id1]:
            selected.append({**row, "branch": "H4_S4"})
    return selected


def metrics_from_values(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "average_win_bps": None, "average_loss_bps": None, "payoff_ratio": None, "max_drawdown_bps": 0.0, "max_losing_streak": 0, "tail_le_minus_100_fraction": None}
    wins, losses = sum(v for v in values if v > 0), abs(sum(v for v in values if v < 0))
    positives, negatives = [v for v in values if v > 0], [v for v in values if v < 0]
    equity = peak = dd = 0.0
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    avg_win = statistics.fmean(positives) if positives else None
    avg_loss = statistics.fmean(negatives) if negatives else None
    return {"count": len(values), "win_rate": sum(v > 0 for v in values) / len(values), "profit_factor_bps": None if losses == 0 else wins / losses, "net_bps": sum(values), "average_win_bps": avg_win, "average_loss_bps": avg_loss, "payoff_ratio": None if avg_win is None or avg_loss is None else avg_win / abs(avg_loss), "max_drawdown_bps": dd, "max_losing_streak": max_streak, "tail_le_minus_100_fraction": sum(v <= -100.0 for v in values) / len(values)}


def raw_metrics(rows: list[dict[str, Any]], extra_cost_bps: float = 0.0) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: str(row["turn_entry_time"]))
    return metrics_from_values([float(row["return_bps"]) - extra_cost_bps for row in ordered])


def assert_close(label: str, actual: float, expected: float, tolerance: float = 1e-9) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise RuntimeError(f"{label} mismatch actual={actual} expected={expected}")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
