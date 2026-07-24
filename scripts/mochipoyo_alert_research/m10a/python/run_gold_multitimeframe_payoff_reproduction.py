from __future__ import annotations

import json
import math
import os
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import frozen_core as c
import payoff_rules as p

STAGE = "M10A_GOLD_MULTI_TIMEFRAME_PAYOFF_DETERMINISTIC_REPRODUCTION"
EXTRA_COSTS = (0.5, 1.0, 1.5, 2.0)
M5_RUNNER_SHARE = 0.75
H1_RUNNER_SHARE = 0.50
EXPECTED = {
    "raw": {
        "M5_S1": {"count": 1256, "pf": 1.3336981886264172},
        "M15_S2": {"count": 1495, "pf": 1.365884145048126},
        "H1_S3": {"count": 191, "pf": 1.7802349633701025},
        "H4_S4": {"count": 70, "pf": 3.295562620459433},
    },
    "M5_ENTRY": {"count": 842, "win_rate": 0.665083135391924, "pf": 1.5373384445763516, "avg_win": 9.40059307827146, "avg_loss": -12.142963364125183, "payoff": 0.7741597167330915, "dd": 227.3232304692574, "tail100": 0.004750593824228029, "extra_2bps_pf": 1.0380554833102582},
    "M5_RUNNER75": {"count": 837, "overlap_skips": 5, "win_rate": 0.6296296296296297, "pf": 1.6651962763806496, "avg_win": 11.360485887595685, "avg_loss": -11.59792769347865, "payoff": 0.9795272214003821, "dd": 211.06607310179675, "tail100": 0.0035842293906810036, "extra_2bps_pf": 1.1664055911962432},
    "H1_ENTRY": {"count": 171, "win_rate": 0.7192982456140351, "pf": 2.814130403928734, "avg_win": 34.418344429800925, "avg_loss": -31.340767818803045, "payoff": 1.0981972308014571, "dd": 271.583159570446, "tail100": 0.023391812865497075, "extra_2bps_pf": 2.4819002508383456},
    "H1_RUNNER50": {"count": 159, "overlap_skips": 12, "win_rate": 0.6792452830188679, "pf": 2.8303858342555084, "avg_win": 40.12947532813278, "avg_loss": -30.024198246139303, "payoff": 1.3365710883984345, "dd": 271.583159570446, "tail100": 0.025157232704402517, "extra_2bps_pf": 2.515705722093707},
    "H4_ENTRY": {"count": 57, "win_rate": 0.7543859649122807, "pf": 4.668798744063922, "avg_win": 73.14596729072778, "avg_loss": -48.12000391046308, "payoff": 1.5200740096952303, "dd": 270.9863310584244, "tail100": 0.017543859649122806, "extra_2bps_pf": 4.351631051771246},
}


