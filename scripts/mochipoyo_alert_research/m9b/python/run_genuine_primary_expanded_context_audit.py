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
EXPECTED_TRADE_COUNT = 43
EXPECTED_FILES = {"XAUUSD": "goldsharp_m1.csv", "BTCUSD": "btcusdsharp_m1.csv"}
TIMEFRAMES = {"m5": 5, "h1": 60, "h4": 240}
TURN_LOOKBACK = 5


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


def bps(delta: float, reference: float) -> float:
    if reference == 0:
        raise RuntimeError("zero price reference")
    return delta / reference * 10000.0


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
            "time_text": r["time"],
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "tick_volume": float(r["tick_volume"]),
            "spread": int(r["spread"]),
        }
        if any(not math.isfinite(float(row[k])) for k in ("open", "high", "low", "close")):
            raise RuntimeError(f"nonfinite M1 OHLC: {path.name} {r['time']}")
        if row["spread"] < 0:
            raise RuntimeError(f"negative spread: {path.name} {r['time']}")
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
    for i, bar in enumerate(bars):
        if bar["end"] <= boundary:
            idx = i
        else:
            break
    if idx is None or idx < 19:
        raise RuntimeError(f"insufficient closed {prefix} history before {boundary.strftime(TIME_FORMAT)}")
    closes = [b["close"] for b in bars]
    r9, r14, r18 = rci(closes, idx, 9), rci(closes, idx, 14), rci(closes, idx, 18)
    p9 = rci(closes, idx - 1, 9)
    p2 = rci(closes, idx - 2, 9)
    d1 = None if r9 is None or p9 is None else r9 - p9
    pd = None if p9 is None or p2 is None else p9 - p2
    accel = None if d1 is None or pd is None else d1 - pd
    sign = 1.0 if direction == "LONG" else -1.0
    return {
        f"{prefix}_closed_bar_start": bars[idx]["start"].strftime(TIME_FORMAT),
        f"{prefix}_closed_bar_end": bars[idx]["end"].strftime(TIME_FORMAT),
        f"{prefix}_rci9": r9,
        f"{prefix}_rci14": r14,
        f"{prefix}_rci18": r18,
        f"{prefix}_rci9_delta1": d1,
        f"{prefix}_rci9_acceleration": accel,
        f"{prefix}_directional_rci9": None if r9 is None else sign * r9,
        f"{prefix}_directional_rci9_delta1": None if d1 is None else sign * d1,
        f"{prefix}_directional_rci9_acceleration": None if accel is None else sign * accel,
    }


