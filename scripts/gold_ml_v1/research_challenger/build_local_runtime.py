from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from raw_engine import (
    SleeveResult,
    apply_historical_ml_truth,
    build_acore,
    build_bstate,
    build_p16_pre_ml,
    build_p18,
    build_p19_pre_ml,
    build_watch024a,
    to_portfolio_rows,
)

EXIT_OK = 0
EXIT_INPUT = 2
EXIT_PARITY = 3

SLEEVES = {
    "A_CORE": {"candidate_id": "GML1-WATCH-022-C", "direction": "LONG", "weight": 1.0, "size": 1.4769230769230768},
    "B_STATE": {"candidate_id": "GML1-H1D1-STATEFUL-REENTRY24-C", "direction": "LONG", "weight": 1.0, "size": 1.4769230769230768},
    "P16": {"candidate_id": "GML1-PROV-016-APPROX", "direction": "LONG", "weight": 0.5, "size": 0.7384615384615384},
    "P18": {"candidate_id": "GML1-PROV-018-APPROX", "direction": "LONG", "weight": 0.25, "size": 0.3692307692307692},
    "P19": {"candidate_id": "GML1-PROV-019-APPROX", "direction": "SHORT", "weight": 1.0, "size": 1.4769230769230768},
    "W024A": {"candidate_id": "GML1-WATCH-024-A", "direction": "SHORT", "weight": 1.0, "size": 1.0},
}

