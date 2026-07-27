from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
M10A_PY = MR / "m10a" / "python"
if str(M10A_PY) not in sys.path:
    sys.path.insert(0, str(M10A_PY))

import frozen_core as frozen

STAGE = "M10W13_FROZEN_HISTORICAL_SHORT_ACTIVATION_INTERVAL_CALIBRATION_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w13_frozen_historical_short_activation_interval_calibration_contract_20260728.json"
TIME_FORMAT = frozen.TIME_FORMAT

M10P_THRESHOLDS = {
    "h1_macd_hist_bps_ge": 3.637199446,
    "h1_macd_line_bps_le": -7.667425443,
    "h1_ret3_bps_ge": 18.70087437,
    "d1_macd_hist_bps_ge": -14.25480242,
}
M10P2_THRESHOLDS = {
    "h4_ema20_30_bps_ge": 37.61355979,
    "h1_atr_pct100_ge": 0.8,
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def fmt(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


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


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10A_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = load_json(metadata_path) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def verify_and_load(data_root: Path) -> tuple[dict[str, list[frozen.Bar]], dict[str, str]]:
    needed = ("M15", "H1", "H4", "D1")
    bars: dict[str, list[frozen.Bar]] = {}
    hashes: dict[str, str] = {}
    for timeframe in needed:
        filename, expected_hash = frozen.EXPECTED_FILES[timeframe]
        path = data_root / filename
        if not path.is_file():
            raise RuntimeError(f"missing frozen GOLD file: {path}")
        actual_hash = frozen.sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"frozen SHA256 mismatch {timeframe}: {actual_hash} expected={expected_hash}")
        bars[timeframe] = frozen.load_bars(path)
        hashes[timeframe] = actual_hash
    return bars, hashes


def feature_arrays(bars: list[frozen.Bar]) -> tuple[list[float], list[float], list[float | None]]:
    closes = [float(bar.close) for bar in bars]
    fast = frozen.ema(closes, 6)
    slow = frozen.ema(closes, 13)
    line = [(a - b) / max(abs(close), 1e-12) * 10000.0 for a, b, close in zip(fast, slow, closes)]
    signal = frozen.ema(line, 4)
    hist = [a - b for a, b in zip(line, signal)]
    ret3: list[float | None] = [None] * len(bars)
    for i in range(3, len(bars)):
        previous = float(bars[i - 3].close)
        if previous != 0:
            ret3[i] = (float(bars[i].close) - previous) / abs(previous) * 10000.0
    return line, hist, ret3


def wilder_atr14(bars: list[frozen.Bar]) -> list[float | None]:
    tr: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            value = float(bar.high) - float(bar.low)
        else:
            previous = float(bars[i - 1].close)
            value = max(float(bar.high) - float(bar.low), abs(float(bar.high) - previous), abs(float(bar.low) - previous))
        tr.append(value)
    out: list[float | None] = [None] * len(bars)
    if len(bars) >= 14:
        out[13] = sum(tr[:14]) / 14.0
        for i in range(14, len(bars)):
            previous = out[i - 1]
            if previous is None:
                raise RuntimeError("ATR recursion lost state")
            out[i] = ((13.0 * previous) + tr[i]) / 14.0
    return out


def atr_percentile100(bars: list[frozen.Bar]) -> list[float | None]:
    atr = wilder_atr14(bars)
    out: list[float | None] = [None] * len(atr)
    for i in range(99, len(atr)):
        window = atr[i - 99:i + 1]
        if any(value is None or not math.isfinite(float(value)) for value in window):
            continue
        current = float(atr[i])
        values = [float(value) for value in window if value is not None]
        out[i] = sum(value <= current for value in values) / len(values)
    return out


def quantile(values: list[int], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = q * (len(ordered) - 1)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return float(ordered[lo])
    weight = position - lo
    return float(ordered[lo] * (1.0 - weight) + ordered[hi] * weight)


def zero_runs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    start_index: int | None = None
    for index, row in enumerate(rows):
        active = bool(row["all_pass"])
        if not active and start_index is None:
            start_index = index
        if active and start_index is not None:
            end_index = index - 1
            result.append({
                "start_index": start_index,
                "end_index": end_index,
                "length_decisions": end_index - start_index + 1,
                "start_decision_time": rows[start_index]["decision_time"],
                "end_decision_time": rows[end_index]["decision_time"],
                "position": "LEADING" if start_index == 0 else "BETWEEN",
            })
            start_index = None
    if start_index is not None:
        end_index = len(rows) - 1
        result.append({
            "start_index": start_index,
            "end_index": end_index,
            "length_decisions": end_index - start_index + 1,
            "start_decision_time": rows[start_index]["decision_time"],
            "end_decision_time": rows[end_index]["decision_time"],
            "position": "TRAILING",
        })
    return result


def summarize_family(rows: list[dict[str, Any]], current_zero: int, condition_names: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    activation_rows = [row for row in rows if bool(row["all_pass"])]
    activation_indices = [i for i, row in enumerate(rows) if bool(row["all_pass"])]
    runs = zero_runs(rows)
    lengths = [int(item["length_decisions"]) for item in runs]
    spacing = [activation_indices[i] - activation_indices[i - 1] for i in range(1, len(activation_indices))]
    yearly: dict[int, dict[str, int]] = defaultdict(lambda: {"eligible_decisions": 0, "activations": 0})
    for row in rows:
        year = datetime.strptime(str(row["decision_time"]), TIME_FORMAT).year
        yearly[year]["eligible_decisions"] += 1
        if bool(row["all_pass"]):
            yearly[year]["activations"] += 1
    yearly_rows = [
        {
            "year": year,
            **counts,
            "activation_rate": counts["activations"] / counts["eligible_decisions"] if counts["eligible_decisions"] else None,
        }
        for year, counts in sorted(yearly.items())
    ]
    pass_counts = {name: sum(bool(row[f"pass_{name}"]) for row in rows) for name in condition_names}
    empirical_percentile = None if not lengths else sum(length <= current_zero for length in lengths) / len(lengths)
    exceed_fraction = None if not lengths else sum(length >= current_zero for length in lengths) / len(lengths)
    max_run = max(lengths) if lengths else None
    p90 = quantile(lengths, 0.90)
    p95 = quantile(lengths, 0.95)
    p99 = quantile(lengths, 0.99)
    if max_run is None:
        classification = "NO_HISTORICAL_ZERO_RUNS_AVAILABLE"
    elif current_zero > max_run:
        classification = "EXCEEDS_FROZEN_HISTORICAL_MAX"
    elif p99 is not None and current_zero > p99:
        classification = "ABOVE_HISTORICAL_P99_WITHIN_MAX"
    elif p95 is not None and current_zero > p95:
        classification = "ABOVE_HISTORICAL_P95"
    elif p90 is not None and current_zero > p90:
        classification = "ABOVE_HISTORICAL_P90"
    else:
        classification = "WITHIN_HISTORICAL_P90_RANGE"
    summary = {
        "eligible_decision_count": len(rows),
        "activation_count": len(activation_rows),
        "activation_rate": len(activation_rows) / len(rows) if rows else None,
        "condition_pass_counts": pass_counts,
        "zero_run_count": len(runs),
        "zero_run_decision_length": {
            "median": quantile(lengths, 0.50),
            "p75": quantile(lengths, 0.75),
            "p90": p90,
            "p95": p95,
            "p99": p99,
            "max": max_run,
        },
        "inter_activation_spacing_decisions": {
            "count": len(spacing),
            "median": quantile(spacing, 0.50),
            "p90": quantile(spacing, 0.90),
            "p95": quantile(spacing, 0.95),
            "max": max(spacing) if spacing else None,
        },
        "current_prospective_zero_match_decisions": current_zero,
        "current_vs_historical_zero_runs": {
            "empirical_fraction_historical_runs_le_current": empirical_percentile,
            "empirical_fraction_historical_runs_ge_current": exceed_fraction,
            "classification": classification,
            "descriptive_only": True,
        },
        "yearly": yearly_rows,
    }
    return summary, activation_rows, runs


def build_m10p_rows(bars: dict[str, list[frozen.Bar]]) -> list[dict[str, Any]]:
    h1, d1 = bars["H1"], bars["D1"]
    h1_line, h1_hist, h1_ret3 = feature_arrays(h1)
    _, d1_hist, _ = feature_arrays(d1)
    d1_close_times = [bar.time + timedelta(days=1) for bar in d1]
    rows: list[dict[str, Any]] = []
    for i in range(3, len(h1) - 1):
        decision = h1[i + 1].time
        id1 = bisect.bisect_right(d1_close_times, decision) - 1
        if id1 < 0 or h1_ret3[i] is None:
            continue
        values = {
            "h1_macd_hist_bps_ge": float(h1_hist[i]),
            "h1_macd_line_bps_le": float(h1_line[i]),
            "h1_ret3_bps_ge": float(h1_ret3[i]),
            "d1_macd_hist_bps_ge": float(d1_hist[id1]),
        }
        flags = {
            "h1_macd_hist_bps_ge": values["h1_macd_hist_bps_ge"] >= M10P_THRESHOLDS["h1_macd_hist_bps_ge"],
            "h1_macd_line_bps_le": values["h1_macd_line_bps_le"] <= M10P_THRESHOLDS["h1_macd_line_bps_le"],
            "h1_ret3_bps_ge": values["h1_ret3_bps_ge"] >= M10P_THRESHOLDS["h1_ret3_bps_ge"],
            "d1_macd_hist_bps_ge": values["d1_macd_hist_bps_ge"] >= M10P_THRESHOLDS["d1_macd_hist_bps_ge"],
        }
        row: dict[str, Any] = {"decision_time": fmt(decision), "h1_source_open": fmt(h1[i].time), "d1_source_open": fmt(d1[id1].time)}
        for name, value in values.items():
            row[f"value_{name}"] = value
            row[f"pass_{name}"] = flags[name]
        row["all_pass"] = all(flags.values())
        rows.append(row)
    return rows


def build_m10p2_rows(bars: dict[str, list[frozen.Bar]]) -> list[dict[str, Any]]:
    m15, h1, h4 = bars["M15"], bars["H1"], bars["H4"]
    h1_atrp = atr_percentile100(h1)
    h4_closes = [float(bar.close) for bar in h4]
    h4_ema20 = frozen.ema(h4_closes, 20)
    h4_ema30 = frozen.ema(h4_closes, 30)
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]
    rows: list[dict[str, Any]] = []
    for i in range(120, len(m15) - 1):
        decision = m15[i + 1].time
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        ih4 = bisect.bisect_right(h4_close_times, decision) - 1
        if ih1 < 0 or ih4 < 0 or h1_atrp[ih1] is None:
            continue
        h4_close = float(h4[ih4].close)
        if h4_close == 0:
            continue
        h4_stack = (float(h4_ema20[ih4]) - float(h4_ema30[ih4])) / abs(h4_close) * 10000.0
        atrp = float(h1_atrp[ih1])
        flags = {
            "h4_ema20_30_bps_ge": h4_stack >= M10P2_THRESHOLDS["h4_ema20_30_bps_ge"],
            "h1_atr_pct100_ge": atrp >= M10P2_THRESHOLDS["h1_atr_pct100_ge"],
        }
        rows.append({
            "decision_time": fmt(decision),
            "h1_source_open": fmt(h1[ih1].time),
            "h4_source_open": fmt(h4[ih4].time),
            "value_h4_ema20_30_bps_ge": h4_stack,
            "pass_h4_ema20_30_bps_ge": flags["h4_ema20_30_bps_ge"],
            "value_h1_atr_pct100_ge": atrp,
            "pass_h1_atr_pct100_ge": flags["h1_atr_pct100_ge"],
            "all_pass": all(flags.values()),
        })
    return rows


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W13"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W13 contract")
        data_root = resolve_data_root(local_root)
        if not data_root.is_dir():
            raise RuntimeError(f"frozen GOLD data root unavailable: {data_root}")
        bars, hashes = verify_and_load(data_root)
        m10p_rows = build_m10p_rows(bars)
        m10p2_rows = build_m10p2_rows(bars)
        current_m10p = int(contract["families"]["M10P_C056_G013"]["current_zero_match_decisions_from_M10W12"])
        current_m10p2 = int(contract["families"]["M10P2_C0212"]["current_zero_match_decisions_from_M10W12"])
        s1, a1, r1 = summarize_family(m10p_rows, current_m10p, list(M10P_THRESHOLDS))
        s2, a2, r2 = summarize_family(m10p2_rows, current_m10p2, list(M10P2_THRESHOLDS))
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_FROZEN_HISTORICAL_ACTIVATION_INTERVAL_CALIBRATION_AUDIT_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "frozen_data_root": str(data_root),
            "verified_sha256": hashes,
            "research_exposed_history": True,
            "fresh_forward_evidence": False,
            "trade_outcomes_read": False,
            "M10P_C056_G013": s1,
            "M10P2_C0212": s2,
            "interpretation": {
                "purpose": "Historical waiting-time calibration only. Do not infer PF/WR/expectancy and do not alter frozen thresholds or starts.",
                "threshold_change_allowed": False,
                "performance_inference_allowed": False,
                "historical_activation_density_is_not_fresh_support": True,
            },
            "guardrails": contract["safety"],
        }
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W13 frozen historical activation-interval calibration only. No trade outcomes, PF/PnL, threshold refit, start reset, or forward backfill.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_m10p_activation_times.csv", a1)
        write_csv(archive / "03_m10p_zero_runs.csv", r1)
        write_csv(archive / "04_m10p2_activation_times.csv", a2)
        write_csv(archive / "05_m10p2_zero_runs.csv", r2)
        (archive / "06_audit.log").write_text("\n".join([
            "status=PASS_FROZEN_HISTORICAL_ACTIVATION_INTERVAL_CALIBRATION_AUDIT_ONLY",
            f"M10P_eligible={len(m10p_rows)} activations={len(a1)} current_zero={current_m10p}",
            f"M10P2_eligible={len(m10p2_rows)} activations={len(a2)} current_zero={current_m10p2}",
            "trade_outcomes_read=false",
            "pf_or_pnl_computed=false",
            "threshold_refit=false",
            "start_reset=false",
            "modify_running_monitors=false",
            "historical_backfill_into_forward=false",
            "",
        ]), encoding="utf-8")
        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt","01_summary.json","02_m10p_activation_times.csv","03_m10p_zero_runs.csv","04_m10p2_activation_times.csv","05_m10p2_zero_runs.csv","06_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)
        print(f"[M10W13 PASS] M10P activations={len(a1)}/{len(m10p_rows)} current_zero={current_m10p}")
        print(f"[M10W13 PASS] M10P2 activations={len(a2)}/{len(m10p2_rows)} current_zero={current_m10p2}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W13 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No runtime/start/threshold/monitor modification was attempted.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
