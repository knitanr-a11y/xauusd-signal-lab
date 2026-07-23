from __future__ import annotations

import json
import os
import shutil
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
RESEARCH_ROOT = REPO_ROOT / "scripts" / "mochipoyo_alert_research"
M9I_PY = RESEARCH_ROOT / "m9i" / "python"
for path in (RESEARCH_ROOT, M9I_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_genuine_source_vs_proxy_gap_audit as audit

# Keep the divergence helper inside M9I's M5/M15/H1/H4 feature contract.
audit.m9e.TIMEFRAMES = audit.FEATURE_TIMEFRAMES

TIME_FORMAT = audit.TIME_FORMAT
DECISION_SHIFT = timedelta(minutes=15)
EXPECTED_SOURCE = 43


def corrected_time(text: str) -> datetime:
    return audit.parse_time(text) + DECISION_SHIFT


def corrected_text(text: str) -> str:
    return corrected_time(text).strftime(TIME_FORMAT)


def write_outputs(root: Path, files: dict[str, Any]) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    for name, payload in files.items():
        path = archive / name
        if name.endswith(".json"):
            audit.dump_json(path, payload)
        elif name.endswith(".csv"):
            audit.write_csv(path, payload)
        else:
            path.write_text(str(payload), encoding="utf-8")
    names = list(files)
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    return latest


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    meta_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    manifest_path = REPO_ROOT / "config" / "mochipoyo_alert_research" / "m9b_frozen_genuine_primary_pairs_20260724.json"
    if not meta_path.is_file() or not manifest_path.is_file():
        print("[M9I2 BLOCKED] required metadata or frozen source manifest missing")
        return 2

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_pairs = list(manifest.get("pairs", []))
    if len(source_pairs) != EXPECTED_SOURCE:
        print(f"[M9I2 BLOCKED] expected {EXPECTED_SOURCE} frozen source PRIMARY pairs, got {len(source_pairs)}")
        return 2
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print(f"[M9I2 BLOCKED] MT5 Files root unavailable: {files_root}")
        return 2

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        proxy_signals: list[dict[str, Any]] = []
        proxy_pairs: list[dict[str, Any]] = []
        boundary_state: dict[str, dict[str, dict[str, Any]]] = {}
        for ticker in ("XAUUSD", "BTCUSD"):
            signals, pairs, states = audit.replay_proxy(ticker, files_root, built_at)
            proxy_signals.extend(signals)
            proxy_pairs.extend(pairs)
            boundary_state[ticker] = states

        windows: dict[str, tuple[datetime, datetime]] = {}
        for ticker in ("XAUUSD", "BTCUSD"):
            times = [corrected_time(row["entry_server_open"]) for row in source_pairs if row["ticker"] == ticker]
            windows[ticker] = (min(times), max(times))

        proxy_primaries: list[dict[str, Any]] = []
        for row in proxy_signals:
            if not row["transition"].startswith("PRIMARY_"):
                continue
            current = audit.parse_time(row["server_open"])
            start, end = windows[row["ticker"]]
            if start <= current <= end:
                proxy_primaries.append(row)

        series_by_ticker: dict[str, dict[str, Any]] = defaultdict(dict)
        close_times: dict[str, dict[str, list[datetime]]] = defaultdict(dict)
        for ticker in ("XAUUSD", "BTCUSD"):
            for timeframe in audit.FEATURE_TIMEFRAMES:
                series = audit.load_indicator_series(files_root / audit.FILE_MAP[ticker][timeframe])
                series_by_ticker[ticker][timeframe] = series
                delta = timedelta(seconds=audit.TF_SECONDS[timeframe])
                close_times[ticker][timeframe] = [bar.server_open + delta for bar in series.bars]
        pivots = audit.build_pivots(series_by_ticker)

        m1 = {ticker: audit.load_m1(files_root / audit.FILE_MAP[ticker]["M1"]) for ticker in ("XAUUSD", "BTCUSD")}
        m1_index = {ticker: {row["time_text"]: i for i, row in enumerate(rows)} for ticker, rows in m1.items()}
        points = {ticker: float(meta["symbols"][ticker]["point"]) for ticker in ("XAUUSD", "BTCUSD")}

        source_panel: list[dict[str, Any]] = []
        source_matches: list[dict[str, Any]] = []
        matched_proxy_ids: set[str] = set()
        source_outcome_missing = 0

        for source in source_pairs:
            ticker = source["ticker"]
            direction = source["direction"]
            source_bar_open = source["entry_server_open"]
            source_exit_bar_open = source["exit_server_open"]
            decision_text = corrected_text(source_bar_open)
            exit_decision_text = corrected_text(source_exit_bar_open)
            decision_time = audit.parse_time(decision_text)

            match_source = {**source, "entry_server_open": decision_text}
            match_class, proxy, diff_minutes, wrong_nearby = audit.nearest_proxy(match_source, proxy_primaries)
            if proxy is not None:
                matched_proxy_ids.add(proxy["replay_signal_id"])

            boundary = boundary_state[ticker].get(decision_text)
            if boundary is None:
                raise RuntimeError(f"corrected source decision M15 boundary missing: {ticker} {decision_text}")
            direct_expected = bool(boundary["direct_long_kernel"] if direction == "LONG" else boundary["direct_short_kernel"])

            row: dict[str, Any] = {
                "row_id": f"SOURCE_{source['primary_raw_id']}",
                "class": "GENUINE_SOURCE_PRIMARY_TIMING_CORRECTED",
                "ticker": ticker,
                "direction": direction,
                "source_bar_open": source_bar_open,
                "source_decision_server_open": decision_text,
                "source_exit_bar_open": source_exit_bar_open,
                "source_exit_decision_server_open": exit_decision_text,
                "source_primary_raw_id": source["primary_raw_id"],
                "source_match_class": match_class,
                "matched_proxy_signal_id": proxy["replay_signal_id"] if proxy else "",
                "proxy_offset_minutes": diff_minutes if diff_minutes is not None else "",
                "wrong_direction_proxy_within_one_bar": wrong_nearby,
                "direct_frozen_primary_kernel_true_at_corrected_source_decision": direct_expected,
                **boundary,
            }
            row.update(audit.features_at(ticker=ticker, decision_time=decision_time, series_by_ticker=series_by_ticker, close_times=close_times, built_at=built_at))
            row.update(audit.divergence_at(row_id=row["row_id"], ticker=ticker, direction=direction, decision_time=decision_time, entry_text=decision_text, series_by_ticker=series_by_ticker, close_times=close_times, pivots=pivots))

            if decision_text in m1_index[ticker] and exit_decision_text in m1_index[ticker]:
                ai, zi = m1_index[ticker][decision_text], m1_index[ticker][exit_decision_text]
                if zi > ai:
                    entry_exec = audit.execution_entry(direction, m1[ticker][ai], points[ticker])
                    exit_exec = audit.execution_exit(direction, m1[ticker][zi], points[ticker])
                    row["outcome_return_bps"] = audit.trade_return(direction, entry_exec, exit_exec)
                else:
                    source_outcome_missing += 1
            else:
                source_outcome_missing += 1
            source_panel.append(row)
            source_matches.append({
                "source_primary_raw_id": source["primary_raw_id"],
                "ticker": ticker,
                "direction": direction,
                "source_bar_open": source_bar_open,
                "corrected_source_decision_server_open": decision_text,
                "classification": match_class,
                "matched_proxy_signal_id": proxy["replay_signal_id"] if proxy else "",
                "proxy_offset_minutes": diff_minutes if diff_minutes is not None else "",
                "proxy_state_before_at_corrected_source_decision": boundary["proxy_state_before"],
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
            decision_time = audit.parse_time(entry_text)
            row: dict[str, Any] = {
                "row_id": f"EXTRA_{proxy['replay_signal_id']}",
                "class": "PROXY_EXTRA_PRIMARY",
                "ticker": ticker,
                "direction": direction,
                "entry_server_open": entry_text,
                "proxy_signal_id": proxy["replay_signal_id"],
                "proxy_state_before": proxy["state_before"],
                "proxy_state_after": proxy["state_after"],
            }
            row.update(audit.features_at(ticker=ticker, decision_time=decision_time, series_by_ticker=series_by_ticker, close_times=close_times, built_at=built_at))
            row.update(audit.divergence_at(row_id=row["row_id"], ticker=ticker, direction=direction, decision_time=decision_time, entry_text=entry_text, series_by_ticker=series_by_ticker, close_times=close_times, pivots=pivots))
            pair = pair_by_entry_signal.get(proxy["replay_signal_id"])
            if pair is not None:
                exit_text = pair["exit_server_open"]
                row["exit_server_open"] = exit_text
                if entry_text in m1_index[ticker] and exit_text in m1_index[ticker]:
                    ai, zi = m1_index[ticker][entry_text], m1_index[ticker][exit_text]
                    if zi > ai:
                        entry_exec = audit.execution_entry(direction, m1[ticker][ai], points[ticker])
                        exit_exec = audit.execution_exit(direction, m1[ticker][zi], points[ticker])
                        row["outcome_return_bps"] = audit.trade_return(direction, entry_exec, exit_exec)
            extra_panel.append(row)

        contrasts = audit.numeric_contrasts(source_panel, extra_panel)
        cat_contrasts = audit.categorical_contrasts(source_panel, extra_panel)
        match_counts = Counter(row["classification"] for row in source_matches)
        direct_kernel_count = sum(bool(row["direct_kernel_true"]) for row in source_matches)
        state_divergence_misses = sum(row["classification"] == "MISSED" and bool(row["direct_kernel_true"]) for row in source_matches)
        direct_kernel_misses = sum(row["classification"] == "MISSED" and not bool(row["direct_kernel_true"]) for row in source_matches)

        outcome_summary: list[dict[str, Any]] = [
            {"class": "GENUINE_SOURCE_PRIMARY_TIMING_CORRECTED", **audit.metrics(source_panel, "outcome_return_bps")},
            {"class": "PROXY_EXTRA_PRIMARY", **audit.metrics(extra_panel, "outcome_return_bps")},
        ]
        for ticker in ("XAUUSD", "BTCUSD"):
            for direction in ("LONG", "SHORT"):
                for class_name, rows in (("GENUINE_SOURCE_PRIMARY_TIMING_CORRECTED", source_panel), ("PROXY_EXTRA_PRIMARY", extra_panel)):
                    selected = [row for row in rows if row["ticker"] == ticker and row["direction"] == direction]
                    outcome_summary.append({"class": class_name, "ticker": ticker, "direction": direction, **audit.metrics(selected, "outcome_return_bps")})

        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "M9I2_SOURCE_TIMING_CORRECTED_GAP_AUDIT",
            "status": "PASS_EXPLORATORY_ONLY",
            "run_at_utc": built_at,
            "audit_only": True,
            "timing_correction": {
                "source_entry_decision_shift_minutes": 15,
                "source_exit_decision_shift_minutes": 15,
                "proxy_timing_changed": False,
                "old_m9i_invalidated": True,
                "old_m9b_source_outcome_metrics_pending_replacement": True,
            },
            "genuine_source_primary_count": len(source_panel),
            "source_outcome_missing_exact_m1": source_outcome_missing,
            "proxy_primary_count_in_corrected_source_windows": len(proxy_primaries),
            "proxy_extra_primary_count": len(extra_panel),
            "source_match_counts": dict(match_counts),
            "source_direct_frozen_kernel_true_count": direct_kernel_count,
            "missed_source_with_direct_kernel_true_count": state_divergence_misses,
            "missed_source_with_direct_kernel_false_count": direct_kernel_misses,
            "source_outcome_metrics_timing_corrected": audit.metrics(source_panel, "outcome_return_bps"),
            "proxy_extra_outcome_metrics": audit.metrics(extra_panel, "outcome_return_bps"),
            "top_numeric_feature_contrasts": contrasts[:20],
            "guardrails": {
                "source_and_proxy_tiers_separate": True,
                "source_bar_open_not_used_as_execution_time": True,
                "classifier_trained": False,
                "threshold_optimized": False,
                "future_features_used": False,
                "same_sample_gate_promotion_allowed": False,
                "m7c_formula_changed": False,
                "m7c_threshold_changed": False,
                "m8c_reset": False,
                "commission": "NOT_MODELED",
                "swap": "NOT_MODELED",
            },
        }
        quality = {
            "frozen_source_count": EXPECTED_SOURCE,
            "source_decision_time": "source M15 bar open + 15 minutes",
            "source_exit_decision_time": "source exit M15 bar open + 15 minutes",
            "closed_bars_only": True,
            "exact_m1_required_for_source_outcome": True,
            "nearest_or_future_m1_fallback": False,
            "proxy_timing": "UNCHANGED_FROZEN_M7C_DECISION_BOUNDARY",
            "historical_spread_used": True,
            "commission": "NOT_MODELED",
            "swap": "NOT_MODELED",
            "mt5_files_root": str(files_root),
        }
        audit_log = "\n".join([
            "status=PASS_EXPLORATORY_ONLY",
            "stage=M9I2_SOURCE_TIMING_CORRECTED_GAP_AUDIT",
            f"genuine_source_primary_count={len(source_panel)}",
            f"proxy_primary_count={len(proxy_primaries)}",
            f"proxy_extra_primary_count={len(extra_panel)}",
            f"source_match_counts={dict(match_counts)}",
            f"source_direct_frozen_kernel_true_count={direct_kernel_count}",
            f"source_outcome_missing_exact_m1={source_outcome_missing}",
            "source_decision_shift_minutes=15",
            "source_exit_decision_shift_minutes=15",
            "m7c_formula_changed=false",
            "m7c_threshold_changed=false",
            "m8c_reset=false",
            "",
        ])
        readme = (
            "M9I2 corrects the confirmed off-by-one-M15 source timing error in M9I. "
            "Source bar-open timestamps identify the bar whose close produced the alert; source decision/execution is therefore evaluated at the next M15 open (+15 minutes). "
            "Proxy timing is unchanged. Old M9I source comparisons and old M9B source outcome metrics are not promotable until replaced by this corrected audit.\n"
        )
        latest = write_outputs(
            local_root / "outputs" / "M9I2",
            {
                "00_READ_ME_FIRST.txt": readme,
                "01_summary.json": summary,
                "02_source_match_classification.csv": source_matches,
                "03_genuine_source_feature_panel.csv": source_panel,
                "04_proxy_extra_feature_panel.csv": extra_panel,
                "05_numeric_feature_contrast.csv": contrasts,
                "06_categorical_feature_contrast.csv": cat_contrasts,
                "07_outcome_summary.csv": outcome_summary,
                "08_data_quality.json": quality,
                "09_audit.log": audit_log,
            },
        )
    except Exception as exc:
        print(f"[M9I2 BLOCKED] {exc}")
        return 2

    print(
        f"[M9I2 PASS] source={len(source_panel)} proxy_primary={len(proxy_primaries)} "
        f"extra={len(extra_panel)} matches={dict(match_counts)}"
    )
    print("[M9I2 OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
