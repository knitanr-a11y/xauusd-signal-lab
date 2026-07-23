from __future__ import annotations

import csv
import json
import math
import os
import shutil
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
EXPECTED_FILES = {"XAUUSD": "goldsharp_m1.csv", "BTCUSD": "btcusdsharp_m1.csv"}
TIMEFRAMES = {"m5": 5, "h1": 60, "h4": 240}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)


def rank_average(values: list[float]) -> list[float]:
    pairs = sorted((v, i) for i, v in enumerate(values))
    ranks = [0.0] * len(values)
    j = 0
    while j < len(pairs):
        k = j + 1
        while k < len(pairs) and pairs[k][0] == pairs[j][0]:
            k += 1
        avg_rank = (j + 1 + k) / 2.0
        for m in range(j, k):
            ranks[pairs[m][1]] = avg_rank
        j = k
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    den = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    return None if den == 0 else sum(a * b for a, b in zip(dx, dy)) / den


def spearman(x: list[float], y: list[float]) -> float | None:
    return None if len(x) < 3 else pearson(rank_average(x), rank_average(y))


def rci(closes: list[float], idx: int, period: int) -> float | None:
    if idx - period + 1 < 0:
        return None
    window = closes[idx - period + 1 : idx + 1]
    corr = pearson([float(i + 1) for i in range(period)], rank_average(window))
    return None if corr is None else corr * 100.0


def load_m1(path: Path) -> list[dict[str, Any]]:
    raw = read_csv(path)
    expected = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    if not raw or list(raw[0].keys()) != expected:
        raise RuntimeError(f"unexpected/empty M1 file: {path}")
    out: list[dict[str, Any]] = []
    previous: datetime | None = None
    for r in raw:
        t = parse_time(r["time"])
        if previous is not None and t <= previous:
            raise RuntimeError(f"M1 time not strictly increasing: {path.name} {r['time']}")
        previous = t
        row = {
            "time": t,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "tick_volume": float(r["tick_volume"]),
            "spread": int(r["spread"]),
        }
        if any(not math.isfinite(row[k]) for k in ("open", "high", "low", "close")):
            raise RuntimeError(f"nonfinite M1 OHLC: {path.name} {r['time']}")
        out.append(row)
    return out


