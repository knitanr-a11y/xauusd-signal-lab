from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
TF_SECONDS = {"M5": 300, "M15": 900, "H1": 3600, "H4": 14400}
FEATURE_TIMEFRAMES = ("M5", "M15", "H1", "H4")
LONG_EXIT_RCI9 = 78.333333333333
SHORT_EXIT_RCI9 = -75.0

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
RESEARCH_ROOT = REPO_ROOT / "scripts" / "mochipoyo_alert_research"
M9E_PY = RESEARCH_ROOT / "m9e" / "python"
for path in (RESEARCH_ROOT, M9E_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from alert_trigger_signature_audit import flatten_features
from feature_snapshot_builder import MINIMUM_WARMUP_BARS, build_feature_payload, load_indicator_series
from mt5_csv_contract import FILE_MAP, TIMEFRAME_SECONDS
import run_causal_divergence_context_audit as m9e


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)


def bps(delta: float, reference: float) -> float:
    if abs(reference) <= 1e-12:
        raise RuntimeError("zero price reference")
    return delta / abs(reference) * 10000.0


def pf(values: list[float]) -> float | None:
    wins = sum(v for v in values if v > 0)
    losses = abs(sum(v for v in values if v < 0))
    return None if losses == 0 else wins / losses


def metrics(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    return {
        "count": len(values),
        "win_rate": (sum(v > 0 for v in values) / len(values)) if values else None,
        "profit_factor_bps": pf(values) if values else None,
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values) if values else None,
        "median_bps": statistics.median(values) if values else None,
    }


