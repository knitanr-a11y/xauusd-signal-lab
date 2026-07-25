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

STAGE = "M10P2_C0212_FRESH_PROSPECTIVE_SHADOW"
VER = "M10P2_RUNTIME_V1_APPEND_SAFE_PREFIX"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10p2_c0212_fresh_prospective_shadow_contract_20260725.json"

H4_EMA20_30_BPS_GE = 37.61355979
H1_ATR_PCT100_GE = 0.8
HORIZON_MINUTES = 240
FIXED_SPREAD_USD = 0.20
CYCLE_SECONDS = 60
LAG = {"M1": 0, "M5": 600, "M15": 1800, "H1": 7200, "H4": 28800, "D1": 172800}
EXPECTED_LIVE_FILE_MAP = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}


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


def fsha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    if (
        contract.get("project") != "MOCHIPOYO_ALERT_RESEARCH"
        or contract.get("stage") != STAGE
        or contract.get("status") != "DESIGN_FROZEN_NOT_STARTED"
    ):
        raise E("unexpected M10P2 contract")
    data = contract.get("data", {})
    if data.get("live_file_map") != EXPECTED_LIVE_FILE_MAP or data.get("historical_backfill") is not False:
        raise E("unsafe M10P2 data contract")
    candidate = contract.get("candidate", {})
    formula = candidate.get("formula", {})
    if (
        float(formula.get("h4_ema20_30_bps_ge", math.nan)) != H4_EMA20_30_BPS_GE
        or float(formula.get("h1_atr_pct100_ge", math.nan)) != H1_ATR_PCT100_GE
        or int(candidate.get("horizon_minutes", -1)) != HORIZON_MINUTES
        or candidate.get("direction") != "SHORT"
        or candidate.get("one_position") is not True
    ):
        raise E("M10P2 frozen C0212 mismatch")
    safety = contract.get("safety", {})
    if safety.get("audit_only") is not True:
        raise E("audit_only required")
    for key in (
        "discord_send", "mt5_order", "live_ready", "final_signal", "entry_gate_enabled",
        "historical_backfill", "collector_reset", "m7c_reset", "m8c_reset", "m9v_reset",
        "m9y_reset", "m10b_reset", "m10e_reset", "m10p_reset", "automatic_live_promotion",
    ):
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
            if attempt == 4:
                break
            time.sleep(0.25)
    raise E(f"cannot obtain stable CSV read: {path}: {last}")


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


def candidate_rows(root: Path, contract: dict[str, Any], start: datetime) -> tuple[list[dict[str, Any]], dict[str, list[p.Bar]]]:
    fmap = contract["data"]["live_file_map"]
    bars = {
        "M1": load_bars_retry(root / fmap["M1"]),
        "M15": load_bars_retry(root / fmap["M15"]),
        "H1": load_bars_retry(root / fmap["H1"]),
        "H4": load_bars_retry(root / fmap["H4"]),
    }
    m1, m15, h1, h4 = bars["M1"], bars["M15"], bars["H1"], bars["H4"]
    if len(m15) < 122 or len(h1) < 120 or len(h4) < 40:
        raise E("insufficient M15/H1/H4 history for C0212")

    h1_atrp = atr_percentile100(h1)
    h4_closes = [float(bar.close) for bar in h4]
    h4_ema20 = c.ema(h4_closes, 20)
    h4_ema30 = c.ema(h4_closes, 30)
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]
    m1_by_time = {bar.time: bar for bar in m1}

    decisions: list[datetime] = []
    for i in range(120, len(m15) - 1):
        decisions.append(m15[i + 1].time)

    # The live CSV newest row is CLOSED, so the current frontier M15 decision may not
    # yet exist as a closed M15 row. Admit only a real exact M1 observation aligned
    # to an M15 boundary at/after the latest closed M15 nominal close.
    nominal = m15[-1].time + timedelta(minutes=15)
    frontier: datetime | None = None
    for bar in m1:
        if bar.time < nominal:
            continue
        if bar.time.minute % 15 == 0 and bar.time.second == 0:
            frontier = bar.time
            break
    if frontier is not None and frontier not in decisions:
        decisions.append(frontier)

    output: list[dict[str, Any]] = []
    for decision in sorted(decisions):
        if decision <= start:
            continue
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        ih4 = bisect.bisect_right(h4_close_times, decision) - 1
        if ih1 < 0 or ih4 < 0 or h1_atrp[ih1] is None:
            continue
        h4_close = float(h4[ih4].close)
        if h4_close == 0:
            continue
        h4_stack = (float(h4_ema20[ih4]) - float(h4_ema30[ih4])) / abs(h4_close) * 10000.0
        atrp = float(h1_atrp[ih1])
        if not (h4_stack >= H4_EMA20_30_BPS_GE and atrp >= H1_ATR_PCT100_GE):
            continue
        output.append({
            "candidate_id": f"M10P2_{decision.strftime('%Y%m%d_%H%M%S')}",
            "decision_time": ft(decision),
            "entry_time": ft(decision),
            "scheduled_exit_time": ft(decision + timedelta(minutes=HORIZON_MINUTES)),
            "h1_source_open": ft(h1[ih1].time),
            "h4_source_open": ft(h4[ih4].time),
            "h4_ema20_30_bps": h4_stack,
            "h1_atr_pct100": atrp,
            "exact_entry_m1_available": decision in m1_by_time,
        })
    return output, bars


