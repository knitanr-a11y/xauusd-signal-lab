from __future__ import annotations

import bisect
import json
import math
import os
import shutil
import statistics
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
M9P_DIR = THIS.parents[2] / "m9p" / "python"
if str(M9P_DIR) not in sys.path:
    sys.path.insert(0, str(M9P_DIR))
import run_gold_dynamic_core_reproduction_audit as m9p

STAGE = "M9X_GOLD_PAYOFF_DECOUPLING_DETERMINISTIC_REPRODUCTION"
REFERENCE_OFFSET_ATR = 0.10
REFERENCE_WAIT_MINUTES = 10
RUNNER_SHARES = (0.25, 0.50, 0.75, 1.00)
STRESS_OFFSETS = (0.00, 0.05, 0.10, 0.15, 0.20)
STRESS_WAITS = (5, 10, 15, 20, 30)
POINT = 0.01
EXPECTED_REFERENCE = {
    "entry_count": 1054,
    "entry_pf": 1.587529100728406,
    "combined_50_pf": 1.657561156085209,
    "combined_50_avg_win": 17.22400846453467,
    "combined_50_avg_loss": -14.331846680015385,
    "combined_50_dd": 291.531445157726,
    "combined_75_pf": 1.6440999252824298,
}


def wilder_atr14(bars: list[m9p.Bar]) -> list[float | None]:
    tr: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            value = bar.high - bar.low
        else:
            previous = bars[i - 1].close
            value = max(bar.high - bar.low, abs(bar.high - previous), abs(bar.low - previous))
        tr.append(value)
    out: list[float | None] = [None] * len(bars)
    if len(bars) >= 14:
        out[13] = sum(tr[:14]) / 14.0
        for i in range(14, len(bars)):
            previous = out[i - 1]
            assert previous is not None
            out[i] = ((13.0 * previous) + tr[i]) / 14.0
    return out


def metric_rows(rows: list[dict[str, Any]], value_key: str = "weighted_return_bps", extra_cost_bps: float = 0.0) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: row["actual_entry_time"])
    values = [float(row[value_key]) - extra_cost_bps * float(row.get("risk_weight", 1.0)) for row in ordered]
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "max_drawdown_bps": 0.0, "max_losing_streak": 0}
    wins = sum(v for v in values if v > 0)
    losses = abs(sum(v for v in values if v < 0))
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
    positive = [v for v in values if v > 0]
    negative = [v for v in values if v < 0]
    return {
        "count": len(values),
        "win_rate": sum(v > 0 for v in values) / len(values),
        "profit_factor_bps": None if losses == 0 else wins / losses,
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values),
        "median_bps": statistics.median(values),
        "average_win_bps": statistics.fmean(positive) if positive else None,
        "average_loss_bps": statistics.fmean(negative) if negative else None,
        "max_drawdown_bps": dd,
        "max_losing_streak": max_streak,
        "tail_le_minus_100_fraction": sum(v <= -100.0 for v in values) / len(values),
    }


