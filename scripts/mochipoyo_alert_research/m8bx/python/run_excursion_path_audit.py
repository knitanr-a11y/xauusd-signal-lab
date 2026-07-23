from __future__ import annotations

import csv
import json
import math
import os
import shutil
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_TRADE_COUNT = 18
EXPECTED_FILES = {"XAUUSD": "goldsharp_m1.csv", "BTCUSD": "btcusdsharp_m1.csv"}
TIME_FORMAT = "%Y.%m.%d %H:%M:%S"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_m1(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    if not rows:
        raise RuntimeError(f"empty M1 CSV: {path}")
    expected = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    if list(rows[0].keys()) != expected:
        raise RuntimeError(f"unexpected M1 header: {path.name}")
    previous = None
    for row in rows:
        t = datetime.strptime(row["time"], TIME_FORMAT)
        if previous is not None and t <= previous:
            raise RuntimeError(f"M1 time not strictly increasing in {path.name}: {row['time']}")
        previous = t
        for k in ("open", "high", "low", "close"):
            v = float(row[k])
            if not math.isfinite(v):
                raise RuntimeError(f"nonfinite {k} in {path.name} at {row['time']}")
        if int(row["spread"]) < 0:
            raise RuntimeError(f"negative spread in {path.name} at {row['time']}")
    return rows


def bps(ret: float) -> float:
    return ret * 10000.0


def path_return(direction: str, entry_exec: float, bar: dict[str, str], point: float) -> tuple[float, float]:
    low = float(bar["low"])
    high = float(bar["high"])
    spread = int(bar["spread"]) * point
    if direction == "LONG":
        adverse = bps((low - entry_exec) / entry_exec)
        favorable = bps((high - entry_exec) / entry_exec)
    elif direction == "SHORT":
        ask_high = high + spread
        ask_low = low + spread
        adverse = bps((entry_exec - ask_high) / entry_exec)
        favorable = bps((entry_exec - ask_low) / entry_exec)
    else:
        raise RuntimeError(f"unknown direction: {direction}")
    return adverse, favorable


def evaluate_trade(trade: dict[str, str], m1_rows: list[dict[str, str]], point: float) -> dict[str, Any]:
    entry_dt = datetime.strptime(trade["entry_server_open"], TIME_FORMAT)
    exit_dt = datetime.strptime(trade["exit_server_open"], TIME_FORMAT)
    if exit_dt < entry_dt:
        raise RuntimeError(f"exit before entry: {trade['trade_id']}")

    window = []
    for row in m1_rows:
        t = datetime.strptime(row["time"], TIME_FORMAT)
        if t < entry_dt:
            continue
        if t > exit_dt:
            break
        window.append((t, row))
    if not window or window[0][0] != entry_dt or window[-1][0] != exit_dt:
        raise RuntimeError(f"exact M1 entry/exit window missing: {trade['trade_id']}")

    entry_exec = float(trade["entry_exec_price"])
    final_ret = float(trade["spread_adjusted_return_bps"])
    adverse_series: list[tuple[datetime, float]] = []
    favorable_series: list[tuple[datetime, float]] = []
    underwater = 0
    for t, row in window:
        adverse, favorable = path_return(trade["direction"], entry_exec, row, point)
        adverse_series.append((t, adverse))
        favorable_series.append((t, favorable))
        if favorable < 0:
            underwater += 1

    mae_t, mae = min(adverse_series, key=lambda x: x[1])
    mfe_t, mfe = max(favorable_series, key=lambda x: x[1])
    elapsed_clock = int((exit_dt - entry_dt).total_seconds() // 60) + 1
    observed = len(window)
    missing_clock = max(elapsed_clock - observed, 0)

    out = dict(trade)
    out.update({
        "mae_bps": mae,
        "mfe_bps": mfe,
        "final_return_bps": final_ret,
        "time_to_mae_minutes": int((mae_t - entry_dt).total_seconds() // 60),
        "time_to_mfe_minutes": int((mfe_t - entry_dt).total_seconds() // 60),
        "peak_to_exit_giveback_bps": mfe - final_ret,
        "recovery_from_mae_to_exit_bps": final_ret - mae,
        "underwater_m1_bar_fraction": underwater / observed if observed else None,
        "observed_m1_rows": observed,
        "elapsed_clock_minutes_inclusive": elapsed_clock,
        "missing_clock_minutes": missing_clock,
        "mae_server_time": mae_t.strftime(TIME_FORMAT),
        "mfe_server_time": mfe_t.strftime(TIME_FORMAT),
    })
    return out


def describe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"trade_count": 0}
    maes = [float(r["mae_bps"]) for r in rows]
    mfes = [float(r["mfe_bps"]) for r in rows]
    finals = [float(r["final_return_bps"]) for r in rows]
    givebacks = [float(r["peak_to_exit_giveback_bps"]) for r in rows]
    underwater = [float(r["underwater_m1_bar_fraction"]) for r in rows]
    return {
        "trade_count": len(rows),
        "win_rate": sum(v > 0 for v in finals) / len(rows),
        "mean_mae_bps": statistics.fmean(maes),
        "median_mae_bps": statistics.median(maes),
        "worst_mae_bps": min(maes),
        "mean_mfe_bps": statistics.fmean(mfes),
        "median_mfe_bps": statistics.median(mfes),
        "best_mfe_bps": max(mfes),
        "mean_final_return_bps": statistics.fmean(finals),
        "median_final_return_bps": statistics.median(finals),
        "mean_peak_to_exit_giveback_bps": statistics.fmean(givebacks),
        "median_peak_to_exit_giveback_bps": statistics.median(givebacks),
        "mean_underwater_m1_bar_fraction": statistics.fmean(underwater),
        "max_missing_clock_minutes": max(int(r["missing_clock_minutes"]) for r in rows),
    }


def grouped(rows: list[dict[str, Any]]) -> dict[str, Any]:
    specs = {
        "by_ticker": lambda r: r["ticker"],
        "by_direction": lambda r: r["direction"],
        "by_outcome": lambda r: r["outcome"],
        "by_ticker_direction": lambda r: f"{r['ticker']}|{r['direction']}",
        "by_ticker_outcome": lambda r: f"{r['ticker']}|{r['outcome']}",
    }
    out = {}
    for name, fn in specs.items():
        g: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            g[fn(r)].append(r)
        out[name] = {k: describe(v) for k, v in sorted(g.items())}
    return out


def main() -> int:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m8b = root / "outputs" / "M8B" / "LATEST"
    trades_path = m8b / "03_extra_entry_trades.csv"
    metadata_path = m8b / "06_symbol_metadata.json"
    if not trades_path.is_file() or not metadata_path.is_file():
        print("[M8BX BLOCKED] M8B LATEST trade/metadata files are missing")
        return 2

    trades = read_csv(trades_path)
    if len(trades) != EXPECTED_TRADE_COUNT:
        print(f"[M8BX BLOCKED] expected {EXPECTED_TRADE_COUNT} M8B trades, got {len(trades)}")
        return 2
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print(f"[M8BX BLOCKED] MT5 Files root from M8B metadata is unavailable: {files_root}")
        return 2

    try:
        m1 = {ticker: load_m1(files_root / filename) for ticker, filename in EXPECTED_FILES.items()}
        evaluated = []
        for trade in trades:
            ticker = trade["ticker"]
            point = float(meta["symbols"][ticker]["point"])
            evaluated.append(evaluate_trade(trade, m1[ticker], point))
    except Exception as exc:
        print(f"[M8BX BLOCKED] {exc}")
        return 2

    evaluated.sort(key=lambda r: (r["entry_decision_time_utc"], r["ticker"]))
    xau = [r for r in evaluated if r["ticker"] == "XAUUSD"]
    xau_deepest = sorted(xau, key=lambda r: float(r["mae_bps"]))
    xau_giveback = sorted(xau, key=lambda r: float(r["peak_to_exit_giveback_bps"]), reverse=True)

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M8BX_EXCURSION_PATH_AUDIT",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_only": True,
        "trade_count": len(evaluated),
        "overall": describe(evaluated),
        "splits": grouped(evaluated),
        "xau_focus": {
            "all": describe(xau),
            "wins": describe([r for r in xau if float(r["final_return_bps"]) > 0]),
            "losses": describe([r for r in xau if float(r["final_return_bps"]) < 0]),
            "deepest_adverse_trade_ids": [r["trade_id"] for r in xau_deepest[:5]],
            "largest_giveback_trade_ids": [r["trade_id"] for r in xau_giveback[:5]],
        },
        "interpretation_guardrails": {
            "m8b_18_is_hypothesis_generation_only": True,
            "no_stop_or_entry_threshold_promoted_from_this_sample": True,
            "m8c_or_later_forward_validation_required": True,
            "win_rate_alone_is_not_sufficient": True,
        },
    }
    quality = {
        "exact_entry_exit_m1_required": True,
        "nearest_bar_fallback_used": False,
        "synthetic_fill_used": False,
        "max_missing_clock_minutes": max(int(r["missing_clock_minutes"]) for r in evaluated),
        "trades_with_missing_clock_minutes": sum(int(r["missing_clock_minutes"]) > 0 for r in evaluated),
        "m1_files_root": str(files_root),
        "symbol_points": {k: meta["symbols"][k]["point"] for k in EXPECTED_FILES},
    }

    out_root = root / "outputs" / "M8BX"
    latest = out_root / "LATEST"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    dump_json(archive / "01_summary.json", summary)
    dump_json(archive / "02_data_quality.json", quality)
    fields = list(evaluated[0].keys())
    write_csv(archive / "03_trade_excursions.csv", evaluated, fields)
    write_csv(archive / "04_xau_excursion_focus.csv", xau, fields)

    split_rows = []
    for family, groups in summary["splits"].items():
        for group_name, stats in groups.items():
            row = {"family": family, "group": group_name}
            row.update(stats)
            split_rows.append(row)
    split_fields = list(split_rows[0].keys())
    write_csv(archive / "05_split_summary.csv", split_rows, split_fields)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "MOCHIPOYO M8BX Excursion Path Audit\n\n"
        "This is exploratory-only analysis of the frozen M8B 18 trades.\n"
        "It measures M1 MAE/MFE, time to extremes, underwater fraction and peak-to-exit giveback.\n"
        "Do not promote a stop or entry threshold from this same 18-trade sample.\n",
        encoding="utf-8",
    )
    (archive / "06_audit.log").write_text(
        f"status=PASS_EXPLORATORY_ONLY\ntrade_count={len(evaluated)}\n"
        f"xau_trade_count={len(xau)}\nmax_missing_clock_minutes={quality['max_missing_clock_minutes']}\n",
        encoding="utf-8",
    )
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_data_quality.json",
        "03_trade_excursions.csv", "04_xau_excursion_focus.csv", "05_split_summary.csv", "06_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            z.write(archive / name, name)
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    print(f"[M8BX PASS] trades={len(evaluated)} xau={len(xau)}")
    print(f"[M8BX OUTPUT] {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