def build_ledgers(candidates: list[dict[str, Any]], m1: list[p.Bar], point: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_time = {bar.time: bar for bar in m1}
    latest_m1 = m1[-1].time
    trades: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    active_until: datetime | None = None
    active_id: str | None = None
    trade_seq = 0

    for row in sorted(candidates, key=lambda item: pt(str(item["decision_time"]))):
        decision = pt(str(row["decision_time"]))
        if active_until is not None and decision < active_until:
            overlaps.append({
                "active_trade_id": active_id,
                "skipped_candidate_id": row["candidate_id"],
                "skipped_decision_time": row["decision_time"],
                "reason": "ONE_POSITION_ACTIVE",
            })
            continue

        entry = by_time.get(decision)
        if entry is None:
            trades.append({
                **row,
                "trade_id": None,
                "status": "ENTRY_DATA_GAP",
                "return_bps": None,
                "fixed0p20_return_bps": None,
            })
            continue

        exit_time = decision + timedelta(minutes=HORIZON_MINUTES)
        exit_bar = by_time.get(exit_time)
        status = "OPEN"
        actual_return: float | None = None
        fixed_return: float | None = None
        exit_open: float | None = None
        exit_spread_points: int | None = None
        actual_exit_ask: float | None = None
        fixed_exit_ask: float | None = None

        if exit_bar is not None:
            status = "RESOLVED"
            exit_open = float(exit_bar.open)
            exit_spread_points = int(exit_bar.spread)
            actual_exit_ask = exit_open + exit_spread_points * point
            fixed_exit_ask = exit_open + FIXED_SPREAD_USD
            actual_return = c.directional_return("SHORT", float(entry.open), actual_exit_ask)
            fixed_return = c.directional_return("SHORT", float(entry.open), fixed_exit_ask)
        elif latest_m1 >= exit_time:
            status = "EXIT_DATA_GAP"

        trade_seq += 1
        trade_id = f"M10P2_T{trade_seq:06d}"
        trades.append({
            **row,
            "trade_id": trade_id,
            "status": status,
            "entry_bid": float(entry.open),
            "exit_open": exit_open,
            "exit_spread_points": exit_spread_points,
            "actual_exit_ask": actual_exit_ask,
            "fixed0p20_exit_ask": fixed_exit_ask,
            "return_bps": actual_return,
            "fixed0p20_return_bps": fixed_return,
        })
        active_until = exit_time
        active_id = trade_id

    return trades, overlaps


def metrics(candidates: list[dict[str, Any]], trades: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in trades if row.get("trade_id")]
    resolved = [row for row in accepted if row.get("status") == "RESOLVED" and row.get("return_bps") is not None]
    actual = c.metrics_from_values([float(row["return_bps"]) for row in resolved])
    fixed = c.metrics_from_values([float(row["fixed0p20_return_bps"]) for row in resolved])
    return {
        "candidate_match_count": len(candidates),
        "accepted_count": len(accepted),
        "resolved_count": len(resolved),
        "open_count": sum(row.get("status") == "OPEN" for row in accepted),
        "entry_data_gap_count": sum(row.get("status") == "ENTRY_DATA_GAP" for row in trades),
        "exit_data_gap_count": sum(row.get("status") == "EXIT_DATA_GAP" for row in accepted),
        "actual": actual,
        "fixed0p20": fixed,
    }


def runtime_paths(local_root: Path) -> tuple[Path, Path, Path, Path]:
    runtime_dir = local_root / "m10p2_runtime"
    return (
        runtime_dir,
        runtime_dir / "m10p2_runtime_manifest.json",
        runtime_dir / "m10p2_runtime_state.json",
        runtime_dir / "m10p2_shadow_loop.lock",
    )


def current_feed_snapshots(root: Path) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for tf, filename in EXPECTED_LIVE_FILE_MAP.items():
        path = root / filename
        if not path.is_file():
            raise E(f"required live CSV missing: {path}")
        snapshots[tf] = v.tail_snapshot(path)
    return snapshots


def verify_runtime(
    root: Path,
    point: float,
    contract: dict[str, Any],
    runtime: dict[str, Any],
    m10p_path: Path,
) -> dict[str, dict[str, Any]]:
    valid(contract)
    if (
        runtime.get("stage") != STAGE
        or runtime.get("runtime_contract_version") != VER
        or runtime.get("contract_sha256") != csha(contract)
        or runtime.get("reset_allowed") is not False
        or runtime.get("historical_backfill_allowed") is not False
        or runtime.get("audit_only") is not True
    ):
        raise E("M10P2 runtime integrity failed")
    if str(root) != str(runtime.get("data_root", "")):
        raise E(f"M10P2 data_root changed after start freeze: {root}")
    frozen_point = float(runtime.get("point", "nan"))
    if not math.isfinite(frozen_point) or abs(point - frozen_point) > 1e-12:
        raise E(f"M10P2 XAUUSD point changed after start freeze: current={point} frozen={frozen_point}")
    if not m10p_path.is_file():
        raise E("M10P chronology anchor missing")
    if runtime.get("m10p_runtime_manifest_sha256_at_freeze") != fsha(m10p_path):
        raise E("M10P chronology anchor changed")
    m10p = js(m10p_path)
    if (
        m10p.get("stage") != "M10P_C056_G013_FRESH_PROSPECTIVE_SHADOW"
        or m10p.get("runtime_contract_version") != "M10P_RUNTIME_V1_APPEND_SAFE_PREFIX"
        or m10p.get("reset_allowed") is not False
    ):
        raise E("M10P chronology anchor unsafe")
    if runtime.get("m10p_prospective_start_server_time") != m10p.get("prospective_start_server_time"):
        raise E("M10P start anchor mismatch")

    for tf, filename in EXPECTED_LIVE_FILE_MAP.items():
        frozen = runtime.get("frozen_row_prefixes", {}).get(tf)
        if not isinstance(frozen, dict):
            raise E(f"missing frozen prefix: {tf}")
        if v2.prefix_fingerprint_rows(root / filename, int(frozen.get("row_count", 0))) != frozen:
            raise E(f"frozen pre-start rows changed: {tf}")

    snapshots = current_feed_snapshots(root)
    latest = {tf: pt(str(item["last_server_open"])) for tf, item in snapshots.items()}
    m1_time = latest["M1"]
    for tf, time_value in latest.items():
        lag = (m1_time - time_value).total_seconds()
        if lag < 0 or lag > LAG[tf]:
            raise E(f"live feed stale/out-of-order during M10P2 cycle: {tf} lag={lag}s")
    return snapshots


def initialize() -> int:
    local_root, root, point = env()
    contract = js(CONTRACT)
    valid(contract)
    runtime_dir, runtime_path, state_path, lock_path = runtime_paths(local_root)
    if lock_path.exists():
        raise E("M10P2 loop lock exists")
    if runtime_path.exists() or state_path.exists():
        raise E("M10P2 runtime already exists; never reinitialize/reset")

    m10p_path = local_root / "m10p_runtime" / "m10p_runtime_manifest.json"
    if not m10p_path.is_file():
        raise E("M10P runtime anchor missing")
    m10p = js(m10p_path)
    if (
        m10p.get("stage") != "M10P_C056_G013_FRESH_PROSPECTIVE_SHADOW"
        or m10p.get("runtime_contract_version") != "M10P_RUNTIME_V1_APPEND_SAFE_PREFIX"
        or m10p.get("reset_allowed") is not False
    ):
        raise E("M10P runtime unsafe")

    first = current_feed_snapshots(root)
    time.sleep(2)
    second = current_feed_snapshots(root)
    if first != second:
        raise E("live CSV changed during M10P2 start freeze; rerun BAT01 without changing anything")

    latest = {tf: pt(str(item["last_server_open"])) for tf, item in second.items()}
    start = latest["M1"]
    for tf, time_value in latest.items():
        lag = (start - time_value).total_seconds()
        if lag < 0 or lag > LAG[tf]:
            raise E(f"{tf} lag invalid: {lag}s")
    m10p_start = pt(str(m10p["prospective_start_server_time"]))
    if start <= m10p_start:
        raise E("M10P2 start must be strictly after M10P start")

    prefixes = {
        tf: v2.prefix_fingerprint_rows(root / filename, int(second[tf]["row_count"]))
        for tf, filename in EXPECTED_LIVE_FILE_MAP.items()
    }
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    runtime = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "runtime_status": "FROZEN_FRESH_START",
        "runtime_contract_version": VER,
        "created_at_utc": now,
        "prospective_start_server_time": ft(start),
        "contract_sha256": csha(contract),
        "contract_path": str(CONTRACT),
        "data_root": str(root),
        "point": point,
        "frozen_row_prefixes": prefixes,
        "m10p_runtime_manifest_sha256_at_freeze": fsha(m10p_path),
        "m10p_prospective_start_server_time": m10p["prospective_start_server_time"],
        "pre_start_candidate_eligibility": False,
        "historical_backfill_allowed": False,
        "reset_allowed": False,
        "audit_only": True,
        "discord_send": False,
        "mt5_order": False,
        "live_ready": False,
        "final_signal": False,
        "entry_gate_enabled": False,
    }
    atom(runtime_path, runtime)
    atom(state_path, {
        "stage": STAGE,
        "status": "INITIALIZED_NO_CYCLE_YET",
        "created_at_utc": now,
        "prospective_start_server_time": ft(start),
        "cycle_count": 0,
        "reset_allowed": False,
    })
    atom(runtime_dir / "m10p2_runtime_start_receipt.json", {
        "status": "PASS",
        "stage": "M10P2_FRESH_START_INITIALIZATION_AUDIT_ONLY",
        "created_at_utc": now,
        "prospective_start_server_time": ft(start),
        "m10p_start": m10p["prospective_start_server_time"],
        "historical_backfill_allowed": False,
        "reset_allowed": False,
        "audit_only": True,
    })
    print(f"[M10P2 INIT PASS] fresh start={ft(start)}")
    return 0


