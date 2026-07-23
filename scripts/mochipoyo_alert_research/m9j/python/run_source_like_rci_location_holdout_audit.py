from __future__ import annotations

import csv
import json
import os
import shutil
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_RESOLVED = 952
EXPECTED_TURNS = 852

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]


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


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pf(values: list[float]) -> float | None:
    wins = sum(value for value in values if value > 0)
    losses = abs(sum(value for value in values if value < 0))
    return None if losses == 0 else wins / losses


def policy_accept(policy: str, row: dict[str, Any]) -> bool:
    ticker = str(row["ticker"])
    direction = str(row["direction"])
    rci9 = as_float(row.get("entry_rci9"))
    if rci9 is None:
        raise RuntimeError(f"entry_rci9 unavailable for {row.get('proxy_trade_id', '')}")
    if policy == "J0_CONTROL":
        return True
    if policy == "J1_BTC_LONG_SIGN":
        return not (ticker == "BTCUSD" and direction == "LONG" and rci9 >= 0.0)
    if policy == "J2_BTC_LONG_NEG50_SENSITIVITY":
        return not (ticker == "BTCUSD" and direction == "LONG" and rci9 > -50.0)
    if policy == "J3_GLOBAL_SIGN_REFERENCE":
        return rci9 < 0.0 if direction == "LONG" else rci9 > 0.0
    raise ValueError(policy)


def chronological_risk(rows: list[dict[str, Any]], return_key: str) -> tuple[float, int]:
    ordered = sorted(rows, key=lambda row: (str(row.get("exit_server_open", "")), str(row.get("ticker", "")), str(row.get("proxy_trade_id", ""))))
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    streak = 0
    max_streak = 0
    for row in ordered:
        value = as_float(row.get(return_key))
        if value is None:
            continue
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_dd, max_streak


def metrics(rows: list[dict[str, Any]], return_key: str, baseline_count: int) -> dict[str, Any]:
    values = [as_float(row.get(return_key)) for row in rows]
    values = [value for value in values if value is not None]
    max_dd, max_streak = chronological_risk(rows, return_key)
    return {
        "count": len(values),
        "retention_fraction": len(values) / baseline_count if baseline_count else None,
        "win_rate": sum(value > 0 for value in values) / len(values) if values else None,
        "profit_factor_bps": pf(values) if values else None,
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values) if values else None,
        "median_bps": statistics.median(values) if values else None,
        "max_drawdown_bps": max_dd,
        "max_losing_streak": max_streak,
    }


