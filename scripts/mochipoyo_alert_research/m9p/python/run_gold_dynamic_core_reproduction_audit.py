from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import os
import shutil
import statistics
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
LONG_EXIT_RCI9 = 78.333333333333
SHORT_EXIT_RCI9 = -75.0
TURN_LOOKBACK = 5
CANONICAL_W = 200
CANONICAL_Q1 = 0.50
CANONICAL_Q2 = 0.75
STRESS_WINDOWS = (120, 160, 180, 200, 220, 240, 250, 300)
STRESS_Q1 = (0.45, 0.50, 0.55)
STRESS_Q2 = (0.70, 0.75, 0.80)
EXTRA_COSTS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
N6_H4_WINDOW = 100
EXPECTED = {
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


def quantile_sorted(values: list[float], q: float) -> float:
    position = q * (len(values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
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


def replay_m7c(m15: list[Bar]) -> tuple[list[dict[str, Any]], list[float]]:
    closes = [bar.close for bar in m15]
    rci9 = rci_series(closes, 9)
    ema20, ema30, ema40 = ema(closes, 20), ema(closes, 30), ema(closes, 40)
    macd_line = [fast - slow for fast, slow in zip(ema(closes, 6), ema(closes, 13))]
    macd_bps = [line / abs(close) * 10000.0 for line, close in zip(macd_line, closes)]
    pairs: list[dict[str, Any]] = []
    state = "IDLE"
    open_primary: tuple[str, datetime] | None = None
    for current_index in range(50, len(m15)):
        selected = current_index - 1
        current = rci9[selected]
        previous = rci9[selected - 1]
        previous2 = rci9[selected - 2]
        if current is None or previous is None or previous2 is None:
            continue
        turn_up = current > previous and previous <= previous2
        turn_down = current < previous and previous >= previous2
        bullish = ema20[selected] > ema30[selected] > ema40[selected]
        bearish = ema20[selected] < ema30[selected] < ema40[selected]
        if state == "IDLE":
            if turn_up and bullish:
                state = "ACTIVE_LONG"
                open_primary = ("LONG", m15[current_index].time)
            elif turn_down and bearish:
                state = "ACTIVE_SHORT"
                open_primary = ("SHORT", m15[current_index].time)
        elif state == "ACTIVE_LONG" and current >= LONG_EXIT_RCI9:
            if open_primary is None:
                raise RuntimeError("LONG exit without primary")
            pairs.append({"direction": open_primary[0], "entry_time": open_primary[1], "exit_time": m15[current_index].time})
            open_primary = None
            state = "IDLE"
        elif state == "ACTIVE_SHORT" and current <= SHORT_EXIT_RCI9:
            if open_primary is None:
                raise RuntimeError("SHORT exit without primary")
            pairs.append({"direction": open_primary[0], "entry_time": open_primary[1], "exit_time": m15[current_index].time})
            open_primary = None
            state = "IDLE"
    return pairs, macd_bps


def directional_return(direction: str, entry: float, exit_price: float) -> float:
    return ((exit_price - entry) if direction == "LONG" else (entry - exit_price)) / abs(entry) * 10000.0


def build_first_turns(pairs: list[dict[str, Any]], m1: list[Bar], point: float) -> list[dict[str, Any]]:
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
            previous = m1[current_index - 1]
            current = m1[current_index]
            if direction == "LONG":
                candidate = previous.low <= min(bar.low for bar in history) and previous.low < signal_bid and current.close > previous.close
            else:
                candidate = previous.high >= max(bar.high for bar in history) and previous.high > signal_bid and current.close < previous.close
            if not candidate:
                continue
            turn_index = current_index + 1
            turn_bar = m1[turn_index]
            entry_exec = turn_bar.open + turn_bar.spread * point if direction == "LONG" else turn_bar.open
            output.append({
                "trade_id": f"XAU_M9P_T{trade_number:06d}",
                "direction": direction,
                "proxy_entry_time": pair["entry_time"].strftime(TIME_FORMAT),
                "turn_entry_time": turn_bar.time.strftime(TIME_FORMAT),
                "exit_time": pair["exit_time"].strftime(TIME_FORMAT),
                "return_bps": directional_return(direction, entry_exec, exit_exec),
            })
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


def metrics(rows: list[dict[str, Any]], extra_cost_bps: float = 0.0) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: row["turn_entry_time"])
    values = [float(row["return_bps"]) - extra_cost_bps for row in ordered]
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "max_drawdown_bps": 0.0, "max_losing_streak": 0}
    wins = sum(value for value in values if value > 0)
    losses = abs(sum(value for value in values if value < 0))
    equity = peak = max_drawdown = 0.0
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    positive = [value for value in values if value > 0]
    negative = [value for value in values if value < 0]
    return {
        "count": len(values),
        "win_rate": sum(value > 0 for value in values) / len(values),
        "profit_factor_bps": None if losses == 0 else wins / losses,
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values),
        "median_bps": statistics.median(values),
        "max_drawdown_bps": max_drawdown,
        "max_losing_streak": max_streak,
        "average_win_bps": statistics.fmean(positive) if positive else None,
        "average_loss_bps": statistics.fmean(negative) if negative else None,
        "tail_le_minus_100_fraction": sum(value <= -100.0 for value in values) / len(values),
    }


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


