from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
MR = THIS.parents[2]
M10A_DIR = MR / "m10a" / "python"
M10F_DIR = MR / "m10f" / "python"
for directory in (M10A_DIR, M10F_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import frozen_core as c
import payoff_rules as pay
import run_short_compound_loss_feature_audit as f

STAGE = "M10G_M15_SHORT_RECLAIM_AUDIT"
CONTRACT = THIS.parents[4] / "config" / "mochipoyo_alert_research" / "m10g_m15_short_reclaim_audit_contract_20260725.json"
OFFSETS = (0.0, 0.05, 0.10, 0.15, 0.20)
WAITS = (5, 10, 15, 20, 30)
FIXED_SPREAD_USD = 0.20
SEED_EXPECTED = {
    "all_count": 1089,
    "all_pf": 1.1566500291510813,
    "fixed0p20_all_pf": 1.1413439010359998,
    "years": {
        2023: None,
        2024: None,
        2025: {"count": 241, "pf": 1.03663660004606},
        2026: {"count": 122, "pf": 1.3615777641528928},
    },
}
FIXED_CLAUSES = [
    [
        {"feature": "H4_atr14_bps", "op": ">=", "threshold": 52.60821382133402},
        {"feature": "H1_atr14_bps", "op": ">=", "threshold": 25.921365071429697},
        {"feature": "H1_ret1_bps", "op": ">=", "threshold": 4.856039581559264},
    ],
    [
        {"feature": "M5_ema30_40_bps", "op": ">=", "threshold": -0.6612073901334448},
        {"feature": "H4_ema30_40_bps", "op": ">=", "threshold": 10.436275364829477},
    ],
]


class AuditError(RuntimeError):
    pass


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10G_GOLD_DATA_ROOT")
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def seed_rows(bars: dict[str, list[c.Bar]], *, point: float) -> list[dict[str, Any]]:
    features = f.precompute_features(bars)
    turns = c.build_timeframe_turns(bars["M15"], bars["M1"], point, "M10G_M15")
    shorts = [row for row in turns if row["direction"] == "SHORT"]
    annotated = f.annotate_short_rows(shorts, bars, features, point=point)
    return [row for row in annotated if not f.rule_match(row, FIXED_CLAUSES)]


def metrics(rows: list[dict[str, Any]], *, value_key: str) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: c.parse_time(str(row["actual_entry_time"])))
    return c.metrics_from_values([float(row[value_key]) for row in ordered])