def monthly(rows: list[dict[str, Any]], policy: str, panel: str, return_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        month = str(row["entry_server_open"])[:7]
        grouped[month].append(row)
    output: list[dict[str, Any]] = []
    for month in sorted(grouped):
        block = grouped[month]
        output.append({"panel": panel, "policy": policy, "month": month, **metrics(block, return_key, len(block))})
    return output


def branches(rows: list[dict[str, Any]], policy: str, panel: str, return_key: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for ticker in ("XAUUSD", "BTCUSD"):
        for direction in ("LONG", "SHORT"):
            block = [row for row in rows if row["ticker"] == ticker and row["direction"] == direction]
            if block:
                output.append({"panel": panel, "policy": policy, "ticker": ticker, "direction": direction, **metrics(block, return_key, len(block))})
    return output


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m9c = local_root / "outputs" / "M9C" / "LATEST"
    summary_path = m9c / "01_summary.json"
    immediate_path = m9c / "04_m1_resolved_trade_outcomes.csv"
    turn_path = m9c / "05_first_turn_context.csv"
    missing = [str(path) for path in (summary_path, immediate_path, turn_path) if not path.is_file()]
    if missing:
        print(f"[M9J BLOCKED] required M9C upstream missing: {missing}")
        return 2

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "PASS_EXPLORATORY_ONLY"
        or summary.get("implementation") != "M9C_CONTEXT_WARMUP_FIX_V2"
        or int(summary.get("m1_resolved_trade_count", -1)) != EXPECTED_RESOLVED
        or int(summary.get("first_turn_count", -1)) != EXPECTED_TURNS
        or summary.get("population_tier") != "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH"
    ):
        print("[M9J BLOCKED] M9C LATEST does not match reviewed frozen pre-source population")
        return 2

    immediate = read_csv(immediate_path)
    turns = read_csv(turn_path)
    if len(immediate) != EXPECTED_RESOLVED or len(turns) != EXPECTED_TURNS:
        print(f"[M9J BLOCKED] unexpected M9C row counts immediate={len(immediate)} turn={len(turns)}")
        return 2

    policies = (
        "J0_CONTROL",
        "J1_BTC_LONG_SIGN",
        "J2_BTC_LONG_NEG50_SENSITIVITY",
        "J3_GLOBAL_SIGN_REFERENCE",
    )
    immediate_summary: list[dict[str, Any]] = []
    turn_summary: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    branch_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []

    for row in immediate:
        detail = {
            "panel": "IMMEDIATE",
            "proxy_trade_id": row["proxy_trade_id"],
            "ticker": row["ticker"],
            "direction": row["direction"],
            "entry_server_open": row["entry_server_open"],
            "exit_server_open": row["exit_server_open"],
            "entry_rci9": row["entry_rci9"],
            "return_bps": row["return_bps"],
        }
        for policy in policies:
            detail[policy] = policy_accept(policy, row)
        detail_rows.append(detail)

    for row in turns:
        detail = {
            "panel": "FIRST_TURN",
            "proxy_trade_id": row["proxy_trade_id"],
            "ticker": row["ticker"],
            "direction": row["direction"],
            "entry_server_open": row["entry_server_open"],
            "exit_server_open": row["exit_server_open"],
            "entry_rci9": row["entry_rci9"],
            "return_bps": row["return_from_first_turn_bps"],
        }
        for policy in policies:
            detail[policy] = policy_accept(policy, row)
        detail_rows.append(detail)

    for policy in policies:
        accepted_immediate = [row for row in immediate if policy_accept(policy, row)]
        accepted_turns = [row for row in turns if policy_accept(policy, row)]
        immediate_summary.append({"panel": "IMMEDIATE", "policy": policy, **metrics(accepted_immediate, "return_bps", len(immediate))})
        turn_summary.append({"panel": "FIRST_TURN", "policy": policy, **metrics(accepted_turns, "return_from_first_turn_bps", len(turns))})
        monthly_rows.extend(monthly(accepted_immediate, policy, "IMMEDIATE", "return_bps"))
        monthly_rows.extend(monthly(accepted_turns, policy, "FIRST_TURN", "return_from_first_turn_bps"))
        branch_rows.extend(branches(accepted_immediate, policy, "IMMEDIATE", "return_bps"))
        branch_rows.extend(branches(accepted_turns, policy, "FIRST_TURN", "return_from_first_turn_bps"))

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9J_SOURCE_LIKE_RCI_LOCATION_HOLDOUT_AUDIT",
        "status": "PASS_EXPLORATORY_HOLDOUT_ONLY",
        "run_at_utc": built_at,
        "upstream": "M9C_CONTEXT_WARMUP_FIX_V2_PRE_SOURCE",
        "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "hypothesis_origin": "M9I2_SOURCE_TIMING_CORRECTED_GAP_AUDIT",
        "immediate_policy_summary": {row["policy"]: {k: v for k, v in row.items() if k not in {"panel", "policy"}} for row in immediate_summary},
        "first_turn_policy_summary": {row["policy"]: {k: v for k, v in row.items() if k not in {"panel", "policy"}} for row in turn_summary},
        "interpretation_contract": {
            "J1_primary_hypothesis": True,
            "J2_sensitivity_only": True,
            "J3_reproduction_reference_only": True,
            "reverse_time_temporal_holdout_not_prospective": True,
            "automatic_forward_promotion": False,
        },
        "guardrails": {
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m8c_reset": False,
            "classifier_trained": False,
            "decimal_threshold_optimized": False,
            "commission": "NOT_MODELED",
            "swap": "NOT_MODELED",
        },
    }

    quality = {
        "m9c_exact_m1_resolved_expected": EXPECTED_RESOLVED,
        "m9c_first_turn_expected": EXPECTED_TURNS,
        "entry_rci9_from_frozen_m15_primary_signal": True,
        "future_data_used_to_construct_trade": False,
        "historical_spread_inherited_from_m9c": True,
        "source_labels_present_in_validation_population": False,
        "validation_is_pre_source_retrospective_holdout": True,
    }

    out_root = local_root / "outputs" / "M9J"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    dump_json(archive / "01_summary.json", result)
    write_csv(archive / "02_immediate_policy_summary.csv", immediate_summary)
    write_csv(archive / "03_first_turn_policy_summary.csv", turn_summary)
    write_csv(archive / "04_monthly_policy_summary.csv", monthly_rows)
    write_csv(archive / "05_ticker_direction_summary.csv", branch_rows)
    write_csv(archive / "06_trade_policy_detail.csv", detail_rows)
    dump_json(archive / "07_data_quality.json", quality)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9J tests the M9I2-derived source-like M15 RCI9 location hypothesis on the separate pre-source M9C population. J1 changes BTC LONG selection only; J2 is sensitivity; J3 is a reproduction-oriented global reference. No live gate is enabled.\n",
        encoding="utf-8",
    )
    (archive / "08_audit.log").write_text(
        "\n".join([
            "status=PASS_EXPLORATORY_HOLDOUT_ONLY",
            "stage=M9J_SOURCE_LIKE_RCI_LOCATION_HOLDOUT_AUDIT",
            f"m9c_immediate={len(immediate)}",
            f"m9c_first_turn={len(turns)}",
            "hypothesis_origin=M9I2_SOURCE_TIMING_CORRECTED_GAP_AUDIT",
            "m7c_formula_changed=false",
            "m7c_threshold_changed=false",
            "m8c_reset=false",
            "automatic_forward_promotion=false",
            "",
        ]),
        encoding="utf-8",
    )

    latest = out_root / "LATEST"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    package = latest / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(latest.iterdir()):
            if path.name == package.name or not path.is_file():
                continue
            zf.write(path, arcname=path.name)

    j1i = next(row for row in immediate_summary if row["policy"] == "J1_BTC_LONG_SIGN")
    j1t = next(row for row in turn_summary if row["policy"] == "J1_BTC_LONG_SIGN")
    print(
        "[M9J PASS] "
        f"J1 immediate count={j1i['count']} WR={j1i['win_rate']:.4f} PF={j1i['profit_factor_bps']:.4f} "
        f"first_turn count={j1t['count']} WR={j1t['win_rate']:.4f} PF={j1t['profit_factor_bps']:.4f}"
    )
    print(f"[M9J OUTPUT] {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
