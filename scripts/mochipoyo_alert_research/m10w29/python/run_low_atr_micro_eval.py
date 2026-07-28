from __future__ import annotations

import csv
import hashlib
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

STAGE = "M10W29_PREREGISTERED_LOW_ATR_BULLISH_NEITHER_MICROSTRUCTURE_EVALUATION_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w28_low_atr_microstructure_preregistration_20260728.json"
TIME_FORMAT = c.TIME_FORMAT
HORIZON = timedelta(minutes=240)
FIXED_SPREAD_USD = 0.20
EXPECTED_FEATURE_SHA256 = "03f0185694485eab2b5e50ab93c2f354a91cdd8b0706f7710b66c2b1173648cd"
EXPECTED_FEATURE_ROWS = 7480


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def load_feature_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"M10W27 feature rows missing: {path}")
    actual_hash = sha256(path)
    if actual_hash != EXPECTED_FEATURE_SHA256:
        raise RuntimeError(f"M10W27 feature SHA mismatch: {actual_hash} expected={EXPECTED_FEATURE_SHA256}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_FEATURE_ROWS:
        raise RuntimeError(f"M10W27 row count drift: {len(rows)} expected={EXPECTED_FEATURE_ROWS}")
    decisions = [str(row.get("decision_time", "")) for row in rows]
    if len(decisions) != len(set(decisions)):
        raise RuntimeError("duplicate decision_time in M10W27 feature rows")
    forbidden = {"actual_return_bps", "fixed0p20_return_bps", "trade_id", "status", "scheduled_exit_time"}
    if rows and forbidden.intersection(rows[0]):
        raise RuntimeError("outcome/trade columns found in pre-entry feature rows")
    return rows


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
    if family == "LMVI1_LONG_M5_VOLUME_IMPULSE":
        return f(row, "m5_tick_volume_ratio20") >= 1.0 and f(row, "m5_body_ratio") >= 0.50 and f(row, "m5_close_location") >= (2.0 / 3.0)
    if family == "LMWR1_LONG_M5_PULLBACK_REJECTION":
        return f(row, "m5_ret3_bps") <= 0.0 and f(row, "m5_lower_wick_ratio") >= 0.40 and f(row, "m5_close_location") >= 0.60
    if family == "LMMO1_LONG_M1_MICRO_MOMENTUM":
        return f(row, "m1_ret5_bps") > 0.0 and f(row, "m1_up_close_count5") >= 3.0 and f(row, "m1_close_location") >= 0.60
    raise RuntimeError(f"unknown family: {family}")


def build_candidates(rows: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        if not matches(row, family):
            continue
        decision = datetime.strptime(str(row["decision_time"]), TIME_FORMAT)
        output.append({
            **row,
            "family": family,
            "direction": "LONG",
            "entry_time": row["decision_time"],
            "scheduled_exit_time": (decision + HORIZON).strftime(TIME_FORMAT),
        })
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
    for row in sorted(candidates, key=lambda x: str(x["decision_time"])):
        decision = datetime.strptime(str(row["decision_time"]), TIME_FORMAT)
        if active_until is not None and decision < active_until:
            skips.append({"active_trade_id": active_id, "skipped_decision_time": row["decision_time"], "family": row["family"], "reason": "ONE_POSITION_ACTIVE"})
            continue
        entry = by_time.get(decision)
        if entry is None:
            trades.append({**row, "trade_id": None, "status": "ENTRY_DATA_GAP", "actual_return_bps": None, "fixed0p20_return_bps": None})
            continue
        exit_time = decision + HORIZON
        seq += 1
        trade_id = f"{row['family']}_T{seq:06d}"
        active_until = exit_time
        active_id = trade_id
        exit_bar = by_time.get(exit_time)
        if exit_bar is None:
            status = "EXIT_DATA_GAP" if latest >= exit_time else "OPEN"
            trades.append({**row, "trade_id": trade_id, "status": status, "entry_spread_points": int(entry.spread), "actual_return_bps": None, "fixed0p20_return_bps": None})
            continue
        actual_entry = float(entry.open) + int(entry.spread) * c.POINT
        fixed_entry = float(entry.open) + FIXED_SPREAD_USD
        exit_bid = float(exit_bar.open)
        trades.append({
            **row,
            "trade_id": trade_id,
            "status": "RESOLVED",
            "entry_spread_points": int(entry.spread),
            "exit_spread_points": int(exit_bar.spread),
            "actual_return_bps": directional_bps(actual_entry, exit_bid),
            "fixed0p20_return_bps": directional_bps(fixed_entry, exit_bid),
        })
    return trades, skips


def metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor": None, "net_bps": 0.0, "average_win_bps": None, "average_loss_bps": None, "payoff_ratio": None, "max_drawdown_bps": 0.0, "max_losing_streak": 0}
    positives = [v for v in values if v > 0]
    negatives = [v for v in values if v < 0]
    gross_loss = abs(sum(negatives))
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
    return {
        "count": len(values),
        "win_rate": len(positives) / len(values),
        "profit_factor": None if gross_loss == 0 else sum(positives) / gross_loss,
        "net_bps": sum(values),
        "average_win_bps": avg_win,
        "average_loss_bps": avg_loss,
        "payoff_ratio": None if avg_win is None or avg_loss is None else avg_win / abs(avg_loss),
        "max_drawdown_bps": dd,
        "max_losing_streak": max_streak,
    }


def split_name(year: int) -> str | None:
    if year in (2023, 2024):
        return "TRAIN_2023_2024"
    if year == 2025:
        return "VALIDATION_2025"
    if year == 2026:
        return "TEST_2026"
    return None


def metric_blocks(trades: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [row for row in trades if row.get("status") == "RESOLVED"]
    groups: dict[str, list[dict[str, Any]]] = {"TRAIN_2023_2024": [], "VALIDATION_2025": [], "TEST_2026": [], "ALL": resolved}
    for row in resolved:
        name = split_name(datetime.strptime(str(row["entry_time"]), TIME_FORMAT).year)
        if name:
            groups[name].append(row)
    output: dict[str, Any] = {}
    for name, selected in groups.items():
        actual = [float(row["actual_return_bps"]) for row in selected]
        fixed = [float(row["fixed0p20_return_bps"]) for row in selected]
        output[name] = {
            "actual": metrics(actual),
            "fixed0p20": metrics(fixed),
            "actual_plus1bps_cost": metrics([v - 1.0 for v in actual]),
            "actual_plus2bps_cost": metrics([v - 2.0 for v in actual]),
        }
    return output


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


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W29"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != "M10W28_LOW_ATR_BULLISH_NEITHER_MICROSTRUCTURE_ENTRY_PREREGISTRATION_AUDIT_ONLY" or contract.get("status") != "HYPOTHESES_FROZEN_BEFORE_LOW_ATR_OUTCOME_EVALUATION":
            raise RuntimeError("unexpected M10W28 contract")
        feature_path = local_root / "outputs" / "M10W27" / "LATEST" / "02_low_atr_bullish_causal_neither_feature_rows.csv"
        feature_rows = load_feature_rows(feature_path)
        data_root = resolve_data_root(local_root)
        m1 = verify_m1(data_root)
        gates = contract["frozen_evaluation"]["decision_tiers"]
        family_results: dict[str, Any] = {}
        all_trades: list[dict[str, Any]] = []
        all_skips: list[dict[str, Any]] = []
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
                "open_count": sum(row.get("status") == "OPEN" for row in trades),
                "overlap_skip_count": len(skips),
                "metrics": blocks,
                "advance": classification in {"ROBUST_CANDIDATE", "STRONG_CANDIDATE"},
            }
            all_trades.extend(trades)
            all_skips.extend(skips)

        archive = output_root / "archive" / utc_stamp()
        archive.mkdir(parents=True, exist_ok=False)
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_PREREGISTERED_LOW_ATR_EVALUATION_AUDIT_ONLY",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_feature_sha256": EXPECTED_FEATURE_SHA256,
            "source_feature_rows": EXPECTED_FEATURE_ROWS,
            "target_regime": contract["target_regime"],
            "families": family_results,
            "formula_change": False,
            "threshold_change": False,
            "horizon_change": False,
            "M10W26_modified": False,
            "historical_result_is_fresh_support": False,
            "automatic_live_promotion": False,
            "guardrails": {"audit_only": True, "nearest_m1_fallback": False, "historical_backfill": False, "discord_send": False, "mt5_order": False, "live_ready": False, "final_signal": False},
        }
        (archive / "00_READ_ME_FIRST.txt").write_text("M10W29 evaluates the three M10W28 preregistered low-ATR bullish causal-NEITHER formulas without tuning. Historical support alone is not fresh support.\n", encoding="utf-8")
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_trade_ledger.csv", all_trades)
        write_csv(archive / "03_overlap_skip_ledger.csv", all_skips)
        (archive / "04_contract_copy.json").write_text(CONTRACT.read_text(encoding="utf-8"), encoding="utf-8")
        (archive / "05_data_quality.json").write_text(json.dumps({"feature_path": str(feature_path), "feature_sha256": EXPECTED_FEATURE_SHA256, "feature_rows": EXPECTED_FEATURE_ROWS, "frozen_m1_verified": True, "closed_rows_contract": True, "time_basis": "MT5_SERVER_TIME", "nearest_m1_fallback": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "06_audit.log").write_text("\n".join(["status=PASS_PREREGISTERED_LOW_ATR_EVALUATION_AUDIT_ONLY", "formula_change=false", "threshold_change=false", "horizon_change=false", "M10W26_modified=false", "discord_send=false", "mt5_order=false", ""]), encoding="utf-8")
        names = [path.name for path in archive.iterdir() if path.is_file()]
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(names):
                zf.write(archive / name, name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print("[M10W29 PASS] preregistered low-ATR evaluation complete")
        for family, result in family_results.items():
            print(f"  {family}: {result['classification']} resolved={result['resolved_count']}")
        print(f"[OUTPUT] {latest / '99_UPLOAD_PACKAGE.zip'}")
        return 0
    except Exception as exc:
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "LATEST_ERROR.txt").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        print(f"[M10W29 BLOCKED] {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
