from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for directory in (MR / "m10a" / "python", MR / "m10w22" / "python", MR / "m10w25" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import frozen_core as c
import run_high_atr_bullish_new_causal_information_availability_audit as feature_core
import run_m10w25_neither_prefix_causal_live_parity_audit as causal_core

STAGE = "M10W27_LOW_ATR_BULLISH_NEITHER_CAUSAL_INFORMATION_AVAILABILITY_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w27_low_atr_bullish_neither_causal_information_availability_contract_20260728.json"
TIME_FORMAT = c.TIME_FORMAT
ATR_LOW_BOUNDARY = 0.33
FEATURES = [
    "h1_atr_pct100",
    "m5_tick_volume_ratio20",
    "m5_body_ratio",
    "m5_close_location",
    "m5_lower_wick_ratio",
    "m5_upper_wick_ratio",
    "m5_ret3_bps",
    "m5_range3_bps",
    "m1_ret5_bps",
    "m1_up_close_count5",
    "m1_close_location",
    "m1_range5_bps",
    "last_closed_m1_spread_bps",
]


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


def coverage_presence(decision: datetime, bins: dict[str, set[datetime]]) -> dict[str, bool]:
    aligned = causal_core.floor_m15(decision)
    return {family: aligned in bins[family] for family in causal_core.FAMILIES}


def build_rows(bars: dict[str, list[c.Bar]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    m1, m5, m15, h1, h4, d1 = (bars[key] for key in ("M1", "M5", "M15", "H1", "H4", "D1"))
    h1_line = feature_core.macd_line_bps(h1)
    h1_atrp = feature_core.atr_percentile100(h1)
    h4_close = [float(bar.close) for bar in h4]
    h4_e20, h4_e30 = c.ema(h4_close, 20), c.ema(h4_close, 30)
    d1_close = [float(bar.close) for bar in d1]
    d1_e20, d1_e30, d1_e40 = c.ema(d1_close, 20), c.ema(d1_close, 30), c.ema(d1_close, 40)

    h1_ct = [bar.time + timedelta(hours=1) for bar in h1]
    h4_ct = [bar.time + timedelta(hours=4) for bar in h4]
    d1_ct = [bar.time + timedelta(days=1) for bar in d1]
    m5_ct = [bar.time + timedelta(minutes=5) for bar in m5]
    m1_ct = [bar.time + timedelta(minutes=1) for bar in m1]

    long_bins, long_diagnostics = causal_core.build_prefix_causal_long_bins(bars)
    short_bins, short_diagnostics = causal_core.build_short_bins(bars)
    bins = {**long_bins, **short_bins}

    rows: list[dict[str, Any]] = []
    broader_regime_count = 0
    excluded_by_coverage = {"LONG_ONLY": 0, "SHORT_ONLY": 0, "BOTH": 0}
    source_timing_violations = 0

    for decision_bar in m15[1:]:
        decision = decision_bar.time
        ih1 = bisect.bisect_right(h1_ct, decision) - 1
        ih4 = bisect.bisect_right(h4_ct, decision) - 1
        id1 = bisect.bisect_right(d1_ct, decision) - 1
        i5 = bisect.bisect_right(m5_ct, decision) - 1
        i1 = bisect.bisect_right(m1_ct, decision) - 1
        if min(ih1, ih4, id1, i5, i1) < 0 or h1_atrp[ih1] is None:
            continue
        regime = (
            d1_e20[id1] > d1_e30[id1] > d1_e40[id1]
            and h4_e20[ih4] > h4_e30[ih4]
            and h1_line[ih1] > 0
            and float(h1_atrp[ih1]) < ATR_LOW_BOUNDARY
        )
        if not regime:
            continue
        broader_regime_count += 1
        presence = coverage_presence(decision, bins)
        coverage = causal_core.coverage_class(presence)
        if coverage != "NEITHER":
            excluded_by_coverage[coverage] += 1
            continue
        if i5 < 19 or i5 < 3 or i1 < 4:
            continue

        last5 = m5[i5]
        last1 = m1[i1]
        if last5.time + timedelta(minutes=5) > decision or last1.time + timedelta(minutes=1) > decision:
            source_timing_violations += 1
            continue

        shape5 = feature_core.bar_shape(last5)
        shape1 = feature_core.bar_shape(last1)
        volume_mean = sum(float(m5[j].tick_volume) for j in range(i5 - 19, i5 + 1)) / 20.0
        m5_ret3 = (float(m5[i5].close) / max(abs(float(m5[i5 - 3].close)), 1e-12) - 1.0) * 10000.0
        m5_range3 = (
            max(float(m5[j].high) for j in range(i5 - 2, i5 + 1))
            - min(float(m5[j].low) for j in range(i5 - 2, i5 + 1))
        ) / max(abs(float(m5[i5].close)), 1e-12) * 10000.0
        m1_ret5 = (float(m1[i1].close) / max(abs(float(m1[i1 - 4].open)), 1e-12) - 1.0) * 10000.0
        m1_up_count = sum(float(m1[j].close) > float(m1[j].open) for j in range(i1 - 4, i1 + 1))
        m1_range5 = (
            max(float(m1[j].high) for j in range(i1 - 4, i1 + 1))
            - min(float(m1[j].low) for j in range(i1 - 4, i1 + 1))
        ) / max(abs(float(m1[i1].close)), 1e-12) * 10000.0
        spread_bps = (int(last1.spread) * c.POINT) / max(abs(float(last1.close)), 1e-12) * 10000.0

        row: dict[str, Any] = {
            "decision_time": decision.strftime(TIME_FORMAT),
            "year": decision.year,
            "causal_coverage_class": coverage,
            "h1_atr_pct100": float(h1_atrp[ih1]),
            "m5_tick_volume_ratio20": feature_core.safe_ratio(float(last5.tick_volume), volume_mean),
            "m5_body_ratio": shape5["body_ratio"],
            "m5_close_location": shape5["close_location"],
            "m5_lower_wick_ratio": shape5["lower_wick_ratio"],
            "m5_upper_wick_ratio": shape5["upper_wick_ratio"],
            "m5_ret3_bps": m5_ret3,
            "m5_range3_bps": m5_range3,
            "m1_ret5_bps": m1_ret5,
            "m1_up_close_count5": m1_up_count,
            "m1_close_location": shape1["close_location"],
            "m1_range5_bps": m1_range5,
            "last_closed_m1_spread_bps": spread_bps,
            "m5_source_open": last5.time.strftime(TIME_FORMAT),
            "m1_source_open": last1.time.strftime(TIME_FORMAT),
            "h1_source_open": h1[ih1].time.strftime(TIME_FORMAT),
            "h4_source_open": h4[ih4].time.strftime(TIME_FORMAT),
            "d1_source_open": d1[id1].time.strftime(TIME_FORMAT),
        }
        for family in causal_core.FAMILIES:
            row[family] = presence[family]
        rows.append(row)

    if source_timing_violations:
        raise RuntimeError(f"lower-timeframe source timing violations: {source_timing_violations}")
    diagnostics = {
        "broader_low_atr_bullish_regime_count": broader_regime_count,
        "causal_neither_count": len(rows),
        "excluded_by_causal_coverage": excluded_by_coverage,
        "long_family": long_diagnostics,
        "short_family": short_diagnostics,
        "lower_timeframe_source_timing_violation_count": 0,
        "future_return_computed": False,
        "future_path_read": False,
    }
    return rows, diagnostics


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W27"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W27 contract")
        data_root = feature_core.resolve_data_root(local_root)
        bars, hashes, paths = feature_core.verify_and_load(data_root)
        rows, causal_diagnostics = build_rows(bars)
        if not rows:
            raise RuntimeError("no prefix-causal low-ATR bullish NEITHER rows")

        groups: dict[str, list[dict[str, Any]]] = {"ALL": rows}
        for year in (2023, 2024, 2025, 2026):
            groups[str(year)] = [row for row in rows if int(row["year"]) == year]
        summaries: list[dict[str, Any]] = []
        for group_name, items in groups.items():
            for feature in FEATURES:
                summaries.append({"group": group_name, **feature_core.feature_summary(items, feature)})
        real_volume = {
            "M1": feature_core.real_volume_nonzero_fraction(paths["M1"]),
            "M5": feature_core.real_volume_nonzero_fraction(paths["M5"]),
        }
        year_counts = {str(year): len(groups[str(year)]) for year in (2023, 2024, 2025, 2026)}
        degenerate = [
            row for row in summaries
            if row["group"] == "ALL"
            and (int(row["unique_count"]) <= 1 or (row["variance"] is not None and float(row["variance"]) == 0.0))
        ]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_OUTCOME_BLIND_LOW_ATR_BULLISH_CAUSAL_NEITHER_INFORMATION_AUDIT_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target_regime": "D1 bullish; H4 EMA20>EMA30; H1 MACD line>0; H1 ATR pct100<0.33; prefix-causal coverage=NEITHER",
            "causal_neither_row_count": len(rows),
            "year_counts": year_counts,
            "causal_coverage_diagnostics": causal_diagnostics,
            "degenerate_feature_count": len(degenerate),
            "real_volume": real_volume,
            "frozen_data_sha256": hashes,
            "outcome_blind_audit": {
                "trade_outcomes_read": False,
                "future_return_computed": False,
                "pf_or_pnl_computed": False,
                "win_loss_label_read": False,
                "feature_profit_ranking": False,
                "entry_formula_created": False,
                "feature_threshold_selected": False,
            },
            "relationship_to_forward": {
                "M10W26_start": "2026.07.28 15:58:00",
                "M10W26_modified": False,
                "existing_monitors_modified": False,
                "historical_backfill_into_forward": False,
            },
            "guardrails": {
                "audit_only": True,
                "discord_send": False,
                "mt5_order": False,
                "live_ready": False,
                "final_signal": False,
                "automatic_live_promotion": False,
            },
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W27 is an outcome-blind causal information inventory for the low-ATR bullish prefix-causal NEITHER blind spot. It does not read or compute returns, PF, PnL, labels or future paths, and it does not modify M10W26 or any existing monitor.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_low_atr_bullish_causal_neither_feature_rows.csv", rows)
        write_csv(archive / "03_feature_availability_distribution.csv", summaries)
        write_csv(archive / "04_degenerate_features.csv", degenerate)
        (archive / "05_causal_coverage_diagnostics.json").write_text(json.dumps(causal_diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "06_real_volume_availability.json").write_text(json.dumps(real_volume, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_data_quality.json").write_text(json.dumps({"data_root": str(data_root), "frozen_data_sha256": hashes, "closed_rows_contract": True, "time_basis": "MT5_SERVER_TIME", "nearest_m1_fallback": False, "historical_backfill_into_forward": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "08_audit.log").write_text("\n".join([
            "status=PASS_OUTCOME_BLIND_LOW_ATR_BULLISH_CAUSAL_NEITHER_INFORMATION_AUDIT_ONLY",
            f"causal_neither_row_count={len(rows)}",
            f"year_counts={json.dumps(year_counts, sort_keys=True)}",
            "trade_outcomes_read=false",
            "future_return_computed=false",
            "pf_or_pnl_computed=false",
            "win_loss_label_read=false",
            "feature_profit_ranking=false",
            "entry_formula_created=false",
            "feature_threshold_selected=false",
            "M10W26_modified=false",
            "existing_monitors_modified=false",
            "discord_send=false",
            "mt5_order=false",
            "",
        ]), encoding="utf-8")
        names = sorted(path.name for path in archive.iterdir() if path.is_file())
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(archive / name, name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print(f"[M10W27 PASS] causal_neither_rows={len(rows)} years={year_counts}")
        print(f"[M10W27 PACKAGE] {latest / '99_UPLOAD_PACKAGE.zip'}")
        return 0
    except Exception as exc:
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "latest_blocked.txt").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        print(f"[M10W27 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