EXPECTED_FINAL = {
    2024: {"trades": 271, "win_rate": 0.6568265682656826, "pf": 2.494488621652696, "R": 137.48083552627205, "DD": 5.907692307692287},
    2025: {"trades": 402, "win_rate": 0.5920398009950248, "pf": 2.0121618989110295, "R": 148.09279029902123, "DD": 7.384615384615387},
    2026: {"trades": 101, "win_rate": 0.6138613861386139, "pf": 1.8772867024210496, "R": 42.055774842215214, "DD": 6.7997924973867985},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def metric(frame: pd.DataFrame) -> dict[str, float | int | None]:
    values = frame["weighted_r"].astype(float)
    gp = float(values[values > 0].sum())
    gl = float(-values[values < 0].sum())
    equity = values.cumsum().to_numpy(float)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    dd = peaks[1:] - equity if len(equity) else np.array([], dtype=float)
    return {
        "trades": int(len(frame)),
        "win_rate": float((frame["r"] > 0).mean()) if len(frame) else None,
        "pf": gp / gl if gl else None,
        "R": float(values.sum()),
        "DD": float(dd.max()) if len(dd) else 0.0,
    }


def _normalized_target(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["decision_time"] = pd.to_datetime(frame["decision_time"], errors="raise")
    frame["exit_time"] = pd.to_datetime(frame["exit_time"], errors="raise")
    mask = frame["comp"].eq("A_CORE")
    frame.loc[mask & frame["candidate_id"].isna(), "candidate_id"] = SLEEVES["A_CORE"]["candidate_id"]
    frame.loc[mask & frame["w"].isna(), "w"] = 1.0
    frame["historical_only"] = frame["comp"].isin(["P16", "P19"])
    return frame


def _keyed(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["candidate_id", "decision_time", "exit_time", "r", "direction", "comp", "w", "size", "weighted_r", "historical_only"]
    out = frame[columns].copy()
    out = out.sort_values(["decision_time", "exit_time", "comp", "candidate_id"], kind="mergesort").reset_index(drop=True)
    for column in ["r", "w", "size", "weighted_r"]:
        out[column] = pd.to_numeric(out[column], errors="raise")
    return out


def compare_frames(actual: pd.DataFrame, target: pd.DataFrame, tolerance: float = 1e-9) -> dict[str, Any]:
    actual = _keyed(actual)
    target = _keyed(target)
    key_columns = ["candidate_id", "decision_time", "exit_time", "direction", "comp", "historical_only"]
    actual_keys = set(map(tuple, actual[key_columns].itertuples(index=False, name=None)))
    target_keys = set(map(tuple, target[key_columns].itertuples(index=False, name=None)))
    missing = sorted(target_keys - actual_keys)
    extra = sorted(actual_keys - target_keys)
    merged = target.merge(actual, on=key_columns, how="inner", suffixes=("_target", "_actual"))
    numeric_diff: dict[str, float] = {}
    for column in ["r", "w", "size", "weighted_r"]:
        diff = (merged[f"{column}_target"] - merged[f"{column}_actual"]).abs()
        numeric_diff[column] = float(diff.max()) if len(diff) else 0.0
    passed = not missing and not extra and all(value <= tolerance for value in numeric_diff.values())
    return {
        "passed": passed,
        "actual_rows": int(len(actual)),
        "target_rows": int(len(target)),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "missing_sample": [list(item) for item in missing[:10]],
        "extra_sample": [list(item) for item in extra[:10]],
        "max_numeric_difference": numeric_diff,
    }


def make_sleeve(comp: str, trades: pd.DataFrame, historical_only: bool = False) -> SleeveResult:
    config = SLEEVES[comp]
    return SleeveResult(
        candidate_id=str(config["candidate_id"]),
        comp=comp,
        direction=str(config["direction"]),
        weight=float(config["weight"]),
        size=float(config["size"]),
        trades=trades,
        historical_only=historical_only,
    )


def build(raw_dir: Path, artifact_dir: Path, truth_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    acore = build_acore(raw_dir)
    bstate = build_bstate(raw_dir)
    p18 = build_p18(raw_dir)
    watch024a = build_watch024a(raw_dir)
    p16_pre = build_p16_pre_ml(raw_dir)
    p19_pre = build_p19_pre_ml(raw_dir)
    p16 = apply_historical_ml_truth(p16_pre, truth_dir / "p16_ml_gate_historical_truth.csv", "P16")
    p19 = apply_historical_ml_truth(p19_pre, truth_dir / "p19_ml_gate_historical_truth.csv", "P19")

    sleeves = [
        make_sleeve("A_CORE", acore),
        make_sleeve("B_STATE", bstate),
        make_sleeve("P16", p16, historical_only=True),
        make_sleeve("P18", p18),
        make_sleeve("P19", p19, historical_only=True),
        make_sleeve("W024A", watch024a),
    ]
    rows = pd.concat([to_portfolio_rows(item) for item in sleeves], ignore_index=True)
    rows = rows[rows["decision_time"].dt.year.between(2024, 2026)].copy()
    rows = rows.sort_values(["decision_time", "exit_time", "comp", "candidate_id"], kind="mergesort").reset_index(drop=True)

    details: dict[str, Any] = {
        "raw_counts_all_available": {
            "A_CORE": int(len(acore)),
            "B_STATE": int(len(bstate)),
            "P16_pre_ml": int(len(p16_pre[p16_pre["decision_time"].dt.year.between(2024, 2026)])),
            "P16_historical_keep": int(len(p16)),
            "P18": int(len(p18)),
            "P19_pre_ml": int(len(p19_pre[p19_pre["decision_time"].dt.year.between(2024, 2026)])),
            "P19_historical_keep": int(len(p19)),
            "W024A": int(len(watch024a)),
        },
        "year_checks": {},
    }
    for year in (2024, 2025, 2026):
        actual = rows[rows["decision_time"].dt.year.eq(year)].copy()
        target = _normalized_target(artifact_dir / f"watch024a_challenger_{year}.csv")
        parity = compare_frames(actual, target)
        metrics = metric(actual)
        expected = EXPECTED_FINAL[year]
        metric_diff = {key: abs(float(metrics[key]) - float(expected[key])) for key in expected}
        metric_pass = all(value <= 1e-9 * max(1.0, abs(float(expected[key]))) for key, value in metric_diff.items())
        details["year_checks"][str(year)] = {
            "row_parity": parity,
            "metrics": metrics,
            "expected_metrics": expected,
            "metric_difference": metric_diff,
            "metric_passed": metric_pass,
            "passed": bool(parity["passed"] and metric_pass),
        }
    details["passed"] = all(item["passed"] for item in details["year_checks"].values())
    return rows, details


def write_outputs(rows: pd.DataFrame, details: dict[str, Any], output_dir: Path, raw_dir: Path, artifact_dir: Path, truth_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for year in (2024, 2025, 2026):
        frame = rows[rows["decision_time"].dt.year.eq(year)].copy()
        frame.to_csv(output_dir / f"research_challenger_local_{year}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S", lineterminator="\n")
    metrics = []
    for year in (2024, 2025, 2026):
        metrics.append({"year": year, **metric(rows[rows["decision_time"].dt.year.eq(year)])})
    pd.DataFrame(metrics).to_csv(output_dir / "metrics_by_year.csv", index=False, lineterminator="\n")
    report = {
        "status": "PASS" if details["passed"] else "FAIL",
        "mode": "research_challenger_historical_parity",
        "p16_p19_policy": "historical frozen ML gate truth only; disabled for live/as-of decisions",
        "raw_dir": str(raw_dir),
        "artifact_dir": str(artifact_dir),
        "truth_dir": str(truth_dir),
        "details": details,
        "controls": {
            "audit_only": True,
            "live_p16": False,
            "live_p19": False,
            "final_signal": False,
            "discord": False,
            "mt5_order": False,
        },
    }
    (output_dir / "parity_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[3]
    default_artifact_dir = root / "config/gold_ml_v1/research_challenger/final_20260627/artifacts"
    default_truth_dir = root / "config/gold_ml_v1/research_challenger/runtime_20260628/registries"
    parser = argparse.ArgumentParser(description="Build and verify the GML1 final research challenger from raw 2023-2026 CSVs")
    parser.add_argument("--raw-dir", type=Path, required=True, help="Directory containing gold_v3_2023_2026_m1/m5/m15/h1/h4/d1.csv")
    parser.add_argument("--artifact-dir", type=Path, default=default_artifact_dir)
    parser.add_argument("--truth-dir", type=Path, default=default_truth_dir)
    parser.add_argument("--output-dir", type=Path, default=root / "outputs/gold_ml_v1/research_challenger_local_runtime")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        rows, details = build(args.raw_dir.resolve(), args.artifact_dir.resolve(), args.truth_dir.resolve())
        write_outputs(rows, details, args.output_dir.resolve(), args.raw_dir.resolve(), args.artifact_dir.resolve(), args.truth_dir.resolve())
        print(json.dumps({"status": "PASS" if details["passed"] else "FAIL", "output_dir": str(args.output_dir.resolve())}, ensure_ascii=False))
        return EXIT_OK if details["passed"] else EXIT_PARITY
    except (FileNotFoundError, ValueError, KeyError, pd.errors.ParserError) as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "input_error.txt").write_text(str(exc), encoding="utf-8", newline="\n")
        print(str(exc), file=sys.stderr)
        return EXIT_INPUT


if __name__ == "__main__":
    raise SystemExit(main())
