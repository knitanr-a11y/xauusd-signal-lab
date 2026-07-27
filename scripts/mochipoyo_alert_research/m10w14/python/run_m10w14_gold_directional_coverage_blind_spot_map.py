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
M10W13_PY = MR / "m10w13" / "python"
for directory in (M10A_PY, M10W13_PY):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import frozen_core as frozen
import run_m10w13_frozen_historical_short_activation_interval_calibration as short_hist

STAGE = "M10W14_GOLD_DIRECTIONAL_COVERAGE_AND_BLIND_SPOT_MAP_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w14_gold_directional_coverage_blind_spot_map_contract_20260728.json"
TIME_FORMAT = frozen.TIME_FORMAT
TURN_LOOKBACK = frozen.TURN_LOOKBACK


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


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
    bars: dict[str, list[frozen.Bar]] = {}
    hashes: dict[str, str] = {}
    for timeframe in ("M1", "M5", "M15", "H1", "H4", "D1"):
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


def causal_first_turn_candidates(pairs: list[dict[str, Any]], m1: list[frozen.Bar], prefix: str) -> list[dict[str, Any]]:
    """Reproduce the frozen first-turn timestamp logic without computing trade returns.

    Episode entry/exit boundaries come from the frozen alert-state machine. Candidate
    timestamp conditions use only observations available at or before the first-turn.
    """
    index = {bar.time: position for position, bar in enumerate(m1)}
    output: list[dict[str, Any]] = []
    for trade_number, pair in enumerate(pairs, start=1):
        if pair["direction"] != "LONG":
            continue
        if pair["entry_time"] not in index or pair["exit_time"] not in index:
            continue
        entry_index = index[pair["entry_time"]]
        exit_index = index[pair["exit_time"]]
        if exit_index <= entry_index:
            continue
        signal_bid = float(m1[entry_index].open)
        for current_index in range(entry_index + 1, exit_index):
            if current_index + 1 >= exit_index:
                break
            history = m1[max(0, current_index - TURN_LOOKBACK):current_index]
            if len(history) < TURN_LOOKBACK:
                continue
            previous = m1[current_index - 1]
            current = m1[current_index]
            candidate = (
                previous.low <= min(bar.low for bar in history)
                and previous.low < signal_bid
                and current.close > previous.close
            )
            if not candidate:
                continue
            turn_bar = m1[current_index + 1]
            output.append({
                "trade_id": f"{prefix}_T{trade_number:06d}",
                "direction": "LONG",
                "proxy_entry_time": pair["entry_time"].strftime(TIME_FORMAT),
                "turn_entry_time": turn_bar.time.strftime(TIME_FORMAT),
                "exit_time": pair["exit_time"].strftime(TIME_FORMAT),
            })
            break
    return output


def build_long_branches(bars: dict[str, list[frozen.Bar]]) -> dict[str, list[dict[str, Any]]]:
    close_times = {
        "M5": [bar.time + timedelta(minutes=5) for bar in bars["M5"]],
        "M15": [bar.time + timedelta(minutes=15) for bar in bars["M15"]],
        "H1": [bar.time + timedelta(hours=1) for bar in bars["H1"]],
        "H4": [bar.time + timedelta(hours=4) for bar in bars["H4"]],
        "D1": [bar.time + timedelta(days=1) for bar in bars["D1"]],
    }
    turns: dict[str, list[dict[str, Any]]] = {}
    for tf in ("M5", "M15", "H1", "H4"):
        pairs = frozen.replay_m7c(bars[tf])
        turns[tf] = causal_first_turn_candidates(pairs, bars["M1"], f"M10W14_{tf}")

    frozen.enrich_indices(turns["M5"], close_times, ("M5", "M15", "H1"))
    frozen.enrich_indices(turns["M15"], close_times, ("M5", "M15"))
    frozen.enrich_indices(turns["H1"], close_times, ("H4", "D1"))
    frozen.enrich_indices(turns["H4"], close_times, ("D1",))

    ratio20_m5 = frozen.m5_ratio20(bars["M5"])
    macd = {tf: frozen.macd_bps(bars[tf]) for tf in ("M5", "M15", "H1", "H4", "D1")}
    rci9_h1 = frozen.rci_series([bar.close for bar in bars["H1"]], 9)
    rci9_d1 = frozen.rci_series([bar.close for bar in bars["D1"]], 9)
    d1_closes = [bar.close for bar in bars["D1"]]
    ema20_d1 = frozen.ema(d1_closes, 20)
    ema30_d1 = frozen.ema(d1_closes, 30)
    ema40_d1 = frozen.ema(d1_closes, 40)

    return {
        "LONG_M5_S1": frozen.select_s1(turns["M5"], ratio20_m5, macd, rci9_h1),
        "LONG_M15_S2": frozen.select_s2(turns["M15"], ratio20_m5, macd["M15"]),
        "LONG_H1_S3": frozen.select_s3(turns["H1"], macd["H4"], macd["D1"]),
        "LONG_H4_S4": frozen.select_s4(turns["H4"], rci9_d1, ema20_d1, ema30_d1, ema40_d1),
    }