def group_metrics(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        current = m9p.parse_time(str(row["actual_entry_time"]))
        if mode == "year":
            label = str(current.year)
        elif mode == "quarter":
            label = f"{current.year}Q{(current.month - 1) // 3 + 1}"
        else:
            label = f"{current.year}-{current.month:02d}"
        groups.setdefault(label, []).append(row)
    return [{mode: label, **metric_rows(group)} for label, group in sorted(groups.items())]


def build_canonical_n3(m1: list[m9p.Bar], m5: list[m9p.Bar], m15: list[m9p.Bar], h4: list[m9p.Bar], point: float) -> list[dict[str, Any]]:
    pairs, m15_macd_bps = m9p.replay_m7c(m15)
    turns = m9p.build_first_turns(pairs, m1, point)
    long_turns = [row for row in turns if row["direction"] == "LONG"]
    ratio20 = m9p.m5_ratio20(m5)
    m5_close = [bar.time + timedelta(minutes=5) for bar in m5]
    m15_close = [bar.time + timedelta(minutes=15) for bar in m15]
    h4_close = [bar.time + timedelta(hours=4) for bar in h4]
    h4_rci = m9p.rci_series([bar.close for bar in h4], 9)
    output: list[dict[str, Any]] = []
    for row in long_turns:
        decision = m9p.parse_time(row["turn_entry_time"])
        i5 = bisect.bisect_right(m5_close, decision) - 1
        i15 = bisect.bisect_right(m15_close, decision) - 1
        ih4 = bisect.bisect_right(h4_close, decision) - 1
        sorted_m5 = sorted(float(v) for v in ratio20[i5 - 199:i5 + 1]) if i5 >= 218 else None
        sorted_m15 = sorted(float(v) for v in m15_macd_bps[i15 - 199:i15 + 1]) if i15 >= 199 else None
        q1 = None if sorted_m5 is None else m9p.quantile_sorted(sorted_m5, 0.50)
        q2 = None if sorted_m15 is None else m9p.quantile_sorted(sorted_m15, 0.75)
        n1 = q1 is not None and ratio20[i5] is not None and float(ratio20[i5]) <= q1
        n2 = q2 is not None and float(m15_macd_bps[i15]) >= q2
        if not (n1 or n2):
            continue
        h4_percentile = None
        if ih4 >= 107:
            values = h4_rci[ih4 - 99:ih4 + 1]
            if all(value is not None for value in values):
                current = float(h4_rci[ih4])
                h4_percentile = sum(float(value) <= current for value in values if value is not None) / 100.0
        output.append({**row, "N1": n1, "N2": n2, "m5_index": i5, "m15_index": i15, "h4_index": ih4, "original_N6_percentile": h4_percentile})
    return output


def precompute_exit_context(m1: list[m9p.Bar], m15: list[m9p.Bar], h1: list[m9p.Bar]) -> tuple[dict[datetime, int], list[datetime], list[float], list[datetime], list[float]]:
    m1_index = {bar.time: i for i, bar in enumerate(m1)}
    m15_closes = [bar.close for bar in m15]
    m15_rci = m9p.rci_series(m15_closes, 9)
    rci_turn_down_times: list[datetime] = []
    for current_index in range(50, len(m15)):
        selected = current_index - 1
        current, previous, previous2 = m15_rci[selected], m15_rci[selected - 1], m15_rci[selected - 2]
        if current is not None and previous is not None and previous2 is not None and current < previous and previous >= previous2:
            rci_turn_down_times.append(m15[current_index].time)
    h1_closes = [bar.close for bar in h1]
    h1_macd = [fast - slow for fast, slow in zip(m9p.ema(h1_closes, 6), m9p.ema(h1_closes, 13))]
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    return m1_index, rci_turn_down_times, h1_macd, h1_close_times, m15_rci


def actual_n6(entry_time: datetime, h4: list[m9p.Bar], h4_rci: list[float | None], h4_close_times: list[datetime]) -> tuple[bool, float | None]:
    index = bisect.bisect_right(h4_close_times, entry_time) - 1
    if index < 107:
        return False, None
    values = h4_rci[index - 99:index + 1]
    if not all(value is not None for value in values):
        return False, None
    current = float(h4_rci[index])
    percentile = sum(float(value) <= current for value in values if value is not None) / 100.0
    return percentile > 0.25 and percentile <= 0.50, percentile


def build_reclaim_rows(
    n3_rows: list[dict[str, Any]], m1: list[m9p.Bar], m5: list[m9p.Bar], h1: list[m9p.Bar], h4: list[m9p.Bar],
    *, point: float, offset_atr: float, wait_minutes: int, runner_share: float, apply_n6_half_risk: bool,
) -> list[dict[str, Any]]:
    m1_index, runner_times, h1_macd, h1_close_times, _ = precompute_exit_context(m1, [], []) if False else (None, None, None, None, None)
    # Local context is intentionally built here once per call only from supplied closed histories.
    m1_index = {bar.time: i for i, bar in enumerate(m1)}
    m5_close_times = [bar.time + timedelta(minutes=5) for bar in m5]
    atr5 = wilder_atr14(m5)
    h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]
    h4_rci = m9p.rci_series([bar.close for bar in h4], 9)
    h1_closes = [bar.close for bar in h1]
    h1_macd = [fast - slow for fast, slow in zip(m9p.ema(h1_closes, 6), m9p.ema(h1_closes, 13))]
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    # Runner times use the unchanged canonical M15 history from the N3 rows' native exits; supplied below through global cache field.
    runner_times = RUNNER_TIMES
    output: list[dict[str, Any]] = []
    for row in n3_rows:
        proxy_time = m9p.parse_time(row["proxy_entry_time"])
        first_time = m9p.parse_time(row["turn_entry_time"])
        native_exit_time = m9p.parse_time(row["exit_time"])
        proxy_index = m1_index.get(proxy_time)
        first_index = m1_index.get(first_time)
        exit_index = m1_index.get(native_exit_time)
        if proxy_index is None or first_index is None or exit_index is None or exit_index <= first_index:
            continue
        i5 = bisect.bisect_right(m5_close_times, first_time) - 1
        if i5 < 0 or atr5[i5] is None or float(atr5[i5]) <= 0:
            continue
        primary_bid = m1[proxy_index].open
        level = primary_bid - offset_atr * float(atr5[i5])
        actual_index: int | None = first_index if m1[first_index].open >= level else None
        if actual_index is None:
            last_check_exclusive = min(exit_index - 1, first_index + wait_minutes)
            for closed_index in range(first_index, last_check_exclusive):
                if m1[closed_index].close >= level:
                    candidate = closed_index + 1
                    if candidate < exit_index and candidate <= first_index + wait_minutes:
                        actual_index = candidate
                    break
        if actual_index is None:
            continue
        actual_time = m1[actual_index].time
        entry_exec = m1[actual_index].open + m1[actual_index].spread * point
        native_exit_exec = m1[exit_index].open
        native_return = (native_exit_exec - entry_exec) / abs(entry_exec) * 10000.0
        h1_index = bisect.bisect_right(h1_close_times, native_exit_time) - 1
        h1_macd_up = h1_index > 0 and h1_macd[h1_index] > h1_macd[h1_index - 1]
        runner_return = native_return
        runner_exit_time: datetime | None = None
        if runner_share > 0 and h1_macd_up:
            position = bisect.bisect_left(runner_times, native_exit_time)
            if position < len(runner_times):
                candidate_time = runner_times[position]
                runner_index = m1_index.get(candidate_time)
                if runner_index is not None:
                    runner_exit_time = candidate_time
                    runner_return = (m1[runner_index].open - entry_exec) / abs(entry_exec) * 10000.0
        raw_return = (1.0 - runner_share) * native_return + runner_share * runner_return if h1_macd_up and runner_exit_time is not None else native_return
        n6, percentile = actual_n6(actual_time, h4, h4_rci, h4_close_times)
        risk_weight = 0.5 if apply_n6_half_risk and n6 else 1.0
        output.append({
            "trade_id": row["trade_id"],
            "proxy_primary_time": row["proxy_entry_time"],
            "first_turn_time": row["turn_entry_time"],
            "actual_entry_time": actual_time.strftime(m9p.TIME_FORMAT),
            "native_exit_time": row["exit_time"],
            "runner_exit_time": None if runner_exit_time is None else runner_exit_time.strftime(m9p.TIME_FORMAT),
            "reclaim_offset_atr": offset_atr,
            "wait_minutes": wait_minutes,
            "entry_delay_minutes": actual_index - first_index,
            "primary_bid": primary_bid,
            "reclaim_level": level,
            "entry_exec": entry_exec,
            "native_return_bps": native_return,
            "h1_macd_up_at_native_exit": h1_macd_up,
            "runner_share": runner_share,
            "runner_return_bps": runner_return,
            "N6_at_actual_entry": n6,
            "N6_percentile_at_actual_entry": percentile,
            "risk_weight": risk_weight,
            "raw_return_bps": raw_return,
            "weighted_return_bps": raw_return * risk_weight,
        })
    return output


