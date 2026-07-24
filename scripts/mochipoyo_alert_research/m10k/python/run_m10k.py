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
M10A_DIR = MR / "m10a" / "python"
M10I_DIR = MR / "m10i" / "python"
M10J_DIR = MR / "m10j" / "python"
for p in (M10A_DIR, M10I_DIR, M10J_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import frozen_core as c
import run_independent_m15_short_archetype_discovery as m10i
import run_m10j as m10j

STAGE = "M10K_M15_SHORT_EXIT_LOSS_TAIL_AUDIT"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10k_m15_short_exit_loss_tail_audit_contract_20260725.json"
POINT = c.POINT
TP_GRID = (1.0, 1.5, 2.0, 2.5)
SL_GRID = (0.75, 1.0, 1.25, 1.5)
HOLD_GRID = (120, 240, 360)


class AuditError(RuntimeError):
    pass


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA/TEMP unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def resolve_data_root(local: Path) -> Path:
    override = os.environ.get("M10K_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    return m10j.resolve_data_root(local)


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


def metric(values: list[float]) -> dict[str, Any]:
    return c.metrics_from_values(values)


def flatten(prefix: str, values: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in values.items()}


def build_seed_rows(bars: dict[str, list[c.Bar]]) -> list[dict[str, Any]]:
    rows = m10j.build_feature_rows(bars)
    f15 = m10i.precompute(bars["M15"])
    atr_by_decision: dict[datetime, float] = {}
    for i in range(120, len(bars["M15"]) - 1):
        atr = f15["atr14"][i]
        if atr is None or not math.isfinite(float(atr)) or float(atr) <= 0:
            continue
        atr_by_decision[bars["M15"][i + 1].time] = float(atr)
    selected: list[dict[str, Any]] = []
    for row in rows:
        if float(row["h4_ema20_30_bps"]) < 37.61355979:
            continue
        if float(row["h1_atr_pct100"]) < 0.8:
            continue
        atr = atr_by_decision.get(row["decision"])
        if atr is None:
            continue
        selected.append({**row, "entry_atr14": atr})
    selected.sort(key=lambda row: row["decision"])
    return selected


def simulate_one(
    seed_rows: list[dict[str, Any]],
    m1: list[c.Bar],
    *,
    tp_atr: float,
    sl_atr: float,
    max_hold: int,
    fixed_spread: float | None,
    allowed_years: set[int],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    index_by_time = {bar.time: idx for idx, bar in enumerate(m1)}
    trades: list[dict[str, Any]] = []
    blocked_until: datetime | None = None
    quality = {"missing_entry": 0, "missing_timeout": 0, "path_gap": 0}
    for seed in seed_rows:
        decision = seed["decision"]
        if int(seed["year"]) not in allowed_years:
            continue
        if blocked_until is not None and decision < blocked_until:
            continue
        entry_idx = index_by_time.get(decision)
        if entry_idx is None:
            quality["missing_entry"] += 1
            continue
        timeout_time = decision + timedelta(minutes=max_hold)
        timeout_idx = index_by_time.get(timeout_time)
        if timeout_idx is None:
            quality["missing_timeout"] += 1
            continue
        # Refuse to infer through any missing M1 minute inside the trade path.
        expected_bars = max_hold + 1
        if timeout_idx - entry_idx + 1 != expected_bars:
            quality["path_gap"] += 1
            continue
        entry_bid = float(m1[entry_idx].open)
        atr = float(seed["entry_atr14"])
        tp_level_ask = entry_bid - tp_atr * atr
        sl_level_ask = entry_bid + sl_atr * atr
        exit_time = timeout_time
        exit_ask: float | None = None
        exit_reason = "TIMEOUT"
        for idx in range(entry_idx, timeout_idx + 1):
            bar = m1[idx]
            spread_usd = float(fixed_spread) if fixed_spread is not None else float(bar.spread) * POINT
            ask_low = float(bar.low) + spread_usd
            ask_high = float(bar.high) + spread_usd
            hit_sl = ask_high >= sl_level_ask
            hit_tp = ask_low <= tp_level_ask
            if hit_sl:
                exit_time = bar.time
                exit_ask = sl_level_ask
                exit_reason = "SL" if not hit_tp else "SL_SAME_BAR_PRIORITY"
                break
            if hit_tp:
                exit_time = bar.time
                exit_ask = tp_level_ask
                exit_reason = "TP"
                break
        if exit_ask is None:
            timeout_bar = m1[timeout_idx]
            spread_usd = float(fixed_spread) if fixed_spread is not None else float(timeout_bar.spread) * POINT
            exit_ask = float(timeout_bar.open) + spread_usd
        ret = c.directional_return("SHORT", entry_bid, exit_ask)
        trades.append({
            "entry_time": decision.strftime(c.TIME_FORMAT),
            "exit_time": exit_time.strftime(c.TIME_FORMAT),
            "year": int(seed["year"]),
            "tp_atr": tp_atr,
            "sl_atr": sl_atr,
            "max_hold_minutes": max_hold,
            "exit_reason": exit_reason,
            "return_bps": ret,
        })
        blocked_until = exit_time
    return trades, quality


def evaluate_cell(seed_rows: list[dict[str, Any]], m1: list[c.Bar], tp: float, sl: float, hold: int) -> dict[str, Any]:
    result: dict[str, Any] = {"tp_atr": tp, "sl_atr": sl, "max_hold_minutes": hold}
    split_years = {
        "train": {2023, 2024},
        "val2025": {2025},
        "test2026": {2026},
        "all": {2023, 2024, 2025, 2026},
    }
    for name, years in split_years.items():
        actual, quality = simulate_one(seed_rows, m1, tp_atr=tp, sl_atr=sl, max_hold=hold, fixed_spread=None, allowed_years=years)
        fixed, fixed_quality = simulate_one(seed_rows, m1, tp_atr=tp, sl_atr=sl, max_hold=hold, fixed_spread=0.20, allowed_years=years)
        result.update(flatten(name, metric([float(row["return_bps"]) for row in actual])))
        result.update(flatten(f"fixed0p20_{name}", metric([float(row["return_bps"]) for row in fixed])))
        result[f"{name}_missing_entry"] = quality["missing_entry"]
        result[f"{name}_missing_timeout"] = quality["missing_timeout"]
        result[f"{name}_path_gap"] = quality["path_gap"]
        result[f"fixed0p20_{name}_path_gap"] = fixed_quality["path_gap"]
        if name == "all":
            reasons: dict[str, int] = {}
            for row in actual:
                reasons[row["exit_reason"]] = reasons.get(row["exit_reason"], 0) + 1
            result["all_exit_reason_counts_json"] = json.dumps(reasons, sort_keys=True)
    train_count = int(result.get("train_count") or 0)
    train_pf = result.get("train_profit_factor_bps")
    result["eligible_discovery"] = bool(train_count >= 40 and train_pf is not None)
    return result


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10K contract")
        local = local_root()
        data_root = resolve_data_root(local)
        paths: dict[str, Path] = {}
        hashes: dict[str, str] = {}
        for tf, (filename, expected) in c.EXPECTED_FILES.items():
            p = data_root / filename
            if not p.is_file():
                raise AuditError(f"missing frozen GOLD file: {p}")
            actual = c.sha256(p)
            if actual != expected:
                raise AuditError(f"SHA256 mismatch for {filename}: {actual}")
            paths[tf] = p
            hashes[tf] = actual
        bars = {tf: c.load_bars(p) for tf, p in paths.items()}
        seed_rows = build_seed_rows(bars)
        cells: list[dict[str, Any]] = []
        for tp in TP_GRID:
            for sl in SL_GRID:
                for hold in HOLD_GRID:
                    cells.append(evaluate_cell(seed_rows, bars["M1"], tp, sl, hold))
        eligible = [row for row in cells if row["eligible_discovery"]]
        eligible.sort(key=lambda row: (
            float(row.get("train_profit_factor_bps") or -math.inf),
            float(row.get("train_net_bps") or -math.inf),
            -float(row.get("train_max_drawdown_bps") or math.inf),
        ), reverse=True)
        shortlist = [{"discovery_rank": idx + 1, **row} for idx, row in enumerate(eligible[:20])]
        robust: list[dict[str, Any]] = []
        stable: list[dict[str, Any]] = []
        for row in shortlist:
            pfs = [row.get("train_profit_factor_bps"), row.get("val2025_profit_factor_bps"), row.get("test2026_profit_factor_bps")]
            counts = [int(row.get("train_count") or 0), int(row.get("val2025_count") or 0), int(row.get("test2026_count") or 0)]
            if all(pf is not None and float(pf) > 1.0 for pf in pfs):
                stable.append(row)
            if (
                counts[0] >= 40 and counts[1] >= 20 and counts[2] >= 15
                and all(pf is not None and float(pf) >= 2.0 for pf in pfs)
                and row.get("fixed0p20_all_profit_factor_bps") is not None
                and float(row["fixed0p20_all_profit_factor_bps"]) > 1.0
            ):
                robust.append(row)
        best_min = sorted(
            shortlist,
            key=lambda row: min(float(row.get("train_profit_factor_bps") or 0), float(row.get("val2025_profit_factor_bps") or 0), float(row.get("test2026_profit_factor_bps") or 0)),
            reverse=True,
        )[:10]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_HISTORICAL_EXIT_LOSS_TAIL_AUDIT_ONLY",
            "run_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "seed": {
                "candidate_id": "M10J_C0212",
                "formula": "h4_ema20_30_bps >= 37.61355979 AND h1_atr_pct100 >= 0.8",
                "seed_decision_count": len(seed_rows),
                "entry_formula_changed": False,
            },
            "grid_cell_count": len(cells),
            "discovery_eligible_count": len(eligible),
            "frozen_shortlist_count": len(shortlist),
            "all_three_split_pf_gt_1_count": len(stable),
            "robust_pf2_candidate_count": len(robust),
            "best_min_split_candidates": best_min,
            "robust_pf2_candidates": robust,
            "split_contract": contract["split_contract"],
            "interpretation": "Historical research-exposed exit optimization only; no forward approval even if PF2 is reached.",
            "guardrails": contract["safety"],
        }
        out_root = local / "outputs" / "M10K"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = out_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10K freezes the M10J C0212 SHORT entry trigger and varies only causal ATR TP/SL/max-hold exits. Historical audit-only; no forward-system modification.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_all_exit_grid_results.csv", cells)
        write_csv(archive / "03_discovery_frozen_shortlist.csv", shortlist)
        write_csv(archive / "04_robust_pf2_candidates.csv", robust)
        write_csv(archive / "05_best_min_split_candidates.csv", best_min)
        (archive / "06_data_quality.json").write_text(json.dumps({
            "frozen_hashes": hashes,
            "newest_row_contract": "CLOSED",
            "time_basis": "MT5 server time",
            "nearest_m1_fallback": False,
            "exact_m1_entry_only": True,
            "M1_path_required_contiguous": True,
            "same_bar_priority": "SL_FIRST_CONSERVATIVE",
            "actual_spread_path": True,
            "fixed_spread_path_usd": 0.20,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_audit.log").write_text("\n".join([
            "status=PASS_HISTORICAL_EXIT_LOSS_TAIL_AUDIT_ONLY",
            f"seed_decisions={len(seed_rows)}",
            f"grid_cells={len(cells)}",
            f"shortlist={len(shortlist)}",
            f"stable_all_split_pf_gt1={len(stable)}",
            f"robust_pf2={len(robust)}",
            "entry_formula_changed=false",
            "m7c_modified_or_reset=false",
            "m10b_modified_or_reset=false",
            "m10e_modified_or_reset=false",
            "discord_send=false",
            "mt5_order=false",
            "live_ready=false",
            "final_signal=false",
            "",
        ]), encoding="utf-8")
        latest = out_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_all_exit_grid_results.csv", "03_discovery_frozen_shortlist.csv", "04_robust_pf2_candidates.csv", "05_best_min_split_candidates.csv", "06_data_quality.json", "07_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)
        print("[M10K PASS] M15 SHORT exit/loss-tail audit completed")
        print(f"[RESULT] grid={len(cells)} stable={len(stable)} robust_pf2={len(robust)}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10K BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] M7C/M10B/M10E and all frozen starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
