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
for path in (M10A_DIR, M10I_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import frozen_core as c
import run_independent_m15_short_archetype_discovery as m10i

STAGE = "M10L_H1_SHORT_CAUSAL_FEATURE_MINING"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10l_h1_short_causal_feature_mining_contract_20260725.json"
HORIZONS = (240, 480, 720)
QUANTILES = (0.10, 0.20, 0.30, 0.70, 0.80, 0.90)
MIN_TRAIN = 40
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
    override = os.environ.get("M10L_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata = local / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not metadata.is_file():
        raise AuditError("M8B symbol metadata unavailable; set M10L_GOLD_DATA_ROOT")
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
    weight = pos - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


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


def build_feature_rows(bars: dict[str, list[c.Bar]]) -> list[dict[str, Any]]:
    fh1 = m10i.precompute(bars["H1"])
    fh4 = m10i.precompute(bars["H4"])
    fd1 = m10i.precompute(bars["D1"])
    fm15 = m10i.precompute(bars["M15"])
    vol_h1 = volume_ratio20(bars["H1"])

    h4_close = [bar.time + timedelta(hours=4) for bar in bars["H4"]]
    d1_close = [bar.time + timedelta(days=1) for bar in bars["D1"]]
    m15_close = [bar.time + timedelta(minutes=15) for bar in bars["M15"]]

    rows: list[dict[str, Any]] = []
    for i in range(120, len(bars["H1"]) - 1):
        decision = bars["H1"][i + 1].time
        if decision.year < 2023 or decision.year > 2026:
            continue
        ih4 = bisect.bisect_right(h4_close, decision) - 1
        id1 = bisect.bisect_right(d1_close, decision) - 1
        im15 = bisect.bisect_right(m15_close, decision) - 1
        if ih4 < 50 or id1 < 50 or im15 < 50:
            continue

        bar = bars["H1"][i]
        prev = bars["H1"][i - 1]
        atr = safe(fh1["atr14"][i])
        atr_pct = safe(fh1["atr_pct100"][i])
        rci = safe(fh1["rci9"][i])
        rci_prev = safe(fh1["rci9"][i - 1])
        ret3 = safe(fh1["ret3"][i])
        ret5 = safe(fh1["ret5"][i])
        vr = safe(vol_h1[i])
        if None in (atr, atr_pct, rci, rci_prev, ret3, ret5, vr) or atr is None or atr <= 0:
            continue
        rng = float(bar.high - bar.low)
        if rng <= 0:
            continue

        e20 = float(fh1["ema20"][i]); e30 = float(fh1["ema30"][i]); e40 = float(fh1["ema40"][i])
        pe20 = float(fh1["ema20"][i - 1])
        mline = float(fh1["macd_line"][i]); mhist = float(fh1["macd_hist"][i]); pmhist = float(fh1["macd_hist"][i - 1])

        h4close = float(bars["H4"][ih4].close)
        h4e20 = float(fh4["ema20"][ih4]); h4e30 = float(fh4["ema30"][ih4]); h4e40 = float(fh4["ema40"][ih4])
        h4hist = float(fh4["macd_hist"][ih4]); h4phist = float(fh4["macd_hist"][ih4 - 1])
        h4rci = safe(fh4["rci9"][ih4]); h4atrp = safe(fh4["atr_pct100"][ih4])

        d1close = float(bars["D1"][id1].close)
        d1e20 = float(fd1["ema20"][id1]); d1e30 = float(fd1["ema30"][id1]); d1e40 = float(fd1["ema40"][id1])
        d1hist = float(fd1["macd_hist"][id1]); d1phist = float(fd1["macd_hist"][id1 - 1])
        d1rci = safe(fd1["rci9"][id1]); d1atrp = safe(fd1["atr_pct100"][id1])

        m15close_value = float(bars["M15"][im15].close)
        m15e20 = float(fm15["ema20"][im15]); m15e30 = float(fm15["ema30"][im15])
        m15hist = float(fm15["macd_hist"][im15]); m15phist = float(fm15["macd_hist"][im15 - 1])
        m15rci = safe(fm15["rci9"][im15])

        if None in (h4rci, h4atrp, d1rci, d1atrp, m15rci):
            continue

        rows.append({
            "decision": decision,
            "year": decision.year,
            "server_hour": decision.hour,
            "h1_rci9": float(rci),
            "h1_rci9_delta": float(rci) - float(rci_prev),
            "h1_atr_pct100": float(atr_pct),
            "h1_ret3_bps": float(ret3),
            "h1_ret5_bps": float(ret5),
            "h1_body_fraction": max(0.0, (float(bar.open) - float(bar.close)) / rng),
            "h1_close_position": (float(bar.close) - float(bar.low)) / rng,
            "h1_close_minus_ema20_atr": (float(bar.close) - e20) / float(atr),
            "h1_high_minus_ema20_atr": (float(bar.high) - e20) / float(atr),
            "h1_ema20_slope_atr": (e20 - pe20) / float(atr),
            "h1_ema20_30_bps": bps(e20, e30, float(bar.close)),
            "h1_ema30_40_bps": bps(e30, e40, float(bar.close)),
            "h1_macd_line_bps": mline,
            "h1_macd_hist_bps": mhist,
            "h1_macd_hist_slope": mhist - pmhist,
            "h1_volume_ratio20": float(vr),
            "h4_ema20_30_bps": bps(h4e20, h4e30, h4close),
            "h4_ema30_40_bps": bps(h4e30, h4e40, h4close),
            "h4_macd_hist_bps": h4hist,
            "h4_macd_hist_slope": h4hist - h4phist,
            "h4_rci9": float(h4rci),
            "h4_atr_pct100": float(h4atrp),
            "d1_ema20_30_bps": bps(d1e20, d1e30, d1close),
            "d1_ema30_40_bps": bps(d1e30, d1e40, d1close),
            "d1_macd_hist_bps": d1hist,
            "d1_macd_hist_slope": d1hist - d1phist,
            "d1_rci9": float(d1rci),
            "d1_atr_pct100": float(d1atrp),
            "m15_ema20_30_bps": bps(m15e20, m15e30, m15close_value),
            "m15_macd_hist_bps": m15hist,
            "m15_macd_hist_slope": m15hist - m15phist,
            "m15_rci9": float(m15rci),
        })
    return rows


FEATURES = [
    "server_hour", "h1_rci9", "h1_rci9_delta", "h1_atr_pct100", "h1_ret3_bps", "h1_ret5_bps",
    "h1_body_fraction", "h1_close_position", "h1_close_minus_ema20_atr", "h1_high_minus_ema20_atr",
    "h1_ema20_slope_atr", "h1_ema20_30_bps", "h1_ema30_40_bps", "h1_macd_line_bps",
    "h1_macd_hist_bps", "h1_macd_hist_slope", "h1_volume_ratio20",
    "h4_ema20_30_bps", "h4_ema30_40_bps", "h4_macd_hist_bps", "h4_macd_hist_slope", "h4_rci9", "h4_atr_pct100",
    "d1_ema20_30_bps", "d1_ema30_40_bps", "d1_macd_hist_bps", "d1_macd_hist_slope", "d1_rci9", "d1_atr_pct100",
    "m15_ema20_30_bps", "m15_macd_hist_bps", "m15_macd_hist_slope", "m15_rci9",
]


def build_conditions(train_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for feature in FEATURES:
        values = [float(row[feature]) for row in train_rows]
        thresholds = sorted({qtile(values, q) for q in QUANTILES})
        for threshold in thresholds:
            for op in ("<=", ">="):
                conditions.append({
                    "id": f"{feature}{op}{threshold:.10g}",
                    "feature": feature,
                    "op": op,
                    "threshold": threshold,
                })
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
            for horizon in HORIZONS:
                out[horizon][idx] = None
            continue
        entry_bid = float(entry.open)
        for horizon in HORIZONS:
            exit_time = decision + timedelta(minutes=horizon)
            exit_bar = m1_by_time.get(exit_time)
            if exit_bar is None:
                out[horizon][idx] = None
                continue
            actual_ask = float(exit_bar.open) + float(exit_bar.spread) * POINT
            fixed_ask = float(exit_bar.open) + 0.20
            out[horizon][idx] = (
                c.directional_return("SHORT", entry_bid, actual_ask),
                c.directional_return("SHORT", entry_bid, fixed_ask),
                exit_time,
            )
    return out


def selected_returns(
    indices: set[int],
    rows: list[dict[str, Any]],
    outcomes: dict[int, tuple[float, float, datetime] | None],
    allowed_years: set[int],
) -> tuple[list[float], list[float]]:
    actual: list[float] = []
    fixed: list[float] = []
    blocked_until: datetime | None = None
    for idx in sorted(indices, key=lambda x: rows[x]["decision"]):
        row = rows[idx]
        if int(row["year"]) not in allowed_years:
            continue
        decision = row["decision"]
        if blocked_until is not None and decision < blocked_until:
            continue
        item = outcomes.get(idx)
        if item is None:
            continue
        actual_ret, fixed_ret, exit_time = item
        actual.append(float(actual_ret))
        fixed.append(float(fixed_ret))
        blocked_until = exit_time
    return actual, fixed


def metrics(values: list[float]) -> dict[str, Any]:
    return c.metrics_from_values(values)


def train_score(indices: set[int], rows: list[dict[str, Any]], outcomes: dict[int, tuple[float, float, datetime] | None]) -> dict[str, Any]:
    actual, fixed = selected_returns(indices, rows, outcomes, {2023, 2024})
    result = metrics(actual)
    fixed_result = metrics(fixed)
    return {
        "count": int(result["count"]),
        "pf": result["profit_factor_bps"],
        "net": result["net_bps"],
        "dd": result["max_drawdown_bps"],
        "fixed_pf": fixed_result["profit_factor_bps"],
    }


def evaluate_formula(
    formula_id: str,
    formula_type: str,
    conditions: list[dict[str, Any]],
    indices: set[int],
    horizon: int,
    rows: list[dict[str, Any]],
    outcomes: dict[int, tuple[float, float, datetime] | None],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "candidate_id": formula_id,
        "formula_type": formula_type,
        "horizon_minutes": horizon,
        "conditions_json": json.dumps(conditions, sort_keys=True, separators=(",", ":")),
        "formula": " AND ".join(f"{cnd['feature']} {cnd['op']} {float(cnd['threshold']):.10g}" for cnd in conditions),
    }
    split_years = {
        "train": {2023, 2024},
        "val2025": {2025},
        "test2026": {2026},
        "all": {2023, 2024, 2025, 2026},
    }
    for name, years in split_years.items():
        actual, fixed = selected_returns(indices, rows, outcomes, years)
        m = metrics(actual); fm = metrics(fixed)
        for key, value in m.items():
            result[f"{name}_{key}"] = value
        for key, value in fm.items():
            result[f"fixed0p20_{name}_{key}"] = value
    return result


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


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10L contract")

        local = local_root()
        data_root = resolve_data_root(local)
        paths: dict[str, Path] = {}
        hashes: dict[str, str] = {}
        for tf, (filename, expected) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise AuditError(f"missing frozen GOLD file: {path}")
            actual = c.sha256(path)
            if actual != expected:
                raise AuditError(f"SHA256 mismatch for {filename}: {actual}")
            paths[tf] = path
            hashes[tf] = actual

        bars = {tf: c.load_bars(path) for tf, path in paths.items()}
        rows = build_feature_rows(bars)
        train_rows = [row for row in rows if int(row["year"]) in (2023, 2024)]
        if len(train_rows) < 1000:
            raise AuditError(f"unexpectedly small H1 discovery rows: {len(train_rows)}")

        conditions = build_conditions(train_rows)
        matched_sets: dict[str, set[int]] = {}
        for cond in conditions:
            matched_sets[cond["id"]] = {idx for idx, row in enumerate(rows) if condition_match(row, cond)}

        outcomes = outcome_cache(rows, bars["M1"])
        discovery_single_rows: list[dict[str, Any]] = []
        frozen_specs: list[dict[str, Any]] = []

        for horizon in HORIZONS:
            scored_singles: list[tuple[dict[str, Any], dict[str, Any], set[int]]] = []
            for cond in conditions:
                indices = matched_sets[cond["id"]]
                score = train_score(indices, rows, outcomes[horizon])
                if score["count"] < MIN_TRAIN or score["pf"] is None:
                    continue
                discovery_single_rows.append({
                    "horizon_minutes": horizon,
                    "condition_id": cond["id"],
                    "feature": cond["feature"],
                    "op": cond["op"],
                    "threshold": cond["threshold"],
                    "train_count": score["count"],
                    "train_pf": score["pf"],
                    "train_net_bps": score["net"],
                    "train_max_drawdown_bps": score["dd"],
                    "fixed0p20_train_pf": score["fixed_pf"],
                })
                scored_singles.append((cond, score, indices))

            scored_singles.sort(
                key=lambda item: (
                    float(item[1]["pf"] or -math.inf),
                    float(item[1]["net"] or -math.inf),
                    -float(item[1]["dd"] or math.inf),
                    int(item[1]["count"]),
                ),
                reverse=True,
            )
            top_singles = scored_singles[:TOP_SINGLES_FOR_PAIRS]

            candidates: list[tuple[str, list[dict[str, Any]], set[int], dict[str, Any]]] = []
            for cond, score, indices in scored_singles:
                candidates.append(("SINGLE", [cond], indices, score))

            for (cond_a, _, idx_a), (cond_b, _, idx_b) in combinations(top_singles, 2):
                if cond_a["feature"] == cond_b["feature"]:
                    continue
                indices = idx_a & idx_b
                score = train_score(indices, rows, outcomes[horizon])
                if score["count"] < MIN_TRAIN or score["pf"] is None:
                    continue
                candidates.append(("AND2", [cond_a, cond_b], indices, score))

            candidates.sort(
                key=lambda item: (
                    float(item[3]["pf"] or -math.inf),
                    float(item[3]["net"] or -math.inf),
                    -float(item[3]["dd"] or math.inf),
                    int(item[3]["count"]),
                ),
                reverse=True,
            )
            for rank, (formula_type, conds, indices, score) in enumerate(candidates[:SHORTLIST_PER_HORIZON], start=1):
                frozen_specs.append({
                    "candidate_id": f"M10L_H{horizon}_C{rank:03d}",
                    "formula_type": formula_type,
                    "conditions": conds,
                    "indices": indices,
                    "horizon": horizon,
                    "discovery_rank": rank,
                    "train_pf_at_freeze": score["pf"],
                })

        shortlist_results: list[dict[str, Any]] = []
        robust: list[dict[str, Any]] = []
        stable: list[dict[str, Any]] = []
        for spec in frozen_specs:
            result = evaluate_formula(
                spec["candidate_id"],
                spec["formula_type"],
                spec["conditions"],
                spec["indices"],
                spec["horizon"],
                rows,
                outcomes[spec["horizon"]],
            )
            result["discovery_rank"] = spec["discovery_rank"]
            shortlist_results.append(result)

            pfs = [result.get("train_profit_factor_bps"), result.get("val2025_profit_factor_bps"), result.get("test2026_profit_factor_bps")]
            counts = [int(result.get("train_count") or 0), int(result.get("val2025_count") or 0), int(result.get("test2026_count") or 0)]
            nets = [float(result.get("train_net_bps") or 0), float(result.get("val2025_net_bps") or 0), float(result.get("test2026_net_bps") or 0)]
            if all(pf is not None and float(pf) > 1.0 for pf in pfs):
                stable.append(result)
            if (
                counts[0] >= 40 and counts[1] >= 20 and counts[2] >= 10
                and all(pf is not None and float(pf) >= 2.0 for pf in pfs)
                and all(net > 0 for net in nets)
                and result.get("fixed0p20_all_profit_factor_bps") is not None
                and float(result["fixed0p20_all_profit_factor_bps"]) > 1.0
            ):
                robust.append(result)

        robust.sort(
            key=lambda row: (
                min(float(row["train_profit_factor_bps"]), float(row["val2025_profit_factor_bps"]), float(row["test2026_profit_factor_bps"])),
                float(row["fixed0p20_all_profit_factor_bps"]),
                int(row["all_count"]),
            ),
            reverse=True,
        )
        best_min = sorted(
            shortlist_results,
            key=lambda row: min(
                float(row.get("train_profit_factor_bps") or 0),
                float(row.get("val2025_profit_factor_bps") or 0),
                float(row.get("test2026_profit_factor_bps") or 0),
            ),
            reverse=True,
        )[:20]

        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_HISTORICAL_H1_SHORT_CAUSAL_FEATURE_MINING_ONLY",
            "run_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "candidate_universe": "all causal H1 decisions; Mochipoyo-independent; M10J/M10K-independent",
            "feature_row_count": len(rows),
            "train_2023_2024_feature_row_count": len(train_rows),
            "feature_count": len(FEATURES),
            "generated_condition_count": len(conditions),
            "frozen_shortlist_count": len(frozen_specs),
            "stable_all_three_split_pf_gt_1_count": len(stable),
            "robust_pf2_candidate_count": len(robust),
            "robust_pf2_candidates": robust[:20],
            "best_min_split_candidates": best_min,
            "split_contract": contract["causality"],
            "interpretation": "Historical audit-only. 2025/2026 were not used to generate, pair, rank, or freeze formulas.",
            "guardrails": contract["safety"],
        }

        out_root = local / "outputs" / "M10L"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = out_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10L Mochipoyo-independent H1 SHORT causal feature mining. Formula generation/ranking uses 2023-2024 only; 2025 and 2026 are locked holdouts until shortlist freeze. Audit-only.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_frozen_shortlist_results.csv", shortlist_results)
        write_csv(archive / "03_robust_pf2_candidates.csv", robust)
        write_csv(archive / "04_best_min_split_pf_candidates.csv", best_min)
        write_csv(archive / "05_discovery_single_conditions.csv", discovery_single_rows)
        (archive / "06_data_quality.json").write_text(json.dumps({
            "frozen_hashes": hashes,
            "newest_row_contract": "CLOSED",
            "time_basis": "MT5 server time",
            "nearest_m1_fallback": False,
            "exact_m1_entry_and_exit_only": True,
            "actual_spread_at_short_exit": True,
            "fixed_spread_sensitivity_usd": 0.20,
            "formula_generation_uses_2025": False,
            "formula_generation_uses_2026": False,
            "m7c_kernel_candidate_universe": False,
            "m10j_seed_candidate_universe": False,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_audit.log").write_text("\n".join([
            "status=PASS_HISTORICAL_H1_SHORT_CAUSAL_FEATURE_MINING_ONLY",
            f"feature_rows={len(rows)}",
            f"train_rows={len(train_rows)}",
            f"features={len(FEATURES)}",
            f"conditions={len(conditions)}",
            f"frozen_shortlist={len(frozen_specs)}",
            f"stable_all_three_split_pf_gt1={len(stable)}",
            f"robust_pf2={len(robust)}",
            "formula_generation_uses_2025=false",
            "formula_generation_uses_2026=false",
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
        names = [
            "00_READ_ME_FIRST.txt", "01_summary.json", "02_frozen_shortlist_results.csv",
            "03_robust_pf2_candidates.csv", "04_best_min_split_pf_candidates.csv",
            "05_discovery_single_conditions.csv", "06_data_quality.json", "07_audit.log",
        ]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)

        print("[M10L PASS] H1 independent SHORT causal feature mining completed")
        print(f"[RESULT] shortlist={len(frozen_specs)} stable={len(stable)} robust_pf2={len(robust)}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10L BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] Existing forward monitors and all frozen starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