def assert_close(label: str, actual: float, expected: float, tolerance: float = 1e-9) -> None:
    if abs(actual - expected) > tolerance:
        raise RuntimeError(f"M9X reproduction mismatch {label}: {actual} != {expected}")


def main() -> int:
    global RUNNER_TIMES
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    data_override = os.environ.get("M9X_GOLD_DATA_ROOT")
    if data_override:
        data_root = Path(data_override)
    else:
        metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
        data_root = Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"
    point = float(os.environ.get("M9X_POINT", str(POINT)))
    if not data_root.is_dir() or not math.isfinite(point):
        print(f"[M9X BLOCKED] data root or point unavailable: {data_root} point={point}")
        return 2
    try:
        paths: dict[str, Path] = {}
        for timeframe, (filename, expected_hash) in m9p.EXPECTED.items():
            path = data_root / filename
            if not path.is_file():
                raise RuntimeError(f"missing required GOLD file: {path}")
            actual = m9p.sha256(path)
            if actual != expected_hash:
                raise RuntimeError(f"SHA256 mismatch {filename}: {actual}")
            paths[timeframe] = path
        m1 = m9p.load_bars(paths["M1"])
        m5 = m9p.load_bars(paths["M5"])
        m15 = m9p.load_bars(paths["M15"])
        h1 = m9p.load_bars(paths["H1"])
        h4 = m9p.load_bars(paths["H4"])
        n3_rows = build_canonical_n3(m1, m5, m15, h4, point)
        m15_rci = m9p.rci_series([bar.close for bar in m15], 9)
        RUNNER_TIMES = []
        for current_index in range(50, len(m15)):
            selected = current_index - 1
            current, previous, previous2 = m15_rci[selected], m15_rci[selected - 1], m15_rci[selected - 2]
            if current is not None and previous is not None and previous2 is not None and current < previous and previous >= previous2:
                RUNNER_TIMES.append(m15[current_index].time)

        entry_only = build_reclaim_rows(n3_rows, m1, m5, h1, h4, point=point, offset_atr=REFERENCE_OFFSET_ATR, wait_minutes=REFERENCE_WAIT_MINUTES, runner_share=0.0, apply_n6_half_risk=False)
        entry_n6 = build_reclaim_rows(n3_rows, m1, m5, h1, h4, point=point, offset_atr=REFERENCE_OFFSET_ATR, wait_minutes=REFERENCE_WAIT_MINUTES, runner_share=0.0, apply_n6_half_risk=True)
        entry_runner = build_reclaim_rows(n3_rows, m1, m5, h1, h4, point=point, offset_atr=REFERENCE_OFFSET_ATR, wait_minutes=REFERENCE_WAIT_MINUTES, runner_share=0.50, apply_n6_half_risk=False)
        combined: dict[float, list[dict[str, Any]]] = {
            share: build_reclaim_rows(n3_rows, m1, m5, h1, h4, point=point, offset_atr=REFERENCE_OFFSET_ATR, wait_minutes=REFERENCE_WAIT_MINUTES, runner_share=share, apply_n6_half_risk=True)
            for share in RUNNER_SHARES
        }
        entry_metrics = metric_rows(entry_only, value_key="raw_return_bps")
        combined50 = metric_rows(combined[0.50])
        combined75 = metric_rows(combined[0.75])
        if len(n3_rows) != 1495:
            raise RuntimeError(f"canonical N3 count mismatch: {len(n3_rows)}")
        if len(entry_only) != EXPECTED_REFERENCE["entry_count"]:
            raise RuntimeError(f"reference entry count mismatch: {len(entry_only)}")
        assert_close("entry_pf", float(entry_metrics["profit_factor_bps"]), EXPECTED_REFERENCE["entry_pf"])
        assert_close("combined50_pf", float(combined50["profit_factor_bps"]), EXPECTED_REFERENCE["combined_50_pf"])
        assert_close("combined50_avg_win", float(combined50["average_win_bps"]), EXPECTED_REFERENCE["combined_50_avg_win"])
        assert_close("combined50_avg_loss", float(combined50["average_loss_bps"]), EXPECTED_REFERENCE["combined_50_avg_loss"])
        assert_close("combined50_dd", float(combined50["max_drawdown_bps"]), EXPECTED_REFERENCE["combined_50_dd"])
        assert_close("combined75_pf", float(combined75["profit_factor_bps"]), EXPECTED_REFERENCE["combined_75_pf"])

        stress_rows: list[dict[str, Any]] = []
        for offset in STRESS_OFFSETS:
            for wait in STRESS_WAITS:
                rows = build_reclaim_rows(n3_rows, m1, m5, h1, h4, point=point, offset_atr=offset, wait_minutes=wait, runner_share=0.50, apply_n6_half_risk=True)
                base = metric_rows(rows)
                cost2 = metric_rows(rows, extra_cost_bps=2.0)
                yearly = group_metrics(rows, "year")
                quarterly = group_metrics(rows, "quarter")
                stress_rows.append({
                    "reclaim_offset_atr": offset,
                    "wait_minutes": wait,
                    "count": base["count"],
                    "win_rate": base["win_rate"],
                    "profit_factor_bps": base["profit_factor_bps"],
                    "average_win_bps": base.get("average_win_bps"),
                    "average_loss_bps": base.get("average_loss_bps"),
                    "max_drawdown_bps": base["max_drawdown_bps"],
                    "extra_2bps_profit_factor": cost2["profit_factor_bps"],
                    "minimum_calendar_year_pf": min(float(row["profit_factor_bps"]) for row in yearly if row["profit_factor_bps"] is not None),
                    "minimum_quarter_pf": min(float(row["profit_factor_bps"]) for row in quarterly if row["profit_factor_bps"] is not None),
                })

        share_rows: list[dict[str, Any]] = []
        for share, rows in combined.items():
            base = metric_rows(rows)
            cost1 = metric_rows(rows, extra_cost_bps=1.0)
            cost2 = metric_rows(rows, extra_cost_bps=2.0)
            yearly = group_metrics(rows, "year")
            share_rows.append({
                "runner_share": share,
                **base,
                "extra_1bps_profit_factor": cost1["profit_factor_bps"],
                "extra_2bps_profit_factor": cost2["profit_factor_bps"],
                "minimum_calendar_year_pf": min(float(row["profit_factor_bps"]) for row in yearly if row["profit_factor_bps"] is not None),
            })

        reference_rows = combined[0.50]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_DETERMINISTIC_HISTORICAL_REPRODUCTION_ONLY",
            "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sample": "research-exposed historical GOLD; not independent forward validation",
            "canonical_n3_count": len(n3_rows),
            "reference": {
                "reclaim_offset_atr": REFERENCE_OFFSET_ATR,
                "wait_minutes": REFERENCE_WAIT_MINUTES,
                "entry_only": entry_metrics,
                "entry_plus_n6": metric_rows(entry_n6),
                "entry_plus_50pct_runner": metric_rows(entry_runner, value_key="raw_return_bps"),
                "combined_50pct_runner": combined50,
                "combined_75pct_runner": combined75,
            },
            "runner_share_sensitivity": share_rows,
            "stress": {
                "combination_count": len(stress_rows),
                "offsets": list(STRESS_OFFSETS),
                "wait_minutes": list(STRESS_WAITS),
            },
            "guardrails": {
                "closed_bars_only": True,
                "historical_spread_used": True,
                "commission": "NOT_MODELED",
                "swap": "NOT_MODELED",
                "m7c_formula_changed": False,
                "m8c_reset": False,
                "m9v_changed_or_reset": False,
                "automatic_live_promotion": False,
                "audit_only": True,
            },
        }
    except Exception as exc:
        print(f"[M9X BLOCKED] {type(exc).__name__}: {exc}")
        return 2

    out_root = Path(os.environ.get("M9X_OUTPUT_ROOT", str(local_root / "outputs" / "M9X")))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9X deterministically reproduces the historical M9W payoff-decoupling architecture. This sample is research-exposed and is NOT fresh forward validation. M9V is not changed or backfilled.\n",
        encoding="utf-8",
    )
    m9p.dump_json(archive / "01_summary.json", summary)
    m9p.write_csv(archive / "02_reference_combined_50pct_ledger.csv", reference_rows)
    m9p.write_csv(archive / "03_runner_share_sensitivity.csv", share_rows)
    m9p.write_csv(archive / "04_reclaim_neighborhood_stress.csv", stress_rows)
    m9p.write_csv(archive / "05_reference_yearly.csv", group_metrics(reference_rows, "year"))
    m9p.write_csv(archive / "06_reference_quarterly.csv", group_metrics(reference_rows, "quarter"))
    m9p.write_csv(archive / "07_reference_monthly.csv", group_metrics(reference_rows, "month"))
    m9p.dump_json(archive / "08_data_quality.json", {
        "data_root": str(data_root),
        "point": point,
        "hashes": {tf: {"file": m9p.EXPECTED[tf][0], "sha256": m9p.EXPECTED[tf][1]} for tf in m9p.EXPECTED},
        "closed_bars_only": True,
        "nearest_m1_fallback": False,
    })
    (archive / "09_audit.log").write_text("\n".join([
        "status=PASS_DETERMINISTIC_HISTORICAL_REPRODUCTION_ONLY",
        f"canonical_n3={len(n3_rows)}",
        f"reference_entry_count={len(entry_only)}",
        f"combined50_pf={combined50['profit_factor_bps']}",
        f"combined75_pf={combined75['profit_factor_bps']}",
        "m9v_changed_or_reset=false",
        "automatic_live_promotion=false",
        "",
    ]), encoding="utf-8")
    names = sorted(path.name for path in archive.iterdir() if path.is_file())
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(f"[M9X PASS] N3={len(n3_rows)} W1={len(entry_only)} COMBINED50_PF={combined50['profit_factor_bps']:.6f} COMBINED75_PF={combined75['profit_factor_bps']:.6f}")
    print("[M9X OUTPUT]", latest)
    return 0


RUNNER_TIMES: list[datetime] = []

if __name__ == "__main__":
    raise SystemExit(main())