def bucket_start(t: datetime, minutes: int) -> datetime:
    minute_of_day = t.hour * 60 + t.minute
    start_minute = (minute_of_day // minutes) * minutes
    return t.replace(hour=start_minute // 60, minute=start_minute % 60, second=0, microsecond=0)


def aggregate(rows: list[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    groups: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[bucket_start(r["time"], minutes)].append(r)
    bars: list[dict[str, Any]] = []
    for start in sorted(groups):
        g = groups[start]
        bars.append({
            "start": start,
            "end": start + timedelta(minutes=minutes),
            "open": g[0]["open"],
            "high": max(x["high"] for x in g),
            "low": min(x["low"] for x in g),
            "close": g[-1]["close"],
            "tick_volume": sum(x["tick_volume"] for x in g),
            "m1_rows": len(g),
        })
    return bars


def asof_rci_features(bars: list[dict[str, Any]], boundary: datetime, prefix: str, direction: str) -> dict[str, Any]:
    idx = None
    for i, b in enumerate(bars):
        if b["end"] <= boundary:
            idx = i
        else:
            break
    if idx is None:
        raise RuntimeError(f"no closed {prefix} bar before {boundary.strftime(TIME_FORMAT)}")
    closes = [b["close"] for b in bars]
    if idx < 19:
        raise RuntimeError(f"insufficient closed {prefix} history for RCI before {boundary.strftime(TIME_FORMAT)}")
    vals: dict[int, float | None] = {p: rci(closes, idx, p) for p in (9, 14, 18)}
    cur9 = vals[9]
    prev9 = rci(closes, idx - 1, 9)
    prev2_9 = rci(closes, idx - 2, 9)
    d1 = None if cur9 is None or prev9 is None else cur9 - prev9
    prev_d = None if prev9 is None or prev2_9 is None else prev9 - prev2_9
    accel = None if d1 is None or prev_d is None else d1 - prev_d
    sign = 1.0 if direction == "LONG" else -1.0
    return {
        f"{prefix}_closed_bar_start": bars[idx]["start"].strftime(TIME_FORMAT),
        f"{prefix}_closed_bar_end": bars[idx]["end"].strftime(TIME_FORMAT),
        f"{prefix}_rci9": cur9,
        f"{prefix}_rci14": vals[14],
        f"{prefix}_rci18": vals[18],
        f"{prefix}_rci9_delta1": d1,
        f"{prefix}_rci9_previous_delta": prev_d,
        f"{prefix}_rci9_acceleration": accel,
        f"{prefix}_rci9_rising": None if d1 is None else d1 > 0,
        f"{prefix}_rci9_ge_80": None if cur9 is None else cur9 >= 80.0,
        f"{prefix}_rci9_le_minus80": None if cur9 is None else cur9 <= -80.0,
        f"{prefix}_directional_rci9": None if cur9 is None else sign * cur9,
        f"{prefix}_directional_rci9_delta1": None if d1 is None else sign * d1,
        f"{prefix}_directional_rci9_acceleration": None if accel is None else sign * accel,
    }


def group_stats(rows: list[dict[str, Any]], key: str, value_key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[str(r[key])].append(r)
    out = []
    for label, g in sorted(groups.items()):
        vals = [float(x[value_key]) for x in g if x.get(value_key) not in (None, "")]
        wins = [v for v in vals if v > 0]
        out.append({
            "grouping": key,
            "group": label,
            "count": len(g),
            "value": value_key,
            "mean": statistics.fmean(vals) if vals else None,
            "median": statistics.median(vals) if vals else None,
            "positive_fraction": len(wins) / len(vals) if vals else None,
        })
    return out


def main() -> int:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m8b = root / "outputs" / "M8B" / "LATEST"
    m8bz = root / "outputs" / "M8BZ" / "LATEST"
    trades_path = m8b / "03_extra_entry_trades.csv"
    meta_path = m8b / "06_symbol_metadata.json"
    turns_path = m8bz / "02_first_turn_candidates.csv"
    if not trades_path.is_file() or not meta_path.is_file() or not turns_path.is_file():
        print("[M8BZ2 BLOCKED] M8B or M8BZ LATEST inputs are missing")
        return 2

    trades = read_csv(trades_path)
    turns = read_csv(turns_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files_root = Path(meta.get("mt5_files_root", ""))
    if len(trades) != 18 or not files_root.is_dir():
        print("[M8BZ2 BLOCKED] frozen M8B population or MT5 Files root is invalid")
        return 2
    trade_map = {r["trade_id"]: r for r in trades}
    if len(trade_map) != 18 or len({r["trade_id"] for r in turns}) != len(turns):
        print("[M8BZ2 BLOCKED] duplicate trade ids in frozen inputs")
        return 2

    try:
        derived: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for ticker, filename in EXPECTED_FILES.items():
            m1 = load_m1(files_root / filename)
            derived[ticker] = {name: aggregate(m1, mins) for name, mins in TIMEFRAMES.items()}

        rows: list[dict[str, Any]] = []
        for turn in turns:
            tid = turn["trade_id"]
            trade = trade_map.get(tid)
            if trade is None:
                raise RuntimeError(f"M8BZ trade not in frozen M8B population: {tid}")
            ticker, direction = trade["ticker"], trade["direction"]
            signal_boundary = parse_time(trade["entry_server_open"])
            turn_boundary = parse_time(turn["candidate_entry_time"])
            row: dict[str, Any] = {
                "trade_id": tid,
                "ticker": ticker,
                "direction": direction,
                "signal_boundary": trade["entry_server_open"],
                "turn_boundary": turn["candidate_entry_time"],
                "initial_pullback_depth_bps": float(turn["pullback_depth_bps"]),
                "minutes_to_first_turn": int(float(turn["minutes_since_signal"])),
                "return_from_first_turn_to_frozen_exit_bps": float(turn["return_to_original_frozen_exit_bps"]),
                "mfe_from_first_turn_to_frozen_exit_bps": float(turn["forward_mfe_to_original_exit_bps"]),
                "mae_from_first_turn_to_frozen_exit_bps": float(turn["forward_mae_to_original_exit_bps"]),
                "turn_m1_rci9": float(turn["m1_rci9"]),
                "turn_m1_rci9_delta1": float(turn["m1_rci9_delta1"]),
            }
            for tf_name in ("m5", "h1", "h4"):
                row.update(asof_rci_features(derived[ticker][tf_name], signal_boundary, f"signal_{tf_name}", direction))
                row.update(asof_rci_features(derived[ticker][tf_name], turn_boundary, f"turn_{tf_name}", direction))
            row["signal_m5_directional_rci9_zone"] = (
                "GE_80" if float(row["signal_m5_directional_rci9"]) >= 80 else
                "50_TO_80" if float(row["signal_m5_directional_rci9"]) >= 50 else
                "MINUS50_TO_50" if float(row["signal_m5_directional_rci9"]) > -50 else
                "LE_MINUS50"
            )
            h1_up = float(row["turn_h1_directional_rci9_delta1"]) > 0
            h4_up = float(row["turn_h4_directional_rci9_delta1"]) > 0
            row["turn_htf_directional_rci9_slope_state"] = (
                "H1_AND_H4_WITH_TRADE" if h1_up and h4_up else
                "H1_ONLY_WITH_TRADE" if h1_up else
                "H4_ONLY_WITH_TRADE" if h4_up else
                "NEITHER_WITH_TRADE"
            )
            rows.append(row)
    except Exception as exc:
        print(f"[M8BZ2 BLOCKED] {exc}")
        return 2

    def corr(a: str, b: str) -> dict[str, Any]:
        pairs = [(float(r[a]), float(r[b])) for r in rows if r.get(a) not in (None, "") and r.get(b) not in (None, "")]
        return {"x": a, "y": b, "count": len(pairs), "spearman_rho": spearman([x for x, _ in pairs], [y for _, y in pairs])}

    correlations = [
        corr("signal_m5_directional_rci9", "initial_pullback_depth_bps"),
        corr("signal_m5_directional_rci9", "minutes_to_first_turn"),
        corr("turn_h1_directional_rci9_delta1", "return_from_first_turn_to_frozen_exit_bps"),
        corr("turn_h4_directional_rci9_delta1", "return_from_first_turn_to_frozen_exit_bps"),
        corr("turn_h1_directional_rci9_delta1", "mfe_from_first_turn_to_frozen_exit_bps"),
        corr("turn_h4_directional_rci9_delta1", "mfe_from_first_turn_to_frozen_exit_bps"),
    ]

    group_rows: list[dict[str, Any]] = []
    group_rows += group_stats(rows, "signal_m5_directional_rci9_zone", "initial_pullback_depth_bps")
    group_rows += group_stats(rows, "signal_m5_directional_rci9_zone", "return_from_first_turn_to_frozen_exit_bps")
    group_rows += group_stats(rows, "turn_htf_directional_rci9_slope_state", "return_from_first_turn_to_frozen_exit_bps")
    group_rows += group_stats(rows, "turn_htf_directional_rci9_slope_state", "mfe_from_first_turn_to_frozen_exit_bps")

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M8BZ2_MULTITIMEFRAME_RCI_CONTEXT_AUDIT",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_only": True,
        "frozen_trade_population": 18,
        "first_turn_rows_evaluated": len(rows),
        "hypotheses": {
            "signal_m5_upper_extreme_may_precede_pullback": "EXPLORATORY_ONLY",
            "turn_h1_h4_rci_slope_with_trade_may_support_continuation": "EXPLORATORY_ONLY",
        },
        "correlations": correlations,
        "guardrails": {
            "same_sample_is_validation": False,
            "fixed_rci_threshold_promotable": False,
            "user_hypothesis_assumed_true": False,
            "new_forward_validation_required": True,
            "existing_m8c_reset": False,
        },
    }
    quality = {
        "source": "M1-derived M5/H1/H4 using MT5 server time",
        "closed_bars_only": True,
        "signal_features_use_bars_ending_at_or_before_signal_boundary": True,
        "turn_features_use_bars_ending_at_or_before_candidate_entry_boundary": True,
        "nearest_bar_fallback": False,
        "future_outcomes_used_for_feature_creation": False,
        "m1_files_root": str(files_root),
    }

    out_root = root / "outputs" / "M8BZ2"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_trade_multitimeframe_context.csv", rows)
    write_csv(archive / "03_group_comparisons.csv", group_rows)
    write_csv(archive / "04_correlations.csv", correlations)
    dump_json(archive / "05_data_quality.json", quality)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M8BZ2 multi-timeframe RCI context audit. User hypotheses are exploratory only; no RCI threshold is promoted from this sample.\n",
        encoding="utf-8",
    )
    (archive / "06_audit.log").write_text(
        f"status=PASS_EXPLORATORY_ONLY\nrows={len(rows)}\nclosed_bars_only=true\nexisting_m8c_reset=false\n",
        encoding="utf-8",
    )
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_trade_multitimeframe_context.csv",
        "03_group_comparisons.csv", "04_correlations.csv", "05_data_quality.json", "06_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(f"[M8BZ2 PASS] rows={len(rows)}")
    print(f"[M8BZ2 OUTPUT] {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
