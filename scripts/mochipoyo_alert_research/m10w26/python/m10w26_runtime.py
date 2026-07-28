from __future__ import annotations

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
for directory in (
    MR / "common" / "python",
    MR / "m10a" / "python",
    MR / "m10w13" / "python",
    MR / "m10w22" / "python",
    MR / "m10w25" / "python",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import bounded_csv_source_adapter as adapter
import frozen_core as c
import run_high_atr_bullish_new_causal_information_availability_audit as feature_core
import run_m10w25_neither_prefix_causal_live_parity_audit as coverage_core

STAGE = "M10W26_MMO1_CAUSAL_NEITHER_FRESH_PROSPECTIVE_SHADOW"
RUNTIME_VERSION = "M10W26_RUNTIME_V1_BOUNDED_PRIVATE_SNAPSHOT"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w26_mmo1_causal_neither_fresh_prospective_shadow_contract_20260728.json"
TIME_FORMAT = adapter.TIME_FORMAT
HORIZON = timedelta(minutes=240)
FIXED_SPREAD_USD = 0.20
ATR_BOUNDARY = 0.67
EXPECTED_FILE_MAP = dict(adapter.FILE_MAP)


class M10W26Error(RuntimeError):
    pass


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def fmt_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise M10W26Error(f"cannot read JSON: {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise M10W26Error(f"JSON object required: {path}")
    return payload


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def canonical_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("project") != "MOCHIPOYO_ALERT_RESEARCH":
        raise M10W26Error("unexpected project")
    if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_STARTED":
        raise M10W26Error("unexpected M10W26 contract status/stage")
    if contract.get("scope") != "XAUUSD_GOLD_ONLY":
        raise M10W26Error("unsafe M10W26 scope")
    data = contract.get("data", {})
    if data.get("live_file_map") != EXPECTED_FILE_MAP or data.get("historical_backfill") is not False:
        raise M10W26Error("unsafe M10W26 data contract")
    candidate = contract.get("candidate", {})
    if candidate.get("family") != "MMO1_LONG_M1_MICRO_MOMENTUM" or candidate.get("direction") != "LONG":
        raise M10W26Error("unexpected M10W26 family/direction")
    if candidate.get("formula") != [
        "m1_ret5_bps > 0.0",
        "m1_up_close_count5 >= 3",
        "m1_close_location >= 0.60",
    ]:
        raise M10W26Error("MMO1 formula changed")
    if int(candidate.get("horizon_minutes", -1)) != 240:
        raise M10W26Error("MMO1 horizon changed")
    if candidate.get("one_position_per_arm") is not True or candidate.get("nearest_m1_fallback") is not False:
        raise M10W26Error("unsafe MMO1 execution semantics")
    coverage = contract.get("causal_coverage", {})
    if coverage.get("required_class") != "NEITHER":
        raise M10W26Error("causal coverage class changed")
    expected_families = [
        "LONG_M5_S1", "LONG_M15_S2", "LONG_H1_S3", "LONG_H4_S4",
        "SHORT_M10P_C056_G013", "SHORT_M10P2_C0212",
    ]
    if coverage.get("families") != expected_families:
        raise M10W26Error("causal coverage families changed")
    safety = contract.get("safety", {})
    if safety.get("audit_only") is not True:
        raise M10W26Error("audit_only required")
    for key in (
        "discord_send", "mt5_order", "live_ready", "final_signal", "entry_gate_enabled",
        "historical_backfill", "existing_forward_modified", "existing_threshold_refit",
        "runtime_reset", "start_reset", "manual_lock_or_journal_deletion",
        "automatic_live_promotion",
    ):
        if safety.get(key) is not False:
            raise M10W26Error(f"unsafe M10W26 flag: {key}")


def runtime_paths(local_root: Path) -> dict[str, Path]:
    directory = local_root / "m10w26_runtime"
    return {
        "directory": directory,
        "runtime": directory / "m10w26_runtime_manifest.json",
        "state": directory / "m10w26_runtime_state.json",
        "receipt": directory / "m10w26_runtime_start_receipt.json",
        "lock": directory / "m10w26_shadow_loop.lock",
        "stop": directory / "STOP_M10W26_SHADOW_LOOP",
        "log": local_root / "logs" / "m10w26" / "m10w26_private_snapshot_forever.log",
        "loop_status": local_root / "logs" / "m10w26" / "latest_m10w26_shadow_loop_status.json",
    }


def load_bars(root: Path) -> dict[str, list[c.Bar]]:
    bars: dict[str, list[c.Bar]] = {}
    for timeframe, filename in EXPECTED_FILE_MAP.items():
        path = root / filename
        if not path.is_file():
            raise M10W26Error(f"private snapshot CSV missing: {path}")
        try:
            bars[timeframe] = c.load_bars(path)
        except Exception as exc:
            raise M10W26Error(f"cannot read private snapshot {timeframe}: {type(exc).__name__}: {exc}") from exc
        if not bars[timeframe]:
            raise M10W26Error(f"empty private snapshot: {timeframe}")
    return bars


def prefix_fingerprint(path: Path, row_count: int) -> dict[str, Any]:
    if row_count <= 0:
        raise M10W26Error(f"invalid frozen row count for {path.name}: {row_count}")
    digest = hashlib.sha256()
    count = 0
    first = last = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != adapter.HEADER:
            raise M10W26Error(f"unexpected CSV header: {path.name}")
        for row in reader:
            if count >= row_count:
                break
            current = parse_time(str(row["time"]))
            if first is None:
                first = current
            last = current
            canonical = "|".join(str(row[name]).strip() for name in adapter.HEADER).encode("utf-8")
            digest.update(canonical + b"\n")
            count += 1
    if count != row_count or first is None or last is None:
        raise M10W26Error(f"frozen prefix shortened for {path.name}: expected={row_count} got={count}")
    return {
        "row_count": count,
        "first_server_open": fmt_time(first),
        "last_server_open": fmt_time(last),
        "sha256": digest.hexdigest(),
    }


def snapshot_info(root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for timeframe, filename in EXPECTED_FILE_MAP.items():
        path = root / filename
        rows, _ = adapter._read_journal(path)
        output[timeframe] = {
            "row_count": len(rows),
            "first_server_open": rows[0][0],
            "last_server_open": rows[-1][0],
            "sha256": adapter.sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    return output


def verify_runtime(local_root: Path, snapshot_root: Path, point: float, contract: dict[str, Any], runtime: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_contract(contract)
    if runtime.get("project") != "MOCHIPOYO_ALERT_RESEARCH" or runtime.get("stage") != STAGE:
        raise M10W26Error("unexpected M10W26 runtime")
    if runtime.get("runtime_contract_version") != RUNTIME_VERSION:
        raise M10W26Error("M10W26 runtime version mismatch")
    if runtime.get("runtime_status") != "FROZEN_FRESH_START":
        raise M10W26Error("M10W26 runtime status changed")
    if runtime.get("contract_sha256") != canonical_sha(contract):
        raise M10W26Error("M10W26 contract changed after start freeze")
    if runtime.get("historical_backfill_allowed") is not False or runtime.get("reset_allowed") is not False:
        raise M10W26Error("unsafe M10W26 runtime flags")
    if runtime.get("audit_only") is not True:
        raise M10W26Error("M10W26 runtime is not audit-only")
    source_root, observed_point = adapter.source_environment(local_root)
    if str(source_root) != str(runtime.get("source_root", "")):
        raise M10W26Error("M10W26 source root changed")
    if abs(float(runtime.get("point", "nan")) - point) > 1e-12 or abs(observed_point - point) > 1e-12:
        raise M10W26Error("M10W26 XAUUSD point changed")
    receipt = load_json(adapter.receipt_path(local_root))
    if receipt.get("status") != "PASS_MIGRATION_READY_FOR_REVIEW":
        raise M10W26Error("bounded adapter migration receipt no longer PASS")
    current = snapshot_info(snapshot_root)
    for timeframe, filename in EXPECTED_FILE_MAP.items():
        frozen = runtime.get("frozen_row_prefixes", {}).get(timeframe)
        if not isinstance(frozen, dict):
            raise M10W26Error(f"missing M10W26 frozen prefix: {timeframe}")
        observed = prefix_fingerprint(snapshot_root / filename, int(frozen.get("row_count", 0)))
        if observed != frozen:
            raise M10W26Error(f"M10W26 pre-start rows changed: {timeframe}")
    start = parse_time(str(runtime.get("prospective_start_server_time", "")))
    m1_times = [bar.time for bar in c.load_bars(snapshot_root / EXPECTED_FILE_MAP["M1"])]
    if start not in set(m1_times):
        raise M10W26Error("M10W26 immutable start anchor missing from M1 snapshot")
    return current


def target_regime_context(bars: dict[str, list[c.Bar]]) -> dict[str, Any]:
    h1, h4, d1 = bars["H1"], bars["H4"], bars["D1"]
    h1_line = feature_core.macd_line_bps(h1)
    h1_atrp = feature_core.atr_percentile100(h1)
    h4_closes = [float(bar.close) for bar in h4]
    h4_e20, h4_e30 = c.ema(h4_closes, 20), c.ema(h4_closes, 30)
    d1_closes = [float(bar.close) for bar in d1]
    d1_e20, d1_e30, d1_e40 = c.ema(d1_closes, 20), c.ema(d1_closes, 30), c.ema(d1_closes, 40)
    return {
        "h1_close_times": [bar.time + timedelta(hours=1) for bar in h1],
        "h4_close_times": [bar.time + timedelta(hours=4) for bar in h4],
        "d1_close_times": [bar.time + timedelta(days=1) for bar in d1],
        "h1_line": h1_line, "h1_atrp": h1_atrp,
        "h4_e20": h4_e20, "h4_e30": h4_e30,
        "d1_e20": d1_e20, "d1_e30": d1_e30, "d1_e40": d1_e40,
    }


def selected_index(times: list[datetime], decision: datetime) -> int:
    return bisect.bisect_right(times, decision) - 1


def target_regime(decision: datetime, context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    ih1 = selected_index(context["h1_close_times"], decision)
    ih4 = selected_index(context["h4_close_times"], decision)
    id1 = selected_index(context["d1_close_times"], decision)
    if min(ih1, ih4, id1) < 0 or context["h1_atrp"][ih1] is None:
        return False, {"available": False}
    d1_bull = context["d1_e20"][id1] > context["d1_e30"][id1] > context["d1_e40"][id1]
    h4_bull = context["h4_e20"][ih4] > context["h4_e30"][ih4]
    h1_positive = context["h1_line"][ih1] > 0
    atrp = float(context["h1_atrp"][ih1])
    return d1_bull and h4_bull and h1_positive and atrp >= ATR_BOUNDARY, {
        "available": True,
        "d1_bullish_stack": d1_bull,
        "h4_ema20_gt_ema30": h4_bull,
        "h1_macd_line_bps": float(context["h1_line"][ih1]),
        "h1_atr_pct100": atrp,
        "h1_source_open": fmt_time(context["h1_close_times"][ih1] - timedelta(hours=1)),
        "h4_source_open": fmt_time(context["h4_close_times"][ih4] - timedelta(hours=4)),
        "d1_source_open": fmt_time(context["d1_close_times"][id1] - timedelta(days=1)),
    }


def mmo1_features(decision: datetime, m1: list[c.Bar]) -> dict[str, Any] | None:
    close_times = [bar.time + timedelta(minutes=1) for bar in m1]
    index = bisect.bisect_right(close_times, decision) - 1
    if index < 4:
        return None
    selected = m1[index - 4:index + 1]
    latest = selected[-1]
    shape = feature_core.bar_shape(latest)
    close_location = shape["close_location"]
    ret5 = (float(latest.close) / max(abs(float(selected[0].open)), 1e-12) - 1.0) * 10000.0
    up_count = sum(float(bar.close) > float(bar.open) for bar in selected)
    return {
        "m1_ret5_bps": ret5,
        "m1_up_close_count5": up_count,
        "m1_close_location": close_location,
        "m1_source_open": fmt_time(latest.time),
        "m1_first_of_five_open": fmt_time(selected[0].time),
        "formula_pass": ret5 > 0.0 and up_count >= 3 and close_location is not None and float(close_location) >= 0.60,
    }


def build_candidates(bars: dict[str, list[c.Bar]], start: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    long_bins, long_diagnostics = coverage_core.build_prefix_causal_long_bins(bars)
    short_bins, short_diagnostics = coverage_core.build_short_bins(bars)
    bins = {**long_bins, **short_bins}
    context = target_regime_context(bars)
    m1 = bars["M1"]
    decisions = sorted({bar.time for bar in m1 if bar.time > start and bar.time.minute % 15 == 0 and bar.time.second == 0})
    candidates: list[dict[str, Any]] = []
    decision_audit: list[dict[str, Any]] = []
    for decision in decisions:
        regime_pass, regime_details = target_regime(decision, context)
        presence = {family: coverage_core.floor_m15(decision) in family_bins for family, family_bins in bins.items()}
        coverage_class = coverage_core.coverage_class(presence)
        feature = mmo1_features(decision, m1)
        feature_pass = bool(feature and feature.get("formula_pass"))
        eligible = regime_pass and coverage_class == "NEITHER" and feature_pass
        row: dict[str, Any] = {
            "decision_time": fmt_time(decision),
            "target_regime_pass": regime_pass,
            "causal_coverage_class": coverage_class,
            "MMO1_formula_pass": feature_pass,
            "eligible_candidate": eligible,
            **{f"presence_{family}": value for family, value in presence.items()},
            **{f"regime_{key}": value for key, value in regime_details.items()},
        }
        if feature:
            row.update(feature)
        decision_audit.append(row)
        if eligible:
            candidates.append({
                **row,
                "candidate_id": f"M10W26_{decision.strftime('%Y%m%d_%H%M%S')}",
                "family": "MMO1_LONG_M1_MICRO_MOMENTUM",
                "direction": "LONG",
                "entry_time": fmt_time(decision),
                "scheduled_exit_time": fmt_time(decision + HORIZON),
            })
    diagnostics = {
        "long_family": long_diagnostics,
        "short_family": short_diagnostics,
        "decision_grid_count_after_start": len(decisions),
        "target_regime_count_after_start": sum(bool(row["target_regime_pass"]) for row in decision_audit),
        "causal_neither_count_after_start": sum(row["causal_coverage_class"] == "NEITHER" for row in decision_audit),
        "mmo1_formula_count_after_start": sum(bool(row["MMO1_formula_pass"]) for row in decision_audit),
        "eligible_candidate_count_after_start": len(candidates),
        "future_reference": False,
    }
    return candidates, decision_audit, diagnostics


def directional_bps(entry_exec: float, exit_exec: float) -> float:
    return (exit_exec - entry_exec) / max(abs(entry_exec), 1e-12) * 10000.0


def build_ledger(candidates: list[dict[str, Any]], m1: list[c.Bar], point: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_time = {bar.time: bar for bar in m1}
    latest = m1[-1].time
    trades: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    active_until: datetime | None = None
    active_id: str | None = None
    sequence = 0
    for row in sorted(candidates, key=lambda item: parse_time(str(item["decision_time"]))):
        decision = parse_time(str(row["decision_time"]))
        if active_until is not None and decision < active_until:
            overlaps.append({"active_trade_id": active_id, "skipped_candidate_id": row["candidate_id"], "skipped_decision_time": row["decision_time"], "reason": "ONE_POSITION_ACTIVE"})
            continue
        entry = by_time.get(decision)
        if entry is None:
            trades.append({**row, "trade_id": None, "status": "ENTRY_DATA_GAP", "actual_return_bps": None, "fixed0p20_return_bps": None})
            continue
        sequence += 1
        trade_id = f"M10W26_T{sequence:06d}"
        exit_time = decision + HORIZON
        active_until = exit_time
        active_id = trade_id
        exit_bar = by_time.get(exit_time)
        if exit_bar is None:
            status = "EXIT_DATA_GAP" if latest >= exit_time else "OPEN"
            trades.append({**row, "trade_id": trade_id, "status": status, "entry_bid_open": float(entry.open), "entry_spread_points": int(entry.spread), "actual_return_bps": None, "fixed0p20_return_bps": None})
            continue
        actual_entry = float(entry.open) + int(entry.spread) * point
        fixed_entry = float(entry.open) + FIXED_SPREAD_USD
        exit_bid = float(exit_bar.open)
        trades.append({
            **row, "trade_id": trade_id, "status": "RESOLVED",
            "entry_bid_open": float(entry.open), "entry_spread_points": int(entry.spread),
            "exit_bid_open": exit_bid, "exit_spread_points": int(exit_bar.spread),
            "actual_return_bps": directional_bps(actual_entry, exit_bid),
            "fixed0p20_return_bps": directional_bps(fixed_entry, exit_bid),
        })
    return trades, overlaps


def metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor": None, "net_bps": 0.0, "average_win_bps": None, "average_loss_bps": None, "payoff_ratio": None, "max_drawdown_bps": 0.0, "max_losing_streak": 0}
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_loss = abs(sum(losses))
    average_win = sum(wins) / len(wins) if wins else None
    average_loss = sum(losses) / len(losses) if losses else None
    equity = peak = drawdown = 0.0
    streak = maximum_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        if value < 0:
            streak += 1
            maximum_streak = max(maximum_streak, streak)
        else:
            streak = 0
    return {
        "count": len(values), "win_rate": len(wins) / len(values),
        "profit_factor": None if gross_loss == 0 else sum(wins) / gross_loss,
        "net_bps": sum(values), "average_win_bps": average_win, "average_loss_bps": average_loss,
        "payoff_ratio": None if average_win is None or average_loss is None else average_win / abs(average_loss),
        "max_drawdown_bps": drawdown, "max_losing_streak": maximum_streak,
    }


def summarize(candidates: list[dict[str, Any]], trades: list[dict[str, Any]], overlaps: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in trades if row.get("trade_id")]
    resolved = [row for row in accepted if row.get("status") == "RESOLVED"]
    actual = [float(row["actual_return_bps"]) for row in resolved]
    fixed = [float(row["fixed0p20_return_bps"]) for row in resolved]
    return {
        "candidate_count": len(candidates), "accepted_count": len(accepted), "resolved_count": len(resolved),
        "open_count": sum(row.get("status") == "OPEN" for row in accepted),
        "entry_data_gap_count": sum(row.get("status") == "ENTRY_DATA_GAP" for row in trades),
        "exit_data_gap_count": sum(row.get("status") == "EXIT_DATA_GAP" for row in accepted),
        "overlap_skip_count": len(overlaps),
        "actual": metrics(actual), "fixed0p20": metrics(fixed),
        "actual_plus1bps_cost": metrics([value - 1.0 for value in actual]),
        "actual_plus2bps_cost": metrics([value - 2.0 for value in actual]),
    }


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


def initialize(snapshot_root: Path, point: float) -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    paths = runtime_paths(local_root)
    contract = load_json(CONTRACT)
    validate_contract(contract)
    if paths["lock"].exists():
        raise M10W26Error("M10W26 loop lock exists; stop loop before initialization")
    if paths["runtime"].exists() or paths["state"].exists() or paths["receipt"].exists():
        raise M10W26Error("M10W26 runtime already exists; reinitialize/reset is forbidden")
    source_root, observed_point = adapter.source_environment(local_root)
    if abs(point - observed_point) > 1e-12:
        raise M10W26Error("initializer point mismatch")
    receipt = load_json(adapter.receipt_path(local_root))
    if receipt.get("status") != "PASS_MIGRATION_READY_FOR_REVIEW":
        raise M10W26Error("bounded adapter migration is not reviewed PASS")
    first = snapshot_info(snapshot_root)
    time.sleep(1.0)
    second = snapshot_info(snapshot_root)
    if first != second:
        raise M10W26Error("private snapshot changed during start freeze")
    start = parse_time(str(second["M1"]["last_server_open"]))
    prefixes = {timeframe: prefix_fingerprint(snapshot_root / filename, int(second[timeframe]["row_count"])) for timeframe, filename in EXPECTED_FILE_MAP.items()}
    now = utc_text()
    runtime = {
        "project": "MOCHIPOYO_ALERT_RESEARCH", "stage": STAGE,
        "runtime_status": "FROZEN_FRESH_START", "runtime_contract_version": RUNTIME_VERSION,
        "created_at_utc": now, "prospective_start_server_time": fmt_time(start),
        "contract_sha256": canonical_sha(contract), "contract_path": str(CONTRACT),
        "source_root": str(source_root), "point": point,
        "frozen_row_prefixes": prefixes, "initial_private_snapshot": second,
        "private_snapshot_model": "M10W26_ONLY_VERIFIED_COPY_UNDER_BOUNDED_ADAPTER_UPDATE_LOCK",
        "pre_start_candidate_eligibility": False, "historical_backfill_allowed": False,
        "reset_allowed": False, "restart_safe": True, "audit_only": True,
        "discord_send": False, "mt5_order": False, "live_ready": False, "final_signal": False, "entry_gate_enabled": False,
    }
    state = {"project": "MOCHIPOYO_ALERT_RESEARCH", "stage": STAGE, "status": "INITIALIZED_NO_CYCLE_YET", "created_at_utc": now, "prospective_start_server_time": fmt_time(start), "cycle_count": 0, "reset_allowed": False}
    start_receipt = {
        "status": "PASS", "stage": "M10W26_FRESH_START_INITIALIZATION_AUDIT_ONLY", "created_at_utc": now,
        "prospective_start_server_time": fmt_time(start), "runtime_manifest": str(paths["runtime"]),
        "contract_sha256": runtime["contract_sha256"], "runtime_contract_version": RUNTIME_VERSION,
        "historical_backfill_allowed": False, "reset_allowed": False, "audit_only": True,
        "discord_send": False, "mt5_order": False, "live_ready": False, "final_signal": False,
    }
    atomic_json(paths["runtime"], runtime)
    atomic_json(paths["state"], state)
    atomic_json(paths["receipt"], start_receipt)
    print(f"[M10W26 INIT PASS] fresh start={fmt_time(start)}")
    print(json.dumps(start_receipt, ensure_ascii=False, indent=2))
    return 0


def once(snapshot_root: Path, point: float) -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    paths = runtime_paths(local_root)
    if not paths["runtime"].is_file():
        raise M10W26Error("M10W26 runtime missing; run the M10W26 initializer once")
    contract = load_json(CONTRACT)
    runtime = load_json(paths["runtime"])
    current_snapshot = verify_runtime(local_root, snapshot_root, point, contract, runtime)
    start = parse_time(str(runtime["prospective_start_server_time"]))
    bars = load_bars(snapshot_root)
    candidates, decisions, coverage_diagnostics = build_candidates(bars, start)
    trades, overlaps = build_ledger(candidates, bars["M1"], point)
    summary_metrics = summarize(candidates, trades, overlaps)
    gates = contract["review_gates"]
    resolved = int(summary_metrics["resolved_count"])
    actual_pf = summary_metrics["actual"].get("profit_factor")
    cost2_pf = summary_metrics["actual_plus2bps_cost"].get("profit_factor")
    review = {
        "operational": resolved >= int(gates["operational_resolved"]),
        "interim": resolved >= int(gates["interim_resolved"]),
        "formal": resolved >= int(gates["formal_resolved"]),
        "actual_pf_above_review_floor": actual_pf is not None and float(actual_pf) >= float(gates["minimum_actual_profit_factor_for_review"]),
        "actual_plus2bps_pf_above_review_floor": cost2_pf is not None and float(cost2_pf) >= float(gates["minimum_actual_plus2bps_profit_factor_for_review"]),
        "automatic_live_promotion": False,
    }
    output_root = local_root / "outputs" / "M10W26"
    archive = output_root / "archive" / utc_stamp()
    archive.mkdir(parents=True, exist_ok=False)
    snapshot_receipt = snapshot_root / "00_snapshot_receipt.json"
    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH", "stage": STAGE, "status": "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        "built_at_utc": utc_text(), "prospective_start_server_time": fmt_time(start),
        "latest_server_open": {timeframe: details["last_server_open"] for timeframe, details in current_snapshot.items()},
        "MMO1_CAUSAL_NEITHER": summary_metrics, "review_readiness": review,
        "frozen_rule": {
            "target_regime": "D1 bullish; H4 EMA20>EMA30; H1 MACD line>0; H1 ATR pct100>=0.67",
            "causal_coverage_class": "NEITHER", "MMO1": "m1_ret5_bps>0 AND m1_up_close_count5>=3 AND m1_close_location>=0.60",
            "horizon_minutes": 240, "one_position": True, "formula_or_threshold_changed": False,
        },
        "causal_coverage_diagnostics": coverage_diagnostics,
        "guardrails": {"audit_only": True, "historical_backfill": False, "pre_start_candidate_eligibility": False, "nearest_m1_fallback": False, "existing_forward_modified": False, "discord_send": False, "mt5_order": False, "live_ready": False, "final_signal": False, "automatic_live_promotion": False},
    }
    (archive / "00_READ_ME_FIRST.txt").write_text("M10W26 is an independent audit-only fresh prospective MMO1 shadow inside prefix-causal high-ATR bullish NEITHER windows. It uses exact M1 execution, a fixed 240-minute horizon and one position. Existing monitors remain unchanged.\n", encoding="utf-8")
    (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(archive / "02_candidate_ledger.csv", candidates)
    write_csv(archive / "03_trade_ledger.csv", trades)
    write_csv(archive / "04_overlap_skip_ledger.csv", overlaps)
    write_csv(archive / "05_post_start_decision_audit.csv", decisions)
    (archive / "06_causal_coverage_diagnostics.json").write_text(json.dumps(coverage_diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "07_runtime_manifest_copy.json").write_text(paths["runtime"].read_text(encoding="utf-8"), encoding="utf-8")
    if snapshot_receipt.is_file():
        shutil.copy2(snapshot_receipt, archive / "08_private_snapshot_receipt.json")
    else:
        (archive / "08_private_snapshot_receipt.json").write_text(json.dumps({"status": "MISSING"}, indent=2) + "\n", encoding="utf-8")
    data_quality = {"private_snapshot_root": str(snapshot_root), "point": point, "closed_rows_contract": True, "prefix_integrity_verified": True, "exact_m1_entry_only": True, "exact_m1_exit_only": True, "nearest_m1_fallback": False, "historical_backfill": False, "current_snapshot": current_snapshot}
    (archive / "09_data_quality.json").write_text(json.dumps(data_quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "10_audit.log").write_text("\n".join([
        "status=PASS_FRESH_PROSPECTIVE_AUDIT_ONLY", f"prospective_start_server_time={fmt_time(start)}",
        f"candidates={len(candidates)}", f"accepted={summary_metrics['accepted_count']}", f"resolved={summary_metrics['resolved_count']}", f"open={summary_metrics['open_count']}", f"overlap_skips={len(overlaps)}",
        "causal_coverage_class=NEITHER", "historical_backfill=false", "existing_forward_modified=false", "discord_send=false", "mt5_order=false", "",
    ]), encoding="utf-8")
    names = [path for path in archive.iterdir() if path.is_file()]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as package:
        for path in sorted(names):
            package.write(path, path.name)
    latest = output_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    old_state = load_json(paths["state"]) if paths["state"].is_file() else {"cycle_count": 0}
    atomic_json(paths["state"], {
        "project": "MOCHIPOYO_ALERT_RESEARCH", "stage": STAGE, "status": "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        "prospective_start_server_time": fmt_time(start), "last_cycle_at_utc": utc_text(),
        "cycle_count": int(old_state.get("cycle_count", 0)) + 1, "candidate_count": len(candidates),
        "accepted_count": int(summary_metrics["accepted_count"]), "resolved_count": resolved,
        "open_count": int(summary_metrics["open_count"]), "reset_allowed": False,
    })
    print(f"[M10W26 PASS] CANDIDATES={len(candidates)} ACCEPTED={summary_metrics['accepted_count']} RESOLVED={resolved} OPEN={summary_metrics['open_count']}")
    print(f"[M10W26 OUTPUT] {latest}")
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="M10W26 MMO1 causal-NEITHER fresh prospective runtime")
    parser.add_argument("mode", choices=("initialize", "once"))
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--point", type=float, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "initialize":
            return initialize(args.snapshot_root, args.point)
        return once(args.snapshot_root, args.point)
    except Exception as exc:
        print(f"[M10W26 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No existing runtime/start/monitor, Discord, or MT5 order was modified.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
