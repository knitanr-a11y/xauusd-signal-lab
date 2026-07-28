from __future__ import annotations

import bisect
import csv
import json
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
for directory in (MR / "m10a" / "python", MR / "m10w13" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import frozen_core as c
import run_m10w13_frozen_historical_short_activation_interval_calibration as short_hist

STAGE = "M10W25_NEITHER_PREFIX_CAUSAL_LIVE_PARITY_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w25_neither_prefix_causal_live_parity_audit_contract_20260728.json"
TIME_FORMAT = c.TIME_FORMAT
FAMILIES = (
    "LONG_M5_S1",
    "LONG_M15_S2",
    "LONG_H1_S3",
    "LONG_H4_S4",
    "SHORT_M10P_C056_G013",
    "SHORT_M10P2_C0212",
)
TF_TO_FAMILY = {
    "M5": "LONG_M5_S1",
    "M15": "LONG_M15_S2",
    "H1": "LONG_H1_S3",
    "H4": "LONG_H4_S4",
}
EXPECTED_GRID_ROWS = 81329
EXPECTED_TARGET_ROWS = 8648
EXPECTED_TARGET_NEITHER = 5917


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


def parse_bool(value: Any) -> bool:
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    raise RuntimeError(f"invalid boolean value: {value!r}")


def pt(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def ft(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def floor_m15(value: datetime) -> datetime:
    return value.replace(minute=(value.minute // 15) * 15, second=0, microsecond=0)


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10A_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = load_json(metadata_path) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def verify_and_load(data_root: Path) -> tuple[dict[str, list[c.Bar]], dict[str, str]]:
    bars: dict[str, list[c.Bar]] = {}
    hashes: dict[str, str] = {}
    for timeframe in ("M1", "M5", "M15", "H1", "H4", "D1"):
        filename, expected_hash = c.EXPECTED_FILES[timeframe]
        path = data_root / filename
        if not path.is_file():
            raise RuntimeError(f"missing frozen GOLD file: {path}")
        actual_hash = c.sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"frozen SHA256 mismatch {timeframe}: {actual_hash} expected={expected_hash}")
        bars[timeframe] = c.load_bars(path)
        hashes[timeframe] = actual_hash
    return bars, hashes


def load_historical_grid(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"M10W14 coverage grid missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        required = {
            "decision_time",
            "d1_ema_stack",
            "h4_ema20_minus_ema30_sign",
            "h1_macd_line_sign",
            "h1_atr_pct100_tercile",
            "coverage_class",
            *FAMILIES,
        }
        missing = sorted(required - fields)
        if missing:
            raise RuntimeError(f"M10W14 coverage grid missing columns: {missing}")
        rows = list(reader)
    if not rows:
        raise RuntimeError("M10W14 coverage grid empty")
    decisions = [str(row["decision_time"]) for row in rows]
    if len(decisions) != len(set(decisions)):
        raise RuntimeError("duplicate decision_time in M10W14 coverage grid")
    return rows


def load_corrected_feature_times(path: Path) -> set[datetime]:
    if not path.is_file():
        raise RuntimeError(f"M10W24B corrected feature rows missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        if "decision_time" not in fields:
            raise RuntimeError("M10W24B corrected feature rows missing decision_time")
        forbidden = {"actual_return_bps", "fixed0p20_return_bps", "trade_id", "status", "scheduled_exit_time"}
        found = sorted(fields & forbidden)
        if found:
            raise RuntimeError(f"outcome/trade columns unexpectedly present in pre-entry feature file: {found}")
        values = [pt(str(row["decision_time"])) for row in reader]
    if not values:
        raise RuntimeError("M10W24B corrected feature rows empty")
    if len(values) != len(set(values)):
        raise RuntimeError("duplicate decision_time in M10W24B corrected feature rows")
    return set(values)


def build_branch_context(bars: dict[str, list[c.Bar]]) -> dict[str, Any]:
    close_times = {
        "M5": [bar.time + timedelta(minutes=5) for bar in bars["M5"]],
        "M15": [bar.time + timedelta(minutes=15) for bar in bars["M15"]],
        "H1": [bar.time + timedelta(hours=1) for bar in bars["H1"]],
        "H4": [bar.time + timedelta(hours=4) for bar in bars["H4"]],
        "D1": [bar.time + timedelta(days=1) for bar in bars["D1"]],
    }
    ratio20_m5 = c.m5_ratio20(bars["M5"])
    macd = {tf: c.macd_bps(bars[tf]) for tf in ("M5", "M15", "H1", "H4", "D1")}
    rci9_h1 = c.rci_series([bar.close for bar in bars["H1"]], 9)
    rci9_d1 = c.rci_series([bar.close for bar in bars["D1"]], 9)
    d1_closes = [bar.close for bar in bars["D1"]]
    return {
        "close_times": close_times,
        "ratio20_m5": ratio20_m5,
        "macd": macd,
        "rci9_h1": rci9_h1,
        "rci9_d1": rci9_d1,
        "d1_ema20": c.ema(d1_closes, 20),
        "d1_ema30": c.ema(d1_closes, 30),
        "d1_ema40": c.ema(d1_closes, 40),
    }


def selected_index(close_times: list[datetime], decision: datetime) -> int:
    return bisect.bisect_right(close_times, decision) - 1


def branch_pass(timeframe: str, decision: datetime, ctx: dict[str, Any]) -> bool:
    close_times = ctx["close_times"]
    if timeframe == "M5":
        i5 = selected_index(close_times["M5"], decision)
        i15 = selected_index(close_times["M15"], decision)
        ih1 = selected_index(close_times["H1"], decision)
        if min(i5, i15, ih1) < 0:
            return False
        row = {"turn_entry_time": ft(decision), "m5_index": i5, "m15_index": i15, "h1_index": ih1}
        return bool(c.select_s1([row], ctx["ratio20_m5"], ctx["macd"], ctx["rci9_h1"]))
    if timeframe == "M15":
        i5 = selected_index(close_times["M5"], decision)
        i15 = selected_index(close_times["M15"], decision)
        if min(i5, i15) < 0:
            return False
        row = {"turn_entry_time": ft(decision), "m5_index": i5, "m15_index": i15}
        return bool(c.select_s2([row], ctx["ratio20_m5"], ctx["macd"]["M15"]))
    if timeframe == "H1":
        ih4 = selected_index(close_times["H4"], decision)
        id1 = selected_index(close_times["D1"], decision)
        if min(ih4, id1) < 0:
            return False
        row = {"turn_entry_time": ft(decision), "h4_index": ih4, "d1_index": id1}
        return bool(c.select_s3([row], ctx["macd"]["H4"], ctx["macd"]["D1"]))
    if timeframe == "H4":
        id1 = selected_index(close_times["D1"], decision)
        if id1 < 0:
            return False
        row = {"turn_entry_time": ft(decision), "d1_index": id1}
        return bool(c.select_s4([row], ctx["rci9_d1"], ctx["d1_ema20"], ctx["d1_ema30"], ctx["d1_ema40"]))
    raise RuntimeError(f"unsupported timeframe: {timeframe}")


def primary_events(tf_bars: list[c.Bar]) -> list[dict[str, Any]]:
    closes = [bar.close for bar in tf_bars]
    rci9 = c.rci_series(closes, 9)
    ema20 = c.ema(closes, 20)
    ema30 = c.ema(closes, 30)
    ema40 = c.ema(closes, 40)
    events: list[dict[str, Any]] = []
    for current_index in range(50, len(tf_bars)):
        selected = current_index - 1
        current = rci9[selected]
        previous = rci9[selected - 1]
        previous2 = rci9[selected - 2]
        if current is None or previous is None or previous2 is None:
            continue
        events.append({
            "time": tf_bars[current_index].time,
            "current_rci9": float(current),
            "turn_up": bool(current > previous and previous <= previous2),
            "turn_down": bool(current < previous and previous >= previous2),
            "bullish": bool(ema20[selected] > ema30[selected] > ema40[selected]),
            "bearish": bool(ema20[selected] < ema30[selected] < ema40[selected]),
        })
    return events


def build_prefix_causal_long_bins(bars: dict[str, list[c.Bar]]) -> tuple[dict[str, set[datetime]], dict[str, Any]]:
    m1 = bars["M1"]
    m1_index = {bar.time: i for i, bar in enumerate(m1)}
    ctx = build_branch_context(bars)
    bins: dict[str, set[datetime]] = {name: set() for name in TF_TO_FAMILY.values()}
    diagnostics: dict[str, Any] = {}

    for timeframe, family in TF_TO_FAMILY.items():
        events = primary_events(bars[timeframe])
        event_cursor = 0
        state = "IDLE"
        signal_bid: float | None = None
        entry_m1_index: int | None = None
        raw_first_turn_consumed = False
        active_long_entries = 0
        active_short_entries = 0
        exact_m1_entry_missing = 0
        raw_first_turn_count = 0
        selected_branch_count = 0
        exit_long_count = 0
        exit_short_count = 0

        for decision_index, decision_bar in enumerate(m1):
            decision = decision_bar.time

            while event_cursor < len(events) and events[event_cursor]["time"] <= decision:
                event = events[event_cursor]
                event_time = event["time"]
                if state == "IDLE":
                    if bool(event["turn_up"]) and bool(event["bullish"]):
                        state = "ACTIVE_LONG"
                        active_long_entries += 1
                        ep = m1_index.get(event_time)
                        if ep is None:
                            signal_bid = None
                            entry_m1_index = None
                            exact_m1_entry_missing += 1
                        else:
                            signal_bid = float(m1[ep].open)
                            entry_m1_index = ep
                        raw_first_turn_consumed = False
                    elif bool(event["turn_down"]) and bool(event["bearish"]):
                        state = "ACTIVE_SHORT"
                        active_short_entries += 1
                        signal_bid = None
                        entry_m1_index = None
                        raw_first_turn_consumed = False
                elif state == "ACTIVE_LONG" and float(event["current_rci9"]) >= c.LONG_EXIT_RCI9:
                    state = "IDLE"
                    signal_bid = None
                    entry_m1_index = None
                    raw_first_turn_consumed = False
                    exit_long_count += 1
                elif state == "ACTIVE_SHORT" and float(event["current_rci9"]) <= c.SHORT_EXIT_RCI9:
                    state = "IDLE"
                    signal_bid = None
                    entry_m1_index = None
                    raw_first_turn_consumed = False
                    exit_short_count += 1
                event_cursor += 1

            if state != "ACTIVE_LONG" or raw_first_turn_consumed or signal_bid is None or entry_m1_index is None:
                continue

            current_index = decision_index - 1
            if current_index < entry_m1_index + 1:
                continue
            history = m1[max(0, current_index - c.TURN_LOOKBACK):current_index]
            if len(history) < c.TURN_LOOKBACK or current_index <= 0:
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

            raw_first_turn_consumed = True
            raw_first_turn_count += 1
            if branch_pass(timeframe, decision, ctx):
                bins[family].add(floor_m15(decision))
                selected_branch_count += 1

        diagnostics[family] = {
            "primary_long_entries": active_long_entries,
            "primary_short_entries": active_short_entries,
            "exact_m1_primary_entry_missing": exact_m1_entry_missing,
            "raw_first_turn_count": raw_first_turn_count,
            "selected_branch_first_turn_count": selected_branch_count,
            "selected_m15_window_count": len(bins[family]),
            "long_exit_count": exit_long_count,
            "short_exit_count": exit_short_count,
            "terminal_state": state,
            "future_exit_reference": False,
            "completed_pair_required": False,
        }
    return bins, diagnostics


def build_short_bins(bars: dict[str, list[c.Bar]]) -> tuple[dict[str, set[datetime]], dict[str, Any]]:
    rows1 = [row for row in short_hist.build_m10p_rows(bars) if bool(row["all_pass"])]
    rows2 = [row for row in short_hist.build_m10p2_rows(bars) if bool(row["all_pass"])]

    source_violations = 0
    for row in rows1:
        decision = pt(str(row["decision_time"]))
        if pt(str(row["h1_source_open"])) + timedelta(hours=1) > decision:
            source_violations += 1
        if pt(str(row["d1_source_open"])) + timedelta(days=1) > decision:
            source_violations += 1
    for row in rows2:
        decision = pt(str(row["decision_time"]))
        if pt(str(row["h1_source_open"])) + timedelta(hours=1) > decision:
            source_violations += 1
        if pt(str(row["h4_source_open"])) + timedelta(hours=4) > decision:
            source_violations += 1
    if source_violations:
        raise RuntimeError(f"short-family source timing violations: {source_violations}")

    bins = {
        "SHORT_M10P_C056_G013": {floor_m15(pt(str(row["decision_time"]))) for row in rows1},
        "SHORT_M10P2_C0212": {floor_m15(pt(str(row["decision_time"]))) for row in rows2},
    }
    diagnostics = {
        "SHORT_M10P_C056_G013": {"activation_count": len(rows1), "m15_window_count": len(bins["SHORT_M10P_C056_G013"])},
        "SHORT_M10P2_C0212": {"activation_count": len(rows2), "m15_window_count": len(bins["SHORT_M10P2_C0212"])},
        "source_timing_violation_count": 0,
        "future_exit_reference": False,
    }
    return bins, diagnostics


def coverage_class(presence: dict[str, bool]) -> str:
    long_any = any(presence[name] for name in FAMILIES if name.startswith("LONG_"))
    short_any = any(presence[name] for name in FAMILIES if name.startswith("SHORT_"))
    if long_any and short_any:
        return "BOTH"
    if long_any:
        return "LONG_ONLY"
    if short_any:
        return "SHORT_ONLY"
    return "NEITHER"


def is_target(row: dict[str, Any]) -> bool:
    return (
        str(row["d1_ema_stack"]) == "BULLISH_20_GT_30_GT_40"
        and str(row["h4_ema20_minus_ema30_sign"]) == "POSITIVE"
        and str(row["h1_macd_line_sign"]) == "POSITIVE"
        and str(row["h1_atr_pct100_tercile"]) == "HIGH_GE_0P67"
    )


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W25"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W25 contract")

        data_root = resolve_data_root(local_root)
        if not data_root.is_dir():
            raise RuntimeError(f"frozen GOLD data root unavailable: {data_root}")
        bars, hashes = verify_and_load(data_root)

        grid_path = local_root / "outputs" / "M10W14" / "LATEST" / "02_m15_coverage_grid.csv"
        feature_path = local_root / "outputs" / "M10W24B" / "LATEST" / "02_corrected_neither_feature_rows.csv"
        historical_grid = load_historical_grid(grid_path)
        feature_times = load_corrected_feature_times(feature_path)

        if len(historical_grid) != EXPECTED_GRID_ROWS:
            raise RuntimeError(f"M10W14 grid row count drift: {len(historical_grid)} expected={EXPECTED_GRID_ROWS}")
        if len(feature_times) != EXPECTED_TARGET_NEITHER:
            raise RuntimeError(f"M10W24B corrected feature row count drift: {len(feature_times)} expected={EXPECTED_TARGET_NEITHER}")

        long_bins, long_diag = build_prefix_causal_long_bins(bars)
        short_bins, short_diag = build_short_bins(bars)
        causal_bins = {**long_bins, **short_bins}

        family_mismatch_counts = {name: 0 for name in FAMILIES}
        target_family_mismatch_counts = {name: 0 for name in FAMILIES}
        coverage_mismatch_count = 0
        target_coverage_mismatch_count = 0
        target_any_family_mismatch_rows = 0
        full_rows: list[dict[str, Any]] = []
        mismatch_rows: list[dict[str, Any]] = []
        target_mismatch_rows: list[dict[str, Any]] = []
        target_rows = 0
        historical_target_neither: set[datetime] = set()
        causal_target_neither: set[datetime] = set()

        for historical in historical_grid:
            decision = pt(str(historical["decision_time"]))
            historical_presence = {name: parse_bool(historical[name]) for name in FAMILIES}
            causal_presence = {name: decision in causal_bins[name] for name in FAMILIES}
            hist_class = str(historical["coverage_class"])
            causal_class = coverage_class(causal_presence)
            family_mismatch = {name: historical_presence[name] != causal_presence[name] for name in FAMILIES}
            any_family_mismatch = any(family_mismatch.values())
            class_mismatch = hist_class != causal_class
            target = is_target(historical)

            for name, mismatch in family_mismatch.items():
                if mismatch:
                    family_mismatch_counts[name] += 1
                    if target:
                        target_family_mismatch_counts[name] += 1
            if class_mismatch:
                coverage_mismatch_count += 1
                if target:
                    target_coverage_mismatch_count += 1
            if target:
                target_rows += 1
                if any_family_mismatch:
                    target_any_family_mismatch_rows += 1
                if hist_class == "NEITHER":
                    historical_target_neither.add(decision)
                if causal_class == "NEITHER":
                    causal_target_neither.add(decision)

            row = {
                "decision_time": ft(decision),
                "target_high_atr_bullish": target,
                "historical_coverage_class": hist_class,
                "causal_coverage_class": causal_class,
                "coverage_class_mismatch": class_mismatch,
                "any_family_presence_mismatch": any_family_mismatch,
                "d1_ema_stack": historical["d1_ema_stack"],
                "h4_ema20_minus_ema30_sign": historical["h4_ema20_minus_ema30_sign"],
                "h1_macd_line_sign": historical["h1_macd_line_sign"],
                "h1_atr_pct100_tercile": historical["h1_atr_pct100_tercile"],
            }
            for name in FAMILIES:
                row[f"historical_{name}"] = historical_presence[name]
                row[f"causal_{name}"] = causal_presence[name]
                row[f"mismatch_{name}"] = family_mismatch[name]
            full_rows.append(row)
            if any_family_mismatch or class_mismatch:
                mismatch_rows.append(row)
                if target:
                    target_mismatch_rows.append(row)

        if target_rows != EXPECTED_TARGET_ROWS:
            raise RuntimeError(f"target high-ATR bullish row count drift: {target_rows} expected={EXPECTED_TARGET_ROWS}")
        if len(historical_target_neither) != EXPECTED_TARGET_NEITHER:
            raise RuntimeError(f"historical target NEITHER count drift: {len(historical_target_neither)} expected={EXPECTED_TARGET_NEITHER}")

        diff_union = historical_target_neither | causal_target_neither | feature_times
        set_diff_rows: list[dict[str, Any]] = []
        for decision in sorted(diff_union):
            historical_flag = decision in historical_target_neither
            causal_flag = decision in causal_target_neither
            feature_flag = decision in feature_times
            if not (historical_flag == causal_flag == feature_flag):
                set_diff_rows.append({
                    "decision_time": ft(decision),
                    "historical_target_NEITHER": historical_flag,
                    "causal_target_NEITHER": causal_flag,
                    "M10W24B_preentry_feature_row": feature_flag,
                })

        target_family_mismatch_total = sum(target_family_mismatch_counts.values())
        pass_for_mmo1 = (
            target_rows == EXPECTED_TARGET_ROWS
            and len(historical_target_neither) == EXPECTED_TARGET_NEITHER
            and target_any_family_mismatch_rows == 0
            and target_family_mismatch_total == 0
            and target_coverage_mismatch_count == 0
            and len(causal_target_neither) == EXPECTED_TARGET_NEITHER
            and len(set_diff_rows) == 0
            and causal_target_neither == historical_target_neither == feature_times
        )
        status = (
            "PASS_MMO1_TARGET_NEITHER_PREFIX_CAUSAL_PARITY_AUDIT_ONLY"
            if pass_for_mmo1
            else "COMPLETE_TARGET_NEITHER_PREFIX_CAUSAL_MISMATCH_REQUIRES_CORRECTION_AUDIT_ONLY"
        )

        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": status,
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "frozen_data_root": str(data_root),
            "verified_sha256": hashes,
            "sources": {
                "historical_coverage_grid": str(grid_path),
                "corrected_preentry_feature_rows": str(feature_path),
                "outcome_files_read": False,
            },
            "reference_counts": {
                "historical_grid_rows": len(historical_grid),
                "target_high_atr_bullish_rows": target_rows,
                "historical_target_neither_rows": len(historical_target_neither),
                "M10W24B_preentry_feature_rows": len(feature_times),
            },
            "prefix_causal_long_diagnostics": long_diag,
            "prefix_causal_short_diagnostics": short_diag,
            "full_grid_parity": {
                "family_presence_mismatch_counts": family_mismatch_counts,
                "coverage_class_mismatch_count": coverage_mismatch_count,
                "mismatch_row_count": len(mismatch_rows),
            },
            "target_parity": {
                "family_presence_mismatch_counts": target_family_mismatch_counts,
                "any_family_mismatch_row_count": target_any_family_mismatch_rows,
                "coverage_class_mismatch_count": target_coverage_mismatch_count,
                "historical_target_neither_count": len(historical_target_neither),
                "causal_target_neither_count": len(causal_target_neither),
                "decision_set_symmetric_difference_count": len(set_diff_rows),
                "exact_three_way_decision_set_match": causal_target_neither == historical_target_neither == feature_times,
            },
            "decision": {
                "pass_for_MMO1_fresh_design": pass_for_mmo1,
                "M10W26_fresh_start_authorized_now": False,
                "next_if_pass": "Freeze M10W26 MMO1 fresh prospective shadow contract/runtime first; only its one-time initializer may create the new immutable live start.",
                "next_if_mismatch": "Do not read outcomes or tune. Freeze a causal-cohort correction contract before any outcome re-evaluation.",
            },
            "guardrails": contract["safety"],
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W25 outcome-blind prefix-causal live-parity audit for M10W24B coverage_class=NEITHER. "
            "No trade ledger, PF/PnL, future return, future path label, threshold refit, or prospective start creation is allowed.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_causal_coverage_grid_comparison.csv", full_rows)
        write_csv(archive / "03_full_grid_mismatch_rows.csv", mismatch_rows)
        write_csv(archive / "04_target_regime_mismatch_rows.csv", target_mismatch_rows)
        write_csv(archive / "05_target_neither_decision_set_diff.csv", set_diff_rows)
        (archive / "06_audit.log").write_text("\n".join([
            f"status={status}",
            f"historical_grid_rows={len(historical_grid)}",
            f"target_high_atr_bullish_rows={target_rows}",
            f"historical_target_neither_rows={len(historical_target_neither)}",
            f"causal_target_neither_rows={len(causal_target_neither)}",
            f"M10W24B_preentry_feature_rows={len(feature_times)}",
            f"target_any_family_mismatch_rows={target_any_family_mismatch_rows}",
            f"target_coverage_class_mismatch_count={target_coverage_mismatch_count}",
            f"target_neither_set_diff_count={len(set_diff_rows)}",
            f"full_grid_coverage_class_mismatch_count={coverage_mismatch_count}",
            "outcome_files_read=false",
            "future_return_computed=false",
            "future_episode_exit_used_for_presence=false",
            "new_prospective_start_created=false",
            "threshold_refit=false",
            "existing_forward_modified=false",
            "",
        ]), encoding="utf-8")

        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = [
            "00_READ_ME_FIRST.txt",
            "01_summary.json",
            "02_causal_coverage_grid_comparison.csv",
            "03_full_grid_mismatch_rows.csv",
            "04_target_regime_mismatch_rows.csv",
            "05_target_neither_decision_set_diff.csv",
            "06_audit.log",
        ]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)

        label = "PASS" if pass_for_mmo1 else "MISMATCH"
        print(
            f"[M10W25 {label}] target={target_rows} historical_neither={len(historical_target_neither)} "
            f"causal_neither={len(causal_target_neither)} target_mismatch={target_coverage_mismatch_count} "
            f"set_diff={len(set_diff_rows)}"
        )
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W25 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No outcome, threshold, prospective start, existing runtime, Discord, or MT5 order was modified.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
