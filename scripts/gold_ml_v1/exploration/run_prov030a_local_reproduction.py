from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

POINT = 0.01
TF_MIN = {"m1": 1, "m5": 5, "m15": 15, "h1": 60, "h4": 240, "d1": 1440}
CID = "GML1-PROV-030-A"
COLUMNS = [
    "candidate_id", "entry_time", "exit_time", "r_value", "outcome", "mfe_r", "mae_r",
    "m15_atr14", "m15_slope20_3_atr", "d1_adx14", "m15_body_atr", "m15_rsi14",
    "m15_adx14", "h1_gap20_50_atr", "h1_slope20_3_atr", "h4_gap20_50_atr",
    "h4_slope20_3_atr",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_raw(raw_dir: Path, timeframe: str) -> pd.DataFrame:
    path = raw_dir / f"gold_v3_2023_2026_{timeframe}.csv"
    frame = pd.read_csv(path)
    frame["open_time"] = pd.to_datetime(frame["time"], format="%Y.%m.%d %H:%M:%S")
    frame["close_time"] = frame["open_time"] + pd.Timedelta(minutes=TF_MIN[timeframe])
    frame = frame.sort_values("open_time", kind="mergesort").reset_index(drop=True)
    if frame["open_time"].duplicated().any():
        raise RuntimeError(f"{timeframe} contains duplicate times")
    return frame


def wilder(series: pd.Series, period: int = 14) -> pd.Series:
    values = series.to_numpy(float)
    output = np.full(len(values), np.nan)
    if len(values) >= period:
        output[period - 1] = np.nanmean(values[:period])
        for index in range(period, len(values)):
            output[index] = (output[index - 1] * (period - 1) + values[index]) / period
    return pd.Series(output, index=series.index)


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous = frame["close"].shift(1)
    return pd.concat(
        [
            (frame["high"] - frame["low"]).abs(),
            (frame["high"] - previous).abs(),
            (frame["low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    difference = close.diff()
    average_gain = wilder(difference.clip(lower=0).fillna(0), period)
    average_loss = wilder((-difference.clip(upper=0)).fillna(0), period)
    relative = average_gain / average_loss.replace(0, np.nan)
    output = 100 - 100 / (1 + relative)
    output = output.where(average_loss != 0, 100)
    output = output.where(average_gain != 0, 0)
    return output.where(~((average_gain == 0) & (average_loss == 0)), 50)


def adx(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    up = frame["high"].diff()
    down = -frame["low"].diff()
    plus = np.where((up > down) & (up > 0), up, 0.0)
    minus = np.where((down > up) & (down > 0), down, 0.0)
    atr = wilder(true_range(frame), period)
    plus_di = 100 * wilder(pd.Series(plus, index=frame.index), period) / atr
    minus_di = 100 * wilder(pd.Series(minus, index=frame.index), period) / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return wilder(dx.fillna(0), period)


def features(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    result = frame.copy()
    atr = wilder(true_range(result), 14)
    result[prefix + "atr14"] = atr
    result[prefix + "rsi14"] = rsi(result["close"])
    result[prefix + "adx14"] = adx(result)
    for period in (20, 50):
        result[prefix + f"ema{period}"] = result["close"].ewm(
            span=period, adjust=False, min_periods=period
        ).mean()
    result[prefix + "body_atr"] = (result["close"] - result["open"]) / atr
    result[prefix + "gap20_50_atr"] = (
        result[prefix + "ema20"] - result[prefix + "ema50"]
    ) / atr
    result[prefix + "slope20_3_atr"] = (
        result[prefix + "ema20"] - result[prefix + "ema20"].shift(3)
    ) / atr
    return result


def prepare(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    m1 = read_raw(raw_dir, "m1")
    m5 = read_raw(raw_dir, "m5")
    m15 = features(read_raw(raw_dir, "m15"), "m15_")
    h1 = features(read_raw(raw_dir, "h1"), "h1_")
    h4 = features(read_raw(raw_dir, "h4"), "h4_")
    d1 = features(read_raw(raw_dir, "d1"), "d1_")
    base = m15.sort_values("close_time").copy()
    for source, columns in [
        (h1, ["h1_ema20", "h1_ema50", "h1_gap20_50_atr", "h1_slope20_3_atr"]),
        (h4, ["h4_ema20", "h4_ema50", "h4_gap20_50_atr", "h4_slope20_3_atr"]),
        (d1, ["d1_adx14"]),
    ]:
        base = pd.merge_asof(
            base.sort_values("close_time"),
            source[["close_time", *columns]].sort_values("close_time"),
            on="close_time",
            direction="backward",
            allow_exact_matches=True,
        )
    return m1, m5, base


def entry_times(events: pd.DataFrame, m5: pd.DataFrame) -> np.ndarray:
    times = pd.DatetimeIndex(m5["open_time"]).asi8
    opens = m5["open"].to_numpy(float)
    highs = m5["high"].to_numpy(float)
    closes = m5["close"].to_numpy(float)
    output = np.full(len(events), -1, np.int64)
    step = 5 * 60 * 1_000_000_000
    for event_index, row in enumerate(events.itertuples(index=False)):
        decision = pd.Timestamp(row.close_time).value
        start = int(np.searchsorted(times, decision))
        if start >= len(times) or times[start] != decision:
            continue
        risk = float(row.m15_atr14)
        if not math.isfinite(risk) or risk <= 0:
            continue
        for offset in range(3):
            index = start + offset
            if index >= len(times) or times[index] != times[start] + offset * step:
                break
            broke = highs[index] >= float(row.high) + 0.05 * risk
            if broke and closes[index] > opens[index]:
                output[event_index] = times[index] + step
                break
    return output


def evaluate(events: pd.DataFrame, entries: np.ndarray, m1: pd.DataFrame) -> pd.DataFrame:
    times = pd.DatetimeIndex(m1["open_time"]).asi8
    opens = m1["open"].to_numpy(float)
    highs = m1["high"].to_numpy(float)
    lows = m1["low"].to_numpy(float)
    closes = m1["close"].to_numpy(float)
    spreads = m1["spread"].to_numpy(float)
    latest_close = int(times[-1]) + 60 * 1_000_000_000
    open_until = -(2**63)
    rows: list[dict[str, Any]] = []
    for event_index, row in enumerate(events.itertuples(index=False)):
        entry_time = int(entries[event_index])
        if entry_time < 0 or entry_time < open_until:
            continue
        start = int(np.searchsorted(times, entry_time))
        if start >= len(times) or times[start] != entry_time:
            continue
        horizon_end = entry_time + 1440 * 60 * 1_000_000_000
        if horizon_end > latest_close:
            continue
        end = int(np.searchsorted(times, horizon_end))
        risk = float(row.m15_atr14)
        entry_price = opens[start] + spreads[start] * POINT
        stop = entry_price - risk
        target = entry_price + 2.5 * risk
        breakeven = False
        exit_index = end - 1
        r_value = 0.0
        outcome = 2
        maximum_favorable = 0.0
        maximum_adverse = 0.0
        for index in range(start, end):
            favorable = (highs[index] - entry_price) / risk
            adverse = (entry_price - lows[index]) / risk
            maximum_favorable = max(maximum_favorable, favorable)
            maximum_adverse = max(maximum_adverse, adverse)
            current_stop = entry_price if breakeven else stop
            if lows[index] <= current_stop:
                exit_index = index
                outcome = 0
                r_value = 0.0 if breakeven else -1.0
                break
            reached_one_r = highs[index] >= entry_price + risk
            reached_target = highs[index] >= target
            if reached_one_r:
                breakeven = True
            if reached_target:
                exit_index = index
                outcome = 1
                r_value = 2.5
                break
        else:
            r_value = (closes[exit_index] - entry_price) / risk
        exit_time = pd.Timestamp(times[exit_index]) + pd.Timedelta(minutes=1)
        open_until = exit_time.value
        rows.append(
            {
                "candidate_id": CID,
                "entry_time": pd.Timestamp(entry_time),
                "exit_time": exit_time,
                "r_value": r_value,
                "outcome": outcome,
                "mfe_r": maximum_favorable,
                "mae_r": maximum_adverse,
                "m15_atr14": row.m15_atr14,
                "m15_slope20_3_atr": row.m15_slope20_3_atr,
                "d1_adx14": row.d1_adx14,
                "m15_body_atr": row.m15_body_atr,
                "m15_rsi14": row.m15_rsi14,
                "m15_adx14": row.m15_adx14,
                "h1_gap20_50_atr": row.h1_gap20_50_atr,
                "h1_slope20_3_atr": row.h1_slope20_3_atr,
                "h4_gap20_50_atr": row.h4_gap20_50_atr,
                "h4_slope20_3_atr": row.h4_slope20_3_atr,
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def metrics(values: pd.Series) -> dict[str, Any]:
    clean = pd.Series(pd.to_numeric(values, errors="coerce")).dropna()
    gross_profit = clean[clean > 0].sum()
    gross_loss = -clean[clean < 0].sum()
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    equity = clean.cumsum()
    drawdown = (equity.cummax() - equity).max() if len(clean) else np.nan
    return {
        "count": int(len(clean)),
        "profit_factor": float(profit_factor),
        "mean_R": float(clean.mean()) if len(clean) else None,
        "total_R": float(clean.sum()),
        "max_DD_R": float(drawdown) if len(clean) else None,
        "win_rate": float((clean > 0).mean()) if len(clean) else None,
    }


def backup_output(output_dir: Path) -> Path | None:
    if not output_dir.exists() or not any(output_dir.iterdir()):
        output_dir.mkdir(parents=True, exist_ok=True)
        return None
    destination = output_dir.parent / f"{output_dir.name}_backups" / datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(output_dir), str(destination))
    output_dir.mkdir(parents=True, exist_ok=True)
    return destination


def run(raw_dir: Path, contract_path: Path, output_dir: Path) -> int:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    previous_output = backup_output(output_dir)
    for filename, expected in contract["expected_input_sha256"].items():
        actual = sha256_file(raw_dir / filename)
        if actual != expected:
            raise RuntimeError(f"input hash mismatch {filename}: {actual} != {expected}")
    m1, m5, base = prepare(raw_dir)
    regime = contract["regime_filter"]
    condition = (
        (base["h1_ema20"] > base["h1_ema50"])
        & (base["h4_ema20"] > base["h4_ema50"])
        & (base["low"] <= base["m15_ema50"])
        & (base["close"] > base["m15_ema50"])
        & (base["m15_body_atr"] > 0)
        & (base["h1_slope20_3_atr"] > 0)
        & (
            base["m15_slope20_3_atr"]
            <= regime["m15_ema20_slope3_over_m15_atr14_max"]
        )
        & (base["d1_adx14"] > regime["d1_adx14_min_exclusive"])
    )
    events = base.loc[condition].sort_values("close_time", kind="mergesort").reset_index(drop=True)
    entries = entry_times(events, m5)
    trades = evaluate(events, entries, m1)
    trade_path = output_dir / "candidate_trades.csv"
    trades.to_csv(trade_path, index=False)
    actual_hash = sha256_file(trade_path)
    expected_hash = contract["canonical_reproduction"]["candidate_trades_sha256"]
    year_metrics = []
    for year in (2023, 2024, 2025, 2026):
        year_metrics.append(
            {
                "year": year,
                **metrics(trades.loc[trades["entry_time"].dt.year == year, "r_value"]),
            }
        )
    pd.DataFrame(year_metrics).to_csv(output_dir / "year_metrics.csv", index=False)
    expected_rows = int(contract["canonical_reproduction"]["candidate_trade_rows"])
    status = "PASS" if actual_hash == expected_hash and len(trades) == expected_rows else "FAIL"
    summary = {
        "status": status,
        "candidate_id": CID,
        "candidate_status": contract["status"],
        "time_contract": contract["time_contract"],
        "previous_output_backup": str(previous_output) if previous_output else None,
        "event_count_before_M5_confirmation": int(len(events)),
        "candidate_trade_rows": int(len(trades)),
        "expected_trade_rows": expected_rows,
        "candidate_trades_sha256": actual_hash,
        "expected_candidate_trades_sha256": expected_hash,
        "year_metrics": year_metrics,
        "existing_frozen_nine_modified": False,
        "prospective_monitoring_activated": False,
        "live_ready": False,
    }
    (output_dir / "local_reproduction_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "GOLD_ML_V1 GML1-PROV-030-A LOCAL AUDIT REPRODUCTION",
        f"status={status}",
        f"candidate_trade_rows={len(trades)}",
        f"expected_trade_rows={expected_rows}",
        f"candidate_trades_sha256={actual_hash}",
        f"expected_candidate_trades_sha256={expected_hash}",
        "time_column=MT5_SERVER_BAR_OPEN_TIME",
        "candidate_status=PROVISIONAL_COST_PASS_PROSPECTIVE_REQUIRED",
        "existing_frozen_nine_modified=FALSE",
        "live_ready=FALSE",
        "",
    ]
    for row in year_metrics:
        lines.append(
            f"{row['year']} count={row['count']} PF={row['profit_factor']:.6f} "
            f"meanR={row['mean_R']:+.6f} totalR={row['total_R']:+.6f} "
            f"DD={row['max_DD_R']:.6f}"
        )
    (output_dir / "LATEST_RUN_SUMMARY.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    (output_dir / "LOCAL_REPRODUCTION_ERROR.txt").write_text(
        "status=PASS\nerror=NONE\n" if status == "PASS" else "status=FAIL\nerror=CANONICAL_MISMATCH\n",
        encoding="utf-8",
    )
    if status != "PASS":
        raise RuntimeError("candidate canonical reproduction mismatch")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        return run(args.raw_dir.resolve(), args.contract.resolve(), args.output_dir.resolve())
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "LOCAL_REPRODUCTION_ERROR.txt").write_text(
            f"status=FAIL\nerror={type(exc).__name__}: {exc}\n\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