def once() -> int:
    local_root, root, point = env()
    contract = js(CONTRACT)
    runtime_dir, runtime_path, state_path, _ = runtime_paths(local_root)
    if not runtime_path.is_file():
        raise E("M10P2 runtime missing; run BAT01 once first")
    runtime = js(runtime_path)
    m10p_path = local_root / "m10p_runtime" / "m10p_runtime_manifest.json"
    latest_snapshots = verify_runtime(root, point, contract, runtime, m10p_path)
    start = pt(str(runtime["prospective_start_server_time"]))

    candidates, bars = candidate_rows(root, contract, start)
    trades, overlaps = build_ledgers(candidates, bars["M1"], point)
    stats = metrics(candidates, trades)
    latest_server_open = {tf: item["last_server_open"] for tf, item in latest_snapshots.items()}
    gates = contract["review_gates"]
    resolved = int(stats["resolved_count"])
    review = {
        "operational": resolved >= int(gates["operational_resolved"]),
        "interim": resolved >= int(gates["interim_resolved"]),
        "formal": resolved >= int(gates["formal_resolved"]),
        "automatic_live_promotion": False,
    }

    output_root = local_root / "outputs" / "M10P2"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = output_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prospective_start_server_time": ft(start),
        "latest_server_open": latest_server_open,
        "frozen_candidate": {
            "candidate_id": "M10J_C0212",
            "h4_ema20_30_bps_ge": H4_EMA20_30_BPS_GE,
            "h1_atr_pct100_ge": H1_ATR_PCT100_GE,
            "horizon_minutes": HORIZON_MINUTES,
        },
        "metrics": stats,
        "overlap_skip_count": len(overlaps),
        "review_readiness": review,
        "historical_reference": contract["historical_reference"],
        "guardrails": {
            "audit_only": True,
            "historical_backfill": False,
            "pre_start_candidate_eligibility": False,
            "threshold_refit_from_prospective_outcomes": False,
            "m10p_modified_or_reset": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "automatic_live_promotion": False,
        },
    }
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10P2 fresh prospective audit-only shadow for deterministically reproduced C0212. "
        "Independent from M10P; no historical backfill; never rerun initializer after start freeze.\n",
        encoding="utf-8",
    )
    (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(archive / "02_candidate_ledger.csv", candidates)
    write_csv(archive / "03_trade_ledger.csv", trades)
    write_csv(archive / "04_overlap_skip_ledger.csv", overlaps)
    (archive / "05_runtime_manifest_copy.json").write_text(runtime_path.read_text(encoding="utf-8"), encoding="utf-8")
    (archive / "06_data_quality.json").write_text(json.dumps({
        "data_root": str(root),
        "point": point,
        "closed_rows_contract": True,
        "prefix_integrity_verified": True,
        "latest_server_open": latest_server_open,
        "decision_timeframe": "M15",
        "h1_atr_percentile_window": 100,
        "exact_m1_entry_only": True,
        "exact_m1_exit_only": True,
        "nearest_m1_fallback": False,
        "exit_data_gap_never_backfilled": True,
        "m10p_chronology_anchor_read_only": True,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "07_audit.log").write_text("\n".join([
        "status=PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        f"prospective_start_server_time={ft(start)}",
        f"candidate_matches={len(candidates)}",
        f"accepted={stats['accepted_count']}",
        f"resolved={stats['resolved_count']}",
        f"open={stats['open_count']}",
        f"entry_data_gap={stats['entry_data_gap_count']}",
        f"exit_data_gap={stats['exit_data_gap_count']}",
        "historical_backfill=false",
        "m10p_modified=false",
        "discord_send=false",
        "mt5_order=false",
        "live_ready=false",
        "final_signal=false",
        "",
    ]), encoding="utf-8")

    latest = output_root / "LATEST"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    package = latest / "99_UPLOAD_PACKAGE.zip"
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_candidate_ledger.csv", "03_trade_ledger.csv",
        "04_overlap_skip_ledger.csv", "05_runtime_manifest_copy.json", "06_data_quality.json", "07_audit.log",
    ]
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(latest / name, arcname=name)

    old_state = js(state_path) if state_path.is_file() else {"cycle_count": 0}
    atom(state_path, {
        "stage": STAGE,
        "status": "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        "prospective_start_server_time": ft(start),
        "last_cycle_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cycle_count": int(old_state.get("cycle_count", 0)) + 1,
        "candidate_match_count": len(candidates),
        "accepted_count": stats["accepted_count"],
        "resolved_count": stats["resolved_count"],
        "open_count": stats["open_count"],
        "entry_data_gap_count": stats["entry_data_gap_count"],
        "exit_data_gap_count": stats["exit_data_gap_count"],
        "latest_server_open": latest_server_open,
        "latest_package": str(package),
        "reset_allowed": False,
    })
    print(
        f"[M10P2 PASS] start={ft(start)} candidates={len(candidates)} "
        f"accepted={stats['accepted_count']} resolved={stats['resolved_count']} open={stats['open_count']}"
    )
    print(f"[PACKAGE] {package}")
    return 0


def forever() -> int:
    local_root, _, _ = env()
    _, runtime_path, _, lock_path = runtime_paths(local_root)
    if not runtime_path.is_file():
        raise E("M10P2 runtime missing; run BAT01 once first")
    if lock_path.exists():
        raise E(f"M10P2 loop lock already exists: {lock_path}")
    atom(lock_path, {
        "stage": STAGE,
        "pid": os.getpid(),
        "started_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    try:
        while True:
            once()
            time.sleep(CYCLE_SECONDS)
    except KeyboardInterrupt:
        print("[M10P2] graceful stop requested")
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
        print(f"[M10P2 BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] M10P and all existing forward monitors/frozen starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