def yearly(rows: list[dict[str, Any]], *, value_key: str) -> list[dict[str, Any]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(c.parse_time(str(row["actual_entry_time"])).year, []).append(row)
    return [{"year": year, **metrics(group, value_key=value_key)} for year, group in sorted(groups.items())]


def build_reclaim(
    rows: list[dict[str, Any]],
    m1: list[c.Bar],
    m15: list[c.Bar],
    *,
    point: float,
    offset_atr: float,
    wait_minutes: int,
) -> list[dict[str, Any]]:
    m1_index = {bar.time: index for index, bar in enumerate(m1)}
    m15_close_times = [bar.time + timedelta(minutes=15) for bar in m15]
    atr15 = pay.wilder_atr14(m15)
    output: list[dict[str, Any]] = []

    for row in rows:
        proxy_time = c.parse_time(str(row["proxy_entry_time"]))
        first_time = c.parse_time(str(row["turn_entry_time"]))
        exit_time = c.parse_time(str(row["exit_time"]))
        proxy_index = m1_index.get(proxy_time)
        first_index = m1_index.get(first_time)
        exit_index = m1_index.get(exit_time)
        if proxy_index is None or first_index is None or exit_index is None or exit_index <= first_index:
            continue

        i15 = bisect.bisect_right(m15_close_times, first_time) - 1
        if i15 < 0 or atr15[i15] is None or float(atr15[i15]) <= 0:
            continue

        atr_value = float(atr15[i15])
        primary_bid = float(m1[proxy_index].open)
        level = primary_bid + offset_atr * atr_value

        actual_index: int | None = first_index if float(m1[first_index].open) <= level else None
        if actual_index is None:
            last_check_exclusive = min(exit_index - 1, first_index + wait_minutes)
            for closed_index in range(first_index, last_check_exclusive):
                if float(m1[closed_index].close) <= level:
                    candidate = closed_index + 1
                    if candidate < exit_index and candidate <= first_index + wait_minutes:
                        actual_index = candidate
                    break
        if actual_index is None:
            continue

        actual_time = m1[actual_index].time
        entry_bid = float(m1[actual_index].open)
        historical_exit_ask = float(m1[exit_index].open) + float(m1[exit_index].spread) * point
        historical_return = (entry_bid - historical_exit_ask) / abs(entry_bid) * 10000.0
        fixed_exit_ask = float(m1[exit_index].open) + FIXED_SPREAD_USD
        fixed_return = (entry_bid - fixed_exit_ask) / abs(entry_bid) * 10000.0

        output.append({
            **row,
            "actual_entry_time": actual_time.strftime(c.TIME_FORMAT),
            "entry_delay_minutes": actual_index - first_index,
            "primary_bid": primary_bid,
            "atr15_at_first_turn": atr_value,
            "reclaim_level": level,
            "reclaim_offset_atr": offset_atr,
            "wait_minutes": wait_minutes,
            "entry_bid": entry_bid,
            "historical_return_bps": historical_return,
            "fixed_spread_0p20_return_bps": fixed_return,
        })
    return output


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
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    data_root = resolve_data_root(local_root)
    point = float(os.environ.get("M10G_POINT", str(c.POINT)))
    if not data_root.is_dir() or not math.isfinite(point):
        print(f"[M10G BLOCKED] data root or point unavailable: {data_root} point={point}")
        return 2

    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10G contract")

        paths: dict[str, Path] = {}
        for tf, (filename, expected_hash) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise AuditError(f"missing required GOLD file: {path}")
            actual_hash = c.sha256(path)
            if actual_hash != expected_hash:
                raise AuditError(f"SHA256 mismatch {filename}: {actual_hash}")
            paths[tf] = path
        bars = {tf: c.load_bars(path) for tf, path in paths.items()}

        seed = seed_rows(bars, point=point)
        seed_values = sorted(seed, key=lambda row: str(row["turn_entry_time"]))
        seed_metrics = c.metrics_from_values([float(row["return_bps"]) for row in seed_values])
        seed_fixed = c.metrics_from_values([float(row["fixed_spread_0p20_return_bps"]) for row in seed_values])
        if seed_metrics["count"] != SEED_EXPECTED["all_count"]:
            raise AuditError(f"seed count mismatch actual={seed_metrics['count']} expected={SEED_EXPECTED['all_count']}")
        c.assert_close("seed.pf", float(seed_metrics["profit_factor_bps"]), SEED_EXPECTED["all_pf"])
        c.assert_close("seed.fixed0p20.pf", float(seed_fixed["profit_factor_bps"]), SEED_EXPECTED["fixed0p20_all_pf"])

        seed_by_year: dict[int, list[dict[str, Any]]] = {}
        for row in seed:
            seed_by_year.setdefault(c.parse_time(str(row["turn_entry_time"])).year, []).append(row)
        for year, expected in SEED_EXPECTED["years"].items():
            if expected is None:
                continue
            yr = c.metrics_from_values([float(row["return_bps"]) for row in seed_by_year.get(year, [])])
            if yr["count"] != expected["count"]:
                raise AuditError(f"seed {year} count mismatch actual={yr['count']} expected={expected['count']}")
            c.assert_close(f"seed.{year}.pf", float(yr["profit_factor_bps"]), float(expected["pf"]))

        grid_rows: list[dict[str, Any]] = []
        ledgers: dict[str, list[dict[str, Any]]] = {}
        for offset in OFFSETS:
            for wait in WAITS:
                rows = build_reclaim(seed, bars["M1"], bars["M15"], point=point, offset_atr=offset, wait_minutes=wait)
                key = f"O{offset:.2f}_W{wait}"
                ledgers[key] = rows
                hist = metrics(rows, value_key="historical_return_bps")
                fixed = metrics(rows, value_key="fixed_spread_0p20_return_bps")
                years = {row["year"]: row for row in yearly(rows, value_key="historical_return_bps")}
                year_pfs = [float(years[year]["profit_factor_bps"]) for year in (2023, 2024, 2025, 2026) if year in years and years[year]["profit_factor_bps"] is not None]
                year_counts = [int(years[year]["count"]) for year in (2023, 2024, 2025, 2026) if year in years]
                grid_rows.append({
                    "offset_atr": offset,
                    "wait_minutes": wait,
                    "accepted_count": hist["count"],
                    "retention_vs_seed": hist["count"] / len(seed) if seed else 0.0,
                    "win_rate": hist["win_rate"],
                    "profit_factor_bps": hist["profit_factor_bps"],
                    "net_bps": hist["net_bps"],
                    "average_win_bps": hist["average_win_bps"],
                    "average_loss_bps": hist["average_loss_bps"],
                    "payoff_ratio": hist["payoff_ratio"],
                    "max_drawdown_bps": hist["max_drawdown_bps"],
                    "max_losing_streak": hist["max_losing_streak"],
                    "tail_le_minus_100_fraction": hist["tail_le_minus_100_fraction"],
                    "fixed0p20_profit_factor_bps": fixed["profit_factor_bps"],
                    "fixed0p20_payoff_ratio": fixed["payoff_ratio"],
                    "fixed0p20_max_drawdown_bps": fixed["max_drawdown_bps"],
                    "pf_2023": years.get(2023, {}).get("profit_factor_bps"),
                    "count_2023": years.get(2023, {}).get("count"),
                    "pf_2024": years.get(2024, {}).get("profit_factor_bps"),
                    "count_2024": years.get(2024, {}).get("count"),
                    "pf_2025": years.get(2025, {}).get("profit_factor_bps"),
                    "count_2025": years.get(2025, {}).get("count"),
                    "pf_2026": years.get(2026, {}).get("profit_factor_bps"),
                    "count_2026": years.get(2026, {}).get("count"),
                    "min_calendar_year_pf": min(year_pfs) if year_pfs else None,
                    "min_calendar_year_count": min(year_counts) if year_counts else 0,
                    "pf2_all": bool(hist["profit_factor_bps"] is not None and float(hist["profit_factor_bps"]) >= 2.0),
                    "pf2_every_calendar_year": bool(len(year_pfs) == 4 and all(value >= 2.0 for value in year_pfs)),
                })

        if len(grid_rows) != 25:
            raise AuditError(f"grid cell mismatch actual={len(grid_rows)} expected=25")

        ranked = sorted(
            grid_rows,
            key=lambda row: (
                float(row["min_calendar_year_pf"] if row["min_calendar_year_pf"] is not None else -math.inf),
                float(row["profit_factor_bps"] if row["profit_factor_bps"] is not None else -math.inf),
                float(row["retention_vs_seed"]),
            ),
            reverse=True,
        )
        best = ranked[0]
        best_key = f"O{float(best['offset_atr']):.2f}_W{int(best['wait_minutes'])}"

    except Exception as exc:
        print(f"[M10G BLOCKED] {type(exc).__name__}: {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_HISTORICAL_M15_SHORT_RECLAIM_AUDIT_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample": "research-exposed frozen GOLD history 2023-01-03 through 2026-06-19; not fresh/OOS evidence",
        "seed": {"candidate_id": "M10F_M15_C0049", "metrics": seed_metrics, "fixed0p20_metrics": seed_fixed},
        "grid_cells": len(grid_rows),
        "pf2_all_cells": sum(bool(row["pf2_all"]) for row in grid_rows),
        "pf2_every_calendar_year_cells": sum(bool(row["pf2_every_calendar_year"]) for row in grid_rows),
        "best_by_min_calendar_year_pf": best,
        "best_is_research_exposed_not_auto_adopted": True,
        "search_contract": {
            "offsets": list(OFFSETS),
            "wait_minutes": list(WAITS),
            "runner_tested": False,
            "fixed_spread_usd": FIXED_SPREAD_USD,
            "m10f_seed_formula_changed": False,
        },
        "guardrails": {
            "historical_research_exposed": True,
            "fresh_forward_validated": False,
            "future_outcome_used_in_entry_gate": False,
            "m10b_modified_or_reset": False,
            "m10e_modified_or_reset": False,
            "historical_backfill": False,
            "automatic_live_promotion": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        },
        "next": "Review the 25-cell family. Only if a broad robust reclaim family improves PF/payoff/DD with usable retention should runner/exit research be considered. No SHORT forward arm from M10G alone.",
    }

    out_root = Path(os.environ.get("M10G_OUTPUT_ROOT", "")) if os.environ.get("M10G_OUTPUT_ROOT") else local_root / "outputs" / "M10G"
    archive = out_root / "archive" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10G audits a bounded causal M15 SHORT reclaim family on the fixed M10F C0049 seed.\n"
        "All history is research-exposed. M10B/M10E remain unchanged. No SHORT forward promotion.\n"
        "Submit 99_UPLOAD_PACKAGE.zip only.\n",
        encoding="utf-8",
    )
    c.dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_reclaim_grid.csv", grid_rows)
    write_csv(archive / "03_seed_m15_short_ledger.csv", seed)
    write_csv(archive / "04_best_reclaim_ledger.csv", ledgers[best_key])
    c.dump_json(archive / "05_data_quality.json", {
        "data_root": str(data_root),
        "point": point,
        "hashes": {tf: {"file": filename, "sha256": digest} for tf, (filename, digest) in c.EXPECTED_FILES.items()},
        "newest_csv_row_contract": "CLOSED",
        "nearest_m1_fallback": False,
    })
    (archive / "06_audit.log").write_text("\n".join([
        "status=PASS_HISTORICAL_M15_SHORT_RECLAIM_AUDIT_ONLY",
        f"seed_count={seed_metrics['count']} seed_pf={seed_metrics['profit_factor_bps']}",
        f"grid_cells={len(grid_rows)}",
        f"pf2_all_cells={summary['pf2_all_cells']}",
        f"pf2_every_calendar_year_cells={summary['pf2_every_calendar_year_cells']}",
        f"best_offset={best['offset_atr']} best_wait={best['wait_minutes']} best_pf={best['profit_factor_bps']} best_min_year_pf={best['min_calendar_year_pf']}",
        "runner_tested=false",
        "future_outcome_used_in_entry_gate=false",
        "m10b_modified_or_reset=false",
        "m10e_modified_or_reset=false",
        "historical_backfill=false",
        "automatic_live_promotion=false",
        "discord_send=false",
        "mt5_order=false",
        "live_ready=false",
        "final_signal=false",
        "",
    ]), encoding="utf-8")
    names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_reclaim_grid.csv", "03_seed_m15_short_ledger.csv", "04_best_reclaim_ledger.csv", "05_data_quality.json", "06_audit.log"]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(
        "[M10G PASS] "
        f"seed={seed_metrics['count']} PF={seed_metrics['profit_factor_bps']:.12f} "
        f"best_offset={best['offset_atr']:.2f} best_wait={best['wait_minutes']} "
        f"best_count={best['accepted_count']} best_PF={float(best['profit_factor_bps']):.12f} "
        f"min_year_PF={float(best['min_calendar_year_pf']):.12f} "
        f"PF2all={summary['pf2_all_cells']} PF2everyyear={summary['pf2_every_calendar_year_cells']}"
    )
    print("[M10G OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