def verify_metric_block(name: str, actual: dict[str, Any], expected: dict[str, Any]) -> None:
    if actual["count"] != expected["count"]:
        raise RuntimeError(f"{name} count mismatch actual={actual['count']} expected={expected['count']}")
    for actual_key, expected_key in (("win_rate", "win_rate"), ("profit_factor_bps", "pf"), ("average_win_bps", "avg_win"), ("average_loss_bps", "avg_loss"), ("payoff_ratio", "payoff"), ("max_drawdown_bps", "dd"), ("tail_le_minus_100_fraction", "tail100")):
        c.assert_close(f"{name}.{actual_key}", float(actual[actual_key]), float(expected[expected_key]))


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10A_GOLD_DATA_ROOT")
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    data_root = resolve_data_root(local_root)
    point = float(os.environ.get("M10A_POINT", str(c.POINT)))
    if not data_root.is_dir() or not math.isfinite(point):
        print(f"[M10A BLOCKED] data root or point unavailable: {data_root} point={point}")
        return 2
    try:
        paths: dict[str, Path] = {}
        for timeframe, (filename, expected_hash) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise RuntimeError(f"missing required GOLD file: {path}")
            actual_hash = c.sha256(path)
            if actual_hash != expected_hash:
                raise RuntimeError(f"SHA256 mismatch {filename}: {actual_hash}")
            paths[timeframe] = path
        bars = {timeframe: c.load_bars(path) for timeframe, path in paths.items()}
        close_times = {
            "M5": [bar.time + timedelta(minutes=5) for bar in bars["M5"]],
            "M15": [bar.time + timedelta(minutes=15) for bar in bars["M15"]],
            "H1": [bar.time + timedelta(hours=1) for bar in bars["H1"]],
            "H4": [bar.time + timedelta(hours=4) for bar in bars["H4"]],
            "D1": [bar.time + timedelta(days=1) for bar in bars["D1"]],
        }
        turns = {tf: c.build_timeframe_turns(bars[tf], bars["M1"], point, f"M10A_{tf}") for tf in ("M5", "M15", "H1", "H4")}
        longs = {tf: [row for row in rows if row["direction"] == "LONG"] for tf, rows in turns.items()}
        c.enrich_indices(longs["M5"], close_times, ("M5", "M15", "H1"))
        c.enrich_indices(longs["M15"], close_times, ("M5", "M15"))
        c.enrich_indices(longs["H1"], close_times, ("H4", "D1"))
        c.enrich_indices(longs["H4"], close_times, ("D1",))
        ratio20_m5 = c.m5_ratio20(bars["M5"])
        macd = {tf: c.macd_bps(bars[tf]) for tf in ("M5", "M15", "H1", "H4", "D1")}
        rci9_h1 = c.rci_series([bar.close for bar in bars["H1"]], 9)
        rci9_d1 = c.rci_series([bar.close for bar in bars["D1"]], 9)
        d1_closes = [bar.close for bar in bars["D1"]]
        ema20_d1, ema30_d1, ema40_d1 = c.ema(d1_closes, 20), c.ema(d1_closes, 30), c.ema(d1_closes, 40)
        branches = {
            "M5_S1": c.select_s1(longs["M5"], ratio20_m5, macd, rci9_h1),
            "M15_S2": c.select_s2(longs["M15"], ratio20_m5, macd["M15"]),
            "H1_S3": c.select_s3(longs["H1"], macd["H4"], macd["D1"]),
            "H4_S4": c.select_s4(longs["H4"], rci9_d1, ema20_d1, ema30_d1, ema40_d1),
        }
        raw = {name: c.raw_metrics(rows) for name, rows in branches.items()}
        for name, expected in EXPECTED["raw"].items():
            if raw[name]["count"] != expected["count"]:
                raise RuntimeError(f"{name} count mismatch actual={raw[name]['count']} expected={expected['count']}")
            c.assert_close(f"{name}.pf", float(raw[name]["profit_factor_bps"]), float(expected["pf"]))

        m5_entry = p.build_m5_reclaim(branches["M5_S1"], bars["M1"], bars["M5"], point=point)
        h1_entry = p.build_htf_reclaim(branches["H1_S3"], bars["M1"], bars["H1"], bars["M5"], signal_delta=timedelta(hours=1), confirm_delta=timedelta(minutes=5), offset_atr=p.H1_ENTRY_OFFSET_ATR, wait_minutes=p.H1_ENTRY_WAIT_MINUTES, point=point, confirm_name="M5")
        h4_entry = p.build_htf_reclaim(branches["H4_S4"], bars["M1"], bars["H4"], bars["M15"], signal_delta=timedelta(hours=4), confirm_delta=timedelta(minutes=15), offset_atr=p.H4_ENTRY_OFFSET_ATR, wait_minutes=p.H4_ENTRY_WAIT_MINUTES, point=point, confirm_name="M15")
        m5_entry_metrics = p.metric_rows(m5_entry, value_key="native_return_bps", time_key="actual_entry_time")
        h1_entry_metrics = p.metric_rows(h1_entry, value_key="native_return_bps", time_key="actual_entry_time")
        h4_entry_metrics = p.metric_rows(h4_entry, value_key="native_return_bps", time_key="actual_entry_time")
        verify_metric_block("M5_ENTRY", m5_entry_metrics, EXPECTED["M5_ENTRY"])
        verify_metric_block("H1_ENTRY", h1_entry_metrics, EXPECTED["H1_ENTRY"])
        verify_metric_block("H4_ENTRY", h4_entry_metrics, EXPECTED["H4_ENTRY"])
        for name, rows, expected in (("M5_ENTRY", m5_entry, EXPECTED["M5_ENTRY"]), ("H1_ENTRY", h1_entry, EXPECTED["H1_ENTRY"]), ("H4_ENTRY", h4_entry, EXPECTED["H4_ENTRY"])):
            cost2 = p.metric_rows(rows, value_key="native_return_bps", time_key="actual_entry_time", extra_cost_bps=2.0)
            c.assert_close(f"{name}.extra_2bps_pf", float(cost2["profit_factor_bps"]), float(expected["extra_2bps_pf"]))

        m5_meta = p.build_runner_meta(m5_entry, bars["M1"], bars["M5"], context_bars=(bars["M15"],), context_deltas=(timedelta(minutes=15),))
        m5_runner, m5_overlap = p.one_position_runner(m5_meta, runner_share=M5_RUNNER_SHARE)
        h1_meta = p.build_runner_meta(h1_entry, bars["M1"], bars["H1"], context_bars=(bars["H4"], bars["D1"]), context_deltas=(timedelta(hours=4), timedelta(days=1)))
        h1_runner, h1_overlap = p.one_position_runner(h1_meta, runner_share=H1_RUNNER_SHARE)
        m5_runner_metrics = p.metric_rows(m5_runner, value_key="weighted_return_bps", time_key="actual_entry_time")
        h1_runner_metrics = p.metric_rows(h1_runner, value_key="weighted_return_bps", time_key="actual_entry_time")
        verify_metric_block("M5_RUNNER75", m5_runner_metrics, EXPECTED["M5_RUNNER75"])
        verify_metric_block("H1_RUNNER50", h1_runner_metrics, EXPECTED["H1_RUNNER50"])
        if len(m5_overlap) != EXPECTED["M5_RUNNER75"]["overlap_skips"]:
            raise RuntimeError(f"M5 runner overlap mismatch actual={len(m5_overlap)}")
        if len(h1_overlap) != EXPECTED["H1_RUNNER50"]["overlap_skips"]:
            raise RuntimeError(f"H1 runner overlap mismatch actual={len(h1_overlap)}")
        for name, rows, expected in (("M5_RUNNER75", m5_runner, EXPECTED["M5_RUNNER75"]), ("H1_RUNNER50", h1_runner, EXPECTED["H1_RUNNER50"])):
            cost2 = p.metric_rows(rows, value_key="weighted_return_bps", time_key="actual_entry_time", extra_cost_bps=2.0)
            c.assert_close(f"{name}.extra_2bps_pf", float(cost2["profit_factor_bps"]), float(expected["extra_2bps_pf"]))

        reference_rows = [
            {"reference": "M5_ENTRY_0P15_ATR5_6M", **m5_entry_metrics},
            {"reference": "M5_RUNNER75_M15_MACD_RISING_M5_RCI_TURNDOWN", **m5_runner_metrics},
            {"reference": "H1_ENTRY_0P05_ATR1H_M5_CONFIRM_30M", **h1_entry_metrics},
            {"reference": "H1_RUNNER50_H4_D1_MACD_RISING_H1_RCI_TURNDOWN", **h1_runner_metrics},
            {"reference": "H4_PRIMARY_RECLAIM_M15_CONFIRM_60M", **h4_entry_metrics},
        ]
        cost_rows: list[dict[str, Any]] = []
        yearly_rows: list[dict[str, Any]] = []
        quarterly_rows: list[dict[str, Any]] = []
        references = (("M5_ENTRY", m5_entry, "native_return_bps"), ("M5_RUNNER75", m5_runner, "weighted_return_bps"), ("H1_ENTRY", h1_entry, "native_return_bps"), ("H1_RUNNER50", h1_runner, "weighted_return_bps"), ("H4_ENTRY", h4_entry, "native_return_bps"))
        for name, rows, value_key in references:
            for cost in EXTRA_COSTS:
                cost_rows.append({"reference": name, "extra_cost_bps_per_trade": cost, **p.metric_rows(rows, value_key=value_key, time_key="actual_entry_time", extra_cost_bps=cost)})
            yearly_rows.extend({"reference": name, **row} for row in p.group_metrics(rows, value_key=value_key, time_key="actual_entry_time", mode="year"))
            quarterly_rows.extend({"reference": name, **row} for row in p.group_metrics(rows, value_key=value_key, time_key="actual_entry_time", mode="quarter"))
    except Exception as exc:
        print(f"[M10A BLOCKED] {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH", "stage": STAGE,
        "status": "PASS_DETERMINISTIC_HISTORICAL_REPRODUCTION_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample": "research-exposed 2023-01-03 through 2026-06-19 GOLD history; not fresh forward evidence",
        "raw_frozen_branches": raw,
        "references": {"M5_ENTRY": m5_entry_metrics, "M5_RUNNER75": {**m5_runner_metrics, "overlap_skips": len(m5_overlap)}, "H1_ENTRY": h1_entry_metrics, "H1_RUNNER50": {**h1_runner_metrics, "overlap_skips": len(h1_overlap)}, "H4_ENTRY": h4_entry_metrics},
        "reference_contract": {
            "M5": "Frozen M9S S1; 0.15*latest fully closed M5 Wilder ATR14 reclaim; max 6 closed M1 bars; latest fully closed M15 MACD rising at native exit enables 75% runner; first causal M5 RCI9 turn-down exit; one-position.",
            "H1": "Frozen M9S S3; 0.05*latest fully closed H1 Wilder ATR14 reclaim; fully closed M5 confirmation; max 30m; latest fully closed H4+D1 MACD rising at native exit enables 50% runner; first causal H1 RCI9 turn-down exit; one-position.",
            "H4": "Frozen M9S S4; original PRIMARY price reclaim confirmed by fully closed M15 within 60m; native exit only; no runner promotion."
        },
        "guardrails": {"newest_csv_row_contract": "CLOSED", "historical_spread_used": True, "commission": "NOT_MODELED", "swap": "NOT_MODELED", "closed_bars_only_for_entry_context": True, "future_outcome_used_in_entry_gate": False, "historical_research_exposed": True, "fresh_forward_validated": False, "m9v_modified_or_reset": False, "m9y_modified_or_reset": False, "historical_backfill": False, "automatic_live_promotion": False, "discord_send": False, "mt5_order": False, "live_ready": False, "final_signal": False, "audit_only": True},
        "next": "Only after user-local deterministic reproduction PASS may a separate fresh prospective contract be frozen. Never retrofit M9V/M9Y or reuse their starts."
    }
    out_root = Path(os.environ.get("M10A_OUTPUT_ROOT", "")) if os.environ.get("M10A_OUTPUT_ROOT") else local_root / "outputs" / "M10A"
    archive = out_root / "archive" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text("M10A independently reproduces historical M9Z GOLD M5/H1/H4 payoff references using only frozen hashed raw CSVs.\nM9V/M9Y are not modified/reset/backfilled. All history is research-exposed; PASS is not fresh validation.\nSubmit 99_UPLOAD_PACKAGE.zip only.\n", encoding="utf-8")
    c.dump_json(archive / "01_summary.json", summary)
    c.write_csv(archive / "02_reference_summary.csv", reference_rows)
    c.write_csv(archive / "03_cost_sensitivity.csv", cost_rows)
    c.write_csv(archive / "04_yearly.csv", yearly_rows)
    c.write_csv(archive / "05_quarterly.csv", quarterly_rows)
    c.write_csv(archive / "06_m5_entry_ledger.csv", m5_entry)
    c.write_csv(archive / "07_m5_runner75_ledger.csv", m5_runner)
    c.write_csv(archive / "08_h1_entry_ledger.csv", h1_entry)
    c.write_csv(archive / "09_h1_runner50_ledger.csv", h1_runner)
    c.write_csv(archive / "10_h4_entry_ledger.csv", h4_entry)
    c.write_csv(archive / "11_overlap_skips.csv", [{"reference": "M5_RUNNER75", **row} for row in m5_overlap] + [{"reference": "H1_RUNNER50", **row} for row in h1_overlap])
    c.dump_json(archive / "12_data_quality.json", {"data_root": str(data_root), "point": point, "hashes": {tf: {"file": filename, "sha256": digest} for tf, (filename, digest) in c.EXPECTED_FILES.items()}, "newest_csv_row_contract": "CLOSED", "nearest_m1_fallback": False})
    (archive / "13_audit.log").write_text("\n".join(["status=PASS_DETERMINISTIC_HISTORICAL_REPRODUCTION_ONLY", f"M5_ENTRY={m5_entry_metrics['count']} PF={m5_entry_metrics['profit_factor_bps']}", f"M5_RUNNER75={m5_runner_metrics['count']} PF={m5_runner_metrics['profit_factor_bps']} overlap_skips={len(m5_overlap)}", f"H1_ENTRY={h1_entry_metrics['count']} PF={h1_entry_metrics['profit_factor_bps']}", f"H1_RUNNER50={h1_runner_metrics['count']} PF={h1_runner_metrics['profit_factor_bps']} overlap_skips={len(h1_overlap)}", f"H4_ENTRY={h4_entry_metrics['count']} PF={h4_entry_metrics['profit_factor_bps']}", "future_outcome_used_in_entry_gate=false", "m9v_modified_or_reset=false", "m9y_modified_or_reset=false", "historical_backfill=false", "automatic_live_promotion=false", "discord_send=false", "mt5_order=false", "live_ready=false", "final_signal=false", ""]), encoding="utf-8")
    names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_reference_summary.csv", "03_cost_sensitivity.csv", "04_yearly.csv", "05_quarterly.csv", "06_m5_entry_ledger.csv", "07_m5_runner75_ledger.csv", "08_h1_entry_ledger.csv", "09_h1_runner50_ledger.csv", "10_h4_entry_ledger.csv", "11_overlap_skips.csv", "12_data_quality.json", "13_audit.log"]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print("[M10A PASS] " f"M5={m5_entry_metrics['count']} PF={m5_entry_metrics['profit_factor_bps']:.12f} " f"M5R75={m5_runner_metrics['count']} PF={m5_runner_metrics['profit_factor_bps']:.12f} " f"H1={h1_entry_metrics['count']} PF={h1_entry_metrics['profit_factor_bps']:.12f} " f"H1R50={h1_runner_metrics['count']} PF={h1_runner_metrics['profit_factor_bps']:.12f} " f"H4={h4_entry_metrics['count']} PF={h4_entry_metrics['profit_factor_bps']:.12f}")
    print("[M10A OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