def floor_m15(value: datetime) -> datetime:
    return value.replace(minute=(value.minute // 15) * 15, second=0, microsecond=0)


def sign_bucket(value: float) -> str:
    if value > 0:
        return "POSITIVE"
    if value < 0:
        return "NEGATIVE"
    return "ZERO"


def atr_bucket(value: float) -> str:
    if value < 0.33:
        return "LOW_LT_0P33"
    if value < 0.67:
        return "MID_0P33_TO_LT_0P67"
    return "HIGH_GE_0P67"


def d1_stack_bucket(e20: float, e30: float, e40: float) -> str:
    if e20 > e30 > e40:
        return "BULLISH_20_GT_30_GT_40"
    if e20 < e30 < e40:
        return "BEARISH_20_LT_30_LT_40"
    return "MIXED"


def build_grid(
    bars: dict[str, list[frozen.Bar]],
    family_bins: dict[str, set[datetime]],
) -> list[dict[str, Any]]:
    h1 = bars["H1"]
    h4 = bars["H4"]
    d1 = bars["D1"]
    h1_line, _, _ = short_hist.feature_arrays(h1)
    h1_atrp = short_hist.atr_percentile100(h1)
    h4_closes = [float(bar.close) for bar in h4]
    h4_ema20 = frozen.ema(h4_closes, 20)
    h4_ema30 = frozen.ema(h4_closes, 30)
    d1_closes = [float(bar.close) for bar in d1]
    d1_ema20 = frozen.ema(d1_closes, 20)
    d1_ema30 = frozen.ema(d1_closes, 30)
    d1_ema40 = frozen.ema(d1_closes, 40)
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]
    d1_close_times = [bar.time + timedelta(days=1) for bar in d1]

    rows: list[dict[str, Any]] = []
    for bar in bars["M15"]:
        decision = bar.time
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        ih4 = bisect.bisect_right(h4_close_times, decision) - 1
        id1 = bisect.bisect_right(d1_close_times, decision) - 1
        if ih1 < 0 or ih4 < 0 or id1 < 0:
            continue
        if h1_atrp[ih1] is None:
            continue
        h4_close = float(h4[ih4].close)
        if h4_close == 0:
            continue
        h4_spread = (float(h4_ema20[ih4]) - float(h4_ema30[ih4])) / abs(h4_close) * 10000.0
        family_presence = {name: decision in bins for name, bins in family_bins.items()}
        long_any = any(value for name, value in family_presence.items() if name.startswith("LONG_"))
        short_any = any(value for name, value in family_presence.items() if name.startswith("SHORT_"))
        if long_any and short_any:
            coverage_class = "BOTH"
        elif long_any:
            coverage_class = "LONG_ONLY"
        elif short_any:
            coverage_class = "SHORT_ONLY"
        else:
            coverage_class = "NEITHER"
        row: dict[str, Any] = {
            "decision_time": decision.strftime(TIME_FORMAT),
            "year": decision.year,
            "d1_ema_stack": d1_stack_bucket(float(d1_ema20[id1]), float(d1_ema30[id1]), float(d1_ema40[id1])),
            "h4_ema20_minus_ema30_sign": sign_bucket(h4_spread),
            "h1_macd_line_sign": sign_bucket(float(h1_line[ih1])),
            "h1_atr_pct100_tercile": atr_bucket(float(h1_atrp[ih1])),
            "coverage_class": coverage_class,
            "long_any": long_any,
            "short_any": short_any,
        }
        row.update(family_presence)
        rows.append(row)
    return rows


def aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    output: list[dict[str, Any]] = []
    for group_key, items in grouped.items():
        counts = {name: sum(row["coverage_class"] == name for row in items) for name in ("LONG_ONLY", "SHORT_ONLY", "BOTH", "NEITHER")}
        n = len(items)
        result: dict[str, Any] = {key: value for key, value in zip(keys, group_key)}
        result.update({
            "decision_count": n,
            **{f"{name.lower()}_count": count for name, count in counts.items()},
            **{f"{name.lower()}_fraction": count / n for name, count in counts.items()},
            "any_direction_fraction": 1.0 - counts["NEITHER"] / n,
            "long_any_fraction": sum(bool(row["long_any"]) for row in items) / n,
            "short_any_fraction": sum(bool(row["short_any"]) for row in items) / n,
        })
        output.append(result)
    return sorted(output, key=lambda row: (-int(row["neither_count"]), -int(row["decision_count"]), tuple(str(row[key]) for key in keys)))


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W14"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W14 contract")
        data_root = resolve_data_root(local_root)
        if not data_root.is_dir():
            raise RuntimeError(f"frozen GOLD data root unavailable: {data_root}")
        bars, hashes = verify_and_load(data_root)

        long_branches = build_long_branches(bars)
        short1 = [row for row in short_hist.build_m10p_rows(bars) if bool(row["all_pass"])]
        short2 = [row for row in short_hist.build_m10p2_rows(bars) if bool(row["all_pass"])]

        family_times: dict[str, list[str]] = {
            **{name: [str(row["turn_entry_time"]) for row in rows] for name, rows in long_branches.items()},
            "SHORT_M10P_C056_G013": [str(row["decision_time"]) for row in short1],
            "SHORT_M10P2_C0212": [str(row["decision_time"]) for row in short2],
        }
        family_bins = {
            name: {floor_m15(datetime.strptime(value, TIME_FORMAT)) for value in values}
            for name, values in family_times.items()
        }
        grid = build_grid(bars, family_bins)
        if not grid:
            raise RuntimeError("coverage grid is empty")

        overall_counts = {name: sum(row["coverage_class"] == name for row in grid) for name in ("LONG_ONLY", "SHORT_ONLY", "BOTH", "NEITHER")}
        n = len(grid)
        family_counts = {name: sum(bool(row[name]) for row in grid) for name in family_bins}
        regime_keys = ("d1_ema_stack", "h4_ema20_minus_ema30_sign", "h1_macd_line_sign", "h1_atr_pct100_tercile")
        regime_rows = aggregate(grid, regime_keys)
        yearly_rows = aggregate(grid, ("year",))
        family_rows = [{"family": name, "m15_window_presence_count": count, "m15_window_presence_rate": count / n} for name, count in sorted(family_counts.items())]

        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_OUTCOME_BLIND_DIRECTIONAL_COVERAGE_MAP_AUDIT_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "frozen_data_root": str(data_root),
            "verified_sha256": hashes,
            "canonical_grid": "M15_SERVER_TIME_WINDOWS",
            "eligible_grid_windows": n,
            "coverage_counts": overall_counts,
            "coverage_rates": {name: count / n for name, count in overall_counts.items()},
            "family_m15_presence_counts": family_counts,
            "regime_group_count": len(regime_rows),
            "top_neither_regimes_preview": regime_rows[:20],
            "interpretation": {
                "coverage_is_not_edge": True,
                "trade_outcomes_read": False,
                "pf_or_pnl_computed": False,
                "future_path_labels_used": False,
                "threshold_change_allowed": False,
                "new_candidate_formula_created": False,
                "next": "Review structural blind spots first. Only after review may M10W15 pre-register independent blind-spot hypotheses before any performance evaluation.",
            },
            "guardrails": contract["safety"],
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W14 outcome-blind GOLD directional coverage map. Candidate availability only; no trade outcomes, PF/PnL, future labels, threshold rescue, or monitor changes.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_m15_coverage_grid.csv", grid)
        write_csv(archive / "03_regime_coverage_map.csv", regime_rows)
        write_csv(archive / "04_yearly_coverage.csv", yearly_rows)
        write_csv(archive / "05_family_presence.csv", family_rows)
        (archive / "06_audit.log").write_text("\n".join([
            "status=PASS_OUTCOME_BLIND_DIRECTIONAL_COVERAGE_MAP_AUDIT_ONLY",
            f"eligible_grid_windows={n}",
            f"long_only={overall_counts['LONG_ONLY']}",
            f"short_only={overall_counts['SHORT_ONLY']}",
            f"both={overall_counts['BOTH']}",
            f"neither={overall_counts['NEITHER']}",
            "trade_outcomes_read=false",
            "pf_or_pnl_computed=false",
            "future_path_labels_used=false",
            "threshold_refit=false",
            "new_candidate_formula_created=false",
            "modify_running_monitors=false",
            "",
        ]), encoding="utf-8")

        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_m15_coverage_grid.csv", "03_regime_coverage_map.csv", "04_yearly_coverage.csv", "05_family_presence.csv", "06_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)
        print(f"[M10W14 PASS] windows={n} coverage={overall_counts}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W14 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No outcome analysis, threshold/start/runtime/monitor modification was attempted.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
