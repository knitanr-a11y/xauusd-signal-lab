from __future__ import annotations

import bisect
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
for path in (M10A_DIR, M10I_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import frozen_core as c
import payoff_rules as pay
import run_independent_m15_short_archetype_discovery as m10i

STAGE = "M10J_INDEPENDENT_M15_SHORT_CAUSAL_FEATURE_MINING"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10j_independent_m15_short_feature_mining_contract_20260725.json"
HORIZONS = (60, 120, 240)
QUANTILES = (0.10, 0.20, 0.30, 0.70, 0.80, 0.90)
POINT = c.POINT
MIN_TRAIN = 40
TOP_SINGLES_FOR_PAIRS = 30
SHORTLIST_PER_HORIZON = 100


class AuditError(RuntimeError):
    pass


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA/TEMP unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def resolve_data_root(local: Path) -> Path:
    override = os.environ.get("M10J_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata = local / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not metadata.is_file():
        raise AuditError("M8B symbol metadata unavailable; set M10J_GOLD_DATA_ROOT")
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    root = str(payload.get("mt5_files_root", "")).strip()
    if not root:
        raise AuditError("mt5_files_root missing in M8B metadata")
    return Path(root) / "gold_v3_2023_2026"


def qtile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = q * (len(ordered) - 1)
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    w = pos - lo
    return ordered[lo] * (1.0 - w) + ordered[hi] * w


def volume_ratio20(bars: list[c.Bar]) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    rolling = 0.0
    for i, bar in enumerate(bars):
        rolling += float(bar.tick_volume)
        if i >= 20:
            rolling -= float(bars[i - 20].tick_volume)
        if i >= 19 and rolling > 0:
            out[i] = float(bar.tick_volume) / (rolling / 20.0)
    return out


def safe(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def bps(a: float, b: float, denominator: float) -> float:
    return (a - b) / max(abs(denominator), 1e-12) * 10000.0


def build_feature_rows(bars: dict[str, list[c.Bar]]) -> list[dict[str, Any]]:
    f15 = m10i.precompute(bars["M15"])
    fh1 = m10i.precompute(bars["H1"])
    fh4 = m10i.precompute(bars["H4"])
    vol15 = volume_ratio20(bars["M15"])
    h1_close_times = [bar.time + timedelta(hours=1) for bar in bars["H1"]]
    h4_close_times = [bar.time + timedelta(hours=4) for bar in bars["H4"]]
    rows: list[dict[str, Any]] = []
    for i in range(120, len(bars["M15"]) - 1):
        decision = bars["M15"][i + 1].time
        if decision.year < 2023 or decision.year > 2026:
            continue
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        ih4 = bisect.bisect_right(h4_close_times, decision) - 1
        if ih1 < 50 or ih4 < 50:
            continue
        bar = bars["M15"][i]
        prev = bars["M15"][i - 1]
        atr = safe(f15["atr14"][i])
        atr_pct = safe(f15["atr_pct100"][i])
        rci = safe(f15["rci9"][i])
        rci_prev = safe(f15["rci9"][i - 1])
        ret3 = safe(f15["ret3"][i])
        ret5 = safe(f15["ret5"][i])
        vr = safe(vol15[i])
        if None in (atr, atr_pct, rci, rci_prev, ret3, ret5, vr) or atr is None or atr <= 0:
            continue
        rng = bar.high - bar.low
        if rng <= 0:
            continue
        e20 = float(f15["ema20"][i]); e30 = float(f15["ema30"][i]); e40 = float(f15["ema40"][i])
        pe20 = float(f15["ema20"][i - 1])
        mline = float(f15["macd_line"][i]); mhist = float(f15["macd_hist"][i]); pmhist = float(f15["macd_hist"][i - 1])
        h1close = bars["H1"][ih1].close
        h1e20 = float(fh1["ema20"][ih1]); h1e30 = float(fh1["ema30"][ih1]); h1e40 = float(fh1["ema40"][ih1])
        h1hist = float(fh1["macd_hist"][ih1]); h1phist = float(fh1["macd_hist"][ih1 - 1])
        h1rci = safe(fh1["rci9"][ih1]); h1atrp = safe(fh1["atr_pct100"][ih1])
        h4close = bars["H4"][ih4].close
        h4e20 = float(fh4["ema20"][ih4]); h4e30 = float(fh4["ema30"][ih4]); h4e40 = float(fh4["ema40"][ih4])
        h4hist = float(fh4["macd_hist"][ih4]); h4phist = float(fh4["macd_hist"][ih4 - 1])
        h4rci = safe(fh4["rci9"][ih4]); h4atrp = safe(fh4["atr_pct100"][ih4])
        if None in (h1rci, h1atrp, h4rci, h4atrp):
            continue
        rows.append({
            "decision": decision,
            "year": decision.year,
            "m15_rci9": float(rci),
            "m15_rci9_delta": float(rci) - float(rci_prev),
            "m15_atr_pct100": float(atr_pct),
            "m15_ret3_bps": float(ret3),
            "m15_ret5_bps": float(ret5),
            "m15_body_fraction": max(0.0, (bar.open - bar.close) / rng),
            "m15_close_position": (bar.close - bar.low) / rng,
            "m15_close_minus_ema20_atr": (bar.close - e20) / float(atr),
            "m15_high_minus_ema20_atr": (bar.high - e20) / float(atr),
            "m15_ema20_slope_atr": (e20 - pe20) / float(atr),
            "m15_ema20_30_bps": bps(e20, e30, bar.close),
            "m15_ema30_40_bps": bps(e30, e40, bar.close),
            "m15_macd_line_bps": mline,
            "m15_macd_hist_bps": mhist,
            "m15_macd_hist_slope": mhist - pmhist,
            "m15_volume_ratio20": float(vr),
            "h1_ema20_30_bps": bps(h1e20, h1e30, h1close),
            "h1_ema30_40_bps": bps(h1e30, h1e40, h1close),
            "h1_macd_hist_bps": h1hist,
            "h1_macd_hist_slope": h1hist - h1phist,
            "h1_rci9": float(h1rci),
            "h1_atr_pct100": float(h1atrp),
            "h4_ema20_30_bps": bps(h4e20, h4e30, h4close),
            "h4_ema30_40_bps": bps(h4e30, h4e40, h4close),
            "h4_macd_hist_bps": h4hist,
            "h4_macd_hist_slope": h4hist - h4phist,
            "h4_rci9": float(h4rci),
            "h4_atr_pct100": float(h4atrp),
        })
    return rows


FEATURES = [
    "m15_rci9", "m15_rci9_delta", "m15_atr_pct100", "m15_ret3_bps", "m15_ret5_bps",
    "m15_body_fraction", "m15_close_position", "m15_close_minus_ema20_atr", "m15_high_minus_ema20_atr",
    "m15_ema20_slope_atr", "m15_ema20_30_bps", "m15_ema30_40_bps", "m15_macd_line_bps",
    "m15_macd_hist_bps", "m15_macd_hist_slope", "m15_volume_ratio20", "h1_ema20_30_bps",
    "h1_ema30_40_bps", "h1_macd_hist_bps", "h1_macd_hist_slope", "h1_rci9", "h1_atr_pct100",
    "h4_ema20_30_bps", "h4_ema30_40_bps", "h4_macd_hist_bps", "h4_macd_hist_slope", "h4_rci9", "h4_atr_pct100",
]


def build_conditions(train_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for feature in FEATURES:
        values = [float(row[feature]) for row in train_rows]
        thresholds = sorted({qtile(values, q) for q in QUANTILES})
        for threshold in thresholds:
            for op in ("<=", ">="):
                cid = f"{feature}{op}{threshold:.10g}"
                conditions.append({"id": cid, "feature": feature, "op": op, "threshold": threshold})
    return conditions


def condition_match(row: dict[str, Any], cond: dict[str, Any]) -> bool:
    value = float(row[cond["feature"]])
    return value <= float(cond["threshold"]) if cond["op"] == "<=" else value >= float(cond["threshold"])


def outcome_cache(rows: list[dict[str, Any]], m1: list[c.Bar]) -> dict[int, dict[int, tuple[float, float, datetime] | None]]:
    m1_by_time = {bar.time: bar for bar in m1}
    out: dict[int, dict[int, tuple[float, float, datetime] | None]] = {h: {} for h in HORIZONS}
    for idx, row in enumerate(rows):
        decision = row["decision"]
        entry = m1_by_time.get(decision)
        if entry is None:
            for h in HORIZONS:
                out[h][idx] = None
            continue
        for h in HORIZONS:
            exit_time = decision + timedelta(minutes=h)
            exit_bar = m1_by_time.get(exit_time)
            if exit_bar is None:
                out[h][idx] = None
                continue
            actual_exit_ask = float(exit_bar.open) + float(exit_bar.spread) * POINT
            fixed_exit_ask = float(exit_bar.open) + 0.20
            out[h][idx] = (
                c.directional_return("SHORT", float(entry.open), actual_exit_ask),
                c.directional_return("SHORT", float(entry.open), fixed_exit_ask),
                exit_time,
            )
    return out


def selected_returns(indices: set[int], rows: list[dict[str, Any]], outcomes: dict[int, tuple[float, float, datetime] | None], allowed_years: set[int] | None) -> tuple[list[float], list[float]]:
    actual: list[float] = []
    fixed: list[float] = []
    blocked_until: datetime | None = None
    for idx in sorted(indices, key=lambda x: rows[x]["decision"]):
        row = rows[idx]
        if allowed_years is not None and int(row["year"]) not in allowed_years:
            continue
        decision = row["decision"]
        if blocked_until is not None and decision < blocked_until:
            continue
        item = outcomes.get(idx)
        if item is None:
            continue
        a, f, exit_time = item
        actual.append(a); fixed.append(f); blocked_until = exit_time
    return actual, fixed


def metric_values(values: list[float]) -> dict[str, Any]:
    return c.metrics_from_values(values)


def discovery_score(indices: set[int], rows: list[dict[str, Any]], outcomes: dict[int, tuple[float, float, datetime] | None]) -> dict[str, Any]:
    actual, fixed = selected_returns(indices, rows, outcomes, {2023, 2024})
    metrics = metric_values(actual)
    fixed_metrics = metric_values(fixed)
    return {"metrics": metrics, "fixed": fixed_metrics}


def flatten(prefix: str, value: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{k}": v for k, v in value.items()}


def formula_text(conds: list[dict[str, Any]]) -> str:
    return " AND ".join(f"{cnd['feature']} {cnd['op']} {float(cnd['threshold']):.10g}" for cnd in conds)


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
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10J contract")
        local = local_root(); data_root = resolve_data_root(local)
        paths: dict[str, Path] = {}; hashes: dict[str, str] = {}
        for tf, (filename, expected) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise AuditError(f"missing frozen GOLD file: {path}")
            actual = c.sha256(path)
            if actual != expected:
                raise AuditError(f"SHA256 mismatch for {filename}: {actual}")
            paths[tf] = path; hashes[tf] = actual
        bars = {tf: c.load_bars(path) for tf, path in paths.items()}
        rows = build_feature_rows(bars)
        train_indices = {i for i, row in enumerate(rows) if int(row["year"]) in (2023, 2024)}
        train_rows = [rows[i] for i in sorted(train_indices)]
        conditions = build_conditions(train_rows)
        masks_all: dict[str, set[int]] = {}
        masks_train: dict[str, set[int]] = {}
        by_id = {cond["id"]: cond for cond in conditions}
        for cond in conditions:
            mask = {i for i, row in enumerate(rows) if condition_match(row, cond)}
            masks_all[cond["id"]] = mask
            masks_train[cond["id"]] = mask & train_indices
        outcomes = outcome_cache(rows, bars["M1"])
        all_shortlists: list[dict[str, Any]] = []
        single_rows: list[dict[str, Any]] = []
        for horizon in HORIZONS:
            singles: list[dict[str, Any]] = []
            for cond in conditions:
                scored = discovery_score(masks_train[cond["id"]], rows, outcomes[horizon])
                m = scored["metrics"]
                if int(m.get("count") or 0) < MIN_TRAIN:
                    continue
                record = {
                    "horizon_minutes": horizon,
                    "formula_type": "SINGLE",
                    "condition_ids": cond["id"],
                    "formula": formula_text([cond]),
                    **flatten("train", m),
                    **flatten("fixed0p20_train", scored["fixed"]),
                }
                singles.append(record); single_rows.append(record)
            singles.sort(key=lambda r: (float(r.get("train_profit_factor_bps") or -math.inf), float(r.get("train_net_bps") or -math.inf), int(r.get("train_count") or 0)), reverse=True)
            top_for_pairs = singles[:TOP_SINGLES_FOR_PAIRS]
            candidates = list(singles)
            seen_pairs: set[tuple[str, str]] = set()
            for left_pos in range(len(top_for_pairs)):
                left_id = str(top_for_pairs[left_pos]["condition_ids"])
                left = by_id[left_id]
                for right_pos in range(left_pos + 1, len(top_for_pairs)):
                    right_id = str(top_for_pairs[right_pos]["condition_ids"])
                    right = by_id[right_id]
                    if left["feature"] == right["feature"]:
                        continue
                    pair_key = tuple(sorted((left_id, right_id)))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    mask = masks_train[left_id] & masks_train[right_id]
                    scored = discovery_score(mask, rows, outcomes[horizon])
                    m = scored["metrics"]
                    if int(m.get("count") or 0) < MIN_TRAIN:
                        continue
                    candidates.append({
                        "horizon_minutes": horizon,
                        "formula_type": "PAIR",
                        "condition_ids": " || ".join(pair_key),
                        "formula": formula_text([left, right]),
                        **flatten("train", m),
                        **flatten("fixed0p20_train", scored["fixed"]),
                    })
            candidates.sort(key=lambda r: (float(r.get("train_profit_factor_bps") or -math.inf), float(r.get("train_net_bps") or -math.inf), int(r.get("train_count") or 0)), reverse=True)
            for rank, candidate in enumerate(candidates[:SHORTLIST_PER_HORIZON], start=1):
                candidate = dict(candidate); candidate["discovery_rank"] = rank
                all_shortlists.append(candidate)
        evaluated: list[dict[str, Any]] = []
        robust: list[dict[str, Any]] = []
        for num, candidate in enumerate(all_shortlists, start=1):
            horizon = int(candidate["horizon_minutes"])
            ids = str(candidate["condition_ids"]).split(" || ")
            mask = set(range(len(rows)))
            for cid in ids:
                mask &= masks_all[cid]
            full_actual, full_fixed = selected_returns(mask, rows, outcomes[horizon], None)
            row: dict[str, Any] = {
                "candidate_id": f"M10J_C{num:04d}",
                **candidate,
            }
            # Re-run each split independently to avoid cross-split one-position carryover.
            for split_name, years in (("train", {2023, 2024}), ("val2025", {2025}), ("test2026", {2026}), ("all", None)):
                a, f = selected_returns(mask, rows, outcomes[horizon], years)
                row.update(flatten(split_name, metric_values(a)))
                row.update(flatten(f"fixed0p20_{split_name}", metric_values(f)))
            train_pf = row.get("train_profit_factor_bps"); val_pf = row.get("val2025_profit_factor_bps"); test_pf = row.get("test2026_profit_factor_bps")
            robust_flag = bool(
                int(row.get("train_count") or 0) >= 40 and int(row.get("val2025_count") or 0) >= 20 and int(row.get("test2026_count") or 0) >= 15
                and train_pf is not None and float(train_pf) >= 2.0
                and val_pf is not None and float(val_pf) >= 2.0
                and test_pf is not None and float(test_pf) >= 2.0
                and float(row.get("train_net_bps") or 0) > 0 and float(row.get("val2025_net_bps") or 0) > 0 and float(row.get("test2026_net_bps") or 0) > 0
                and row.get("fixed0p20_all_profit_factor_bps") is not None and float(row["fixed0p20_all_profit_factor_bps"]) > 1.0
            )
            row["robust_pf2"] = robust_flag
            evaluated.append(row)
            if robust_flag:
                robust.append(row)
        evaluated.sort(key=lambda r: (int(r["horizon_minutes"]), int(r["discovery_rank"])))
        robust.sort(key=lambda r: (float(r.get("test2026_profit_factor_bps") or -math.inf), float(r.get("val2025_profit_factor_bps") or -math.inf), float(r.get("train_profit_factor_bps") or -math.inf)), reverse=True)
        positive_all_splits = [r for r in evaluated if all(r.get(k) is not None and float(r[k]) > 1.0 for k in ("train_profit_factor_bps", "val2025_profit_factor_bps", "test2026_profit_factor_bps"))]
        best_min = sorted(evaluated, key=lambda r: min(float(r.get("train_profit_factor_bps") or -math.inf), float(r.get("val2025_profit_factor_bps") or -math.inf), float(r.get("test2026_profit_factor_bps") or -math.inf)), reverse=True)[:20]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_HISTORICAL_CAUSAL_FEATURE_MINING_ONLY",
            "run_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "candidate_universe": "all causal M15 decisions; Mochipoyo-independent",
            "feature_row_count": len(rows),
            "feature_count": len(FEATURES),
            "generated_condition_count": len(conditions),
            "frozen_shortlist_count": len(evaluated),
            "robust_pf2_candidate_count": len(robust),
            "all_three_split_pf_gt_1_count": len(positive_all_splits),
            "best_min_split_pf_candidates": best_min,
            "robust_pf2_candidates": robust[:20],
            "split_contract": {"discovery": "2023-2024", "validation": "2025", "final_test": "2026 through 2026-06-19"},
            "anti_leakage": {"condition_thresholds_from_discovery_only": True, "pairing_and_shortlist_ranking_from_discovery_only": True, "validation_or_test_used_to_generate_or_rank": False},
            "guardrails": {"audit_only": True, "m7c_modified_or_reset": False, "m10b_modified_or_reset": False, "m10e_modified_or_reset": False, "historical_backfill": False, "discord_send": False, "mt5_order": False, "live_ready": False, "final_signal": False, "automatic_live_promotion": False},
        }
        output_root = local / "outputs" / "M10J"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp; archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text("M10J independent M15 SHORT causal feature mining. Formula generation/ranking uses 2023-2024 only. 2025 and 2026 are locked validation/final-test splits. Historical audit-only.\n", encoding="utf-8")
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_frozen_shortlist_results.csv", evaluated)
        write_csv(archive / "03_robust_pf2_candidates.csv", robust)
        write_csv(archive / "04_best_min_split_pf_candidates.csv", best_min)
        write_csv(archive / "05_discovery_single_conditions.csv", single_rows)
        (archive / "06_data_quality.json").write_text(json.dumps({"frozen_hashes": hashes, "newest_row_contract": "CLOSED", "time_basis": "MT5 server time", "nearest_m1_fallback": False, "exact_m1_entry_and_exit_only": True, "actual_spread_at_short_exit": True, "fixed_spread_sensitivity_usd": 0.20}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_audit.log").write_text("\n".join([
            "status=PASS_HISTORICAL_CAUSAL_FEATURE_MINING_ONLY",
            f"feature_rows={len(rows)}", f"feature_count={len(FEATURES)}", f"generated_conditions={len(conditions)}", f"frozen_shortlist={len(evaluated)}", f"robust_pf2={len(robust)}", f"all_three_split_pf_gt_1={len(positive_all_splits)}",
            "thresholds_from_2023_2024_only=true", "validation_or_test_used_to_generate_or_rank=false", "m7c_modified_or_reset=false", "m10b_modified_or_reset=false", "m10e_modified_or_reset=false", "discord_send=false", "mt5_order=false", "live_ready=false", "final_signal=false", ""
        ]), encoding="utf-8")
        latest = output_root / "LATEST"
        if latest.exists(): shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_frozen_shortlist_results.csv", "03_robust_pf2_candidates.csv", "04_best_min_split_pf_candidates.csv", "05_discovery_single_conditions.csv", "06_data_quality.json", "07_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names: zf.write(latest / name, arcname=name)
        print("[M10J PASS] independent M15 SHORT causal feature mining completed")
        print(f"[RESULT] shortlist={len(evaluated)} robust_pf2={len(robust)} all_split_pf_gt1={len(positive_all_splits)}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10J BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] M7C/M10B/M10E and all forward starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
