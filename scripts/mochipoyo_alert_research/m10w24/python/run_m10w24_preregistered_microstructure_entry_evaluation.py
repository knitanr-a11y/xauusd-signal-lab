from __future__ import annotations

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
M10A_PY = MR / "m10a" / "python"
if str(M10A_PY) not in sys.path:
    sys.path.insert(0, str(M10A_PY))
import frozen_core as c

STAGE = "M10W24_PREREGISTERED_HIGH_ATR_BULLISH_MICROSTRUCTURE_ENTRY_EVALUATION_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w23_high_atr_bullish_microstructure_entry_preregistration_20260728.json"
TIME_FORMAT = c.TIME_FORMAT
HORIZON = timedelta(minutes=240)
FIXED_SPREAD_USD = 0.20


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def load_feature_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"M10W22 causal feature rows missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError("M10W22 causal feature rows empty")
    return rows


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


def verify_m1(data_root: Path) -> list[c.Bar]:
    filename, expected_hash = c.EXPECTED_FILES["M1"]
    path = data_root / filename
    if not path.is_file():
        raise RuntimeError(f"frozen M1 missing: {path}")
    actual = c.sha256(path)
    if actual != expected_hash:
        raise RuntimeError(f"frozen M1 SHA mismatch: {actual} expected={expected_hash}")
    return c.load_bars(path)


