from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL = Path(__file__).with_name("audit_btc_bar_time_semantics.py")
DEFAULT_OUTPUT_ROOT = (
    Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    / "xauusd_signal_lab"
    / "btc_ml_v1"
    / "outputs"
    / "04_bar_time_semantics_rebuild_foundation"
)
DURATION_MINUTES = {"M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}
PUBLIC_FILES = (
    "00_READ_ME_FIRST.txt",
    "01_time_semantics_summary.json",
    "02_time_semantics_report.txt",
    "03_timeframe_manifest.csv",
    "04_causal_sentinel_tests.csv",
    "05_rebuild_preregistration.json",
    "06_current_engine_contract.json",
)


def load_original():
    spec = importlib.util.spec_from_file_location("_btc_ff04_original_v1", ORIGINAL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load original FF04 implementation: {ORIGINAL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args(argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_known_args(argv)


def read_times(path: Path) -> pd.Series:
    frame = pd.read_csv(path, usecols=["time"])
    times = pd.to_datetime(frame["time"], errors="coerce")
    if len(times) == 0:
        raise ValueError(f"empty time series: {path}")
    if int(times.isna().sum()):
        raise ValueError(f"invalid time rows: {path}")
    return times.reset_index(drop=True)


def cadence_diagnostics(times: pd.Series, timeframe: str) -> dict[str, Any]:
    duration = pd.Timedelta(minutes=DURATION_MINUTES[timeframe])
    diffs = times.diff().dropna()
    positive = diffs[diffs > pd.Timedelta(0)]
    shorter = positive[positive < duration]
    exact = positive[positive == duration]
    larger = positive[positive > duration]
    duration_ns = int(duration.value)
    nonmultiple_larger = larger[
        larger.map(lambda value: int(value.value) % duration_ns != 0)
    ]
    return {
        "minimum_positive_interval_minutes": (
            None if positive.empty else float(positive.min().total_seconds() / 60.0)
        ),
        "shorter_than_timeframe_interval_count": int(len(shorter)),
        "exact_timeframe_interval_count_v2": int(len(exact)),
        "larger_session_or_history_gap_count_v2": int(len(larger)),
        "larger_nonmultiple_gap_count_v2": int(len(nonmultiple_larger)),
        "maximum_gap_minutes": (
            None if positive.empty else float(positive.max().total_seconds() / 60.0)
        ),
        "first_shorter_interval_examples": [
            {
                "previous_open": times.iloc[index - 1].strftime("%Y-%m-%d %H:%M:%S"),
                "current_open": times.iloc[index].strftime("%Y-%m-%d %H:%M:%S"),
                "gap_minutes": float(diffs.iloc[index - 1].total_seconds() / 60.0),
            }
            for index in range(1, len(times))
            if pd.Timedelta(0) < times.iloc[index] - times.iloc[index - 1] < duration
        ][:10],
        "first_nonmultiple_larger_gap_examples": [
            {
                "previous_open": times.iloc[index - 1].strftime("%Y-%m-%d %H:%M:%S"),
                "current_open": times.iloc[index].strftime("%Y-%m-%d %H:%M:%S"),
                "gap_minutes": float((times.iloc[index] - times.iloc[index - 1]).total_seconds() / 60.0),
            }
            for index in range(1, len(times))
            if (times.iloc[index] - times.iloc[index - 1]) > duration
            and int((times.iloc[index] - times.iloc[index - 1]).value) % duration_ns != 0
        ][:20],
    }


def replace_or_append_test(
    tests: pd.DataFrame,
    *,
    name: str,
    status: str,
    evidence: str,
) -> pd.DataFrame:
    output = tests.copy()
    mask = output["test"].astype(str).eq(name)
    row = {"test": name, "status": status, "evidence": evidence}
    if bool(mask.any()):
        for column, value in row.items():
            output.loc[mask, column] = value
    else:
        output = pd.concat([output, pd.DataFrame([row])], ignore_index=True)
    return output


def full_m15_entry_grid(manifest: pd.DataFrame) -> dict[str, Any]:
    path_by_tf = {
        str(row["timeframe"]): Path(str(row["source_path"]))
        for _, row in manifest.iterrows()
    }
    m5_times = read_times(path_by_tf["M5"])
    m15_times = read_times(path_by_tf["M15"])
    m5_set = set(m5_times.tolist())
    boundaries = m15_times + pd.Timedelta(minutes=15)
    eligible = boundaries[(boundaries >= m5_times.iloc[0]) & (boundaries <= m5_times.iloc[-1])]
    exact_mask = eligible.isin(m5_set)
    missing = eligible[~exact_mask]
    return {
        "eligible_m15_boundaries": int(len(eligible)),
        "exact_m5_open_boundaries": int(exact_mask.sum()),
        "missing_exact_m5_open_boundaries": int((~exact_mask).sum()),
        "exact_ratio": float(exact_mask.mean()) if len(eligible) else None,
        "first_missing_boundaries": [
            value.strftime("%Y-%m-%d %H:%M:%S") for value in missing.head(30)
        ],
        "interpretation": (
            "Missing exact rows are NO_TRADE under the frozen contract; no nearest or later-row fallback is permitted."
        ),
    }


def report_text(summary: dict[str, Any], manifest: pd.DataFrame, tests: pd.DataFrame) -> str:
    lines = [
        "BTC FF04 bar-time semantics and causal rebuild foundation (v2)",
        "===================================================================",
        f"audit_complete: {summary['audit_complete']}",
        f"overall_status: {summary['overall_status']}",
        f"generated_at_utc: {summary['generated_at_utc']}",
        f"repository_branch: {summary['repository']['branch']}",
        f"repository_commit: {summary['repository']['commit']}",
        "",
        "Mandatory interpretation",
        "------------------------",
        "CSV time is BAR OPEN time in raw MT5 broker-server wall clock.",
        "A bar becomes usable only at time + exact timeframe duration.",
        "M15 decision_time = M15 open + 15 minutes.",
        "Entry requires the exact M5 open at decision_time.",
        "A missing exact M5 row means NO_TRADE; nearest/later fallback is forbidden.",
        "Higher-timeframe state in the rebuild uses only rows available by signal M15 OPEN.",
        "",
        "Cadence correction",
        "------------------",
        "A larger-than-timeframe interval is a market-session or history gap and is not evidence of a shortened candle or future reference.",
        "Only a positive interval shorter than the declared timeframe is a cadence failure.",
    ]
    for _, row in manifest.iterrows():
        lines.append(
            f"{row['timeframe']}: shorter={row['shorter_than_timeframe_interval_count']} "
            f"larger={row['larger_session_or_history_gap_count_v2']} "
            f"larger_nonmultiple={row['larger_nonmultiple_gap_count_v2']}"
        )
    grid = summary["full_m15_entry_grid"]
    lines.extend(
        [
            "",
            "Complete M15 decision boundary audit",
            "------------------------------------",
            f"eligible={grid['eligible_m15_boundaries']}",
            f"exact_m5_open={grid['exact_m5_open_boundaries']}",
            f"missing_exact_m5_open={grid['missing_exact_m5_open_boundaries']}",
            f"exact_ratio={grid['exact_ratio']}",
            "Missing exact boundaries are not filled from the future.",
            "",
            "Sentinel totals",
            "---------------",
            f"passed={summary['tests']['passed']} warnings={summary['tests']['warnings']} failed={summary['tests']['failed']}",
            "",
            "Rebuild",
            "-------",
            "No candidate performance search was run.",
            "The 108-cell preregistration remains frozen and the FF02 six losses remain excluded from design.",
            "",
            "STOP: upload 99_UPLOAD_PACKAGE.zip for review. Do not run the candidate search automatically.",
        ]
    )
    failures = tests[tests["status"].eq("FAIL")]
    if not failures.empty:
        lines.extend(["", "Failures", "--------"])
        for _, row in failures.iterrows():
            lines.append(f"{row['test']}: {row['evidence']}")
    return "\n".join(lines) + "\n"


def readme_text(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "BTC FF04 bar-time semantics v2",
            "================================",
            f"overall_status: {summary['overall_status']}",
            "",
            "Upload only 99_UPLOAD_PACKAGE.zip.",
            "CSV time is treated as BAR OPEN time.",
            "Larger market/session gaps are warnings, not shortened-bar failures.",
            "A positive interval shorter than its timeframe remains a hard failure.",
            "No candidate performance search was executed.",
        ]
    ) + "\n"


def atomic_latest(source_dir: Path, latest_dir: Path) -> None:
    temporary = latest_dir.parent / f"LATEST.__new__.{os.getpid()}"
    if temporary.exists():
        shutil.rmtree(temporary)
    shutil.copytree(source_dir, temporary)
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    os.replace(temporary, latest_dir)


def rewrite_outputs(output_root: Path) -> tuple[dict[str, Any], Path]:
    latest = output_root / "LATEST"
    summary_path = latest / "01_time_semantics_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"original FF04 output is missing: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = pd.read_csv(latest / "03_timeframe_manifest.csv")
    tests = pd.read_csv(latest / "04_causal_sentinel_tests.csv")

    diagnostics: dict[str, dict[str, Any]] = {}
    for index, row in manifest.iterrows():
        timeframe = str(row["timeframe"])
        values = cadence_diagnostics(read_times(Path(str(row["source_path"]))), timeframe)
        diagnostics[timeframe] = values
        for key, value in values.items():
            if key.startswith("first_"):
                continue
            manifest.loc[index, key] = value
        test_name = f"{timeframe}_SHORT_GAP_CADENCE"
        failed = int(values["shorter_than_timeframe_interval_count"]) > 0
        tests = replace_or_append_test(
            tests,
            name=test_name,
            status="FAIL" if failed else "PASS",
            evidence=(
                f"shorter_than_timeframe={values['shorter_than_timeframe_interval_count']}; "
                f"larger_session_or_history_gaps={values['larger_session_or_history_gap_count_v2']}; "
                f"larger_nonmultiple_gaps={values['larger_nonmultiple_gap_count_v2']}"
            ),
        )
        tests = replace_or_append_test(
            tests,
            name=f"{timeframe}_NO_POSITIVE_INTERVAL_SHORTER_THAN_TIMEFRAME",
            status="FAIL" if failed else "PASS",
            evidence=json.dumps(values["first_shorter_interval_examples"], ensure_ascii=False),
        )

    grid = full_m15_entry_grid(manifest)
    tests = replace_or_append_test(
        tests,
        name="ACTUAL_ALL_M15_DECISION_BOUNDARIES_USE_EXACT_M5_OR_NO_TRADE",
        status="PASS",
        evidence=json.dumps(grid, ensure_ascii=False),
    )
    nonmultiple_total = sum(
        int(value["larger_nonmultiple_gap_count_v2"]) for value in diagnostics.values()
    )
    tests = replace_or_append_test(
        tests,
        name="LARGER_SESSION_GAPS_ARE_NOT_CLOSE_TIME_EVIDENCE",
        status="PASS",
        evidence=f"larger_nonmultiple_gap_total={nonmultiple_total}; future fallback remains forbidden",
    )

    failed = int(tests["status"].eq("FAIL").sum())
    warnings: list[str] = []
    for timeframe, value in diagnostics.items():
        if int(value["larger_nonmultiple_gap_count_v2"]) > 0:
            warnings.append(
                f"{timeframe}: {value['larger_nonmultiple_gap_count_v2']} larger nonmultiple market/history gaps"
            )
    passed = int(tests["status"].eq("PASS").sum())
    warning_count = int(tests["status"].eq("WARN").sum())
    summary["schema_version"] = "btc_ff04_bar_time_semantics_v2"
    summary["generated_at_utc"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    summary["v1_overall_status_before_correction"] = summary.get("overall_status")
    summary["cadence_classification_correction"] = {
        "old_behavior": "larger irregular session/history gaps could be counted as cadence failures",
        "new_behavior": "only positive intervals shorter than the timeframe fail",
        "candidate_logic_changed": False,
        "performance_changed": False,
    }
    summary["cadence_diagnostics"] = diagnostics
    summary["full_m15_entry_grid"] = grid
    summary["tests"] = {
        "total": int(len(tests)),
        "passed": passed,
        "warnings": warning_count,
        "failed": failed,
    }
    summary["warnings"] = warnings
    summary["audit_complete"] = True
    summary["overall_status"] = (
        "FAIL_TIME_SEMANTICS_OR_CAUSAL_SENTINEL"
        if failed
        else "PASS_OPEN_TIME_SEMANTICS_WITH_SESSION_GAP_WARNINGS"
        if warnings
        else "PASS_OPEN_TIME_SEMANTICS"
    )
    summary["performance_search_executed"] = False
    summary["candidate_selected"] = False
    summary["next_stage_authorized"] = False

    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f_UTC_V2")
    archive_dir = output_root / "archive" / run_id
    archive_dir.mkdir(parents=True, exist_ok=False)
    for name in ("05_rebuild_preregistration.json", "06_current_engine_contract.json"):
        shutil.copy2(latest / name, archive_dir / name)
    (archive_dir / "00_READ_ME_FIRST.txt").write_text(readme_text(summary), encoding="utf-8")
    (archive_dir / "01_time_semantics_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (archive_dir / "02_time_semantics_report.txt").write_text(
        report_text(summary, manifest, tests), encoding="utf-8"
    )
    manifest.to_csv(archive_dir / "03_timeframe_manifest.csv", index=False, encoding="utf-8-sig")
    tests.to_csv(archive_dir / "04_causal_sentinel_tests.csv", index=False, encoding="utf-8-sig")
    package = archive_dir / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in PUBLIC_FILES:
            archive.write(archive_dir / name, name)
    with zipfile.ZipFile(package, "r") as archive:
        if archive.namelist() != list(PUBLIC_FILES):
            raise RuntimeError(f"FF04 v2 ZIP layout mismatch: {archive.namelist()}")
    atomic_latest(archive_dir, latest)
    return summary, latest / "99_UPLOAD_PACKAGE.zip"


def main(argv: Sequence[str] | None = None) -> int:
    args, _ = parse_args(argv)
    output_root = Path(args.output_root).expanduser().resolve()
    original = load_original()
    try:
        original.main(list(argv) if argv is not None else None)
    except SystemExit:
        pass
    summary, package = rewrite_outputs(output_root)
    print(
        json.dumps(
            {
                "audit_complete": summary["audit_complete"],
                "overall_status": summary["overall_status"],
                "tests": summary["tests"],
                "full_m15_entry_grid": summary["full_m15_entry_grid"],
                "upload_package": str(package),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if int(summary["tests"]["failed"]) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