def grouped(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        current = parse_time(row["turn_entry_time"])
        if mode == "year":
            label = str(current.year)
        elif mode == "quarter":
            label = f"{current.year}Q{(current.month - 1) // 3 + 1}"
        else:
            label = f"{current.year}-{current.month:02d}"
        groups.setdefault(label, []).append(row)
    return [{mode: label, **metrics(group)} for label, group in sorted(groups.items())]


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    data_override = os.environ.get("M9P_GOLD_DATA_ROOT")
    if data_override:
        data_root = Path(data_override)
    else:
        files_root = Path(metadata.get("mt5_files_root", ""))
        data_root = files_root / "gold_v3_2023_2026"
    point_raw = os.environ.get("M9P_POINT")
    point = float(point_raw) if point_raw is not None else float(metadata.get("symbols", {}).get("XAUUSD", {}).get("point", "nan"))
    if not data_root.is_dir() or not math.isfinite(point):
        print(f"[M9P BLOCKED] GOLD data root or XAUUSD point unavailable: {data_root} point={point}")
        return 2

    paths: dict[str, Path] = {}
    try:
        for timeframe, (filename, expected_hash) in EXPECTED.items():
            path = data_root / filename
            if not path.is_file():
                raise RuntimeError(f"required GOLD file missing: {path}")
            actual_hash = sha256(path)
            if actual_hash != expected_hash:
                raise RuntimeError(f"SHA256 mismatch for {filename}: {actual_hash}")
            paths[timeframe] = path

        m15 = load_bars(paths["M15"])
        m5 = load_bars(paths["M5"])
        h4 = load_bars(paths["H4"])
        m1 = load_bars(paths["M1"])
        pairs, m15_macd_bps = replay_m7c(m15)
        first_turns = build_first_turns(pairs, m1, point)
        long_turns = [row for row in first_turns if row["direction"] == "LONG"]
        ratio20 = m5_ratio20(m5)
        m5_close_times = [bar.time + timedelta(minutes=5) for bar in m5]
        m15_close_times = [bar.time + timedelta(minutes=15) for bar in m15]
        h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]
        h4_rci9 = rci_series([bar.close for bar in h4], 9)

        for row in long_turns:
            decision = parse_time(row["turn_entry_time"])
            row["m5_index"] = bisect.bisect_right(m5_close_times, decision) - 1
            row["m15_index"] = bisect.bisect_right(m15_close_times, decision) - 1
            row["h4_index"] = bisect.bisect_right(h4_close_times, decision) - 1

        cache: dict[tuple[int, int], tuple[list[float] | None, list[float] | None]] = {}
        for window in STRESS_WINDOWS:
            for row_number, row in enumerate(long_turns):
                i5 = int(row["m5_index"])
                i15 = int(row["m15_index"])
                sorted_m5 = sorted(float(value) for value in ratio20[i5 - window + 1:i5 + 1]) if i5 >= window + 18 else None
                sorted_m15 = sorted(float(value) for value in m15_macd_bps[i15 - window + 1:i15 + 1]) if i15 >= window - 1 else None
                cache[(row_number, window)] = (sorted_m5, sorted_m15)

        canonical_rows: list[dict[str, Any]] = []
        stress_rows: list[dict[str, Any]] = []
        for row_number, row in enumerate(long_turns):
            sorted_m5, sorted_m15 = cache[(row_number, CANONICAL_W)]
            n1_threshold = None if sorted_m5 is None else quantile_sorted(sorted_m5, CANONICAL_Q1)
            n2_threshold = None if sorted_m15 is None else quantile_sorted(sorted_m15, CANONICAL_Q2)
            n1 = n1_threshold is not None and float(ratio20[int(row["m5_index"])]) <= n1_threshold
            n2 = n2_threshold is not None and float(m15_macd_bps[int(row["m15_index"])]) >= n2_threshold
            h4_percentile = None
            ih4 = int(row["h4_index"])
            if ih4 >= 107:
                values = h4_rci9[ih4 - 99:ih4 + 1]
                if all(value is not None for value in values):
                    current = float(h4_rci9[ih4])
                    h4_percentile = sum(float(value) <= current for value in values if value is not None) / 100.0
            canonical_rows.append({
                **row,
                "N1": n1,
                "N2": n2,
                "N3": n1 or n2,
                "N1_current_ratio20": None if int(row["m5_index"]) < 0 else ratio20[int(row["m5_index"])],
                "N1_threshold": n1_threshold,
                "N2_current_macd_line_bps": None if int(row["m15_index"]) < 0 else m15_macd_bps[int(row["m15_index"])],
                "N2_threshold": n2_threshold,
                "N6_h4_rci9_percentile": h4_percentile,
                "N6_risk_zone": h4_percentile is not None and h4_percentile > 0.25 and h4_percentile <= 0.50,
            })

        for window in STRESS_WINDOWS:
            for q1 in STRESS_Q1:
                for q2 in STRESS_Q2:
                    selected: list[dict[str, Any]] = []
                    for row_number, row in enumerate(long_turns):
                        sorted_m5, sorted_m15 = cache[(row_number, window)]
                        n1 = sorted_m5 is not None and float(ratio20[int(row["m5_index"])]) <= quantile_sorted(sorted_m5, q1)
                        n2 = sorted_m15 is not None and float(m15_macd_bps[int(row["m15_index"])]) >= quantile_sorted(sorted_m15, q2)
                        if n1 or n2:
                            selected.append(row)
                    base = metrics(selected)
                    cost2 = metrics(selected, 2.0)
                    yearly = grouped(selected, "year")
                    stress_rows.append({
                        "window": window,
                        "N1_quantile": q1,
                        "N2_quantile": q2,
                        "count": base["count"],
                        "win_rate": base["win_rate"],
                        "profit_factor_bps": base["profit_factor_bps"],
                        "max_drawdown_bps": base["max_drawdown_bps"],
                        "extra_2bps_profit_factor": cost2["profit_factor_bps"],
                        "minimum_calendar_year_pf": min(float(item["profit_factor_bps"]) for item in yearly if item["profit_factor_bps"] is not None),
                    })

        n1_rows = [row for row in canonical_rows if row["N1"]]
        n2_rows = [row for row in canonical_rows if row["N2"]]
        n3_rows = [row for row in canonical_rows if row["N3"]]
        n6_risk = [row for row in n3_rows if row["N6_risk_zone"]]
        n6_complement = [row for row in n3_rows if not row["N6_risk_zone"]]
        cost_rows = [{"extra_cost_bps_per_trade": cost, **metrics(n3_rows, cost)} for cost in EXTRA_COSTS]

    except Exception as exc:
        print(f"[M9P BLOCKED] {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9P_GOLD_DYNAMIC_CORE_DETERMINISTIC_REPRODUCTION",
        "status": "PASS_HISTORICAL_REPRODUCTION_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "population": {"paired_m7c_trades": len(pairs), "first_turn_trades": len(first_turns), "long_first_turn_trades": len(long_turns)},
        "N1": metrics(n1_rows),
        "N2": metrics(n2_rows),
        "N3": metrics(n3_rows),
        "N3_yearly": grouped(n3_rows, "year"),
        "N3_quarterly": grouped(n3_rows, "quarter"),
        "N6_risk": metrics(n6_risk),
        "N6_complement": metrics(n6_complement),
        "stress": {
            "combination_count": len(stress_rows),
            "all_combinations_min_year_pf_above_1": all(float(row["minimum_calendar_year_pf"]) > 1.0 for row in stress_rows),
            "all_combinations_extra_2bps_pf_above_1": all(float(row["extra_2bps_profit_factor"]) > 1.0 for row in stress_rows),
        },
        "guardrails": {"historical_spread_used": True, "commission": "NOT_MODELED", "swap": "NOT_MODELED", "future_feature_use": False, "m7c_formula_changed": False, "m8c_reset": False, "automatic_live_promotion": False, "audit_only": True},
    }

    output_override = os.environ.get("M9P_OUTPUT_ROOT")
    out_root = Path(output_override) if output_override else local_root / "outputs" / "M9P"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text("M9P deterministically reproduces strict causal N1/N2/N3 on the supplied GOLD history. N6 is descriptive risk only and is not a gate. The sample is research-exposed, not independent live validation. Historical spread is used; commission/swap are not modeled.\n", encoding="utf-8")
    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_yearly_candidate_summary.csv", grouped(n3_rows, "year"))
    write_csv(archive / "03_quarterly_candidate_summary.csv", grouped(n3_rows, "quarter"))
    write_csv(archive / "04_monthly_candidate_summary.csv", grouped(n3_rows, "month"))
    write_csv(archive / "05_candidate_trade_ledger.csv", canonical_rows)
    write_csv(archive / "06_parameter_neighborhood_stress.csv", stress_rows)
    write_csv(archive / "07_cost_sensitivity.csv", cost_rows)
    write_csv(archive / "08_n6_risk_layer_summary.csv", [{"group": "N6_RISK", **metrics(n6_risk)}, {"group": "N6_COMPLEMENT", **metrics(n6_complement)}])
    dump_json(archive / "09_data_quality.json", {"data_root": str(data_root), "point": point, "hashes": {tf: {"file": EXPECTED[tf][0], "sha256": EXPECTED[tf][1]} for tf in EXPECTED}, "closed_bars_only": True, "nearest_m1_fallback": False})
    (archive / "10_audit.log").write_text("\n".join(["status=PASS_HISTORICAL_REPRODUCTION_ONLY", f"n1={len(n1_rows)}", f"n2={len(n2_rows)}", f"n3={len(n3_rows)}", f"n6_risk={len(n6_risk)}", f"stress_combinations={len(stress_rows)}", f"stress_all_min_year_pf_above_1={summary['stress']['all_combinations_min_year_pf_above_1']}", f"stress_all_extra_2bps_pf_above_1={summary['stress']['all_combinations_extra_2bps_pf_above_1']}", "m7c_formula_changed=false", "m8c_reset=false", "automatic_live_promotion=false", ""]), encoding="utf-8")
    names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_yearly_candidate_summary.csv", "03_quarterly_candidate_summary.csv", "04_monthly_candidate_summary.csv", "05_candidate_trade_ledger.csv", "06_parameter_neighborhood_stress.csv", "07_cost_sensitivity.csv", "08_n6_risk_layer_summary.csv", "09_data_quality.json", "10_audit.log"]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(f"[M9P PASS] N1={len(n1_rows)} N2={len(n2_rows)} N3={len(n3_rows)} N6_RISK={len(n6_risk)}")
    print("[M9P OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
