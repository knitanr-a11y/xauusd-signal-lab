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

STAGE = "M10P_C056_G013_FRESH_PROSPECTIVE_SHADOW"
VER = "M10P_RUNTIME_V1_APPEND_SAFE_PREFIX"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10p_c056_g013_fresh_prospective_shadow_contract_20260725.json"

H1_HIST_GE = 3.637199446
H1_LINE_LE = -7.667425443
H1_RET3_GE = 18.70087437
D1_HIST_GE = -14.25480242
HORIZON_MINUTES = 240
FIXED_SPREAD_USD = 0.20
CYCLE_SECONDS = 60
LAG = {"M1": 0, "M5": 600, "M15": 1800, "H1": 7200, "H4": 28800, "D1": 172800}


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
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        raise E("unexpected M10P contract")
    data = contract.get("data", {})
    expected_map = {"M1", "M5", "M15", "H1", "H4", "D1"}
    if data.get("historical_backfill") is not False or set(data.get("live_file_map", {})) != expected_map:
        raise E("unsafe M10P data contract")
    candidate = contract.get("candidate", {})
    seed = candidate.get("seed_formula", {})
    regime = candidate.get("regime_formula", {})
    if (
        float(seed.get("h1_macd_hist_bps_ge", math.nan)) != H1_HIST_GE
        or float(seed.get("h1_macd_line_bps_le", math.nan)) != H1_LINE_LE
        or float(regime.get("h1_ret3_bps_ge", math.nan)) != H1_RET3_GE
        or float(regime.get("d1_macd_hist_bps_ge", math.nan)) != D1_HIST_GE
        or int(candidate.get("horizon_minutes", -1)) != HORIZON_MINUTES
        or candidate.get("direction") != "SHORT"
        or candidate.get("one_position") is not True
    ):
        raise E("M10P frozen candidate mismatch")
    safety = contract.get("safety", {})
    if safety.get("audit_only") is not True:
        raise E("audit_only required")
    for key in (
        "discord_send", "mt5_order", "live_ready", "final_signal", "entry_gate_enabled", "historical_backfill",
        "collector_reset", "m7c_reset", "m8c_reset", "m9v_reset", "m9y_reset", "m10b_reset", "m10e_reset",
        "automatic_live_promotion",
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


def feature_arrays(bars: list[p.Bar]) -> tuple[list[float], list[float], list[float | None]]:
    closes = [float(bar.close) for bar in bars]
    fast = c.ema(closes, 6)
    slow = c.ema(closes, 13)
    line = [(a - b) / max(abs(close), 1e-12) * 10000.0 for a, b, close in zip(fast, slow, closes)]
    signal = c.ema(line, 4)
    hist = [a - b for a, b in zip(line, signal)]
    ret3: list[float | None] = [None] * len(bars)
    for i in range(3, len(bars)):
        prev = float(bars[i - 3].close)
        if prev != 0:
            ret3[i] = (float(bars[i].close) - prev) / abs(prev) * 10000.0
    return line, hist, ret3


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


def candidate_rows(root: Path, contract: dict[str, Any], start: datetime) -> tuple[list[dict[str, Any]], dict[str, list[p.Bar]]]:
    fmap = contract["data"]["live_file_map"]
    bars = {
        "M1": load_bars_retry(root / fmap["M1"]),
        "H1": load_bars_retry(root / fmap["H1"]),
        "D1": load_bars_retry(root / fmap["D1"]),
    }
    m1, h1, d1 = bars["M1"], bars["H1"], bars["D1"]
    if len(h1) < 20 or len(d1) < 20:
        raise E("insufficient H1/D1 history")
    h1_line, h1_hist, h1_ret3 = feature_arrays(h1)
    _, d1_hist, _ = feature_arrays(d1)
    d1_close_times = [bar.time + timedelta(days=1) for bar in d1]
    m1_by_time = {bar.time: bar for bar in m1}

    decisions: list[tuple[datetime, int]] = []
    for i in range(3, len(h1) - 1):
        decision = h1[i + 1].time
        decisions.append((decision, i))

    # The CSV contract contains only CLOSED H1 bars. Add the current frontier decision
    # from the first exact M1 observation at/after the latest closed H1's nominal close.
    # This also handles the first tradable H1 after a market-closed gap without inventing a price.
    last_i = len(h1) - 1
    nominal = h1[last_i].time + timedelta(hours=1)
    frontier: datetime | None = None
    for bar in m1:
        if bar.time < nominal:
            continue
        if bar.time.minute == 0 and bar.time.second == 0:
            frontier = bar.time
            break
    if frontier is not None and all(decision != frontier for decision, _ in decisions):
        decisions.append((frontier, last_i))

    output: list[dict[str, Any]] = []
    for decision, ih1 in sorted(decisions, key=lambda item: item[0]):
        if decision <= start:
            continue
        id1 = bisect.bisect_right(d1_close_times, decision) - 1
        if id1 < 0 or ih1 < 3:
            continue
        ret3 = h1_ret3[ih1]
        if ret3 is None:
            continue
        values = {
            "h1_macd_hist_bps": float(h1_hist[ih1]),
            "h1_macd_line_bps": float(h1_line[ih1]),
            "h1_ret3_bps": float(ret3),
            "d1_macd_hist_bps": float(d1_hist[id1]),
        }
        matched = (
            values["h1_macd_hist_bps"] >= H1_HIST_GE
            and values["h1_macd_line_bps"] <= H1_LINE_LE
            and values["h1_ret3_bps"] >= H1_RET3_GE
            and values["d1_macd_hist_bps"] >= D1_HIST_GE
        )
        if not matched:
            continue
        output.append({
            "candidate_id": f"M10P_{decision.strftime('%Y%m%d_%H%M%S')}",
            "decision_time": ft(decision),
            "entry_time": ft(decision),
            "scheduled_exit_time": ft(decision + timedelta(minutes=HORIZON_MINUTES)),
            "h1_source_open": ft(h1[ih1].time),
            "d1_source_open": ft(d1[id1].time),
            **values,
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
            trades.append({**row, "trade_id": None, "status": "ENTRY_DATA_GAP", "return_bps": None, "fixed0p20_return_bps": None})
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
        trade_id = f"M10P_T{sum(1 for x in trades if x.get('trade_id')) + 1:06d}"
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


def metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in trades if row.get("trade_id")]
    resolved = [row for row in accepted if row.get("status") == "RESOLVED" and row.get("return_bps") is not None]
    actual = c.metrics_from_values([float(row["return_bps"]) for row in resolved])
    fixed = c.metrics_from_values([float(row["fixed0p20_return_bps"]) for row in resolved])
    return {
        "candidate_match_count": len(trades),
        "accepted_count": len(accepted),
        "resolved_count": len(resolved),
        "open_count": sum(row.get("status") == "OPEN" for row in accepted),
        "entry_data_gap_count": sum(row.get("status") == "ENTRY_DATA_GAP" for row in trades),
        "exit_data_gap_count": sum(row.get("status") == "EXIT_DATA_GAP" for row in accepted),
        "actual": actual,
        "fixed0p20": fixed,
    }


def runtime_paths(local_root: Path) -> tuple[Path, Path, Path, Path]:
    runtime_dir = local_root / "m10p_runtime"
    return (
        runtime_dir,
        runtime_dir / "m10p_runtime_manifest.json",
        runtime_dir / "m10p_runtime_state.json",
        runtime_dir / "m10p_shadow_loop.lock",
    )


def verify_runtime(root: Path, contract: dict[str, Any], runtime: dict[str, Any], m10e_path: Path) -> None:
    valid(contract)
    if (
        runtime.get("stage") != STAGE
        or runtime.get("runtime_contract_version") != VER
        or runtime.get("contract_sha256") != csha(contract)
        or runtime.get("reset_allowed") is not False
        or runtime.get("historical_backfill_allowed") is not False
        or runtime.get("audit_only") is not True
    ):
        raise E("M10P runtime integrity failed")
    if runtime.get("m10e_runtime_manifest_sha256_at_freeze") != fsha(m10e_path):
        raise E("M10E chronology anchor changed")
    m10e = js(m10e_path)
    if (
        m10e.get("stage") != "M10E_H1_COMPOUND_LOSS_FILTER_FRESH_PROSPECTIVE_SHADOW"
        or m10e.get("runtime_contract_version") != "M10E_RUNTIME_V1_APPEND_SAFE_PREFIX"
        or m10e.get("reset_allowed") is not False
    ):
        raise E("M10E chronology anchor unsafe")
    for tf, filename in contract["data"]["live_file_map"].items():
        frozen = runtime.get("frozen_row_prefixes", {}).get(tf)
        if not isinstance(frozen, dict):
            raise E(f"missing frozen prefix: {tf}")
        if v2.prefix_fingerprint_rows(root / filename, int(frozen.get("row_count", 0))) != frozen:
            raise E(f"frozen pre-start rows changed: {tf}")


def initialize() -> int:
    local_root, root, point = env()
    contract = js(CONTRACT)
    valid(contract)
    runtime_dir, runtime_path, state_path, lock_path = runtime_paths(local_root)
    if lock_path.exists():
        raise E("M10P loop lock exists")
    if runtime_path.exists() or state_path.exists():
        raise E("M10P runtime already exists; never reinitialize/reset")

    m10e_path = local_root / "m10e_runtime" / "m10e_runtime_manifest.json"
    if not m10e_path.is_file():
        raise E("M10E runtime anchor missing")
    m10e = js(m10e_path)
    if (
        m10e.get("stage") != "M10E_H1_COMPOUND_LOSS_FILTER_FRESH_PROSPECTIVE_SHADOW"
        or m10e.get("runtime_contract_version") != "M10E_RUNTIME_V1_APPEND_SAFE_PREFIX"
        or m10e.get("reset_allowed") is not False
    ):
        raise E("M10E runtime unsafe")

    fmap = contract["data"]["live_file_map"]
    for filename in fmap.values():
        if not (root / filename).is_file():
            raise E(f"required live CSV missing: {root / filename}")

    def snapshot() -> dict[str, Any]:
        return {tf: v.tail_snapshot(root / filename) for tf, filename in fmap.items()}

    first = snapshot()
    time.sleep(2)
    second = snapshot()
    if first != second:
        raise E("live CSV changed during M10P start freeze; rerun BAT01 without changing anything")
    latest = {tf: pt(str(item["last_server_open"])) for tf, item in second.items()}
    start = latest["M1"]
    for tf, time_value in latest.items():
        lag = (start - time_value).total_seconds()
        if lag < 0 or lag > LAG[tf]:
            raise E(f"{tf} lag invalid: {lag}s")
    m10e_start = pt(str(m10e["prospective_start_server_time"]))
    if start <= m10e_start:
        raise E("M10P start must be strictly after M10E start")

    prefixes = {
        tf: v2.prefix_fingerprint_rows(root / filename, int(second[tf]["row_count"]))
        for tf, filename in fmap.items()
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
        "m10e_runtime_manifest_sha256_at_freeze": fsha(m10e_path),
        "m10e_prospective_start_server_time": m10e["prospective_start_server_time"],
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
    atom(runtime_dir / "m10p_runtime_start_receipt.json", {
        "status": "PASS",
        "stage": "M10P_FRESH_START_INITIALIZATION_AUDIT_ONLY",
        "created_at_utc": now,
        "prospective_start_server_time": ft(start),
        "m10e_start": m10e["prospective_start_server_time"],
        "historical_backfill_allowed": False,
        "reset_allowed": False,
        "audit_only": True,
    })
    print(f"[M10P INIT PASS] fresh start={ft(start)}")
    return 0


def once() -> int:
    local_root, root, point = env()
    contract = js(CONTRACT)
    runtime_dir, runtime_path, state_path, _ = runtime_paths(local_root)
    if not runtime_path.is_file():
        raise E("M10P runtime missing; run BAT01 once first")
    runtime = js(runtime_path)
    m10e_path = local_root / "m10e_runtime" / "m10e_runtime_manifest.json"
    verify_runtime(root, contract, runtime, m10e_path)
    start = pt(str(runtime["prospective_start_server_time"]))

    candidates, bars = candidate_rows(root, contract, start)
    trades, overlaps = build_ledgers(candidates, bars["M1"], point)
    stats = metrics(trades)
    latest_snapshots = {tf: v.tail_snapshot(root / filename) for tf, filename in contract["data"]["live_file_map"].items()}
    latest_server_open = {tf: item["last_server_open"] for tf, item in latest_snapshots.items()}
    gates = contract["review_gates"]
    resolved = int(stats["resolved_count"])
    review = {
        "operational": resolved >= int(gates["operational_resolved"]),
        "interim": resolved >= int(gates["interim_resolved"]),
        "formal": resolved >= int(gates["formal_resolved"]),
        "pf2_claim_allowed": resolved >= int(gates["formal_resolved"]),
        "automatic_live_promotion": False,
    }

    output_root = local_root / "outputs" / "M10P"
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
            "seed_id": "M10L_H240_C056",
            "gate_id": "M10N_G013",
            "h1_macd_hist_bps_ge": H1_HIST_GE,
            "h1_macd_line_bps_le": H1_LINE_LE,
            "h1_ret3_bps_ge": H1_RET3_GE,
            "d1_macd_hist_bps_ge": D1_HIST_GE,
            "horizon_minutes": HORIZON_MINUTES,
        },
        "metrics": stats,
        "overlap_skip_count": len(overlaps),
        "review_readiness": review,
        "guardrails": {
            "audit_only": True,
            "historical_backfill": False,
            "pre_start_candidate_eligibility": False,
            "threshold_refit_from_prospective_outcomes": False,
            "m7c_modified_or_reset": False,
            "m10b_modified_or_reset": False,
            "m10e_modified_or_reset": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "automatic_live_promotion": False,
        },
    }
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10P fresh prospective audit-only shadow for frozen C056+G013. No historical backfill. Do not rerun initializer after the start is frozen.\n",
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
        "exact_m1_entry_only": True,
        "exact_m1_exit_only": True,
        "nearest_m1_fallback": False,
        "exit_data_gap_never_backfilled": True,
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
    print(f"[M10P PASS] start={ft(start)} candidates={len(candidates)} accepted={stats['accepted_count']} resolved={stats['resolved_count']} open={stats['open_count']}")
    print(f"[PACKAGE] {package}")
    return 0


def forever() -> int:
    local_root, _, _ = env()
    _, runtime_path, _, lock_path = runtime_paths(local_root)
    if not runtime_path.is_file():
        raise E("M10P runtime missing; run BAT01 once first")
    if lock_path.exists():
        raise E(f"M10P loop lock already exists: {lock_path}")
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
        print("[M10P] graceful stop requested")
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
        print(f"[M10P BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] Existing forward monitors and all frozen starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
