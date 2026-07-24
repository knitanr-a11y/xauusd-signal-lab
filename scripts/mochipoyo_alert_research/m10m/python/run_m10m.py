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
from itertools import combinations
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
M10A_DIR = MR / "m10a" / "python"
M10I_DIR = MR / "m10i" / "python"
M10L_DIR = MR / "m10l" / "python"
for path in (M10A_DIR, M10I_DIR, M10L_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import frozen_core as c
import run_independent_m15_short_archetype_discovery as m10i
import run_m10l as m10l

STAGE = "M10M_M5_SHORT_CAUSAL_FEATURE_MINING"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10m_m5_short_causal_feature_mining_contract_20260725.json"
HORIZONS = (60, 120, 240)
QUANTILES = (0.10, 0.20, 0.30, 0.70, 0.80, 0.90)
MIN_TRAIN = 80
TOP_SINGLES_FOR_PAIRS = 30
SHORTLIST_PER_HORIZON = 100
POINT = c.POINT


class AuditError(RuntimeError):
    pass


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA/TEMP unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def resolve_data_root(local: Path) -> Path:
    override = os.environ.get("M10M_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata = local / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not metadata.is_file():
        raise AuditError("M8B symbol metadata unavailable; set M10M_GOLD_DATA_ROOT")
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    root = str(payload.get("mt5_files_root", "")).strip()
    if not root:
        raise AuditError("mt5_files_root missing in M8B metadata")
    return Path(root) / "gold_v3_2023_2026"


def build_feature_rows(bars: dict[str, list[c.Bar]]) -> list[dict[str, Any]]:
    fm5 = m10i.precompute(bars["M5"])
    fm15 = m10i.precompute(bars["M15"])
    fh1 = m10i.precompute(bars["H1"])
    fh4 = m10i.precompute(bars["H4"])
    vol_m5 = m10l.volume_ratio20(bars["M5"])
    m15_close = [bar.time + timedelta(minutes=15) for bar in bars["M15"]]
    h1_close = [bar.time + timedelta(hours=1) for bar in bars["H1"]]
    h4_close = [bar.time + timedelta(hours=4) for bar in bars["H4"]]

    rows: list[dict[str, Any]] = []
    for i in range(120, len(bars["M5"]) - 1):
        decision = bars["M5"][i + 1].time
        if decision.year < 2023 or decision.year > 2026:
            continue
        im15 = bisect.bisect_right(m15_close, decision) - 1
        ih1 = bisect.bisect_right(h1_close, decision) - 1
        ih4 = bisect.bisect_right(h4_close, decision) - 1
        if im15 < 50 or ih1 < 50 or ih4 < 50:
            continue

        bar = bars["M5"][i]
        atr = m10l.safe(fm5["atr14"][i]); atrp = m10l.safe(fm5["atr_pct100"][i])
        rci = m10l.safe(fm5["rci9"][i]); prci = m10l.safe(fm5["rci9"][i - 1])
        ret3 = m10l.safe(fm5["ret3"][i]); ret5 = m10l.safe(fm5["ret5"][i]); vr = m10l.safe(vol_m5[i])
        if None in (atr, atrp, rci, prci, ret3, ret5, vr) or atr is None or atr <= 0:
            continue
        rng = float(bar.high - bar.low)
        if rng <= 0:
            continue

        e20 = float(fm5["ema20"][i]); e30 = float(fm5["ema30"][i]); e40 = float(fm5["ema40"][i])
        pe20 = float(fm5["ema20"][i - 1])
        mline = float(fm5["macd_line"][i]); mhist = float(fm5["macd_hist"][i]); pmhist = float(fm5["macd_hist"][i - 1])

        def ctx(tf: str, idx: int, f: dict[str, Any]) -> dict[str, float] | None:
            close = float(bars[tf][idx].close)
            e20x = float(f["ema20"][idx]); e30x = float(f["ema30"][idx]); e40x = float(f["ema40"][idx])
            hist = float(f["macd_hist"][idx]); phist = float(f["macd_hist"][idx - 1])
            rcix = m10l.safe(f["rci9"][idx]); atrpx = m10l.safe(f["atr_pct100"][idx])
            if rcix is None or atrpx is None:
                return None
            return {
                "ema20_30_bps": m10l.bps(e20x, e30x, close),
                "ema30_40_bps": m10l.bps(e30x, e40x, close),
                "macd_hist_bps": hist,
                "macd_hist_slope": hist - phist,
                "rci9": float(rcix),
                "atr_pct100": float(atrpx),
            }

        c15 = ctx("M15", im15, fm15); c1 = ctx("H1", ih1, fh1); c4 = ctx("H4", ih4, fh4)
        if c15 is None or c1 is None or c4 is None:
            continue

        row: dict[str, Any] = {
            "decision": decision,
            "year": decision.year,
            "server_hour": decision.hour,
            "m5_rci9": float(rci),
            "m5_rci9_delta": float(rci) - float(prci),
            "m5_atr_pct100": float(atrp),
            "m5_ret3_bps": float(ret3),
            "m5_ret5_bps": float(ret5),
            "m5_body_fraction": max(0.0, (float(bar.open) - float(bar.close)) / rng),
            "m5_close_position": (float(bar.close) - float(bar.low)) / rng,
            "m5_close_minus_ema20_atr": (float(bar.close) - e20) / float(atr),
            "m5_high_minus_ema20_atr": (float(bar.high) - e20) / float(atr),
            "m5_ema20_slope_atr": (e20 - pe20) / float(atr),
            "m5_ema20_30_bps": m10l.bps(e20, e30, float(bar.close)),
            "m5_ema30_40_bps": m10l.bps(e30, e40, float(bar.close)),
            "m5_macd_line_bps": mline,
            "m5_macd_hist_bps": mhist,
            "m5_macd_hist_slope": mhist - pmhist,
            "m5_volume_ratio20": float(vr),
        }
        for prefix, values in (("m15", c15), ("h1", c1), ("h4", c4)):
            for key, value in values.items():
                row[f"{prefix}_{key}"] = value
        rows.append(row)
    return rows


FEATURES = [
    "server_hour", "m5_rci9", "m5_rci9_delta", "m5_atr_pct100", "m5_ret3_bps", "m5_ret5_bps",
    "m5_body_fraction", "m5_close_position", "m5_close_minus_ema20_atr", "m5_high_minus_ema20_atr",
    "m5_ema20_slope_atr", "m5_ema20_30_bps", "m5_ema30_40_bps", "m5_macd_line_bps",
    "m5_macd_hist_bps", "m5_macd_hist_slope", "m5_volume_ratio20",
    "m15_ema20_30_bps", "m15_ema30_40_bps", "m15_macd_hist_bps", "m15_macd_hist_slope", "m15_rci9", "m15_atr_pct100",
    "h1_ema20_30_bps", "h1_ema30_40_bps", "h1_macd_hist_bps", "h1_macd_hist_slope", "h1_rci9", "h1_atr_pct100",
    "h4_ema20_30_bps", "h4_ema30_40_bps", "h4_macd_hist_bps", "h4_macd_hist_slope", "h4_rci9", "h4_atr_pct100",
]


def build_conditions(train_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for feature in FEATURES:
        values = [float(row[feature]) for row in train_rows]
        thresholds = sorted({m10l.qtile(values, q) for q in QUANTILES})
        for threshold in thresholds:
            for op in ("<=", ">="):
                out.append({"id": f"{feature}{op}{threshold:.10g}", "feature": feature, "op": op, "threshold": threshold})
    return out


def condition_match(row: dict[str, Any], cond: dict[str, Any]) -> bool:
    value = float(row[cond["feature"]])
    return value <= float(cond["threshold"]) if cond["op"] == "<=" else value >= float(cond["threshold"])


def outcome_cache(rows: list[dict[str, Any]], m1: list[c.Bar]) -> dict[int, dict[int, tuple[float, float, datetime] | None]]:
    by_time = {bar.time: bar for bar in m1}
    out = {h: {} for h in HORIZONS}
    for idx, row in enumerate(rows):
        decision = row["decision"]
        entry = by_time.get(decision)
        for h in HORIZONS:
            if entry is None:
                out[h][idx] = None
                continue
            exit_bar = by_time.get(decision + timedelta(minutes=h))
            if exit_bar is None:
                out[h][idx] = None
                continue
            entry_bid = float(entry.open)
            out[h][idx] = (
                c.directional_return("SHORT", entry_bid, float(exit_bar.open) + float(exit_bar.spread) * POINT),
                c.directional_return("SHORT", entry_bid, float(exit_bar.open) + 0.20),
                decision + timedelta(minutes=h),
            )
    return out


def selected_returns(indices: set[int], rows: list[dict[str, Any]], outcomes: dict[int, tuple[float, float, datetime] | None], years: set[int]) -> tuple[list[float], list[float]]:
    actual: list[float] = []; fixed: list[float] = []; blocked_until: datetime | None = None
    for idx in sorted(indices, key=lambda x: rows[x]["decision"]):
        row = rows[idx]
        if int(row["year"]) not in years:
            continue
        decision = row["decision"]
        if blocked_until is not None and decision < blocked_until:
            continue
        item = outcomes.get(idx)
        if item is None:
            continue
        a, f, exit_time = item
        actual.append(float(a)); fixed.append(float(f)); blocked_until = exit_time
    return actual, fixed


def train_score(indices: set[int], rows: list[dict[str, Any]], outcomes: dict[int, tuple[float, float, datetime] | None]) -> dict[str, Any]:
    actual, fixed = selected_returns(indices, rows, outcomes, {2023, 2024})
    m = c.metrics_from_values(actual); fm = c.metrics_from_values(fixed)
    return {"count": int(m["count"]), "pf": m["profit_factor_bps"], "net": m["net_bps"], "dd": m["max_drawdown_bps"], "fixed_pf": fm["profit_factor_bps"]}


def evaluate_formula(candidate_id: str, formula_type: str, conds: list[dict[str, Any]], indices: set[int], horizon: int, rows: list[dict[str, Any]], outcomes: dict[int, tuple[float, float, datetime] | None]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "candidate_id": candidate_id, "formula_type": formula_type, "horizon_minutes": horizon,
        "conditions_json": json.dumps(conds, sort_keys=True, separators=(",", ":")),
        "formula": " AND ".join(f"{x['feature']} {x['op']} {float(x['threshold']):.10g}" for x in conds),
    }
    for name, years in (("train", {2023, 2024}), ("val2025", {2025}), ("test2026", {2026}), ("all", {2023, 2024, 2025, 2026})):
        actual, fixed = selected_returns(indices, rows, outcomes, years)
        m = c.metrics_from_values(actual); fm = c.metrics_from_values(fixed)
        for key, value in m.items(): result[f"{name}_{key}"] = value
        for key, value in fm.items(): result[f"fixed0p20_{name}_{key}"] = value
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig"); return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10M contract")
        local = local_root(); data_root = resolve_data_root(local)
        paths: dict[str, Path] = {}; hashes: dict[str, str] = {}
        for tf, (filename, expected) in c.EXPECTED_FILES.items():
            p = data_root / filename
            if not p.is_file(): raise AuditError(f"missing frozen GOLD file: {p}")
            actual = c.sha256(p)
            if actual != expected: raise AuditError(f"SHA256 mismatch for {filename}: {actual}")
            paths[tf] = p; hashes[tf] = actual
        bars = {tf: c.load_bars(p) for tf, p in paths.items()}
        rows = build_feature_rows(bars)
        train_rows = [r for r in rows if int(r["year"]) in (2023, 2024)]
        if len(train_rows) < 10000: raise AuditError(f"unexpectedly small M5 discovery rows: {len(train_rows)}")
        conditions = build_conditions(train_rows)
        matched_sets = {cond["id"]: {i for i, row in enumerate(rows) if condition_match(row, cond)} for cond in conditions}
        outcomes = outcome_cache(rows, bars["M1"])
        discovery_singles: list[dict[str, Any]] = []; frozen_specs: list[dict[str, Any]] = []
        for horizon in HORIZONS:
            scored: list[tuple[dict[str, Any], dict[str, Any], set[int]]] = []
            for cond in conditions:
                indices = matched_sets[cond["id"]]; score = train_score(indices, rows, outcomes[horizon])
                if score["count"] < MIN_TRAIN or score["pf"] is None: continue
                discovery_singles.append({"horizon_minutes": horizon, "condition_id": cond["id"], "feature": cond["feature"], "op": cond["op"], "threshold": cond["threshold"], "train_count": score["count"], "train_pf": score["pf"], "train_net_bps": score["net"], "train_max_drawdown_bps": score["dd"], "fixed0p20_train_pf": score["fixed_pf"]})
                scored.append((cond, score, indices))
            scored.sort(key=lambda x: (float(x[1]["pf"] or -math.inf), float(x[1]["net"] or -math.inf), -float(x[1]["dd"] or math.inf), int(x[1]["count"])), reverse=True)
            top = scored[:TOP_SINGLES_FOR_PAIRS]
            candidates: list[tuple[str, list[dict[str, Any]], set[int], dict[str, Any]]] = [("SINGLE", [cond], idxs, score) for cond, score, idxs in scored]
            for (a, _, ia), (b, _, ib) in combinations(top, 2):
                if a["feature"] == b["feature"]: continue
                idxs = ia & ib; score = train_score(idxs, rows, outcomes[horizon])
                if score["count"] >= MIN_TRAIN and score["pf"] is not None: candidates.append(("AND2", [a, b], idxs, score))
            candidates.sort(key=lambda x: (float(x[3]["pf"] or -math.inf), float(x[3]["net"] or -math.inf), -float(x[3]["dd"] or math.inf), int(x[3]["count"])), reverse=True)
            for rank, (ft, conds, idxs, score) in enumerate(candidates[:SHORTLIST_PER_HORIZON], 1):
                frozen_specs.append({"candidate_id": f"M10M_H{horizon}_C{rank:03d}", "formula_type": ft, "conditions": conds, "indices": idxs, "horizon": horizon, "discovery_rank": rank})
        shortlist: list[dict[str, Any]] = []; stable: list[dict[str, Any]] = []; robust: list[dict[str, Any]] = []
        for spec in frozen_specs:
            result = evaluate_formula(spec["candidate_id"], spec["formula_type"], spec["conditions"], spec["indices"], spec["horizon"], rows, outcomes[spec["horizon"]]); result["discovery_rank"] = spec["discovery_rank"]; shortlist.append(result)
            pfs = [result.get("train_profit_factor_bps"), result.get("val2025_profit_factor_bps"), result.get("test2026_profit_factor_bps")]
            counts = [int(result.get("train_count") or 0), int(result.get("val2025_count") or 0), int(result.get("test2026_count") or 0)]
            nets = [float(result.get("train_net_bps") or 0), float(result.get("val2025_net_bps") or 0), float(result.get("test2026_net_bps") or 0)]
            if all(pf is not None and float(pf) > 1.0 for pf in pfs): stable.append(result)
            if counts[0] >= 80 and counts[1] >= 40 and counts[2] >= 20 and all(pf is not None and float(pf) >= 2.0 for pf in pfs) and all(net > 0 for net in nets) and result.get("fixed0p20_all_profit_factor_bps") is not None and float(result["fixed0p20_all_profit_factor_bps"]) > 1.0: robust.append(result)
        stable.sort(key=lambda r: (min(float(r.get("train_profit_factor_bps") or 0), float(r.get("val2025_profit_factor_bps") or 0), float(r.get("test2026_profit_factor_bps") or 0)), float(r.get("all_profit_factor_bps") or 0)), reverse=True)
        robust.sort(key=lambda r: (min(float(r["train_profit_factor_bps"]), float(r["val2025_profit_factor_bps"]), float(r["test2026_profit_factor_bps"])), float(r["fixed0p20_all_profit_factor_bps"])), reverse=True)
        best_min = stable[:20] if stable else sorted(shortlist, key=lambda r: min(float(r.get("train_profit_factor_bps") or 0), float(r.get("val2025_profit_factor_bps") or 0), float(r.get("test2026_profit_factor_bps") or 0)), reverse=True)[:20]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH", "stage": STAGE, "status": "PASS_HISTORICAL_M5_SHORT_CAUSAL_FEATURE_MINING_ONLY", "run_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "candidate_universe": "all causal M5 decisions; Mochipoyo-independent; M10J/M10L-independent", "feature_row_count": len(rows), "train_2023_2024_feature_row_count": len(train_rows), "feature_count": len(FEATURES), "generated_condition_count": len(conditions), "frozen_shortlist_count": len(frozen_specs),
            "stable_all_three_split_pf_gt_1_count": len(stable), "robust_pf2_candidate_count": len(robust), "robust_pf2_candidates": robust[:20], "best_min_split_candidates": best_min,
            "reference_only": {"M10J_C0212": "kept for later portfolio/regime comparison; not used to generate M10M formulas", "M10L_H240_C056": "kept for later portfolio/regime comparison; not used to generate M10M formulas"},
            "split_contract": contract["causality"], "interpretation": "Historical audit-only. 2025/2026 were locked until formula shortlist freeze.", "guardrails": contract["safety"]
        }
        out_root = local / "outputs" / "M10M"; stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S"); archive = out_root / "archive" / stamp; archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text("M10M Mochipoyo-independent M5 SHORT causal feature mining. 2023-2024 discovery only; 2025/2026 locked until shortlist freeze. Audit-only.\n", encoding="utf-8")
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_frozen_shortlist_results.csv", shortlist); write_csv(archive / "03_robust_pf2_candidates.csv", robust); write_csv(archive / "04_best_min_split_pf_candidates.csv", best_min); write_csv(archive / "05_discovery_single_conditions.csv", discovery_singles)
        (archive / "06_data_quality.json").write_text(json.dumps({"frozen_hashes": hashes, "newest_row_contract": "CLOSED", "time_basis": "MT5 server time", "nearest_m1_fallback": False, "exact_m1_entry_and_exit_only": True, "actual_spread_at_short_exit": True, "fixed_spread_sensitivity_usd": 0.20, "formula_generation_uses_2025": False, "formula_generation_uses_2026": False, "m7c_kernel_candidate_universe": False, "m10j_seed_candidate_universe": False, "m10l_candidate_universe": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_audit.log").write_text("\n".join(["status=PASS_HISTORICAL_M5_SHORT_CAUSAL_FEATURE_MINING_ONLY", f"feature_rows={len(rows)}", f"train_rows={len(train_rows)}", f"features={len(FEATURES)}", f"conditions={len(conditions)}", f"frozen_shortlist={len(frozen_specs)}", f"stable_all_three_split_pf_gt1={len(stable)}", f"robust_pf2={len(robust)}", "formula_generation_uses_2025=false", "formula_generation_uses_2026=false", "m7c_modified_or_reset=false", "m10b_modified_or_reset=false", "m10e_modified_or_reset=false", "discord_send=false", "mt5_order=false", "live_ready=false", "final_signal=false", ""]), encoding="utf-8")
        latest = out_root / "LATEST"
        if latest.exists(): shutil.rmtree(latest)
        shutil.copytree(archive, latest); package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_frozen_shortlist_results.csv", "03_robust_pf2_candidates.csv", "04_best_min_split_pf_candidates.csv", "05_discovery_single_conditions.csv", "06_data_quality.json", "07_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names: zf.write(latest / name, arcname=name)
        print("[M10M PASS] M5 independent SHORT causal feature mining completed"); print(f"[RESULT] shortlist={len(frozen_specs)} stable={len(stable)} robust_pf2={len(robust)}"); print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10M BLOCKED] {type(exc).__name__}: {exc}"); print("[SAFE] Existing forward monitors and all frozen starts were not modified."); return 2


if __name__ == "__main__":
    raise SystemExit(main())