def f(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    if value in (None, ""):
        return math.nan
    return float(value)


def matches(row: dict[str, Any], family: str) -> bool:
    if family == "MVI1_LONG_M5_VOLUME_IMPULSE":
        return f(row, "m5_tick_volume_ratio20") >= 1.0 and f(row, "m5_body_ratio") >= 0.50 and f(row, "m5_close_location") >= (2.0 / 3.0)
    if family == "MWR1_LONG_M5_PULLBACK_REJECTION":
        return f(row, "m5_ret3_bps") <= 0.0 and f(row, "m5_lower_wick_ratio") >= 0.40 and f(row, "m5_close_location") >= 0.60
    if family == "MMO1_LONG_M1_MICRO_MOMENTUM":
        return f(row, "m1_ret5_bps") > 0.0 and f(row, "m1_up_close_count5") >= 3.0 and f(row, "m1_close_location") >= 0.60
    raise RuntimeError(f"unknown family: {family}")


def build_candidates(rows: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        if not matches(row, family):
            continue
        output.append({**row, "family": family, "direction": "LONG", "entry_time": row["decision_time"], "scheduled_exit_time": (datetime.strptime(row["decision_time"], TIME_FORMAT) + HORIZON).strftime(TIME_FORMAT)})
    return output


def directional_bps(entry_exec: float, exit_exec: float) -> float:
    return (exit_exec - entry_exec) / max(abs(entry_exec), 1e-12) * 10000.0


def build_ledger(candidates: list[dict[str, Any]], m1: list[c.Bar]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_time = {bar.time: bar for bar in m1}
    latest = m1[-1].time
    active_until: datetime | None = None
    active_id: str | None = None
    trades: list[dict[str, Any]] = []
    skips: list[dict[str, Any]] = []
    seq = 0
    for row in sorted(candidates, key=lambda x: x["decision_time"]):
        decision = datetime.strptime(row["decision_time"], TIME_FORMAT)
        if active_until is not None and decision < active_until:
            skips.append({"active_trade_id": active_id, "skipped_decision_time": row["decision_time"], "reason": "ONE_POSITION_ACTIVE"})
            continue
        entry = by_time.get(decision)
        if entry is None:
            trades.append({**row, "trade_id": None, "status": "ENTRY_DATA_GAP", "actual_return_bps": None, "fixed0p20_return_bps": None})
            continue
        exit_time = decision + HORIZON
        exit_bar = by_time.get(exit_time)
        seq += 1
        trade_id = f"{row['family']}_T{seq:06d}"
        active_until = exit_time
        active_id = trade_id
        if exit_bar is None:
            status = "EXIT_DATA_GAP" if latest >= exit_time else "OPEN"
            trades.append({**row, "trade_id": trade_id, "status": status, "actual_return_bps": None, "fixed0p20_return_bps": None})
            continue
        actual_entry = float(entry.open) + int(entry.spread) * c.POINT
        actual_exit = float(exit_bar.open)
        fixed_entry = float(entry.open) + FIXED_SPREAD_USD
        fixed_exit = float(exit_bar.open)
        trades.append({
            **row,
            "trade_id": trade_id,
            "status": "RESOLVED",
            "entry_spread_points": int(entry.spread),
            "exit_spread_points": int(exit_bar.spread),
            "actual_return_bps": directional_bps(actual_entry, actual_exit),
            "fixed0p20_return_bps": directional_bps(fixed_entry, fixed_exit),
        })
    return trades, skips


def metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor": None, "net_bps": 0.0, "average_win_bps": None, "average_loss_bps": None, "payoff_ratio": None, "max_drawdown_bps": 0.0, "max_losing_streak": 0}
    positives = [v for v in values if v > 0]
    negatives = [v for v in values if v < 0]
    gross_win = sum(positives)
    gross_loss = abs(sum(negatives))
    pf = None if gross_loss == 0 else gross_win / gross_loss
    avg_win = sum(positives) / len(positives) if positives else None
    avg_loss = sum(negatives) / len(negatives) if negatives else None
    equity = peak = dd = 0.0
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {"count": len(values), "win_rate": sum(v > 0 for v in values) / len(values), "profit_factor": pf, "net_bps": sum(values), "average_win_bps": avg_win, "average_loss_bps": avg_loss, "payoff_ratio": None if avg_win is None or avg_loss is None else avg_win / abs(avg_loss), "max_drawdown_bps": dd, "max_losing_streak": max_streak}


def split_name(year: int) -> str | None:
    if year in (2023, 2024): return "TRAIN_2023_2024"
    if year == 2025: return "VALIDATION_2025"
    if year == 2026: return "TEST_2026"
    return None


def metric_blocks(trades: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [row for row in trades if row.get("status") == "RESOLVED"]
    groups: dict[str, list[dict[str, Any]]] = {"TRAIN_2023_2024": [], "VALIDATION_2025": [], "TEST_2026": [], "ALL": resolved}
    for row in resolved:
        name = split_name(datetime.strptime(str(row["entry_time"]), TIME_FORMAT).year)
        if name:
            groups[name].append(row)
    out: dict[str, Any] = {}
    for name, selected in groups.items():
        actual = [float(row["actual_return_bps"]) for row in selected]
        fixed = [float(row["fixed0p20_return_bps"]) for row in selected]
        out[name] = {
            "actual": metrics(actual),
            "fixed0p20": metrics(fixed),
            "actual_plus1bps_cost": metrics([v - 1.0 for v in actual]),
            "actual_plus2bps_cost": metrics([v - 2.0 for v in actual]),
        }
    return out


def pf(block: dict[str, Any]) -> float:
    value = block.get("profit_factor")
    if value is None:
        return float("inf") if int(block.get("count", 0)) > 0 else 0.0
    return float(value)


def classify(blocks: dict[str, Any], gates: dict[str, Any]) -> str:
    split_names = ("TRAIN_2023_2024", "VALIDATION_2025", "TEST_2026")
    counts = [int(blocks[name]["actual"]["count"]) for name in split_names]
    if min(counts) < 20:
        return "INSUFFICIENT_DENSITY"
    split_pfs = [pf(blocks[name]["actual"]) for name in split_names]
    all_pf = pf(blocks["ALL"]["actual"])
    fixed_pf = pf(blocks["ALL"]["fixed0p20"])
    cost2_pf = pf(blocks["ALL"]["actual_plus2bps_cost"])
    nets = [float(blocks[name]["actual"]["net_bps"]) for name in split_names]
    if min(split_pfs) <= 1.0 or fixed_pf <= 1.0 or cost2_pf <= 1.0:
        return "REJECT"
    strong = gates["STRONG_CANDIDATE"]
    if min(split_pfs) >= float(strong["minimum_pf_each_split"]) and all_pf >= float(strong["minimum_all_pf"]) and fixed_pf >= float(strong["minimum_fixed0p20_all_pf"]) and cost2_pf >= float(strong["minimum_extra2bps_all_pf"]) and all(net > 0 for net in nets):
        return "STRONG_CANDIDATE"
    robust = gates["ROBUST_CANDIDATE"]
    if min(split_pfs) >= float(robust["minimum_pf_each_split"]) and all_pf >= float(robust["minimum_all_pf"]) and fixed_pf >= float(robust["minimum_fixed0p20_all_pf"]) and cost2_pf >= float(robust["minimum_extra2bps_all_pf"]) and all(net > 0 for net in nets):
        return "ROBUST_CANDIDATE"
    return "WEAK_OR_INCONSISTENT"


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W24"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != "M10W23_HIGH_ATR_BULLISH_MICROSTRUCTURE_ENTRY_PREREGISTRATION_AUDIT_ONLY" or contract.get("status") != "HYPOTHESES_FROZEN_BEFORE_OUTCOME_EVALUATION":
            raise RuntimeError("unexpected M10W23 contract")
        feature_path = local_root / "outputs" / "M10W22" / "LATEST" / "02_target_regime_causal_feature_rows.csv"
        feature_rows = load_feature_rows(feature_path)
        data_root = resolve_data_root(local_root)
        m1 = verify_m1(data_root)
        gates = contract["frozen_evaluation"]["decision_tiers"]
        family_results: dict[str, Any] = {}
        all_trade_rows: list[dict[str, Any]] = []
        all_skip_rows: list[dict[str, Any]] = []
        for family in contract["families"]:
            candidates = build_candidates(feature_rows, family)
            trades, skips = build_ledger(candidates, m1)
            blocks = metric_blocks(trades)
            classification = classify(blocks, gates)
            family_results[family] = {
                "classification": classification,
                "candidate_count": len(candidates),
                "accepted_count": sum(row.get("trade_id") is not None for row in trades),
                "resolved_count": sum(row.get("status") == "RESOLVED" for row in trades),
                "entry_data_gap_count": sum(row.get("status") == "ENTRY_DATA_GAP" for row in trades),
                "exit_data_gap_count": sum(row.get("status") == "EXIT_DATA_GAP" for row in trades),
                "overlap_skip_count": len(skips),
                "metrics": blocks,
                "advance_to_fresh_shadow": classification in ("ROBUST_CANDIDATE", "STRONG_CANDIDATE"),
            }
            all_trade_rows.extend(trades)
            all_skip_rows.extend({"family": family, **row} for row in skips)
        advancing = [name for name, result in family_results.items() if result["advance_to_fresh_shadow"]]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_PREREGISTERED_MICROSTRUCTURE_ENTRY_EVALUATION_AUDIT_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "source_feature_rows": str(feature_path),
            "target_regime_row_count": len(feature_rows),
            "families": family_results,
            "advancing_families": advancing,
            "interpretation": {
                "historical_result_is_final_support": False,
                "no_formula_or_threshold_change_after_results": True,
                "fresh_shadow_required_for_any_pass": True,
                "M10W19_modified": False,
            },
            "guardrails": contract["safety"],
        }
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text("M10W24 preregistered microstructure entry evaluation. M10W23 formulas are frozen; no post-result tuning. Historical support is not final support.\n", encoding="utf-8")
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_trade_ledger_all_families.csv", all_trade_rows)
        write_csv(archive / "03_overlap_skip_ledger_all_families.csv", all_skip_rows)
        (archive / "04_audit.log").write_text("\n".join([
            "status=PASS_PREREGISTERED_MICROSTRUCTURE_ENTRY_EVALUATION_AUDIT_ONLY",
            f"target_regime_rows={len(feature_rows)}",
            f"advancing_families={','.join(advancing) if advancing else 'NONE'}",
            "formula_change_after_results=false",
            "threshold_change_after_results=false",
            "M10W19_modified=false",
            "automatic_live_promotion=false",
            "",
        ]), encoding="utf-8")
        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_trade_ledger_all_families.csv", "03_overlap_skip_ledger_all_families.csv", "04_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)
        print(f"[M10W24 PASS] advancing={advancing if advancing else 'NONE'}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W24 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No current monitor, frozen start, formula, or threshold was modified.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
