from __future__ import annotations

import csv
import json
import math
import os
import shutil
import statistics
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_TRADE_COUNT = 18
EXPECTED_FILES = {"XAUUSD": "goldsharp_m1.csv", "BTCUSD": "btcusdsharp_m1.csv"}
TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
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
        return float("nan")
    return delta / reference * 10000.0


def mean_or_none(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def median_or_none(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def load_m1(path: Path) -> list[dict[str, Any]]:
    raw = read_csv(path)
    expected = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    if not raw or list(raw[0].keys()) != expected:
        raise RuntimeError(f"unexpected/empty M1 file: {path}")
    rows: list[dict[str, Any]] = []
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
            "real_volume": float(r["real_volume"]),
        }
        if any(not math.isfinite(float(row[k])) for k in ("open", "high", "low", "close")):
            raise RuntimeError(f"nonfinite OHLC: {path.name} {r['time']}")
        if row["spread"] < 0:
            raise RuntimeError(f"negative spread: {path.name} {r['time']}")
        rows.append(row)
    return rows


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1.0 - alpha) * out[-1])
    return out


def wilder_atr(rows: list[dict[str, Any]], period: int = 14) -> list[float | None]:
    tr: list[float] = []
    for i, r in enumerate(rows):
        if i == 0:
            tr.append(r["high"] - r["low"])
        else:
            prev_close = rows[i - 1]["close"]
            tr.append(max(r["high"] - r["low"], abs(r["high"] - prev_close), abs(r["low"] - prev_close)))
    out: list[float | None] = [None] * len(rows)
    if len(rows) < period:
        return out
    seed = statistics.fmean(tr[:period])
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(rows)):
        prev = (prev * (period - 1) + tr[i]) / period
        out[i] = prev
    return out


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
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    dx = [v - mx for v in x]
    dy = [v - my for v in y]
    den = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if den == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / den


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    return pearson(rank_average(x), rank_average(y))


def rci(closes: list[float], idx: int, period: int) -> float | None:
    if idx - period + 1 < 0:
        return None
    window = closes[idx - period + 1 : idx + 1]
    time_ranks = [float(i + 1) for i in range(period)]
    price_ranks = rank_average(window)
    corr = pearson(time_ranks, price_ranks)
    return None if corr is None else corr * 100.0


