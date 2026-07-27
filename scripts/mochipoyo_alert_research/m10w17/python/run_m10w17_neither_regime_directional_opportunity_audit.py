from __future__ import annotations

import csv
import json
import math
import os
import shutil
import statistics
import sys
import zipfile
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
M10A_PY = MR / "m10a" / "python"
if str(M10A_PY) not in sys.path:
    sys.path.insert(0, str(M10A_PY))

import frozen_core as frozen

STAGE = "M10W17_NEITHER_REGIME_DIRECTIONAL_OPPORTUNITY_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w17_neither_regime_directional_opportunity_contract_20260728.json"
TIME_FORMAT = frozen.TIME_FORMAT
POINT = frozen.POINT
HORIZON = timedelta(minutes=240)
REGIME_KEYS = ("d1_ema_stack", "h4_ema20_minus_ema30_sign", "h1_macd_line_sign", "h1_atr_pct100_tercile")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


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


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10A_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = load_json(metadata_path) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def verify_m1(data_root: Path) -> tuple[list[frozen.Bar], str]:
    filename, expected_hash = frozen.EXPECTED_FILES["M1"]
    path = data_root / filename
    if not path.is_file():
        raise RuntimeError(f"missing frozen GOLD M1: {path}")
    actual_hash = frozen.sha256(path)
    if actual_hash != expected_hash:
        raise RuntimeError(f"frozen M1 SHA256 mismatch actual={actual_hash} expected={expected_hash}")
    return frozen.load_bars(path), actual_hash


def bucket_id(row: dict[str, str]) -> str:
    return "|".join(row[key] for key in REGIME_KEYS)


