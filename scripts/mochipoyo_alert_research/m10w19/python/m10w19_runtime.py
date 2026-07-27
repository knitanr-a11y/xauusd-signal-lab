from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import os
import shutil
import sys
import time
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for directory in (MR / "m9v" / "python", MR / "m9p" / "python", MR / "m10a" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import m9v_core as v
import m9v_core_v2 as v2
import run_gold_dynamic_core_reproduction_audit as p
import frozen_core as c
import payoff_rules as pay

STAGE = "M10W19_BLC1_ATR_FILTER_FRESH_PROSPECTIVE_SHADOW"
VER = "M10W19_RUNTIME_V1_APPEND_SAFE_PREFIX"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w19_blc1_atr_filter_fresh_prospective_shadow_contract_20260728.json"
HORIZON_MINUTES = 240
ATR_GATE_LT = 0.67
FIXED_SPREAD_USD = 0.20
CYCLE_SECONDS = 60
EXPECTED_LIVE_FILE_MAP = {
    "M1": "goldsharp_m1.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}
ALLOWED_OBSERVED_M1_BARS = {"M1": 0, "M15": 30, "H1": 120, "H4": 480, "D1": 2880}


class E(RuntimeError):
    pass


def pt(value: str) -> datetime:
    return datetime.strptime(value, p.TIME_FORMAT)


def ft(value: datetime) -> str:
    return value.strftime(p.TIME_FORMAT)


def js(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise E(f"JSON object required: {path}")
    return payload


def atom(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def csha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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


def valid(contract: dict[str, Any]) -> None:
    if contract.get("project") != "MOCHIPOYO_ALERT_RESEARCH" or contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_STARTED":
        raise E("unexpected M10W19 contract")
    data = contract.get("data", {})
    if data.get("live_file_map") != EXPECTED_LIVE_FILE_MAP or data.get("historical_backfill") is not False:
        raise E("unsafe M10W19 data contract")
    candidate = contract.get("candidate", {})
    if candidate.get("direction") != "LONG" or int(candidate.get("horizon_minutes", -1)) != HORIZON_MINUTES or candidate.get("one_position_per_arm") is not True:
        raise E("M10W19 frozen BLC1 contract mismatch")
    if abs(float(candidate.get("atr_gate_boundary", math.nan)) - ATR_GATE_LT) > 1e-12:
        raise E("M10W19 ATR boundary mismatch")
    safety = contract.get("safety", {})
    if safety.get("audit_only") is not True:
        raise E("audit_only required")
    for key in ("discord_send", "mt5_order", "live_ready", "final_signal", "historical_backfill", "entry_gate_enabled", "collector_reset", "m7c_reset", "m8c_reset", "m9v_reset", "m9y_reset", "m10b_reset", "m10e_reset", "m10p_reset", "m10p2_reset", "existing_forward_modified", "automatic_live_promotion"):
        if safety.get(key) is not False:
            raise E(f"unsafe flag {key}")


def env() -> tuple[Path, Path, float]:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not metadata_path.is_file():
        raise E(f"M8B metadata missing: {metadata_path}")
    metadata = js(metadata_path)
    data_root = Path(str(metadata.get("mt5_files_root", "")))
    point = float(metadata.get("symbols", {}).get("XAUUSD", {}).get("point", "nan"))
    if not data_root.is_dir() or not math.isfinite(point) or point <= 0:
        raise E(f"MT5 root/point unavailable: {data_root} {point}")
    return local_root, data_root, point


def load_bars_retry(path: Path) -> list[p.Bar]:
    last: Exception | None = None
    for attempt in range(5):
        try:
            return p.load_bars(path)
        except Exception as exc:
            last = exc
            if attempt < 4:
                time.sleep(0.25)
    raise E(f"cannot obtain stable CSV read: {path}: {last}")


def current_feed_snapshots(root: Path) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for tf, filename in EXPECTED_LIVE_FILE_MAP.items():
        path = root / filename
        if not path.is_file():
            raise E(f"required live CSV missing: {path}")
        snapshots[tf] = v.tail_snapshot(path)
    return snapshots


def observed_feed_health(root: Path, snapshots: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    if snapshots is None:
        snapshots = current_feed_snapshots(root)
    latest = {tf: pt(str(item["last_server_open"])) for tf, item in snapshots.items()}
    latest_m1 = latest["M1"]
    m1 = load_bars_retry(root / EXPECTED_LIVE_FILE_MAP["M1"])
    m1_times = [bar.time for bar in m1]
    end = bisect.bisect_right(m1_times, latest_m1)
    if end == 0 or m1_times[end - 1] != latest_m1:
        raise E("M1 tail snapshot not present in stable M1 read")
    details: dict[str, dict[str, Any]] = {}
    for tf, value in latest.items():
        if value > latest_m1:
            raise E(f"feed out-of-order: {tf}")
        start = bisect.bisect_right(m1_times, value, hi=end)
        observed = end - start
        limit = ALLOWED_OBSERVED_M1_BARS[tf]
        details[tf] = {"last_server_open": ft(value), "observed_m1_bars_after_tf": observed, "allowed_observed_m1_bars": limit}
        if observed > limit:
            raise E(f"feed stale: {tf} observed_m1_bars={observed} limit={limit}")
    return details


def atr_percentile100(bars: list[p.Bar]) -> list[float | None]:
    atr = pay.wilder_atr14(bars)
    out: list[float | None] = [None] * len(atr)
    for i in range(99, len(atr)):
        window = atr[i - 99:i + 1]
        if any(value is None or not math.isfinite(float(value)) for value in window):
            continue
        current = float(atr[i])
        values = [float(value) for value in window if value is not None]
        out[i] = sum(value <= current for value in values) / len(values)
    return out


def macd_line_hist(bars: list[p.Bar]) -> tuple[list[float], list[float]]:
    closes = [float(bar.close) for bar in bars]
    fast = c.ema(closes, 6)
    slow = c.ema(closes, 13)
    line = [(a - b) / max(abs(close), 1e-12) * 10000.0 for a, b, close in zip(fast, slow, closes)]
    signal = c.ema(line, 4)
    hist = [a - b for a, b in zip(line, signal)]
    return line, hist


def candidate_rows(root: Path, start: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[p.Bar]]]:
    bars = {tf: load_bars_retry(root / filename) for tf, filename in EXPECTED_LIVE_FILE_MAP.items()}
    m1, m15, h1, h4, d1 = bars["M1"], bars["M15"], bars["H1"], bars["H4"], bars["D1"]
    if len(m15) < 3 or len(h1) < 120 or len(h4) < 40 or len(d1) < 40:
        raise E("insufficient history for BLC1 fresh shadow")
    _, m15_hist = macd_line_hist(m15)
    h1_line, _ = macd_line_hist(h1)
    h1_atrp = atr_percentile100(h1)
    h4_closes = [float(bar.close) for bar in h4]
    h4_e20, h4_e30 = c.ema(h4_closes, 20), c.ema(h4_closes, 30)
    d1_closes = [float(bar.close) for bar in d1]
    d1_e20, d1_e30, d1_e40 = c.ema(d1_closes, 20), c.ema(d1_closes, 30), c.ema(d1_closes, 40)
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]
    d1_close_times = [bar.time + timedelta(days=1) for bar in d1]
    m1_by_time = {bar.time: bar for bar in m1}

    decisions: list[tuple[datetime, int]] = [(m15[i + 1].time, i) for i in range(1, len(m15) - 1)]
    nominal = m15[-1].time + timedelta(minutes=15)
    if nominal in m1_by_time and nominal.minute % 15 == 0 and all(item[0] != nominal for item in decisions):
        decisions.append((nominal, len(m15) - 1))

    baseline: list[dict[str, Any]] = []
    filtered: list[dict[str, Any]] = []
    for decision, i in sorted(decisions, key=lambda item: item[0]):
        if decision <= start:
            continue
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        ih4 = bisect.bisect_right(h4_close_times, decision) - 1
        id1 = bisect.bisect_right(d1_close_times, decision) - 1
        if min(ih1, ih4, id1) < 0 or h1_atrp[ih1] is None:
            continue
        regime = d1_e20[id1] > d1_e30[id1] > d1_e40[id1] and h4_e20[ih4] > h4_e30[ih4] and h1_line[ih1] > 0
        trigger = m15_hist[i - 1] < 0 and m15_hist[i] >= 0
        if not (regime and trigger):
            continue
        atrp = float(h1_atrp[ih1])
        row = {
            "candidate_id": f"M10W19_{decision.strftime('%Y%m%d_%H%M%S')}",
            "decision_time": ft(decision),
            "entry_time": ft(decision),
            "scheduled_exit_time": ft(decision + timedelta(minutes=HORIZON_MINUTES)),
            "m15_trigger_source_open": ft(m15[i].time),
            "h1_source_open": ft(h1[ih1].time),
            "h4_source_open": ft(h4[ih4].time),
            "d1_source_open": ft(d1[id1].time),
            "m15_hist_previous_bps": float(m15_hist[i - 1]),
            "m15_hist_current_bps": float(m15_hist[i]),
            "h1_macd_line_bps": float(h1_line[ih1]),
            "h1_atr_pct100": atrp,
            "filter_pass": atrp < ATR_GATE_LT,
            "exact_entry_m1_available": decision in m1_by_time,
        }
        baseline.append(row)
        if atrp < ATR_GATE_LT:
            filtered.append(row)
    return baseline, filtered, bars


def directional_bps(entry_exec: float, exit_exec: float) -> float:
    return (exit_exec - entry_exec) / max(abs(entry_exec), 1e-12) * 10000.0


def build_ledger(candidates: list[dict[str, Any]], m1: list[p.Bar], point: float, arm: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_time = {bar.time: bar for bar in m1}
    latest = m1[-1].time
    trades: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    active_until: datetime | None = None
    active_id: str | None = None
    seq = 0
    for row in sorted(candidates, key=lambda item: pt(str(item["decision_time"]))):
        decision = pt(str(row["decision_time"]))
        if active_until is not None and decision < active_until:
            overlaps.append({"arm": arm, "active_trade_id": active_id, "skipped_candidate_id": row["candidate_id"], "skipped_decision_time": row["decision_time"], "reason": "ONE_POSITION_ACTIVE"})
            continue
        entry = by_time.get(decision)
        if entry is None:
            trades.append({**row, "arm": arm, "trade_id": None, "status": "ENTRY_DATA_GAP", "actual_return_bps": None, "fixed0p20_return_bps": None})
            continue
        exit_time = decision + timedelta(minutes=HORIZON_MINUTES)
        exit_bar = by_time.get(exit_time)
        seq += 1
        trade_id = f"{arm}_T{seq:06d}"
        if exit_bar is None:
            status = "EXIT_DATA_GAP" if latest >= exit_time else "OPEN"
            trades.append({**row, "arm": arm, "trade_id": trade_id, "status": status, "actual_return_bps": None, "fixed0p20_return_bps": None})
        else:
            actual_entry = float(entry.open) + int(entry.spread) * point
            actual_exit = float(exit_bar.open)
            fixed_entry = float(entry.open) + FIXED_SPREAD_USD
            fixed_exit = float(exit_bar.open)
            trades.append({
                **row, "arm": arm, "trade_id": trade_id, "status": "RESOLVED",
                "entry_bid_open": float(entry.open), "entry_spread_points": int(entry.spread), "exit_bid_open": float(exit_bar.open),
                "actual_return_bps": directional_bps(actual_entry, actual_exit),
                "fixed0p20_return_bps": directional_bps(fixed_entry, fixed_exit),
            })
        active_until = exit_time
        active_id = trade_id
    return trades, overlaps


def stats(candidates: list[dict[str, Any]], trades: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in trades if row.get("trade_id")]
    resolved = [row for row in accepted if row.get("status") == "RESOLVED" and row.get("actual_return_bps") is not None]
    actual_values = [float(row["actual_return_bps"]) for row in resolved]
    fixed_values = [float(row["fixed0p20_return_bps"]) for row in resolved]
    return {
        "candidate_match_count": len(candidates),
        "accepted_count": len(accepted),
        "resolved_count": len(resolved),
        "open_count": sum(row.get("status") == "OPEN" for row in accepted),
        "entry_data_gap_count": sum(row.get("status") == "ENTRY_DATA_GAP" for row in trades),
        "exit_data_gap_count": sum(row.get("status") == "EXIT_DATA_GAP" for row in accepted),
        "actual": c.metrics_from_values(actual_values),
        "fixed0p20": c.metrics_from_values(fixed_values),
        "actual_plus1bps_cost": c.metrics_from_values([value - 1.0 for value in actual_values]),
        "actual_plus2bps_cost": c.metrics_from_values([value - 2.0 for value in actual_values]),
    }


def runtime_paths(local_root: Path) -> tuple[Path, Path, Path, Path]:
    runtime_dir = local_root / "m10w19_runtime"
    return runtime_dir, runtime_dir / "m10w19_runtime_manifest.json", runtime_dir / "m10w19_runtime_state.json", runtime_dir / "m10w19_shadow_loop.lock"


def verify_runtime(root: Path, point: float, contract: dict[str, Any], runtime: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    valid(contract)
    if runtime.get("stage") != STAGE or runtime.get("runtime_contract_version") != VER or runtime.get("contract_sha256") != csha(contract) or runtime.get("reset_allowed") is not False or runtime.get("historical_backfill_allowed") is not False or runtime.get("audit_only") is not True:
        raise E("M10W19 runtime integrity failed")
    if str(root) != str(runtime.get("data_root", "")):
        raise E("M10W19 data_root changed after start freeze")
    if abs(float(runtime.get("point", "nan")) - point) > 1e-12:
        raise E("M10W19 point changed after start freeze")
    for tf, filename in EXPECTED_LIVE_FILE_MAP.items():
        frozen = runtime.get("frozen_row_prefixes", {}).get(tf)
        if not isinstance(frozen, dict) or v2.prefix_fingerprint_rows(root / filename, int(frozen.get("row_count", 0))) != frozen:
            raise E(f"M10W19 frozen pre-start rows changed: {tf}")
    snapshots = current_feed_snapshots(root)
    health = observed_feed_health(root, snapshots)
    return snapshots, health


def initialize() -> int:
    local_root, root, point = env()
    contract = js(CONTRACT)
    valid(contract)
    runtime_dir, runtime_path, state_path, lock_path = runtime_paths(local_root)
    if lock_path.exists():
        raise E("M10W19 loop lock exists")
    if runtime_path.exists() or state_path.exists():
        raise E("M10W19 runtime already exists; never reinitialize/reset")
    first = current_feed_snapshots(root)
    observed_feed_health(root, first)
    time.sleep(2)
    second = current_feed_snapshots(root)
    observed_feed_health(root, second)
    if first != second:
        raise E("live CSV changed during M10W19 start freeze; rerun initializer without changing anything")
    latest = {tf: pt(str(item["last_server_open"])) for tf, item in second.items()}
    start = latest["M1"]
    prefixes = {tf: v2.prefix_fingerprint_rows(root / filename, int(second[tf]["row_count"])) for tf, filename in EXPECTED_LIVE_FILE_MAP.items()}
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    runtime = {
        "project": "MOCHIPOYO_ALERT_RESEARCH", "stage": STAGE, "runtime_status": "FROZEN_FRESH_START",
        "runtime_contract_version": VER, "created_at_utc": now, "prospective_start_server_time": ft(start),
        "contract_sha256": csha(contract), "contract_path": str(CONTRACT), "data_root": str(root), "point": point,
        "frozen_row_prefixes": prefixes, "pre_start_candidate_eligibility": False, "historical_backfill_allowed": False,
        "reset_allowed": False, "restart_safe": True, "audit_only": True, "discord_send": False, "mt5_order": False,
        "live_ready": False, "final_signal": False, "entry_gate_enabled": False,
    }
    atom(runtime_path, runtime)
    atom(state_path, {"stage": STAGE, "status": "INITIALIZED_NO_CYCLE_YET", "created_at_utc": now, "prospective_start_server_time": ft(start), "cycle_count": 0, "reset_allowed": False})
    atom(runtime_dir / "m10w19_runtime_start_receipt.json", {"status": "PASS", "stage": "M10W19_FRESH_START_INITIALIZATION_AUDIT_ONLY", "created_at_utc": now, "prospective_start_server_time": ft(start), "historical_backfill_allowed": False, "reset_allowed": False, "audit_only": True})
    print(f"[M10W19 INIT PASS] fresh start={ft(start)}")
    return 0


def once() -> int:
    local_root, root, point = env()
    contract = js(CONTRACT)
    runtime_dir, runtime_path, state_path, _ = runtime_paths(local_root)
    if not runtime_path.is_file():
        raise E("M10W19 runtime missing; run BAT01 once first")
    runtime = js(runtime_path)
    snapshots, health = verify_runtime(root, point, contract, runtime)
    start = pt(str(runtime["prospective_start_server_time"]))
    baseline_candidates, filtered_candidates, bars = candidate_rows(root, start)
    baseline_trades, baseline_overlaps = build_ledger(baseline_candidates, bars["M1"], point, "W0_BLC1_BASELINE")
    filtered_trades, filtered_overlaps = build_ledger(filtered_candidates, bars["M1"], point, "W1_BLC1_ATR_FILTERED")
    s0 = stats(baseline_candidates, baseline_trades)
    s1 = stats(filtered_candidates, filtered_trades)
    latest_server_open = {tf: item["last_server_open"] for tf, item in snapshots.items()}
    gates = contract["review_gates"]
    resolved = int(s1["resolved_count"])
    review = {
        "operational": resolved >= int(gates["operational_filtered_resolved"]),
        "interim": resolved >= int(gates["interim_filtered_resolved"]),
        "formal": resolved >= int(gates["formal_filtered_resolved"]),
        "automatic_live_promotion": False,
    }
    def pf(block: dict[str, Any]) -> float | None:
        value = block.get("profit_factor")
        return None if value is None else float(value)
    comparison = {
        "resolved_count_delta_filtered_minus_baseline": int(s1["resolved_count"]) - int(s0["resolved_count"]),
        "actual_net_bps_delta": float(s1["actual"]["net_bps"]) - float(s0["actual"]["net_bps"]),
        "actual_pf_baseline": pf(s0["actual"]), "actual_pf_filtered": pf(s1["actual"]),
        "fixed0p20_pf_baseline": pf(s0["fixed0p20"]), "fixed0p20_pf_filtered": pf(s1["fixed0p20"]),
        "plus2bps_pf_baseline": pf(s0["actual_plus2bps_cost"]), "plus2bps_pf_filtered": pf(s1["actual_plus2bps_cost"]),
    }
    output_root = local_root / "outputs" / "M10W19"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = output_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH", "stage": STAGE, "status": "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "prospective_start_server_time": ft(start),
        "latest_server_open": latest_server_open, "W0_BLC1_BASELINE": s0, "W1_BLC1_ATR_FILTERED": s1,
        "comparison": comparison, "review_readiness": review,
        "frozen_rule": {"atr_gate_lt": ATR_GATE_LT, "horizon_minutes": HORIZON_MINUTES, "baseline_formula_changed": False},
        "guardrails": {"audit_only": True, "historical_backfill": False, "pre_start_candidate_eligibility": False, "threshold_or_gate_refit_from_prospective_outcomes": False, "existing_forward_modified": False, "discord_send": False, "mt5_order": False, "live_ready": False, "final_signal": False, "automatic_live_promotion": False},
    }
    (archive / "00_READ_ME_FIRST.txt").write_text("M10W19 fresh prospective two-arm BLC1 loss-reduction shadow. W0 baseline vs W1 frozen h1_atr_pct100<0.67. No backfill, refit, Discord, orders, or existing-monitor changes.\n", encoding="utf-8")
    (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(archive / "02_baseline_candidate_ledger.csv", baseline_candidates)
    write_csv(archive / "03_filtered_candidate_ledger.csv", filtered_candidates)
    write_csv(archive / "04_baseline_trade_ledger.csv", baseline_trades)
    write_csv(archive / "05_filtered_trade_ledger.csv", filtered_trades)
    write_csv(archive / "06_baseline_overlap.csv", baseline_overlaps)
    write_csv(archive / "07_filtered_overlap.csv", filtered_overlaps)
    (archive / "08_runtime_manifest_copy.json").write_text(runtime_path.read_text(encoding="utf-8"), encoding="utf-8")
    (archive / "09_data_quality.json").write_text(json.dumps({"data_root": str(root), "point": point, "closed_rows_contract": True, "prefix_integrity_verified": True, "feed_health": health, "latest_server_open": latest_server_open, "exact_m1_entry_only": True, "exact_m1_exit_only": True, "nearest_m1_fallback": False, "historical_backfill": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "10_audit.log").write_text("\n".join(["status=PASS_FRESH_PROSPECTIVE_AUDIT_ONLY", f"prospective_start_server_time={ft(start)}", f"baseline_candidates={len(baseline_candidates)}", f"baseline_resolved={s0['resolved_count']}", f"filtered_candidates={len(filtered_candidates)}", f"filtered_resolved={s1['resolved_count']}", "atr_gate_lt=0.67", "historical_backfill=false", "existing_forward_modified=false", "discord_send=false", "mt5_order=false", ""]), encoding="utf-8")
    latest = output_root / "LATEST"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    package = latest / "99_UPLOAD_PACKAGE.zip"
    names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_baseline_candidate_ledger.csv", "03_filtered_candidate_ledger.csv", "04_baseline_trade_ledger.csv", "05_filtered_trade_ledger.csv", "06_baseline_overlap.csv", "07_filtered_overlap.csv", "08_runtime_manifest_copy.json", "09_data_quality.json", "10_audit.log"]
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(latest / name, arcname=name)
    old_state = js(state_path) if state_path.is_file() else {"cycle_count": 0}
    atom(state_path, {"stage": STAGE, "status": "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY", "prospective_start_server_time": ft(start), "last_cycle_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "cycle_count": int(old_state.get("cycle_count", 0)) + 1, "baseline_candidate_count": len(baseline_candidates), "baseline_resolved_count": s0["resolved_count"], "filtered_candidate_count": len(filtered_candidates), "filtered_resolved_count": s1["resolved_count"], "latest_server_open": latest_server_open, "latest_package": str(package), "reset_allowed": False})
    print(f"[M10W19 PASS] start={ft(start)} baseline_resolved={s0['resolved_count']} filtered_resolved={s1['resolved_count']}")
    print(f"[PACKAGE] {package}")
    return 0


def forever() -> int:
    local_root, _, _ = env()
    _, runtime_path, _, lock_path = runtime_paths(local_root)
    if not runtime_path.is_file():
        raise E("M10W19 runtime missing; run BAT01 once first")
    if lock_path.exists():
        raise E(f"M10W19 loop lock already exists: {lock_path}")
    atom(lock_path, {"stage": STAGE, "pid": os.getpid(), "started_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")})
    try:
        while True:
            once()
            time.sleep(CYCLE_SECONDS)
    except KeyboardInterrupt:
        print("[M10W19] graceful stop requested")
        return 0
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("initialize", "once", "forever"))
    args = parser.parse_args()
    try:
        if args.mode == "initialize":
            return initialize()
        if args.mode == "once":
            return once()
        return forever()
    except Exception as exc:
        print(f"[M10W19 BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] Existing forward monitors/frozen starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