def precompute(rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
    closes = [r["close"] for r in rows]
    e20, e30, e40 = ema(closes, 20), ema(closes, 30), ema(closes, 40)
    e6, e13 = ema(closes, 6), ema(closes, 13)
    macd = [a - b for a, b in zip(e6, e13)]
    macd_signal = ema(macd, 4)
    macd_hist = [a - b for a, b in zip(macd, macd_signal)]
    atr14 = wilder_atr(rows, 14)
    return {"close": closes, "ema20": e20, "ema30": e30, "ema40": e40, "macd": macd, "macd_signal": macd_signal, "macd_hist": macd_hist, "atr14": atr14}


def directional_return(direction: str, current: float, previous: float) -> float:
    raw = bps(current - previous, previous)
    return raw if direction == "LONG" else -raw


def execution_entry(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "LONG" else row["open"]


def execution_exit(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "SHORT" else row["open"]


def trade_return(direction: str, entry: float, exit_price: float) -> float:
    return bps(exit_price - entry, entry) if direction == "LONG" else bps(entry - exit_price, entry)


def outcome_excursions(direction: str, entry_exec: float, rows: list[dict[str, Any]], point: float) -> tuple[float, float]:
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


def candidate_features(trade: dict[str, str], rows: list[dict[str, Any]], pre: dict[str, list[Any]], idx: int, entry_idx: int, point: float) -> dict[str, Any]:
    direction = trade["direction"]
    current = rows[idx]
    signal_bid = float(trade["entry_bid_open"])
    close = current["close"]
    segment = rows[entry_idx : idx + 1]
    if direction == "LONG":
        extreme = min(r["low"] for r in segment)
        pullback_depth = bps(signal_bid - extreme, signal_bid)
        rebound = bps(close - extreme, extreme)
    else:
        extreme = max(r["high"] for r in segment)
        pullback_depth = bps(extreme - signal_bid, signal_bid)
        rebound = bps(extreme - close, extreme)

    def dret(k: int) -> float | None:
        return None if idx - k < 0 else directional_return(direction, close, rows[idx - k]["close"])

    rci9 = rci(pre["close"], idx, 9)
    rci9_prev = rci(pre["close"], idx - 1, 9) if idx > 0 else None
    rci14 = rci(pre["close"], idx, 14)
    rci18 = rci(pre["close"], idx, 18)
    e20, e30, e40 = pre["ema20"][idx], pre["ema30"][idx], pre["ema40"][idx]
    ema20_slope3 = None if idx < 3 else bps(e20 - pre["ema20"][idx - 3], pre["ema20"][idx - 3])
    hist = pre["macd_hist"][idx]
    hist_prev = pre["macd_hist"][idx - 1] if idx > 0 else None
    rng = current["high"] - current["low"]
    body = abs(current["close"] - current["open"])
    if rng > 0:
        lower_wick = min(current["open"], current["close"]) - current["low"]
        upper_wick = current["high"] - max(current["open"], current["close"])
        body_fraction = body / rng
        directional_wick_fraction = lower_wick / rng if direction == "LONG" else upper_wick / rng
        close_loc = (current["close"] - current["low"]) / rng if direction == "LONG" else (current["high"] - current["close"]) / rng
    else:
        body_fraction, directional_wick_fraction, close_loc = 0.0, 0.0, 0.5
    vol_start = max(0, idx - 19)
    vol_mean = statistics.fmean(rows[j]["tick_volume"] for j in range(vol_start, idx + 1))
    atr = pre["atr14"][idx]
    return {
        "pullback_depth_bps": pullback_depth,
        "rebound_from_extreme_bps": rebound,
        "minutes_since_signal": int((current["time"] - rows[entry_idx]["time"]).total_seconds() // 60),
        "directional_return_1m_bps": dret(1),
        "directional_return_3m_bps": dret(3),
        "directional_return_5m_bps": dret(5),
        "m1_rci9": rci9,
        "m1_rci14": rci14,
        "m1_rci18": rci18,
        "m1_rci9_delta1": None if rci9 is None or rci9_prev is None else rci9 - rci9_prev,
        "m1_ema20": e20,
        "m1_ema30": e30,
        "m1_ema40": e40,
        "m1_ema20_minus_ema30_bps": bps(e20 - e30, close),
        "m1_ema30_minus_ema40_bps": bps(e30 - e40, close),
        "m1_price_minus_ema20_bps": bps(close - e20, e20),
        "m1_ema20_slope3_bps": ema20_slope3,
        "m1_macd_6_13": pre["macd"][idx],
        "m1_macd_signal_4": pre["macd_signal"][idx],
        "m1_macd_hist": hist,
        "m1_macd_hist_delta1": None if hist_prev is None else hist - hist_prev,
        "m1_macd_hist_bps": bps(hist, close),
        "m1_macd_hist_delta1_bps": None if hist_prev is None else bps(hist - hist_prev, close),
        "m1_atr14_bps": None if atr is None else bps(atr, close),
        "m1_bar_range_bps": bps(rng, close),
        "m1_body_fraction": body_fraction,
        "m1_directional_wick_fraction": directional_wick_fraction,
        "m1_close_location_directional": close_loc,
        "m1_tick_volume_ratio20": current["tick_volume"] / vol_mean if vol_mean > 0 else None,
        "m1_spread_bps": bps(current["spread"] * point, close),
        "signal_entry_rci9": float(trade["entry_rci9"]),
        "signal_entry_rci9_delta1": float(trade["entry_rci9_delta1"]),
        "signal_entry_ema_alignment": trade["entry_ema_alignment"],
        "signal_entry_ema20_minus_ema30_bps": float(trade["entry_ema20_minus_ema30_bps"]),
        "signal_entry_ema30_minus_ema40_bps": float(trade["entry_ema30_minus_ema40_bps"]),
    }


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


def numeric_feature_names() -> list[str]:
    return [
        "pullback_depth_bps", "rebound_from_extreme_bps", "minutes_since_signal", "directional_return_1m_bps", "directional_return_3m_bps", "directional_return_5m_bps",
        "m1_rci9", "m1_rci14", "m1_rci18", "m1_rci9_delta1", "m1_ema20_minus_ema30_bps", "m1_ema30_minus_ema40_bps", "m1_price_minus_ema20_bps",
        "m1_ema20_slope3_bps", "m1_macd_hist_bps", "m1_macd_hist_delta1_bps", "m1_atr14_bps", "m1_bar_range_bps", "m1_body_fraction",
        "m1_directional_wick_fraction", "m1_close_location_directional", "m1_tick_volume_ratio20", "m1_spread_bps", "signal_entry_rci9", "signal_entry_rci9_delta1",
        "signal_entry_ema20_minus_ema30_bps", "signal_entry_ema30_minus_ema40_bps"
    ]


def feature_comparison(first_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for feature in numeric_feature_names():
        valid = [r for r in first_rows if r.get(feature) is not None and math.isfinite(float(r[feature]))]
        wins = [float(r[feature]) for r in valid if float(r["return_to_original_frozen_exit_bps"]) > 0]
        losses = [float(r[feature]) for r in valid if float(r["return_to_original_frozen_exit_bps"]) < 0]
        out.append({
            "feature": feature,
            "valid_count": len(valid),
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_median": statistics.median(wins) if wins else None,
            "loss_median": statistics.median(losses) if losses else None,
            "median_difference_win_minus_loss": None if not wins or not losses else statistics.median(wins) - statistics.median(losses),
            "win_mean": statistics.fmean(wins) if wins else None,
            "loss_mean": statistics.fmean(losses) if losses else None,
        })
    return out


def feature_correlations(first_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for feature in numeric_feature_names():
        pairs = [(float(r[feature]), float(r["return_to_original_frozen_exit_bps"])) for r in first_rows if r.get(feature) is not None and math.isfinite(float(r[feature]))]
        rho = spearman([a for a, _ in pairs], [b for _, b in pairs]) if len(pairs) >= 3 else None
        out.append({"feature": feature, "count": len(pairs), "spearman_rho_with_return": rho})
    out.sort(key=lambda r: abs(r["spearman_rho_with_return"]) if r["spearman_rho_with_return"] is not None else -1, reverse=True)
    return out


def main() -> int:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m8b = root / "outputs" / "M8B" / "LATEST"
    trades_path, metadata_path = m8b / "03_extra_entry_trades.csv", m8b / "06_symbol_metadata.json"
    if not trades_path.is_file() or not metadata_path.is_file():
        print("[M8BZ BLOCKED] M8B LATEST trade/metadata files are missing")
        return 2
    trades = read_csv(trades_path)
    if len(trades) != EXPECTED_TRADE_COUNT:
        print(f"[M8BZ BLOCKED] expected {EXPECTED_TRADE_COUNT} M8B trades, got {len(trades)}")
        return 2
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    files_root = Path(metadata.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print(f"[M8BZ BLOCKED] MT5 Files root unavailable: {files_root}")
        return 2
    try:
        m1 = {ticker: load_m1(files_root / filename) for ticker, filename in EXPECTED_FILES.items()}
        pre = {ticker: precompute(m1[ticker]) for ticker in EXPECTED_FILES}
        index = {ticker: {row["time_text"]: i for i, row in enumerate(m1[ticker])} for ticker in EXPECTED_FILES}
        all_candidates: list[dict[str, Any]] = []
        first_candidates: list[dict[str, Any]] = []
        for trade in trades:
            ticker, direction = trade["ticker"], trade["direction"]
            rows = m1[ticker]
            point = float(metadata["symbols"][ticker]["point"])
            entry_text, exit_text = trade["entry_server_open"], trade["exit_server_open"]
            if entry_text not in index[ticker] or exit_text not in index[ticker]:
                raise RuntimeError(f"exact M1 entry/exit index missing: {trade['trade_id']}")
            entry_idx, exit_idx = index[ticker][entry_text], index[ticker][exit_text]
            if exit_idx <= entry_idx:
                raise RuntimeError(f"invalid entry/exit ordering: {trade['trade_id']}")
            trade_candidates: list[dict[str, Any]] = []
            for i in range(entry_idx + 1, exit_idx):
                if i + 1 >= exit_idx:
                    break
                if not is_turn_candidate(direction, rows, i, float(trade["entry_bid_open"])):
                    continue
                entry_exec = execution_entry(direction, rows[i + 1], point)
                exit_exec = execution_exit(direction, rows[exit_idx], point)
                future_rows = rows[i + 1 : exit_idx + 1]
                mfe, mae = outcome_excursions(direction, entry_exec, future_rows, point)
                x: dict[str, Any] = {
                    "trade_id": trade["trade_id"], "ticker": ticker, "direction": direction,
                    "original_signal_time": entry_text, "turn_confirmation_time": rows[i]["time_text"], "candidate_entry_time": rows[i + 1]["time_text"],
                    "original_frozen_exit_time": exit_text, "candidate_entry_exec_price": entry_exec,
                    "return_to_original_frozen_exit_bps": trade_return(direction, entry_exec, exit_exec),
                    "forward_mfe_to_original_exit_bps": mfe, "forward_mae_to_original_exit_bps": mae,
                    "original_trade_return_bps": float(trade["spread_adjusted_return_bps"]), "original_trade_outcome": trade["outcome"],
                    "candidate_generation_used_future_outcome": False, "same_confirmation_bar_entry_used": False,
                }
                x.update(candidate_features(trade, rows, pre[ticker], i, entry_idx, point))
                trade_candidates.append(x)
            for n, x in enumerate(trade_candidates, start=1):
                x["candidate_number_within_trade"] = n
                x["is_first_confirmed_turn"] = n == 1
                all_candidates.append(x)
            if trade_candidates:
                first_candidates.append(trade_candidates[0])
        comparisons = feature_comparison(first_candidates)
        correlations = feature_correlations(first_candidates)
    except Exception as exc:
        print(f"[M8BZ BLOCKED] {exc}")
        return 2
    first_returns = [float(r["return_to_original_frozen_exit_bps"]) for r in first_candidates]
    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH", "stage": "M8BZ_PULLBACK_STATE_FEATURE_AUDIT", "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "audit_only": True,
        "frozen_trade_population": len(trades), "trades_with_at_least_one_causal_turn_candidate": len(first_candidates),
        "first_turn_coverage": len(first_candidates) / len(trades) if trades else None, "all_turn_candidate_count": len(all_candidates),
        "first_turn_win_rate_to_original_exit": sum(v > 0 for v in first_returns) / len(first_returns) if first_returns else None,
        "first_turn_net_bps_to_original_exit": sum(first_returns), "feature_analysis_population": "FIRST_CONFIRMED_TURN_PER_TRADE_ONLY",
        "all_candidates_are_independent_samples": False, "machine_learning_fit_used": False, "fixed_bps_minimum_used_for_candidate_generation": False,
        "interpretation_guardrails": {"same_18_is_validation": False, "feature_threshold_promotion_allowed": False, "feature_signature_hypothesis_generation_allowed": True, "new_forward_validation_required": True, "existing_m8c_must_not_be_reset": True},
        "top_absolute_spearman_features": correlations[:10],
    }
    quality = {
        "exact_m1_entry_exit_required": True, "nearest_bar_fallback_used": False, "turn_confirmation_uses_completed_m1_only": True,
        "entry_is_next_observed_m1_open": True, "future_outcomes_used_only_after_candidate_freeze": True,
        "local_features": ["RCI9/14/18", "EMA20/30/40", "MACD6/13/4", "ATR14", "price action", "tick volume", "spread"],
        "fixed_bps_trigger_used": False, "commission": "NOT_MODELED", "swap": "NOT_MODELED", "mt5_files_root": str(files_root),
    }
    out_root = root / "outputs" / "M8BZ"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_first_turn_candidates.csv", first_candidates)
    write_csv(archive / "03_all_turn_candidates.csv", all_candidates)
    write_csv(archive / "04_feature_win_loss_comparison.csv", comparisons)
    write_csv(archive / "05_feature_return_correlations.csv", correlations)
    dump_json(archive / "06_data_quality.json", quality)
    (archive / "00_READ_ME_FIRST.txt").write_text("M8BZ pullback-state feature audit.\nCandidate generation uses no fixed bps minimum and no future outcome.\nLocal M1 RCI/EMA/MACD/ATR/price-action features are captured at completed turn confirmation.\nThe same frozen M8B 18 trades are hypothesis-generation only; no feature threshold is promoted here.\n", encoding="utf-8")
    (archive / "07_audit.log").write_text(f"status=PASS_EXPLORATORY_ONLY\nfrozen_trades={len(trades)}\ntrades_with_first_turn={len(first_candidates)}\nall_turn_candidates={len(all_candidates)}\n", encoding="utf-8")
    names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_first_turn_candidates.csv", "03_all_turn_candidates.csv", "04_feature_win_loss_comparison.csv", "05_feature_return_correlations.csv", "06_data_quality.json", "07_audit.log"]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(f"[M8BZ PASS] trades={len(trades)} first_turn={len(first_candidates)} all_candidates={len(all_candidates)}")
    print(f"[M8BZ OUTPUT] {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