def sample_neither(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    last_by_bucket: dict[str, datetime] = {}
    for row in rows:
        if row.get("coverage_class") != "NEITHER":
            continue
        current = datetime.strptime(row["decision_time"], TIME_FORMAT)
        bid = bucket_id(row)
        last = last_by_bucket.get(bid)
        if last is not None and current < last + HORIZON:
            continue
        last_by_bucket[bid] = current
        selected.append({
            "bucket_id": bid,
            "decision_time": row["decision_time"],
            "exit_time": (current + HORIZON).strftime(TIME_FORMAT),
            **{key: row[key] for key in REGIME_KEYS},
        })
    return selected


def split_name(year: int) -> str | None:
    if year in (2023, 2024):
        return "TRAIN_2023_2024"
    if year == 2025:
        return "VALIDATION_2025"
    if year == 2026:
        return "TEST_2026"
    return None


def directional_return(direction: str, entry_bar: frozen.Bar, exit_bar: frozen.Bar, fixed_spread: float | None = None) -> float:
    entry_bid = float(entry_bar.open)
    exit_bid = float(exit_bar.open)
    if fixed_spread is None:
        entry_spread = float(entry_bar.spread) * POINT
        exit_spread = float(exit_bar.spread) * POINT
    else:
        entry_spread = fixed_spread
        exit_spread = fixed_spread
    if direction == "LONG":
        entry_exec = entry_bid + entry_spread
        exit_exec = exit_bid
        return (exit_exec - entry_exec) / max(abs(entry_exec), 1e-12) * 10000.0
    entry_exec = entry_bid
    exit_exec = exit_bid + exit_spread
    return (entry_exec - exit_exec) / max(abs(entry_exec), 1e-12) * 10000.0


def metric(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count":0,"win_rate":None,"profit_factor":None,"net_bps":0.0,"average_win_bps":None,"average_loss_bps":None,"payoff_ratio":None,"max_drawdown_bps":0.0,"max_losing_streak":0}
    positives = [v for v in values if v > 0]
    negatives = [v for v in values if v < 0]
    gross_win = sum(positives)
    gross_loss = abs(sum(negatives))
    pf = None if gross_loss == 0 else gross_win / gross_loss
    avg_win = statistics.fmean(positives) if positives else None
    avg_loss = statistics.fmean(negatives) if negatives else None
    equity = peak = max_dd = 0.0
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "count": len(values),
        "win_rate": sum(v > 0 for v in values) / len(values),
        "profit_factor": pf,
        "net_bps": sum(values),
        "average_win_bps": avg_win,
        "average_loss_bps": avg_loss,
        "payoff_ratio": None if avg_win is None or avg_loss is None else avg_win / abs(avg_loss),
        "max_drawdown_bps": max_dd,
        "max_losing_streak": max_streak,
    }


def classify(metrics: dict[str, dict[str, Any]], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    rule = contract["selection_rule_frozen_before_run"]
    reasons: list[str] = []
    density = rule["density_gate"]
    for split, minimum in (("TRAIN_2023_2024", density["minimum_train_count"]), ("VALIDATION_2025", density["minimum_validation_count"]), ("TEST_2026", density["minimum_test_count"])):
        if int(metrics[split]["actual"]["count"]) < int(minimum):
            reasons.append(f"{split}_COUNT_LT_{minimum}")
    for split, section in (("TRAIN_2023_2024","train_discovery"),("VALIDATION_2025","validation_confirmation"),("TEST_2026","test_confirmation")):
        m = metrics[split]["actual"]
        threshold = float(rule[section]["minimum_actual_pf"])
        if m["profit_factor"] is None or float(m["profit_factor"]) < threshold:
            reasons.append(f"{split}_PF_LT_{threshold}")
        if bool(rule[section]["net_positive"]) and float(m["net_bps"]) <= 0:
            reasons.append(f"{split}_NET_NOT_POSITIVE")
    all_rule = rule["all_sample_cost_robustness"]
    if metrics["ALL"]["fixed0p20"]["profit_factor"] is None or float(metrics["ALL"]["fixed0p20"]["profit_factor"]) < float(all_rule["minimum_fixed0p20_pf"]):
        reasons.append("ALL_FIXED0P20_PF_FAIL")
    if metrics["ALL"]["actual_plus2bps_cost"]["profit_factor"] is None or float(metrics["ALL"]["actual_plus2bps_cost"]["profit_factor"]) < float(all_rule["minimum_extra2bps_pf"]):
        reasons.append("ALL_PLUS2BPS_PF_FAIL")
    if bool(all_rule["extra2bps_net_positive"]) and float(metrics["ALL"]["actual_plus2bps_cost"]["net_bps"]) <= 0:
        reasons.append("ALL_PLUS2BPS_NET_NOT_POSITIVE")
    return not reasons, reasons


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W17"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W17 contract")
        grid_path = local_root / "outputs" / "M10W14" / "LATEST" / "02_m15_coverage_grid.csv"
        if not grid_path.is_file():
            raise RuntimeError(f"M10W14 coverage grid unavailable: {grid_path}")
        grid = read_csv(grid_path)
        if not grid:
            raise RuntimeError("M10W14 coverage grid empty")
        data_root = resolve_data_root(local_root)
        m1, m1_hash = verify_m1(data_root)
        m1_index = {bar.time: bar for bar in m1}
        samples = sample_neither(grid)

        ledger: list[dict[str, Any]] = []
        gap_count = 0
        for sample in samples:
            entry_time = datetime.strptime(sample["decision_time"], TIME_FORMAT)
            exit_time = entry_time + HORIZON
            entry_bar = m1_index.get(entry_time)
            exit_bar = m1_index.get(exit_time)
            if entry_bar is None or exit_bar is None:
                gap_count += 1
                continue
            split = split_name(entry_time.year)
            if split is None:
                continue
            for direction in ("LONG", "SHORT"):
                actual = directional_return(direction, entry_bar, exit_bar, None)
                fixed = directional_return(direction, entry_bar, exit_bar, 0.20)
                ledger.append({
                    **sample,
                    "direction": direction,
                    "split": split,
                    "entry_spread_points": int(entry_bar.spread),
                    "exit_spread_points": int(exit_bar.spread),
                    "actual_return_bps": actual,
                    "fixed0p20_return_bps": fixed,
                })

        by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in ledger:
            by_key[(str(row["bucket_id"]), str(row["direction"]))].append(row)

        result_rows: list[dict[str, Any]] = []
        stable_rows: list[dict[str, Any]] = []
        detailed: dict[str, Any] = {}
        for (bid, direction), rows in sorted(by_key.items()):
            rows = sorted(rows, key=lambda row: str(row["decision_time"]))
            split_rows = {
                "TRAIN_2023_2024": [r for r in rows if r["split"] == "TRAIN_2023_2024"],
                "VALIDATION_2025": [r for r in rows if r["split"] == "VALIDATION_2025"],
                "TEST_2026": [r for r in rows if r["split"] == "TEST_2026"],
                "ALL": rows,
            }
            metrics: dict[str, dict[str, Any]] = {}
            for split, sr in split_rows.items():
                actual_values = [float(r["actual_return_bps"]) for r in sr]
                fixed_values = [float(r["fixed0p20_return_bps"]) for r in sr]
                metrics[split] = {
                    "actual": metric(actual_values),
                    "fixed0p20": metric(fixed_values),
                    "actual_plus1bps_cost": metric([v - 1.0 for v in actual_values]),
                    "actual_plus2bps_cost": metric([v - 2.0 for v in actual_values]),
                }
            passed, reasons = classify(metrics, contract)
            first = rows[0]
            row = {
                "bucket_id": bid,
                "direction": direction,
                **{key: first[key] for key in REGIME_KEYS},
                "stable_opportunity_pass": passed,
                "failure_reasons": ";".join(reasons),
                "train_count": metrics["TRAIN_2023_2024"]["actual"]["count"],
                "train_pf": metrics["TRAIN_2023_2024"]["actual"]["profit_factor"],
                "train_net_bps": metrics["TRAIN_2023_2024"]["actual"]["net_bps"],
                "validation_count": metrics["VALIDATION_2025"]["actual"]["count"],
                "validation_pf": metrics["VALIDATION_2025"]["actual"]["profit_factor"],
                "validation_net_bps": metrics["VALIDATION_2025"]["actual"]["net_bps"],
                "test_count": metrics["TEST_2026"]["actual"]["count"],
                "test_pf": metrics["TEST_2026"]["actual"]["profit_factor"],
                "test_net_bps": metrics["TEST_2026"]["actual"]["net_bps"],
                "all_count": metrics["ALL"]["actual"]["count"],
                "all_pf": metrics["ALL"]["actual"]["profit_factor"],
                "all_net_bps": metrics["ALL"]["actual"]["net_bps"],
                "all_fixed0p20_pf": metrics["ALL"]["fixed0p20"]["profit_factor"],
                "all_plus2bps_pf": metrics["ALL"]["actual_plus2bps_cost"]["profit_factor"],
                "all_plus2bps_net_bps": metrics["ALL"]["actual_plus2bps_cost"]["net_bps"],
            }
            result_rows.append(row)
            if passed:
                stable_rows.append(row)
            detailed[f"{bid}::{direction}"] = {"metrics": metrics, "pass": passed, "failure_reasons": reasons}

        result_rows.sort(key=lambda r: (not bool(r["stable_opportunity_pass"]), -(float(r["validation_pf"]) if r["validation_pf"] is not None else -999.0), -(float(r["test_pf"]) if r["test_pf"] is not None else -999.0)))
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_NEITHER_REGIME_DIRECTIONAL_OPPORTUNITY_AUDIT_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "coverage_grid_rows": len(grid),
            "sampled_neither_observations_before_exact_m1_gap_filter": len(samples),
            "exact_m1_gap_count": gap_count,
            "resolved_directional_ledger_rows": len(ledger),
            "evaluated_bucket_direction_pairs": len(result_rows),
            "stable_opportunity_pass_count": len(stable_rows),
            "stable_opportunities": stable_rows,
            "verified_M1_sha256": m1_hash,
            "selection_rule": contract["selection_rule_frozen_before_run"],
            "interpretation": {
                "existing_family_thresholds_changed": False,
                "new_event_trigger_created": False,
                "passing_bucket_is_trade_signal": False,
                "next_if_pass": "Pre-register a causal event-entry hypothesis inside only the passing exact bucket(s), without changing the bucket cuts, then evaluate and eventually require fresh prospective shadow.",
                "next_if_none": "Treat the coarse M10W14 EMA/MACD/ATR blind-spot regime space as lacking stable unconditional directional opportunity under this frozen test; add genuinely new information instead of tuning existing thresholds.",
            },
            "guardrails": contract["safety"],
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text("M10W17 evaluates pre-existing M10W14 NEITHER regime buckets under a frozen non-overlap 240-minute directional opportunity rule. It does not modify existing candidates or create a new event trigger.\n", encoding="utf-8")
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_sampled_neither_observations.csv", samples)
        write_csv(archive / "03_directional_ledger.csv", ledger)
        write_csv(archive / "04_bucket_direction_metrics.csv", result_rows)
        write_csv(archive / "05_stable_opportunities.csv", stable_rows)
        (archive / "06_detailed_metrics.json").write_text(json.dumps(detailed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_audit.log").write_text("\n".join([
            "status=PASS_NEITHER_REGIME_DIRECTIONAL_OPPORTUNITY_AUDIT_ONLY",
            f"coverage_grid_rows={len(grid)}",
            f"sampled_neither_observations={len(samples)}",
            f"exact_m1_gap_count={gap_count}",
            f"evaluated_bucket_direction_pairs={len(result_rows)}",
            f"stable_opportunity_pass_count={len(stable_rows)}",
            "existing_family_threshold_refit=false",
            "new_event_trigger_created=false",
            "existing_forward_modified=false",
            "",
        ]), encoding="utf-8")
        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt","01_summary.json","02_sampled_neither_observations.csv","03_directional_ledger.csv","04_bucket_direction_metrics.csv","05_stable_opportunities.csv","06_detailed_metrics.json","07_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)
        print(f"[M10W17 PASS] pairs={len(result_rows)} stable={len(stable_rows)} gaps={gap_count}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W17 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No existing threshold/start/runtime/monitor was changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
