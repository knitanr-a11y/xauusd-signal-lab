from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
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
for directory in (MR / "m9v" / "python", MR / "m9y" / "python", MR / "m9p" / "python", MR / "m10a" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import m9v_core as v
import m9v_core_v2 as v2
import m9y_core as y
import run_gold_dynamic_core_reproduction_audit as p
import payoff_rules as pay

STAGE = "M10E_H1_COMPOUND_LOSS_FILTER_FRESH_PROSPECTIVE_SHADOW"
VER = "M10E_RUNTIME_V1_APPEND_SAFE_PREFIX"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10e_h1_compound_loss_filter_fresh_prospective_shadow_contract_20260725.json"

M5_MACD_SLOPE_LE = -0.1308
H1_EMA30_MINUS_EMA40_BPS_GE = 17.3333
RUNNER_SHARE = 0.50
ARMS = ("E0_H1_BASELINE_RUNNER50", "E1_H1_FILTERED_RUNNER50")
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
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def valid(contract: dict[str, Any]) -> None:
    if contract.get("project") != "MOCHIPOYO_ALERT_RESEARCH" or contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_STARTED":
        raise E("unexpected M10E contract")
    data = contract.get("data", {})
    if data.get("historical_backfill") is not False or set(data.get("live_file_map", {})) != {"M1", "M5", "M15", "H1", "H4", "D1"}:
        raise E("unsafe M10E data contract")
    rule = contract.get("compound_filter", {})
    if float(rule.get("m5_macd_bps_slope_le", math.nan)) != M5_MACD_SLOPE_LE or float(rule.get("h1_ema30_minus_ema40_bps_ge", math.nan)) != H1_EMA30_MINUS_EMA40_BPS_GE:
        raise E("M10E fixed compound filter mismatch")
    if set(contract.get("arms", {})) != set(ARMS):
        raise E("M10E arm mismatch")
    safety = contract.get("safety", {})
    if safety.get("audit_only") is not True:
        raise E("audit_only required")
    for key in (
        "discord_send", "mt5_order", "live_ready", "final_signal", "entry_gate_enabled",
        "historical_backfill", "m7c_reset", "m8c_reset", "m9v_reset", "m9y_reset",
        "m10b_reset", "automatic_live_promotion",
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
    if not data_root.is_dir() or not math.isfinite(point):
        raise E(f"MT5 root/point unavailable: {data_root} {point}")
    return local_root, data_root, point


def stable_feed(latest: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    summary_path = latest / "01_summary.json"
    ledger_path = latest / "02_branch_candidate_ledger.csv"
    for attempt in range(5):
        try:
            first = summary_path.read_bytes()
            ledger = ledger_path.read_bytes()
            second = summary_path.read_bytes()
            if first != second:
                raise OSError("M9V summary changed during read")
            return json.loads(first.decode()), list(csv.DictReader(io.StringIO(ledger.decode("utf-8-sig"))))
        except Exception:
            if attempt == 4:
                raise E("cannot obtain stable M9V feed")
            time.sleep(0.25)
    raise E("unreachable")


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [row for row in rows if row.get("weighted_return_bps") is not None]
    if not resolved:
        return {
            "accepted_count": len(rows), "resolved_count": 0, "open_count": len(rows),
            "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0,
            "average_win_bps": None, "average_loss_bps": None, "payoff_ratio": None,
            "max_drawdown_bps": 0.0, "max_losing_streak": 0, "tail_le_minus_100_fraction": None,
        }
    ordered = sorted(resolved, key=lambda row: pt(str(row["actual_entry_time"])))
    values = [float(row["weighted_return_bps"]) for row in ordered]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    equity = peak = drawdown = 0.0
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        streak = streak + 1 if value < 0 else 0
        max_streak = max(max_streak, streak)
    average_win = sum(wins) / len(wins) if wins else None
    average_loss = sum(losses) / len(losses) if losses else None
    gross_loss = abs(sum(losses))
    return {
        "accepted_count": len(rows), "resolved_count": len(resolved), "open_count": len(rows) - len(resolved),
        "win_rate": sum(value > 0 for value in values) / len(values),
        "profit_factor_bps": None if gross_loss == 0 else sum(wins) / gross_loss,
        "net_bps": sum(values), "average_win_bps": average_win, "average_loss_bps": average_loss,
        "payoff_ratio": None if average_win is None or average_loss in (None, 0) else average_win / abs(average_loss),
        "max_drawdown_bps": drawdown, "max_losing_streak": max_streak,
        "tail_le_minus_100_fraction": sum(value <= -100 for value in values) / len(values),
    }


def normalize_h1(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        if row.get("branch") != "S3_H1" or not (row.get("native_exit_time") or "").strip():
            continue
        output.append({
            "trade_id": row.get("candidate_id"),
            "proxy_entry_time": row["proxy_primary_time"],
            "turn_entry_time": row["turn_entry_time"],
            "exit_time": row["native_exit_time"],
            "return_bps": row.get("return_bps"),
        })
    return output


def annotate_filter(rows: list[dict[str, Any]], m5: list[p.Bar], h1: list[p.Bar]) -> list[dict[str, Any]]:
    m5_close_times = [bar.time + timedelta(minutes=5) for bar in m5]
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    m5_macd = p.macd_bps(m5)
    h1_closes = [bar.close for bar in h1]
    h1_ema30 = p.ema(h1_closes, 30)
    h1_ema40 = p.ema(h1_closes, 40)
    output: list[dict[str, Any]] = []
    for row in rows:
        decision = pt(str(row["actual_entry_time"]))
        i5 = bisect.bisect_right(m5_close_times, decision) - 1
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        if i5 <= 0 or ih1 < 0:
            raise E(f"entry feature context unavailable at {row['actual_entry_time']}")
        slope = float(m5_macd[i5]) - float(m5_macd[i5 - 1])
        h1_close = float(h1_closes[ih1])
        if h1_close == 0:
            raise E(f"zero H1 close at {row['actual_entry_time']}")
        stack_bps = (float(h1_ema30[ih1]) - float(h1_ema40[ih1])) / abs(h1_close) * 10000.0
        excluded = slope <= M5_MACD_SLOPE_LE and stack_bps >= H1_EMA30_MINUS_EMA40_BPS_GE
        output.append({
            **row,
            "entry_feature_m5_closed_index": i5,
            "entry_feature_h1_closed_index": ih1,
            "m5_macd_bps_slope": slope,
            "h1_ema30_minus_ema40_bps": stack_bps,
            "compound_filter_excluded": excluded,
        })
    return output


def arm(name: str, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    active_until: datetime | None = None
    open_position = False
    active_id: str | None = None
    for row in sorted(rows, key=lambda item: pt(str(item["actual_entry_time"]))):
        entry_time = pt(str(row["actual_entry_time"]))
        if open_position or (active_until is not None and entry_time < active_until):
            skipped.append({
                "arm": name, "active_trade_id": active_id, "skipped_trade_id": row.get("trade_id"),
                "skipped_actual_entry_time": row["actual_entry_time"], "reason": "ONE_POSITION_ACTIVE",
            })
            continue
        native_return = float(row["native_return_bps"])
        native_exit = pt(str(row["exit_time"]))
        effective_exit: datetime | None = native_exit
        weighted_return: float | None = native_return
        runner_used = False
        if row.get("runner_eligible") is True:
            if row.get("runner_exit_time") and row.get("runner_return_bps") is not None:
                runner_used = True
                effective_exit = pt(str(row["runner_exit_time"]))
                weighted_return = (1.0 - RUNNER_SHARE) * native_return + RUNNER_SHARE * float(row["runner_return_bps"])
            else:
                effective_exit = None
                weighted_return = None
        accepted_row = {
            **row,
            "arm": name,
            "arm_trade_id": f"{name}_T{len(accepted)+1:06d}",
            "runner_share": RUNNER_SHARE,
            "runner_used": runner_used,
            "weighted_return_bps": weighted_return,
            "effective_exit_time": ft(effective_exit) if effective_exit else None,
        }
        accepted.append(accepted_row)
        active_id = accepted_row["arm_trade_id"]
        open_position = effective_exit is None
        active_until = effective_exit
    return accepted, skipped


def loadbars(root: Path, contract: dict[str, Any]) -> dict[str, list[p.Bar]]:
    return {tf: p.load_bars(root / filename) for tf, filename in contract["data"]["live_file_map"].items()}


def audit(root: Path, point: float, contract: dict[str, Any], runtime: dict[str, Any], m9v_path: Path, m9v_latest: Path, m9y_path: Path, m10b_path: Path) -> dict[str, Any]:
    valid(contract)
    if (
        runtime.get("stage") != STAGE
        or runtime.get("runtime_contract_version") != VER
        or runtime.get("contract_sha256") != csha(contract)
        or runtime.get("reset_allowed") is not False
        or runtime.get("historical_backfill_allowed") is not False
    ):
        raise E("M10E runtime integrity failed")

    m9v = js(m9v_path)
    if (
        m9v.get("stage") != v.STAGE
        or m9v.get("runtime_contract_version") != v2.RUNTIME_CONTRACT_VERSION
        or runtime.get("m9v_runtime_manifest_sha256") != fsha(m9v_path)
        or runtime.get("m9v_prospective_start_server_time") != m9v.get("prospective_start_server_time")
    ):
        raise E("M9V immutable upstream mismatch")
    if runtime.get("m9y_runtime_manifest_sha256_at_freeze") != fsha(m9y_path):
        raise E("M9Y chronology anchor changed")
    if runtime.get("m10b_runtime_manifest_sha256_at_freeze") != fsha(m10b_path):
        raise E("M10B chronology anchor changed")

    for tf, filename in contract["data"]["live_file_map"].items():
        frozen = runtime["frozen_row_prefixes"].get(tf)
        if not isinstance(frozen, dict) or v2.prefix_fingerprint_rows(root / filename, int(frozen.get("row_count", 0))) != frozen:
            raise E(f"frozen pre-start rows changed: {tf}")

    upstream_summary, feed = stable_feed(m9v_latest)
    if (
        upstream_summary.get("stage") != v.STAGE
        or upstream_summary.get("status") != "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY"
        or upstream_summary.get("prospective_start_server_time") != m9v.get("prospective_start_server_time")
    ):
        raise E("M9V feed mismatch")
    if upstream_summary.get("guardrails", {}).get("historical_backfill") is not False:
        raise E("unsafe M9V feed")

    start = pt(str(runtime["prospective_start_server_time"]))
    post_start = [
        row for row in feed
        if row.get("branch") == "S3_H1"
        and row.get("proxy_primary_time")
        and pt(str(row["proxy_primary_time"])) > start
    ]
    bars = loadbars(root, contract)
    native = normalize_h1(post_start)
    entries = pay.build_htf_reclaim(
        native, bars["M1"], bars["H1"], bars["M5"],
        signal_delta=timedelta(hours=1), confirm_delta=timedelta(minutes=5),
        offset_atr=pay.H1_ENTRY_OFFSET_ATR, wait_minutes=pay.H1_ENTRY_WAIT_MINUTES,
        point=point, confirm_name="M5",
    )
    runner_meta = pay.build_runner_meta(
        entries, bars["M1"], bars["H1"],
        context_bars=(bars["H4"], bars["D1"]),
        context_deltas=(timedelta(hours=4), timedelta(days=1)),
    )
    annotated = annotate_filter(runner_meta, bars["M5"], bars["H1"])
    filtered_input = [row for row in annotated if not bool(row["compound_filter_excluded"])]
    excluded = [row for row in annotated if bool(row["compound_filter_excluded"])]

    baseline, baseline_skips = arm("E0_H1_BASELINE_RUNNER50", annotated)
    filtered, filtered_skips = arm("E1_H1_FILTERED_RUNNER50", filtered_input)
    return {
        "start_server_time": ft(start),
        "latest_server_open": {tf: ft(items[-1].time) for tf, items in bars.items()},
        "upstream_resolved_post_start": len(native),
        "entries": annotated,
        "skipped_reclaim": len(native) - len(entries),
        "excluded": excluded,
        "arms": {
            "E0_H1_BASELINE_RUNNER50": baseline,
            "E1_H1_FILTERED_RUNNER50": filtered,
        },
        "arm_metrics": {
            "E0_H1_BASELINE_RUNNER50": metrics(baseline),
            "E1_H1_FILTERED_RUNNER50": metrics(filtered),
        },
        "overlaps": baseline_skips + filtered_skips,
    }


def initialize() -> int:
    local_root, root, _ = env()
    contract = js(CONTRACT)
    valid(contract)
    runtime_dir = local_root / "m10e_runtime"
    runtime_path = runtime_dir / "m10e_runtime_manifest.json"
    lock = runtime_dir / "m10e_shadow_loop.lock"
    if lock.exists():
        raise E("M10E loop lock exists")
    if runtime_path.exists():
        raise E("M10E runtime already exists; never reinitialize/reset")

    m9v_path = local_root / "m9v_runtime" / "m9v_runtime_manifest.json"
    m9y_path = local_root / "m9y_runtime" / "m9y_runtime_manifest.json"
    m10b_path = local_root / "m10b_runtime" / "m10b_runtime_manifest.json"
    if not m9v_path.is_file() or not m9y_path.is_file() or not m10b_path.is_file():
        raise E("M9V/M9Y/M10B runtime anchor missing")
    m9v = js(m9v_path)
    m9y = js(m9y_path)
    m10b = js(m10b_path)
    if m9v.get("stage") != v.STAGE or m9v.get("runtime_contract_version") != v2.RUNTIME_CONTRACT_VERSION or m9v.get("reset_allowed") is not False:
        raise E("M9V runtime unsafe")
    if m9y.get("stage") != y.STAGE or m9y.get("runtime_contract_version") != y.RUNTIME_CONTRACT_VERSION or m9y.get("reset_allowed") is not False:
        raise E("M9Y runtime unsafe")
    if m10b.get("stage") != "M10B_GOLD_MULTI_TIMEFRAME_PAYOFF_FRESH_PROSPECTIVE_SHADOW" or m10b.get("runtime_contract_version") != "M10B_RUNTIME_V1_APPEND_SAFE_PREFIX" or m10b.get("reset_allowed") is not False:
        raise E("M10B runtime unsafe")

    def snapshot() -> dict[str, Any]:
        return {tf: v.tail_snapshot(root / filename) for tf, filename in contract["data"]["live_file_map"].items()}

    first = snapshot()
    time.sleep(2)
    second = snapshot()
    if first != second:
        raise E("live CSV changed during M10E start freeze")
    latest = {tf: pt(str(item["last_server_open"])) for tf, item in second.items()}
    start = latest["M1"]
    for tf, time_value in latest.items():
        lag = (start - time_value).total_seconds()
        if lag < 0 or lag > LAG[tf]:
            raise E(f"{tf} lag invalid: {lag}s")
    anchors = (
        pt(str(m9v["prospective_start_server_time"])),
        pt(str(m9y["prospective_start_server_time"])),
        pt(str(m10b["prospective_start_server_time"])),
    )
    if any(start <= anchor for anchor in anchors):
        raise E("M10E start must be strictly after M9V, M9Y and M10B")

    prefixes = {
        tf: v2.prefix_fingerprint_rows(root / filename, int(second[tf]["row_count"]))
        for tf, filename in contract["data"]["live_file_map"].items()
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
        "frozen_row_prefixes": prefixes,
        "m9v_runtime_manifest_sha256": fsha(m9v_path),
        "m9v_prospective_start_server_time": m9v["prospective_start_server_time"],
        "m9y_runtime_manifest_sha256_at_freeze": fsha(m9y_path),
        "m9y_prospective_start_server_time": m9y["prospective_start_server_time"],
        "m10b_runtime_manifest_sha256_at_freeze": fsha(m10b_path),
        "m10b_prospective_start_server_time": m10b["prospective_start_server_time"],
        "m9v_upstream_read_only": True,
        "m9y_output_dependency": False,
        "m10b_output_dependency": False,
        "pre_start_primary_candidate_eligibility": False,
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
    atom(runtime_dir / "m10e_runtime_start_receipt.json", {
        "status": "PASS",
        "stage": "M10E_FRESH_START_INITIALIZATION_AUDIT_ONLY",
        "created_at_utc": now,
        "prospective_start_server_time": ft(start),
        "m9v_start": m9v["prospective_start_server_time"],
        "m9y_start": m9y["prospective_start_server_time"],
        "m10b_start": m10b["prospective_start_server_time"],
        "historical_backfill_allowed": False,
        "reset_allowed": False,
        "audit_only": True,
    })
    print(f"[M10E INIT PASS] fresh start={ft(start)}")
    return 0


def once() -> int:
    local_root, root, point = env()
    contract = js(CONTRACT)
    runtime_path = local_root / "m10e_runtime" / "m10e_runtime_manifest.json"
    if not runtime_path.is_file():
        raise E("M10E runtime missing; run BAT01 once first")
    result = audit(
        root, point, contract, js(runtime_path),
        local_root / "m9v_runtime" / "m9v_runtime_manifest.json",
        local_root / "outputs" / "M9V" / "LATEST",
        local_root / "m9y_runtime" / "m9y_runtime_manifest.json",
        local_root / "m10b_runtime" / "m10b_runtime_manifest.json",
    )
    output_root = local_root / "outputs" / "M10E"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = output_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)

    counts = {name: len(rows) for name, rows in result["arms"].items()}
    gates = contract["review_gates"]
    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prospective_start_server_time": result["start_server_time"],
        "latest_server_open": result["latest_server_open"],
        "native_base_materialization": "RESOLVED_ONLY; open upstream H1 candidates are absent until native EXIT resolves. Entry and compound-filter decisions use only bars closed by actual entry time.",
        "upstream_resolved_post_start": result["upstream_resolved_post_start"],
        "h1_entry_candidate_count": len(result["entries"]),
        "skipped_reclaim_count": result["skipped_reclaim"],
        "compound_excluded_before_one_position": len(result["excluded"]),
        "fixed_compound_filter": {
            "m5_macd_bps_slope_le": M5_MACD_SLOPE_LE,
            "h1_ema30_minus_ema40_bps_ge": H1_EMA30_MINUS_EMA40_BPS_GE,
            "feature_decision_time": "actual H1 reclaim entry; latest fully closed M5/H1 only",
        },
        "arm_metrics": result["arm_metrics"],
        "review_readiness": {
            "operational": counts["E0_H1_BASELINE_RUNNER50"] >= gates["H1_operational_accepted"],
            "interim": counts["E0_H1_BASELINE_RUNNER50"] >= gates["H1_interim_accepted"],
            "formal": counts["E0_H1_BASELINE_RUNNER50"] >= gates["H1_formal_accepted"],
            "automatic_live_promotion": False,
        },
        "guardrails": {
            "audit_only": True,
            "historical_backfill": False,
            "pre_start_primary_candidate_eligibility": False,
            "future_outcome_used_in_entry_gate": False,
            "mae_mfe_exit_path_used_as_filter_feature": False,
            "m9v_modified_or_reset": False,
            "m9y_modified_or_reset": False,
            "m10b_modified_or_reset": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        },
    }
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10E fresh audit-only H1 baseline-vs-compound-filter shadow.\n"
        "Independent new start; M9V/M9Y/M10B are not reset or backfilled.\n"
        "Resolved-only upstream materialization. No live promotion.\n",
        encoding="utf-8",
    )
    p.dump_json(archive / "01_summary.json", summary)
    p.write_csv(archive / "02_h1_entry_candidates_with_filter.csv", result["entries"])
    p.write_csv(archive / "03_E0_H1_BASELINE_RUNNER50_ledger.csv", result["arms"]["E0_H1_BASELINE_RUNNER50"])
    p.write_csv(archive / "04_E1_H1_FILTERED_RUNNER50_ledger.csv", result["arms"]["E1_H1_FILTERED_RUNNER50"])
    p.write_csv(archive / "05_compound_excluded_entry_candidates.csv", result["excluded"])
    p.write_csv(archive / "06_overlap_skip_metadata.csv", result["overlaps"])
    p.dump_json(archive / "07_runtime_manifest_copy.json", js(runtime_path))
    p.dump_json(archive / "08_data_quality.json", {
        "data_root": str(root), "point": point, "closed_rows_contract": True,
        "prefix_integrity_verified": True, "latest_server_open": result["latest_server_open"],
    })
    (archive / "09_audit.log").write_text("\n".join([
        "status=PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
        f"start={result['start_server_time']}",
        f"upstream_resolved_post_start={result['upstream_resolved_post_start']}",
        f"h1_entry_candidates={len(result['entries'])}",
        f"compound_excluded_before_one_position={len(result['excluded'])}",
        *(f"{name}={count}" for name, count in counts.items()),
        "native_base_materialization=resolved_only",
        "future_outcome_used_in_entry_gate=false",
        "mae_mfe_exit_path_used_as_filter_feature=false",
        "historical_backfill=false",
        "m9v_modified_or_reset=false",
        "m9y_modified_or_reset=false",
        "m10b_modified_or_reset=false",
        "discord_send=false",
        "mt5_order=false",
        "live_ready=false",
        "final_signal=false",
        "",
    ]), encoding="utf-8")

    names = [path.name for path in archive.iterdir() if path.is_file()]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(names):
            zf.write(archive / name, name)
    latest = output_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print("[M10E PASS] " + " ".join(f"{name}={count}" for name, count in counts.items()) + f" excluded={len(result['excluded'])}")
    print("[M10E OUTPUT]", latest)
    return 0


def forever() -> int:
    local_root, _, _ = env()
    runtime_dir = local_root / "m10e_runtime"
    lock = runtime_dir / "m10e_shadow_loop.lock"
    stop_file = runtime_dir / "STOP_M10E_SHADOW_LOOP"
    runtime_path = runtime_dir / "m10e_runtime_manifest.json"
    if not runtime_path.is_file():
        raise E("M10E runtime missing")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        raise E("M10E loop lock exists")
    stop_file.unlink(missing_ok=True)
    cycles = 0
    try:
        while not stop_file.exists():
            cycles += 1
            rc = once()
            if rc != 0:
                return rc
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and not stop_file.exists():
                time.sleep(1)
        print(f"[M10E LOOP STOPPED] cycles={cycles}")
        return 0
    finally:
        lock.unlink(missing_ok=True)


def stop() -> int:
    local_root, _, _ = env()
    stop_file = local_root / "m10e_runtime" / "STOP_M10E_SHADOW_LOOP"
    stop_file.parent.mkdir(parents=True, exist_ok=True)
    stop_file.write_text("operator stop requested\n", encoding="utf-8")
    print("[M10E STOP REQUESTED]", stop_file)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("init", "once", "forever", "stop"))
    mode = parser.parse_args().mode
    try:
        return {"init": initialize, "once": once, "forever": forever, "stop": stop}[mode]()
    except Exception as exc:
        print(f"[M10E {mode.upper()} BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] collector/M7C/M8C/M9V/M9Y/M10B unchanged.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