def load_m1(path: Path) -> list[dict[str, Any]]:
    raw = read_csv(path)
    expected = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    if not raw or list(raw[0].keys()) != expected:
        raise RuntimeError(f"unexpected/empty M1 file: {path}")
    output: list[dict[str, Any]] = []
    previous: datetime | None = None
    for row in raw:
        current = parse_time(row["time"])
        if previous is not None and current <= previous:
            raise RuntimeError(f"M1 time not strictly ascending: {path.name} {row['time']}")
        previous = current
        output.append({
            "time": current,
            "time_text": row["time"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "tick_volume": int(row["tick_volume"]),
            "spread": int(row["spread"]),
        })
    return output


def execution_entry(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "LONG" else row["open"]


def execution_exit(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "SHORT" else row["open"]


def trade_return(direction: str, entry: float, exit_price: float) -> float:
    return bps(exit_price - entry, entry) if direction == "LONG" else bps(entry - exit_price, entry)


def as_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    try:
        return float(value)
    except Exception:
        return str(value)


def replay_proxy(ticker: str, files_root: Path, built_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    series = load_indicator_series(files_root / FILE_MAP[ticker]["M15"])
    state = "IDLE"
    open_primary: dict[str, Any] | None = None
    signals: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    boundary_state: dict[str, dict[str, Any]] = {}
    seq = 0

    for current_index in range(MINIMUM_WARMUP_BARS, len(series.bars)):
        current_bar = series.bars[current_index]
        selected_index = current_index - 1
        payload = build_feature_payload(
            series,
            selected_index=selected_index,
            ticker=ticker,
            timeframe="M15",
            source_filename=FILE_MAP[ticker]["M15"],
            decision_time_utc=current_bar.server_open,
            selected_utc_close=current_bar.server_open,
            selected_offset_hours=0.0,
            built_at_utc=built_at,
        )
        flat = flatten_features(series, selected_index, payload)
        rci9 = float(flat["rci9"])
        direct_long = bool(flat.get("rci9_turn_up")) and flat.get("ema_alignment") == "BULLISH_STACK"
        direct_short = bool(flat.get("rci9_turn_down")) and flat.get("ema_alignment") == "BEARISH_STACK"
        state_before = state
        transition: str | None = None
        state_after = state
        if state == "IDLE":
            if direct_long:
                transition = "PRIMARY_LONG"
                state_after = "ACTIVE_LONG"
            elif direct_short:
                transition = "PRIMARY_SHORT"
                state_after = "ACTIVE_SHORT"
        elif state == "ACTIVE_LONG" and rci9 >= LONG_EXIT_RCI9:
            transition = "LONG_EXIT"
            state_after = "IDLE"
        elif state == "ACTIVE_SHORT" and rci9 <= SHORT_EXIT_RCI9:
            transition = "SHORT_EXIT"
            state_after = "IDLE"

        time_text = current_bar.server_open.strftime(TIME_FORMAT)
        boundary_state[time_text] = {
            "proxy_state_before": state_before,
            "proxy_state_after": state_after,
            "direct_long_kernel": direct_long,
            "direct_short_kernel": direct_short,
            "transition": transition or "",
            "m15_rci9": rci9,
            "m15_rci9_delta1": flat.get("rci9_delta1"),
            "m15_rci9_turn_up": flat.get("rci9_turn_up"),
            "m15_rci9_turn_down": flat.get("rci9_turn_down"),
            "m15_ema_alignment": flat.get("ema_alignment"),
        }

        if transition is not None:
            seq += 1
            signal = {
                "replay_signal_id": f"{ticker}_{seq:06d}",
                "ticker": ticker,
                "server_open": time_text,
                "transition": transition,
                "state_before": state_before,
                "state_after": state_after,
                "rci9": rci9,
                "rci9_delta1": flat.get("rci9_delta1"),
                "rci9_turn_up": flat.get("rci9_turn_up"),
                "rci9_turn_down": flat.get("rci9_turn_down"),
                "ema_alignment": flat.get("ema_alignment"),
                "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
            }
            signals.append(signal)
            if transition.startswith("PRIMARY_"):
                direction = "LONG" if transition == "PRIMARY_LONG" else "SHORT"
                open_primary = {**signal, "direction": direction}
            else:
                if open_primary is None:
                    raise RuntimeError(f"proxy exit without open primary: {ticker} {time_text}")
                pairs.append({
                    "proxy_trade_id": f"{ticker}_GAP_{len(pairs)+1:06d}",
                    "ticker": ticker,
                    "direction": open_primary["direction"],
                    "entry_server_open": open_primary["server_open"],
                    "exit_server_open": signal["server_open"],
                    "entry_signal_id": open_primary["replay_signal_id"],
                    "exit_signal_id": signal["replay_signal_id"],
                })
                open_primary = None
        state = state_after

    return signals, pairs, boundary_state


def features_at(
    *, ticker: str, decision_time: datetime, series_by_ticker: dict[str, dict[str, Any]], close_times: dict[str, dict[str, list[datetime]]], built_at: str
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for timeframe in FEATURE_TIMEFRAMES:
        series = series_by_ticker[ticker][timeframe]
        closes = close_times[ticker][timeframe]
        selected_index = bisect.bisect_right(closes, decision_time) - 1
        prefix = timeframe.lower()
        if selected_index < MINIMUM_WARMUP_BARS - 1:
            output[f"{prefix}_context_available"] = False
            continue
        payload = build_feature_payload(
            series,
            selected_index=selected_index,
            ticker=ticker,
            timeframe=timeframe,
            source_filename=FILE_MAP[ticker][timeframe],
            decision_time_utc=decision_time,
            selected_utc_close=closes[selected_index],
            selected_offset_hours=0.0,
            built_at_utc=built_at,
        )
        flat = flatten_features(series, selected_index, payload)
        output[f"{prefix}_context_available"] = True
        output[f"{prefix}_selected_bar_open"] = series.bars[selected_index].server_open.strftime(TIME_FORMAT)
        for key, value in flat.items():
            output[f"{prefix}_{key}"] = as_scalar(value)
    return output


def build_pivots(series_by_ticker: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pivots: dict[str, Any] = defaultdict(lambda: defaultdict(dict))
    for ticker in series_by_ticker:
        for timeframe in FEATURE_TIMEFRAMES:
            series = series_by_ticker[ticker][timeframe]
            for scale_name, spec in m9e.SCALES.items():
                raw = m9e.precompute_confirmed_pivots(series, depth=int(spec["depth"]), right=int(spec["right"]))
                pivots[ticker][timeframe][scale_name] = {}
                for side in ("LOW", "HIGH"):
                    events = raw[side]
                    pivots[ticker][timeframe][scale_name][side] = {
                        "events": events,
                        "confirmations": [int(event["confirmation_index"]) for event in events],
                    }
    return pivots


def divergence_at(
    *, row_id: str, ticker: str, direction: str, decision_time: datetime, entry_text: str,
    series_by_ticker: dict[str, dict[str, Any]], close_times: dict[str, dict[str, list[datetime]]], pivots: dict[str, Any]
) -> dict[str, Any]:
    dummy = {
        "proxy_trade_id": row_id,
        "ticker": ticker,
        "direction": direction,
        "entry_server_open": entry_text,
        "exit_server_open": "",
        "return_from_first_turn_bps": "",
        "initial_pullback_depth_bps": "",
        "minutes_to_first_turn": "",
    }
    base, detail, _ = m9e.build_context_for_row(
        source_row=dummy,
        panel_kind="TURN",
        decision_time=decision_time,
        series_by_ticker=series_by_ticker,
        close_times=close_times,
        pivots=pivots,
    )
    counts = Counter()
    for event in detail:
        timeframe = str(event["timeframe"])
        if timeframe not in FEATURE_TIMEFRAMES:
            continue
        confirmed = parse_time(str(event["second_pivot_confirmed_by"]))
        age_bars = (decision_time - confirmed).total_seconds() / float(TF_SECONDS[timeframe])
        if age_bars < -1e-9:
            raise RuntimeError("future divergence confirmation detected")
        role = str(event["directional_role"]).lower()
        subtype = str(event["divergence_subtype"]).lower()
        for cutoff in (3, 5):
            if age_bars <= cutoff + 1e-9:
                counts[f"div_le{cutoff}_{role}_any"] += 1
                counts[f"div_le{cutoff}_{role}_{subtype}"] += 1
    output = {
        "div_all_supportive_count": int(base.get("supportive_regular_count", 0)) + int(base.get("supportive_hidden_count", 0)),
        "div_all_opposing_count": int(base.get("opposing_regular_count", 0)) + int(base.get("opposing_hidden_count", 0)),
    }
    for cutoff in (3, 5):
        for role in ("supportive", "opposing"):
            output[f"div_le{cutoff}_{role}_any"] = counts[f"div_le{cutoff}_{role}_any"]
            output[f"div_le{cutoff}_{role}_regular"] = counts[f"div_le{cutoff}_{role}_regular"]
            output[f"div_le{cutoff}_{role}_hidden"] = counts[f"div_le{cutoff}_{role}_hidden"]
    return output


def nearest_proxy(source: dict[str, Any], proxy_primaries: list[dict[str, Any]]) -> tuple[str, dict[str, Any] | None, int | None, bool]:
    source_time = parse_time(source["entry_server_open"])
    same = []
    opposite_nearby = False
    for proxy in proxy_primaries:
        if proxy["ticker"] != source["ticker"]:
            continue
        proxy_time = parse_time(proxy["server_open"])
        diff = int((proxy_time - source_time).total_seconds() / 60)
        if abs(diff) <= 15:
            proxy_direction = "LONG" if proxy["transition"] == "PRIMARY_LONG" else "SHORT"
            if proxy_direction == source["direction"]:
                same.append((abs(diff), diff, proxy))
            else:
                opposite_nearby = True
    if not same:
        return "MISSED", None, None, opposite_nearby
    same.sort(key=lambda item: (item[0], abs(item[1]), item[1]))
    _, diff, proxy = same[0]
    if diff == 0:
        label = "EXACT"
    elif diff < 0:
        label = "WITHIN_ONE_BAR_EARLY"
    else:
        label = "WITHIN_ONE_BAR_LATE"
    return label, proxy, diff, opposite_nearby


def numeric_contrasts(source_rows: list[dict[str, Any]], extra_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocked_prefixes = ("source_", "proxy_", "outcome_", "entry_", "exit_", "class", "ticker", "direction", "row_id")
    keys = sorted(set().union(*(row.keys() for row in source_rows + extra_rows)))
    output: list[dict[str, Any]] = []
    for key in keys:
        if key.startswith(blocked_prefixes) or key.endswith("_selected_bar_open") or key.endswith("_context_available"):
            continue
        svals: list[float] = []
        evals: list[float] = []
        for row, target in ((source_rows, svals), (extra_rows, evals)):
            for item in row:
                value = item.get(key)
                if isinstance(value, bool) or value in (None, ""):
                    continue
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(number):
                    target.append(number)
        if len(svals) < 10 or len(evals) < 10:
            continue
        sm, em = statistics.fmean(svals), statistics.fmean(evals)
        ss = statistics.stdev(svals) if len(svals) > 1 else 0.0
        es = statistics.stdev(evals) if len(evals) > 1 else 0.0
        pooled = math.sqrt((ss * ss + es * es) / 2.0)
        smd = None if pooled <= 1e-12 else (sm - em) / pooled
        output.append({
            "feature": key,
            "source_n": len(svals),
            "extra_n": len(evals),
            "source_mean": sm,
            "extra_mean": em,
            "source_median": statistics.median(svals),
            "extra_median": statistics.median(evals),
            "standardized_mean_difference_source_minus_extra": smd,
            "abs_smd": None if smd is None else abs(smd),
        })
    return sorted(output, key=lambda row: -1 if row["abs_smd"] is None else -float(row["abs_smd"]))


def categorical_contrasts(source_rows: list[dict[str, Any]], extra_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [key for key in sorted(set().union(*(row.keys() for row in source_rows + extra_rows))) if key.endswith("ema_alignment") or key.endswith("rci9_turn_up") or key.endswith("rci9_turn_down")]
    output: list[dict[str, Any]] = []
    for key in keys:
        sc = Counter(str(row.get(key)) for row in source_rows if row.get(key) not in (None, ""))
        ec = Counter(str(row.get(key)) for row in extra_rows if row.get(key) not in (None, ""))
        labels = sorted(set(sc) | set(ec))
        for label in labels:
            output.append({
                "feature": key,
                "value": label,
                "source_count": sc[label],
                "source_fraction": sc[label] / sum(sc.values()) if sc else None,
                "extra_count": ec[label],
                "extra_fraction": ec[label] / sum(ec.values()) if ec else None,
            })
    return output


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    meta_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    manifest_path = REPO_ROOT / "config" / "mochipoyo_alert_research" / "m9b_frozen_genuine_primary_pairs_20260724.json"
    if not meta_path.is_file():
        print("[M9I BLOCKED] M8B symbol metadata missing")
        return 2
    if not manifest_path.is_file():
        print("[M9I BLOCKED] frozen genuine source manifest missing")
        return 2
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_pairs = list(manifest.get("pairs", []))
    if int(manifest.get("frozen_primary_trade_count", -1)) != 43 or len(source_pairs) != 43:
        print(f"[M9I BLOCKED] expected 43 frozen source PRIMARY pairs, got {len(source_pairs)}")
        return 2
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print(f"[M9I BLOCKED] MT5 Files root unavailable: {files_root}")
        return 2

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        proxy_signals: list[dict[str, Any]] = []
        proxy_pairs: list[dict[str, Any]] = []
        boundary_state: dict[str, dict[str, dict[str, Any]]] = {}
        for ticker in ("XAUUSD", "BTCUSD"):
            signals, pairs, states = replay_proxy(ticker, files_root, built_at)
            proxy_signals.extend(signals)
            proxy_pairs.extend(pairs)
            boundary_state[ticker] = states

        windows: dict[str, tuple[datetime, datetime]] = {}
        for ticker in ("XAUUSD", "BTCUSD"):
            times = [parse_time(row["entry_server_open"]) for row in source_pairs if row["ticker"] == ticker]
            windows[ticker] = (min(times), max(times))

        proxy_primaries = []
        for row in proxy_signals:
            if not row["transition"].startswith("PRIMARY_"):
                continue
            current = parse_time(row["server_open"])
            start, end = windows[row["ticker"]]
            if start <= current <= end:
                proxy_primaries.append(row)

        series_by_ticker: dict[str, dict[str, Any]] = defaultdict(dict)
        close_times: dict[str, dict[str, list[datetime]]] = defaultdict(dict)
        for ticker in ("XAUUSD", "BTCUSD"):
            for timeframe in FEATURE_TIMEFRAMES:
                series = load_indicator_series(files_root / FILE_MAP[ticker][timeframe])
                series_by_ticker[ticker][timeframe] = series
                delta = timedelta(seconds=TF_SECONDS[timeframe])
                close_times[ticker][timeframe] = [bar.server_open + delta for bar in series.bars]
        pivots = build_pivots(series_by_ticker)

        m1 = {ticker: load_m1(files_root / FILE_MAP[ticker]["M1"]) for ticker in ("XAUUSD", "BTCUSD")}
        m1_index = {ticker: {row["time_text"]: i for i, row in enumerate(rows)} for ticker, rows in m1.items()}
        points = {ticker: float(meta["symbols"][ticker]["point"]) for ticker in ("XAUUSD", "BTCUSD")}

        source_panel: list[dict[str, Any]] = []
        source_matches: list[dict[str, Any]] = []
        matched_proxy_ids: set[str] = set()
        for source in source_pairs:
            ticker = source["ticker"]
            direction = source["direction"]
            entry_text = source["entry_server_open"]
            exit_text = source["exit_server_open"]
            decision_time = parse_time(entry_text)
            match_class, proxy, diff_minutes, wrong_nearby = nearest_proxy(source, proxy_primaries)
            if proxy is not None:
                matched_proxy_ids.add(proxy["replay_signal_id"])
            boundary = boundary_state[ticker].get(entry_text)
            if boundary is None:
                raise RuntimeError(f"source M15 boundary missing in proxy replay: {ticker} {entry_text}")
            direct_expected = bool(boundary["direct_long_kernel"] if direction == "LONG" else boundary["direct_short_kernel"])
            row: dict[str, Any] = {
                "row_id": f"SOURCE_{source['primary_raw_id']}",
                "class": "GENUINE_SOURCE_PRIMARY",
                "ticker": ticker,
                "direction": direction,
                "entry_server_open": entry_text,
                "exit_server_open": exit_text,
                "source_primary_raw_id": source["primary_raw_id"],
                "source_match_class": match_class,
                "matched_proxy_signal_id": proxy["replay_signal_id"] if proxy else "",
                "proxy_offset_minutes": diff_minutes if diff_minutes is not None else "",
                "wrong_direction_proxy_within_one_bar": wrong_nearby,
                "direct_frozen_primary_kernel_true_at_source_boundary": direct_expected,
                **boundary,
            }
            row.update(features_at(ticker=ticker, decision_time=decision_time, series_by_ticker=series_by_ticker, close_times=close_times, built_at=built_at))
            row.update(divergence_at(row_id=row["row_id"], ticker=ticker, direction=direction, decision_time=decision_time, entry_text=entry_text, series_by_ticker=series_by_ticker, close_times=close_times, pivots=pivots))
            if entry_text in m1_index[ticker] and exit_text in m1_index[ticker]:
                ai, zi = m1_index[ticker][entry_text], m1_index[ticker][exit_text]
                if zi > ai:
                    entry_exec = execution_entry(direction, m1[ticker][ai], points[ticker])
                    exit_exec = execution_exit(direction, m1[ticker][zi], points[ticker])
                    row["outcome_return_bps"] = trade_return(direction, entry_exec, exit_exec)
            source_panel.append(row)
            source_matches.append({
                "source_primary_raw_id": source["primary_raw_id"],
                "ticker": ticker,
                "direction": direction,
                "source_entry_server_open": entry_text,
                "classification": match_class,
                "matched_proxy_signal_id": proxy["replay_signal_id"] if proxy else "",
                "proxy_offset_minutes": diff_minutes if diff_minutes is not None else "",
                "wrong_direction_proxy_within_one_bar": wrong_nearby,
                "proxy_state_before_at_source": boundary["proxy_state_before"],
                "direct_kernel_true": direct_expected,
            })

        pair_by_entry_signal = {pair["entry_signal_id"]: pair for pair in proxy_pairs}
        extra_panel: list[dict[str, Any]] = []
        for proxy in proxy_primaries:
            if proxy["replay_signal_id"] in matched_proxy_ids:
                continue
            ticker = proxy["ticker"]
            direction = "LONG" if proxy["transition"] == "PRIMARY_LONG" else "SHORT"
            entry_text = proxy["server_open"]
            decision_time = parse_time(entry_text)
            row = {
                "row_id": f"EXTRA_{proxy['replay_signal_id']}",
                "class": "PROXY_EXTRA_PRIMARY",
                "ticker": ticker,
                "direction": direction,
                "entry_server_open": entry_text,
                "proxy_signal_id": proxy["replay_signal_id"],
                "proxy_state_before": proxy["state_before"],
                "proxy_state_after": proxy["state_after"],
            }
            row.update(features_at(ticker=ticker, decision_time=decision_time, series_by_ticker=series_by_ticker, close_times=close_times, built_at=built_at))
            row.update(divergence_at(row_id=row["row_id"], ticker=ticker, direction=direction, decision_time=decision_time, entry_text=entry_text, series_by_ticker=series_by_ticker, close_times=close_times, pivots=pivots))
            pair = pair_by_entry_signal.get(proxy["replay_signal_id"])
            if pair is not None:
                exit_text = pair["exit_server_open"]
                row["exit_server_open"] = exit_text
                if entry_text in m1_index[ticker] and exit_text in m1_index[ticker]:
                    ai, zi = m1_index[ticker][entry_text], m1_index[ticker][exit_text]
                    if zi > ai:
                        entry_exec = execution_entry(direction, m1[ticker][ai], points[ticker])
                        exit_exec = execution_exit(direction, m1[ticker][zi], points[ticker])
                        row["outcome_return_bps"] = trade_return(direction, entry_exec, exit_exec)
            extra_panel.append(row)

        contrasts = numeric_contrasts(source_panel, extra_panel)
        cat_contrasts = categorical_contrasts(source_panel, extra_panel)
        match_counts = Counter(row["classification"] for row in source_matches)
        direct_kernel_count = sum(bool(row["direct_kernel_true"]) for row in source_matches)
        state_divergence_misses = sum(row["classification"] == "MISSED" and bool(row["direct_kernel_true"]) for row in source_matches)
        direct_kernel_misses = sum(row["classification"] == "MISSED" and not bool(row["direct_kernel_true"]) for row in source_matches)

        outcome_summary = [
            {"class": "GENUINE_SOURCE_PRIMARY", **metrics(source_panel, "outcome_return_bps")},
            {"class": "PROXY_EXTRA_PRIMARY", **metrics(extra_panel, "outcome_return_bps")},
        ]
        for ticker in ("XAUUSD", "BTCUSD"):
            for direction in ("LONG", "SHORT"):
                for class_name, rows in (("GENUINE_SOURCE_PRIMARY", source_panel), ("PROXY_EXTRA_PRIMARY", extra_panel)):
                    selected = [row for row in rows if row["ticker"] == ticker and row["direction"] == direction]
                    outcome_summary.append({"class": class_name, "ticker": ticker, "direction": direction, **metrics(selected, "outcome_return_bps")})

    except Exception as exc:
        print(f"[M9I BLOCKED] {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9I_GENUINE_SOURCE_VS_PROXY_GAP_AUDIT",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": built_at,
        "audit_only": True,
        "genuine_source_primary_count": len(source_panel),
        "proxy_primary_count_in_source_windows": len(proxy_primaries),
        "proxy_extra_primary_count": len(extra_panel),
        "source_match_counts": dict(match_counts),
        "source_direct_frozen_kernel_true_count": direct_kernel_count,
        "missed_source_with_direct_kernel_true_count": state_divergence_misses,
        "missed_source_with_direct_kernel_false_count": direct_kernel_misses,
        "source_outcome_metrics": metrics(source_panel, "outcome_return_bps"),
        "proxy_extra_outcome_metrics": metrics(extra_panel, "outcome_return_bps"),
        "top_numeric_feature_contrasts": contrasts[:20],
        "guardrails": {
            "source_and_proxy_tiers_separate": True,
            "proxy_called_genuine": False,
            "classifier_trained": False,
            "threshold_optimized": False,
            "future_features_used": False,
            "future_pivot_confirmation_used": False,
            "same_sample_gate_promotion_allowed": False,
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m8c_reset": False,
            "commission": "NOT_MODELED",
            "swap": "NOT_MODELED",
        },
    }
    quality = {
        "genuine_manifest": str(manifest_path),
        "frozen_source_count": 43,
        "feature_timeframes": list(FEATURE_TIMEFRAMES),
        "closed_bars_only": True,
        "direct_kernel_checked_at_source_boundary_regardless_of_state": True,
        "proxy_replay_state_initialized_from_full_available_M15_history": True,
        "fresh_divergence_age_windows_bars": [3, 5],
        "outcome_spread_adjusted": True,
        "commission": "NOT_MODELED",
        "swap": "NOT_MODELED",
        "mt5_files_root": str(files_root),
    }

    out_root = local_root / "outputs" / "M9I"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9I compares the 43 frozen genuine source PRIMARY boundaries against unchanged frozen-proxy PRIMARY states and proxy-extra states. It is diagnostic only and does not retrofit or promote a gate.\n",
        encoding="utf-8",
    )
    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_source_match_classification.csv", source_matches)
    write_csv(archive / "03_genuine_source_feature_panel.csv", source_panel)
    write_csv(archive / "04_proxy_extra_feature_panel.csv", extra_panel)
    write_csv(archive / "05_numeric_feature_contrast.csv", contrasts)
    write_csv(archive / "06_categorical_feature_contrast.csv", cat_contrasts)
    write_csv(archive / "07_outcome_summary.csv", outcome_summary)
    write_csv(archive / "08_proxy_primary_ledger_in_source_windows.csv", proxy_primaries)
    dump_json(archive / "09_data_quality.json", quality)
    (archive / "10_audit.log").write_text(
        "\n".join([
            "status=PASS_EXPLORATORY_ONLY",
            f"genuine_source_primary_count={len(source_panel)}",
            f"proxy_primary_count_in_source_windows={len(proxy_primaries)}",
            f"proxy_extra_primary_count={len(extra_panel)}",
            f"source_match_counts={dict(match_counts)}",
            f"source_direct_frozen_kernel_true_count={direct_kernel_count}",
            f"missed_source_with_direct_kernel_true_count={state_divergence_misses}",
            f"missed_source_with_direct_kernel_false_count={direct_kernel_misses}",
            "m7c_formula_changed=false",
            "m7c_threshold_changed=false",
            "m8c_reset=false",
            "",
        ]),
        encoding="utf-8",
    )
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_source_match_classification.csv",
        "03_genuine_source_feature_panel.csv", "04_proxy_extra_feature_panel.csv",
        "05_numeric_feature_contrast.csv", "06_categorical_feature_contrast.csv",
        "07_outcome_summary.csv", "08_proxy_primary_ledger_in_source_windows.csv",
        "09_data_quality.json", "10_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(
        f"[M9I PASS] source={len(source_panel)} proxy_primary={len(proxy_primaries)} "
        f"proxy_extra={len(extra_panel)} matches={dict(match_counts)}"
    )
    print("[M9I OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