def execution_entry(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "LONG" else row["open"]


def execution_exit(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "SHORT" else row["open"]


def directional_trade_return(direction: str, entry: float, exit_price: float) -> float:
    return bps(exit_price - entry, entry) if direction == "LONG" else bps(entry - exit_price, entry)


def excursions(direction: str, entry_exec: float, rows: list[dict[str, Any]], point: float) -> tuple[float, float]:
    favorable: list[float] = []
    adverse: list[float] = []
    for row in rows:
        if direction == "LONG":
            favorable.append(bps(row["high"] - entry_exec, entry_exec))
            adverse.append(bps(row["low"] - entry_exec, entry_exec))
        else:
            ask_high = row["high"] + row["spread"] * point
            ask_low = row["low"] + row["spread"] * point
            favorable.append(bps(entry_exec - ask_low, entry_exec))
            adverse.append(bps(entry_exec - ask_high, entry_exec))
    return max(favorable), min(adverse)


def is_turn_candidate(direction: str, rows: list[dict[str, Any]], idx: int, signal_bid: float) -> bool:
    if idx < 1:
        return False
    prev, current = rows[idx - 1], rows[idx]
    start = max(0, idx - TURN_LOOKBACK)
    history = rows[start:idx]
    if len(history) < TURN_LOOKBACK:
        return False
    if direction == "LONG":
        return prev["low"] <= min(r["low"] for r in history) and prev["low"] < signal_bid and current["close"] > prev["close"]
    return prev["high"] >= max(r["high"] for r in history) and prev["high"] > signal_bid and current["close"] < prev["close"]


def pullback_depth(direction: str, signal_bid: float, rows: list[dict[str, Any]]) -> float:
    if direction == "LONG":
        extreme = min(r["low"] for r in rows)
        return bps(signal_bid - extreme, signal_bid)
    extreme = max(r["high"] for r in rows)
    return bps(extreme - signal_bid, signal_bid)


def pf(values: list[float]) -> float | None:
    wins = sum(v for v in values if v > 0)
    losses = abs(sum(v for v in values if v < 0))
    return None if losses == 0 else wins / losses


def metric_block(rows: list[dict[str, Any]], return_key: str, mfe_key: str | None = None, mae_key: str | None = None) -> dict[str, Any]:
    vals = [float(r[return_key]) for r in rows if r.get(return_key) not in (None, "")]
    out: dict[str, Any] = {
        "count": len(vals),
        "win_rate": (sum(v > 0 for v in vals) / len(vals)) if vals else None,
        "profit_factor_bps": pf(vals) if vals else None,
        "net_bps": sum(vals),
        "mean_bps": statistics.fmean(vals) if vals else None,
        "median_bps": statistics.median(vals) if vals else None,
    }
    if mfe_key:
        m = [float(r[mfe_key]) for r in rows if r.get(mfe_key) not in (None, "")]
        out["mean_mfe_bps"] = statistics.fmean(m) if m else None
    if mae_key:
        m = [float(r[mae_key]) for r in rows if r.get(mae_key) not in (None, "")]
        out["mean_mae_bps"] = statistics.fmean(m) if m else None
    return out


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    repo_root = Path(__file__).resolve().parents[4]
    manifest_path = repo_root / "config" / "mochipoyo_alert_research" / "m9b_frozen_genuine_primary_pairs_20260724.json"
    meta_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not manifest_path.is_file() or not meta_path.is_file():
        print("[M9B BLOCKED] frozen manifest or M8B symbol metadata is missing")
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pairs = manifest.get("pairs", [])
    if len(pairs) != EXPECTED_TRADE_COUNT or len({int(p["primary_raw_id"]) for p in pairs}) != EXPECTED_TRADE_COUNT:
        print("[M9B BLOCKED] frozen genuine PRIMARY manifest is invalid")
        return 2

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print(f"[M9B BLOCKED] MT5 Files root unavailable: {files_root}")
        return 2

    try:
        m1: dict[str, list[dict[str, Any]]] = {}
        index: dict[str, dict[str, int]] = {}
        derived: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for ticker, filename in EXPECTED_FILES.items():
            rows = load_m1(files_root / filename)
            m1[ticker] = rows
            index[ticker] = {row["time_text"]: i for i, row in enumerate(rows)}
            derived[ticker] = {name: aggregate(rows, mins) for name, mins in TIMEFRAMES.items()}

        trade_rows: list[dict[str, Any]] = []
        turn_rows: list[dict[str, Any]] = []

        for pair in pairs:
            ticker = pair["ticker"]
            direction = pair["direction"]
            point = float(meta["symbols"][ticker]["point"])
            entry_text = pair["entry_server_open"]
            exit_text = pair["exit_server_open"]
            if entry_text not in index[ticker] or exit_text not in index[ticker]:
                raise RuntimeError(f"exact M1 entry/exit missing for primary {pair['primary_raw_id']}")
            ei, xi = index[ticker][entry_text], index[ticker][exit_text]
            if xi <= ei:
                raise RuntimeError(f"invalid source entry/exit ordering for primary {pair['primary_raw_id']}")

            rows = m1[ticker]
            signal_bid = rows[ei]["open"]
            entry_exec = execution_entry(direction, rows[ei], point)
            exit_exec = execution_exit(direction, rows[xi], point)
            source_return = directional_trade_return(direction, entry_exec, exit_exec)
            source_mfe, source_mae = excursions(direction, entry_exec, rows[ei:xi + 1], point)

            base: dict[str, Any] = {
                **pair,
                "entry_bid_open": signal_bid,
                "entry_exec_price": entry_exec,
                "exit_exec_price": exit_exec,
                "source_return_bps": source_return,
                "source_outcome": "WIN" if source_return > 0 else "LOSS" if source_return < 0 else "FLAT",
                "source_mfe_bps": source_mfe,
                "source_mae_bps": source_mae,
                "holding_minutes_clock": int((rows[xi]["time"] - rows[ei]["time"]).total_seconds() // 60),
            }
            for tf in ("m5", "h1", "h4"):
                base.update(asof_rci_features(derived[ticker][tf], rows[ei]["time"], f"signal_{tf}", direction))
            base["signal_m5_directional_rci9_zone"] = (
                "GE_80" if float(base["signal_m5_directional_rci9"]) >= 80 else
                "50_TO_80" if float(base["signal_m5_directional_rci9"]) >= 50 else
                "MINUS50_TO_50" if float(base["signal_m5_directional_rci9"]) > -50 else
                "LE_MINUS50"
            )

            first_turn: dict[str, Any] | None = None
            for i in range(ei + 1, xi):
                if i + 1 >= xi:
                    break
                if not is_turn_candidate(direction, rows, i, signal_bid):
                    continue
                turn_entry_idx = i + 1
                turn_entry_exec = execution_entry(direction, rows[turn_entry_idx], point)
                turn_exit_exec = execution_exit(direction, rows[xi], point)
                turn_return = directional_trade_return(direction, turn_entry_exec, turn_exit_exec)
                turn_mfe, turn_mae = excursions(direction, turn_entry_exec, rows[turn_entry_idx:xi + 1], point)
                first_turn = {
                    "primary_raw_id": pair["primary_raw_id"],
                    "exit_raw_id": pair["exit_raw_id"],
                    "ticker": ticker,
                    "direction": direction,
                    "signal_boundary": entry_text,
                    "turn_confirmation_time": rows[i]["time_text"],
                    "turn_entry_time": rows[turn_entry_idx]["time_text"],
                    "source_exit_time": exit_text,
                    "initial_pullback_depth_bps": pullback_depth(direction, signal_bid, rows[ei:i + 1]),
                    "minutes_to_first_turn": int((rows[i]["time"] - rows[ei]["time"]).total_seconds() // 60),
                    "turn_entry_exec_price": turn_entry_exec,
                    "return_from_first_turn_to_source_exit_bps": turn_return,
                    "turn_outcome": "WIN" if turn_return > 0 else "LOSS" if turn_return < 0 else "FLAT",
                    "mfe_from_first_turn_to_source_exit_bps": turn_mfe,
                    "mae_from_first_turn_to_source_exit_bps": turn_mae,
                    "source_immediate_return_bps": source_return,
                    "signal_m5_directional_rci9": base["signal_m5_directional_rci9"],
                    "signal_m5_directional_rci9_zone": base["signal_m5_directional_rci9_zone"],
                }
                for tf in ("m5", "h1", "h4"):
                    first_turn.update(asof_rci_features(derived[ticker][tf], rows[turn_entry_idx]["time"], f"turn_{tf}", direction))
                h1_with = float(first_turn["turn_h1_directional_rci9_delta1"]) > 0
                h4_with = float(first_turn["turn_h4_directional_rci9_delta1"]) > 0
                first_turn["turn_htf_directional_rci9_slope_state"] = (
                    "H1_AND_H4_WITH_TRADE" if h1_with and h4_with else
                    "H1_ONLY_WITH_TRADE" if h1_with else
                    "H4_ONLY_WITH_TRADE" if h4_with else
                    "NEITHER_WITH_TRADE"
                )
                turn_rows.append(first_turn)
                break

            base["has_first_causal_turn"] = first_turn is not None
            if first_turn:
                base["initial_pullback_depth_bps"] = first_turn["initial_pullback_depth_bps"]
                base["minutes_to_first_turn"] = first_turn["minutes_to_first_turn"]
                base["first_turn_return_bps"] = first_turn["return_from_first_turn_to_source_exit_bps"]
                base["first_turn_htf_state"] = first_turn["turn_htf_directional_rci9_slope_state"]
            trade_rows.append(base)

        if len(trade_rows) != EXPECTED_TRADE_COUNT:
            raise RuntimeError(f"expected {EXPECTED_TRADE_COUNT} trade rows, got {len(trade_rows)}")

        m5_pairs = [(float(r["signal_m5_directional_rci9"]), float(r["initial_pullback_depth_bps"])) for r in turn_rows]
        h1_pairs = [(float(r["turn_h1_directional_rci9_delta1"]), float(r["return_from_first_turn_to_source_exit_bps"])) for r in turn_rows]
        h4_pairs = [(float(r["turn_h4_directional_rci9_delta1"]), float(r["return_from_first_turn_to_source_exit_bps"])) for r in turn_rows]

        signal_zone_summary: list[dict[str, Any]] = []
        for zone in ("GE_80", "50_TO_80", "MINUS50_TO_50", "LE_MINUS50"):
            group = [r for r in turn_rows if r["signal_m5_directional_rci9_zone"] == zone]
            vals = [float(r["return_from_first_turn_to_source_exit_bps"]) for r in group]
            depths = [float(r["initial_pullback_depth_bps"]) for r in group]
            signal_zone_summary.append({
                "zone": zone,
                "count": len(group),
                "mean_initial_pullback_bps": statistics.fmean(depths) if depths else None,
                "median_initial_pullback_bps": statistics.median(depths) if depths else None,
                "positive_fraction_from_first_turn": (sum(v > 0 for v in vals) / len(vals)) if vals else None,
                "net_bps_from_first_turn": sum(vals),
                "profit_factor_from_first_turn": pf(vals) if vals else None,
            })

        htf_summary: list[dict[str, Any]] = []
        for state in ("H1_AND_H4_WITH_TRADE", "H1_ONLY_WITH_TRADE", "H4_ONLY_WITH_TRADE", "NEITHER_WITH_TRADE"):
            group = [r for r in turn_rows if r["turn_htf_directional_rci9_slope_state"] == state]
            vals = [float(r["return_from_first_turn_to_source_exit_bps"]) for r in group]
            htf_summary.append({
                "state": state,
                "count": len(group),
                "positive_fraction": (sum(v > 0 for v in vals) / len(vals)) if vals else None,
                "net_bps": sum(vals),
                "profit_factor_bps": pf(vals) if vals else None,
                "mean_return_bps": statistics.fmean(vals) if vals else None,
            })

        ticker_direction_summary: list[dict[str, Any]] = []
        for ticker in ("XAUUSD", "BTCUSD"):
            for direction in ("LONG", "SHORT"):
                group = [r for r in trade_rows if r["ticker"] == ticker and r["direction"] == direction]
                first_group = [r for r in turn_rows if r["ticker"] == ticker and r["direction"] == direction]
                ticker_direction_summary.append({
                    "ticker": ticker,
                    "direction": direction,
                    "source_primary_count": len(group),
                    **{f"source_{k}": v for k, v in metric_block(group, "source_return_bps", "source_mfe_bps", "source_mae_bps").items()},
                    "first_turn_count": len(first_group),
                    **{f"turn_{k}": v for k, v in metric_block(first_group, "return_from_first_turn_to_source_exit_bps", "mfe_from_first_turn_to_source_exit_bps", "mae_from_first_turn_to_source_exit_bps").items()},
                })

    except Exception as exc:
        print(f"[M9B BLOCKED] {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9B_GENUINE_PRIMARY_EXPANDED_CONTEXT_AUDIT",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_only": True,
        "population_tier": "TIER_A_GENUINE_SOURCE_PRIMARY",
        "frozen_genuine_primary_count": len(trade_rows),
        "source_immediate": metric_block(trade_rows, "source_return_bps", "source_mfe_bps", "source_mae_bps"),
        "first_causal_turn": {
            "count": len(turn_rows),
            "coverage": len(turn_rows) / len(trade_rows),
            **metric_block(turn_rows, "return_from_first_turn_to_source_exit_bps", "mfe_from_first_turn_to_source_exit_bps", "mae_from_first_turn_to_source_exit_bps"),
        },
        "exploratory_correlations": {
            "signal_m5_directional_rci9_vs_initial_pullback_depth_spearman": spearman([a for a, _ in m5_pairs], [b for _, b in m5_pairs]),
            "turn_h1_directional_rci9_delta1_vs_return_spearman": spearman([a for a, _ in h1_pairs], [b for _, b in h1_pairs]),
            "turn_h4_directional_rci9_delta1_vs_return_spearman": spearman([a for a, _ in h4_pairs], [b for _, b in h4_pairs]),
        },
        "guardrails": {
            "same_43_is_validation": False,
            "threshold_promotion_allowed": False,
            "proxy_replay_mixed_in": False,
            "next_tier_after_review": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
            "m8c_reset": False,
            "m7c_changed": False,
        },
    }
    quality = {
        "exact_m1_source_entry_exit_required": True,
        "nearest_bar_fallback_used": False,
        "historical_spread_used": True,
        "commission": "NOT_MODELED",
        "swap": "NOT_MODELED",
        "turn_definition_same_family_as_m8bz": True,
        "turn_confirmation_completed_m1_only": True,
        "turn_entry_next_observed_m1_open": True,
        "higher_timeframes_closed_bars_only": True,
        "higher_timeframes_derived_from_m1": True,
        "mt5_files_root": str(files_root),
        "symbol_points": {ticker: meta["symbols"][ticker]["point"] for ticker in EXPECTED_FILES},
    }

    out_root = local_root / "outputs" / "M9B"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_genuine_primary_trades.csv", trade_rows)
    write_csv(archive / "03_first_turn_context.csv", turn_rows)
    write_csv(archive / "04_signal_m5_zone_summary.csv", signal_zone_summary)
    write_csv(archive / "05_turn_htf_slope_summary.csv", htf_summary)
    write_csv(archive / "06_ticker_direction_summary.csv", ticker_direction_summary)
    dump_json(archive / "07_data_quality.json", quality)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9B genuine-source PRIMARY expanded context audit.\n"
        "Population is the 43 frozen genuine source PRIMARY trades from M9A; proxy replay is not mixed in.\n"
        "M5/H1/H4 use only fully closed derived bars. Same 43 are hypothesis-generation only.\n",
        encoding="utf-8",
    )
    (archive / "08_audit.log").write_text(
        f"status=PASS_EXPLORATORY_ONLY\n"
        f"genuine_primary_trades={len(trade_rows)}\n"
        f"trades_with_first_turn={len(turn_rows)}\n"
        f"proxy_replay_mixed_in=false\n",
        encoding="utf-8",
    )
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_genuine_primary_trades.csv",
        "03_first_turn_context.csv", "04_signal_m5_zone_summary.csv",
        "05_turn_htf_slope_summary.csv", "06_ticker_direction_summary.csv",
        "07_data_quality.json", "08_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)

    print(f"[M9B PASS] genuine_primary={len(trade_rows)} first_turn={len(turn_rows)}")
    print(f"[M9B OUTPUT] {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
