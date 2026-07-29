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
CUTOFF = pd.Timestamp("2026-07-02 02:15:00")
TF_MINUTES = {"M5": 5, "M15": 15, "H1": 60, "D1": 1440, "H4": 240}
TFS = ("M5", "M15", "H1", "D1", "H4")
FRESHNESS_PY = ROOT / "scripts" / "run_btc_youtube_candidates_dry_run_cycle.py"
RESOLVER_PY = ROOT / "scripts" / "run_btc_youtube_candidates_operational_forever.py"
STAGE_ID = "01_fresh_forward_availability"
DEFAULT_OUTPUT_ROOT = (
    Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    / "xauusd_signal_lab"
    / "btc_ml_v1"
    / "outputs"
    / STAGE_ID
)
KNOWN_TERMINAL = Path(
    r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
)
KNOWN_HISTORY = Path(r"C:\BTC_REPRO\history")

CANDIDATE_REQUIREMENTS = {
    "BTC4_RISK_CAP_400": ("H4_AFTER_CUTOFF", "M5_AFTER_CUTOFF"),
    "BTC5_TWO_PIVOT_P2_CLEAN_N_382_786": ("M5_AFTER_CUTOFF",),
    "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886": ("M15_AFTER_CUTOFF",),
    "BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110": (
        "M5_AFTER_CUTOFF",
        "M15_AFTER_CUTOFF",
        "H1_AFTER_CUTOFF",
    ),
    "BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080": (
        "M5_AFTER_CUTOFF",
        "M15_AFTER_CUTOFF",
        "H1_AFTER_CUTOFF",
        "D1_AFTER_CUTOFF",
    ),
}


def load_module(name: str, path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"required existing BTC support module is missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load existing BTC support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def text_time(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def path_key(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().resolve()))


def git_identity() -> dict[str, str]:
    marker = ROOT / ".git"
    result = {"commit": "UNKNOWN_NO_GIT_METADATA", "branch": "UNKNOWN_NO_GIT_METADATA"}
    if marker.is_file():
        text = marker.read_text(encoding="utf-8", errors="replace").strip()
        if text.lower().startswith("gitdir:"):
            raw = Path(text.split(":", 1)[1].strip())
            marker = raw if raw.is_absolute() else (ROOT / raw).resolve()
    if not marker.is_dir():
        return result
    try:
        head = (marker / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
        if not head.startswith("ref:"):
            return {"commit": head, "branch": "DETACHED_HEAD"}
        ref = head.split(":", 1)[1].strip()
        result["branch"] = ref.removeprefix("refs/heads/")
        loose = marker / ref
        if loose.is_file():
            result["commit"] = loose.read_text(encoding="utf-8", errors="replace").strip()
            return result
        packed = marker / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line or line.startswith(("#", "^")):
                    continue
                sha, name = line.split(" ", 1)
                if name.strip() == ref:
                    result["commit"] = sha.strip()
                    return result
        result["commit"] = "UNKNOWN_GIT_REF_NOT_RESOLVED"
    except Exception as exc:
        result = {
            "commit": f"UNKNOWN_GIT_READ_FAILED:{type(exc).__name__}",
            "branch": "UNKNOWN_GIT_READ_FAILED",
        }
    return result


def read_times(path: Path) -> tuple[dict[str, Any], pd.Series | None]:
    resolved = path.expanduser().resolve()
    row: dict[str, Any] = {
        "path": str(resolved),
        "file_size_bytes": None,
        "rows": 0,
        "first_raw_mt5_broker_server_timestamp": "",
        "latest_raw_closed_bar_timestamp": "",
        "timestamp_timezone_state": "UNKNOWN",
        "selected_broker_utc_offset_hours": None,
        "broker_offset_inference_evidence": {},
        "latest_utc_converted_closed_bar_timestamp": "",
        "rows_strictly_after_cutoff_utc": None,
        "non_ascending_timestamp_count": None,
        "duplicate_timestamp_count": None,
        "read_error_or_ambiguity": "",
    }
    try:
        row["file_size_bytes"] = int(resolved.stat().st_size)
        last_error = ""
        for kwargs in ({"low_memory": False}, {"sep": None, "engine": "python"}):
            try:
                header = pd.read_csv(resolved, nrows=0, **kwargs)
                columns = {str(column).strip().lower(): column for column in header.columns}
                if "time" not in columns:
                    raise ValueError(f"missing time column: {list(header.columns)}")
                frame = pd.read_csv(resolved, usecols=[columns["time"]], **kwargs)
                break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
        else:
            raise ValueError(last_error)

        times = pd.to_datetime(frame.iloc[:, 0], errors="coerce")
        if len(times) == 0:
            raise ValueError("empty CSV")
        invalid = int(times.isna().sum())
        if invalid:
            raise ValueError(f"invalid time rows: {invalid}")

        aware = [getattr(value, "tzinfo", None) is not None for value in times]
        if all(not value for value in aware):
            timezone_state = "NAIVE_MT5_BROKER_SERVER_WALL_CLOCK"
        elif all(aware):
            timezone_state = "TIMEZONE_AWARE_INPUT"
        else:
            raise ValueError("mixed naive and timezone-aware timestamps")

        row.update(
            rows=int(len(times)),
            first_raw_mt5_broker_server_timestamp=text_time(times.iloc[0]),
            latest_raw_closed_bar_timestamp=text_time(times.iloc[-1]),
            timestamp_timezone_state=timezone_state,
            non_ascending_timestamp_count=int((times.diff() < pd.Timedelta(0)).sum()),
            duplicate_timestamp_count=int(times.duplicated(keep="first").sum()),
        )
        return row, times
    except Exception as exc:
        row["read_error_or_ambiguity"] = f"{type(exc).__name__}: {exc}"
        return row, None


def exact_file(directory: Path, filename: str) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.name.lower() == filename.lower()
    )


def add_unique(found: dict[str, list[Path]], timeframe: str, path: Path, seen: set[str]) -> None:
    if path.is_file() and path_key(path) not in seen:
        seen.add(path_key(path))
        found[timeframe].append(path)


def discover(resolver: Any, args: argparse.Namespace) -> tuple[dict[str, list[Path]], list[dict[str, Any]]]:
    found = {timeframe: [] for timeframe in TFS}
    locations: list[dict[str, Any]] = []
    seen: set[str] = set()

    explicit = {
        "M5": args.m5_csv,
        "M15": args.m15_csv,
        "H1": args.h1_csv,
        "D1": args.d1_csv,
        "H4": args.h4_csv,
    }
    for timeframe, path in explicit.items():
        if path is None:
            continue
        locations.append({
            "label": f"EXPLICIT_{timeframe}_CSV",
            "path": str(path.expanduser().resolve()),
            "exists": path.is_file(),
            "resolution_errors": [] if path.is_file() else ["explicit file does not exist"],
        })
        add_unique(found, timeframe, path, seen)

    for label, directory in (
        ("REPOSITORY_FILES", args.repo_files_dir),
        ("KNOWN_MT5_TERMINAL_FILES", args.terminal_files_dir),
        ("KNOWN_REPRO_HISTORY", args.repro_history_dir),
    ):
        item: dict[str, Any] = {
            "label": label,
            "path": str(directory.expanduser().resolve()),
            "exists": directory.is_dir(),
            "resolution_errors": [],
        }
        locations.append(item)
        if not directory.is_dir():
            continue
        for timeframe in ("M5", "M15", "H4"):
            try:
                candidate = Path(resolver.resolve_live_csv(directory, timeframe.lower()))
            except FileNotFoundError:
                continue
            except Exception as exc:
                item["resolution_errors"].append(
                    f"{timeframe}: {type(exc).__name__}: {exc}"
                )
                continue
            add_unique(found, timeframe, candidate, seen)
        for timeframe in ("H1", "D1"):
            matches = exact_file(directory, f"btcusdsharp_{timeframe.lower()}.csv")
            if len(matches) > 1:
                item["resolution_errors"].append(
                    f"{timeframe}: multiple exact btcusdsharp files: {[p.name for p in matches]}"
                )
            elif matches:
                add_unique(found, timeframe, matches[0], seen)
    return found, locations


def infer_clock(
    freshness: Any,
    records: list[dict[str, Any]],
    explicit_offset: float | None,
) -> dict[str, Any]:
    required = ("_naive_utc", "infer_broker_utc_offset_hours", "_server_time_series_to_utc")
    missing = [name for name in required if not hasattr(freshness, name)]
    if missing:
        return {
            "status": "BLOCKED_CANONICAL_CONVERSION_FUNCTION_MISSING",
            "selected_utc_offset_hours": None,
            "missing_functions": missing,
            "implementation": str(FRESHNESS_PY.relative_to(ROOT)),
        }

    references: list[tuple[pd.Timestamp, dict[str, Any]]] = []
    for row in records:
        if row["timeframe"] not in {"M5", "M15"}:
            continue
        if row["read_error_or_ambiguity"]:
            continue
        if int(row["non_ascending_timestamp_count"] or 0) > 0:
            continue
        latest = pd.Timestamp(row["latest_raw_closed_bar_timestamp"])
        references.append((latest + pd.Timedelta(minutes=TF_MINUTES[row["timeframe"]]), row))
    if not references:
        return {
            "status": "BLOCKED_NO_VALID_M5_M15_REFERENCE",
            "selected_utc_offset_hours": None,
            "implementation": str(FRESHNESS_PY.relative_to(ROOT)),
            "functions_reused": list(required),
        }

    reference, source = max(references, key=lambda pair: pair[0])
    now_utc = freshness._naive_utc()
    inferred, ages = freshness.infer_broker_utc_offset_hours(reference, now_utc=now_utc)
    selected = float(explicit_offset) if explicit_offset is not None else float(inferred)
    return {
        "status": "READY_CANONICAL_MAIN_CONVERSION",
        "timestamp_contract": "MT5 CSV time is broker-server wall clock; naive values are not UTC",
        "selected_utc_offset_hours": selected,
        "selection_mode": "EXPLICIT_CANONICAL_OVERRIDE" if explicit_offset is not None else "AUTO_NEAREST_UTC2_UTC3",
        "offset_candidates_hours": list(getattr(freshness, "BROKER_UTC_OFFSET_CANDIDATES", (2.0, 3.0))),
        "candidate_reference_ages_minutes": ages,
        "now_utc": text_time(now_utc),
        "reference": {
            "timeframe": source["timeframe"],
            "path": source["path"],
            "latest_closed_bar_broker_server": source["latest_raw_closed_bar_timestamp"],
            "synthetic_next_bar_open_broker_server": text_time(reference),
        },
        "implementation": str(FRESHNESS_PY.relative_to(ROOT)),
        "functions_reused": list(required),
    }


def apply_clock(
    freshness: Any,
    records: list[dict[str, Any]],
    parsed: dict[str, pd.Series | None],
    clock: dict[str, Any],
) -> None:
    offset = clock.get("selected_utc_offset_hours")
    if offset is None:
        return
    evidence = {
        key: clock.get(key)
        for key in (
            "status",
            "selection_mode",
            "offset_candidates_hours",
            "candidate_reference_ages_minutes",
            "reference",
            "implementation",
            "functions_reused",
        )
    }
    for row in records:
        times = parsed.get(path_key(Path(row["path"])))
        if times is None or row["read_error_or_ambiguity"]:
            continue
        utc_times = freshness._server_time_series_to_utc(times, float(offset))
        row["selected_broker_utc_offset_hours"] = float(offset)
        row["broker_offset_inference_evidence"] = evidence
        row["latest_utc_converted_closed_bar_timestamp"] = text_time(utc_times.iloc[-1])
        row["rows_strictly_after_cutoff_utc"] = int((utc_times > CUTOFF).sum())


def blocking_reasons(row: dict[str, Any] | None) -> list[str]:
    if row is None:
        return ["NO_MATCHING_BTCUSD_FILE"]
    reasons: list[str] = []
    if row["read_error_or_ambiguity"]:
        reasons.append(f"READ_ERROR_OR_AMBIGUITY:{row['read_error_or_ambiguity']}")
    if row["selected_broker_utc_offset_hours"] is None:
        reasons.append("BROKER_UTC_OFFSET_NOT_RESOLVED")
    if int(row["non_ascending_timestamp_count"] or 0) > 0:
        reasons.append(f"NON_ASCENDING_TIMESTAMPS:{row['non_ascending_timestamp_count']}")
    if int(row["duplicate_timestamp_count"] or 0) > 0:
        reasons.append(f"DUPLICATE_TIMESTAMPS:{row['duplicate_timestamp_count']}")
    if int(row["rows_strictly_after_cutoff_utc"] or 0) <= 0:
        reasons.append("NO_ROWS_STRICTLY_AFTER_CUTOFF_UTC")
    return reasons


def choose_latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [
        row for row in rows
        if not row["read_error_or_ambiguity"]
        and row["latest_utc_converted_closed_bar_timestamp"]
    ]
    return max(
        valid,
        key=lambda row: pd.Timestamp(row["latest_utc_converted_closed_bar_timestamp"]),
        default=None,
    )


def candidate_readiness(selected: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    requirements: dict[str, dict[str, Any]] = {}
    for timeframe in TFS:
        row = selected[timeframe]
        reasons = blocking_reasons(row)
        requirements[f"{timeframe}_AFTER_CUTOFF"] = {
            "satisfied": not reasons,
            "path": "" if row is None else row["path"],
            "rows_strictly_after_cutoff_utc": (
                None if row is None else row["rows_strictly_after_cutoff_utc"]
            ),
            "blocking_reasons": reasons,
        }

    result: dict[str, Any] = {}
    for candidate, names in CANDIDATE_REQUIREMENTS.items():
        checks = {name: requirements[name] for name in names}
        missing = [name for name, check in checks.items() if not check["satisfied"]]
        result[candidate] = {
            "status": "READY" if not missing else "BLOCKED",
            "requirements": checks,
            "missing_or_ambiguous_requirements": missing,
        }
    return result


def report_text(summary: dict[str, Any]) -> str:
    lines = [
        "BTC FF01 fresh-forward availability read-only audit",
        "=" * 55,
        f"audit_complete: {summary['audit_complete']}",
        f"overall_status: {summary['overall_status']}",
        f"generated_at_utc: {summary['generated_at_utc']}",
        f"repository_branch: {summary['repository']['branch']}",
        f"repository_commit: {summary['repository']['commit']}",
        f"cutoff_utc_exclusive: {summary['cutoff_utc_exclusive']}",
        f"broker_utc_offset_hours: {summary['broker_clock'].get('selected_utc_offset_hours')}",
        f"broker_clock_status: {summary['broker_clock'].get('status')}",
        "",
        "Correction: the 2017-start H4 package was historical reproduction-only and is not a fresh-forward readiness requirement.",
        "Safety: source CSV read-only. No fresh trades, performance evaluation, reproduction, collector, Discord, MT5 order, live-ready or final signal.",
        "",
        "Timeframes",
        "----------",
    ]
    for timeframe in TFS:
        item = summary["timeframes"][timeframe]
        row = item["selected_fresh_tail"]
        lines.append(f"{timeframe}: {item['status']}")
        if row is None:
            lines.append("  path=NOT_FOUND")
        else:
            lines.extend([
                f"  path={row['path']}",
                f"  size={row['file_size_bytes']} rows={row['rows']}",
                f"  first_server={row['first_raw_mt5_broker_server_timestamp']}",
                f"  latest_server_closed={row['latest_raw_closed_bar_timestamp']}",
                f"  latest_utc_closed={row['latest_utc_converted_closed_bar_timestamp']}",
                f"  after_cutoff={row['rows_strictly_after_cutoff_utc']}",
                f"  non_ascending={row['non_ascending_timestamp_count']} duplicates={row['duplicate_timestamp_count']}",
                f"  read_error_or_ambiguity={row['read_error_or_ambiguity'] or 'NONE'}",
            ])
        lines.append(f"  blocking_reasons={item['blocking_reasons'] or ['NONE']}")

    lines.extend(["", "Candidate readiness", "-------------------"])
    for candidate, value in summary["candidate_readiness"].items():
        missing = value["missing_or_ambiguous_requirements"] or ["NONE"]
        lines.append(f"{candidate}: {value['status']} missing_or_ambiguous={missing}")
    if summary.get("fatal_error"):
        lines.extend(["", f"fatal_error: {summary['fatal_error']}"])
    lines.extend([
        "",
        "STOP: FF01 ends here. Upload 99_UPLOAD_PACKAGE.zip. Do not run FF02 or any evaluator without explicit approval.",
    ])
    return "\n".join(lines) + "\n"


def read_me_text(summary: dict[str, Any]) -> str:
    return "\n".join([
        "BTC ML V1 / FF01 fresh-forward availability audit",
        "=" * 55,
        f"generated_at_utc: {summary['generated_at_utc']}",
        f"repository_branch: {summary['repository']['branch']}",
        f"repository_commit: {summary['repository']['commit']}",
        f"overall_status: {summary['overall_status']}",
        "",
        "Files in this folder:",
        "01_availability_summary.json  machine-readable complete availability result",
        "02_availability_report.txt    human-readable candidate-specific READY/BLOCKED report",
        "99_UPLOAD_PACKAGE.zip         upload this single file to ChatGPT",
        "",
        "The old 2017-start H4 package was historical reproduction-only.",
        "It is not required for current fresh-forward readiness.",
        "",
        "This stage is availability-only and source-CSV read-only.",
        "No candidate engine, fresh performance evaluator, reproduction, collector, Discord, MT5 order, live-ready or final-signal action was run.",
        "",
        "After uploading 99_UPLOAD_PACKAGE.zip, stop. FF02 is not authorized.",
    ]) + "\n"


def replace_latest(archive_dir: Path, latest_dir: Path, names: Sequence[str]) -> None:
    temp_latest = latest_dir.parent / f"LATEST.__new__.{os.getpid()}"
    if temp_latest.exists():
        shutil.rmtree(temp_latest)
    temp_latest.mkdir(parents=True, exist_ok=False)
    for name in names:
        shutil.copy2(archive_dir / name, temp_latest / name)
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    os.replace(temp_latest, latest_dir)


def write_outputs(summary: dict[str, Any], output_root: Path) -> dict[str, str]:
    root = output_root.expanduser().resolve()
    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f_UTC")
    archive_dir = root / "archive" / run_id
    latest_dir = root / "LATEST"
    archive_dir.mkdir(parents=True, exist_ok=False)

    readme = archive_dir / "00_READ_ME_FIRST.txt"
    summary_json = archive_dir / "01_availability_summary.json"
    report = archive_dir / "02_availability_report.txt"
    package = archive_dir / "99_UPLOAD_PACKAGE.zip"

    readme.write_text(read_me_text(summary), encoding="utf-8")
    summary_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    report.write_text(report_text(summary), encoding="utf-8")
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in (readme, summary_json, report):
            archive.write(path, path.name)

    names = [readme.name, summary_json.name, report.name, package.name]
    replace_latest(archive_dir, latest_dir, names)
    return {
        "output_root": str(root),
        "archive_dir": str(archive_dir),
        "latest_dir": str(latest_dir),
        "availability_summary": str(latest_dir / summary_json.name),
        "availability_report": str(latest_dir / report.name),
        "upload_package": str(latest_dir / package.name),
    }


def base_summary() -> dict[str, Any]:
    return {
        "schema_version": "btc_ff01_fresh_forward_availability_v2",
        "stage": "BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "repository": git_identity(),
        "cutoff_utc_exclusive": text_time(CUTOFF),
        "latest_csv_row_contract": "CLOSED",
        "historical_h4_warmup_policy": {
            "status": "NOT_REQUIRED_FOR_FRESH_FORWARD",
            "purpose": "historical full reproduction only",
            "old_reference_package": "BTCUSD_H4_WARMUP_PACKAGE.zip",
        },
        "audit_complete": False,
        "overall_status": "BLOCKED_AUDIT_NOT_COMPLETED",
        "fatal_error": "",
        "known_locations": [],
        "broker_clock": {},
        "timeframes": {
            timeframe: {
                "status": "BLOCKED",
                "inspected_files": [],
                "selected_fresh_tail": None,
                "blocking_reasons": ["AUDIT_NOT_COMPLETED"],
            }
            for timeframe in TFS
        },
        "candidate_readiness": {
            candidate: {
                "status": "BLOCKED",
                "requirements": {},
                "missing_or_ambiguous_requirements": list(requirements),
            }
            for candidate, requirements in CANDIDATE_REQUIREMENTS.items()
        },
        "safety": {
            "source_csv_access": "READ_ONLY",
            "source_csv_modified": False,
            "source_csv_copied": False,
            "source_csv_moved": False,
            "source_csv_regenerated": False,
            "candidate_engines_executed": False,
            "fresh_trade_generation_executed": False,
            "fresh_performance_evaluation_executed": False,
            "reproduction_script_executed": False,
            "collector_touched": False,
            "m7c_touched": False,
            "m8c_touched": False,
            "mochipoyo_branch_touched": False,
            "m10w24b_touched": False,
            "gold_touched": False,
            "orders_enabled": False,
            "discord_enabled": False,
            "live_ready": False,
            "final_signal": False,
        },
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    summary = base_summary()
    freshness = load_module("_btc_ff01_existing_freshness", FRESHNESS_PY)
    resolver = load_module("_btc_ff01_existing_resolver", RESOLVER_PY)
    paths, locations = discover(resolver, args)

    records: list[dict[str, Any]] = []
    parsed: dict[str, pd.Series | None] = {}
    for timeframe, candidates in paths.items():
        for path in candidates:
            row, times = read_times(path)
            row["timeframe"] = timeframe
            records.append(row)
            parsed[path_key(path)] = times

    clock = infer_clock(freshness, records, args.broker_utc_offset_hours)
    apply_clock(freshness, records, parsed, clock)
    grouped = {
        timeframe: [row for row in records if row["timeframe"] == timeframe]
        for timeframe in TFS
    }
    selected = {timeframe: choose_latest(grouped[timeframe]) for timeframe in TFS}
    readiness = candidate_readiness(selected)

    timeframe_summary: dict[str, Any] = {}
    for timeframe in TFS:
        row = selected[timeframe]
        reasons = blocking_reasons(row)
        timeframe_summary[timeframe] = {
            "status": "READY" if not reasons else "BLOCKED",
            "inspected_files": grouped[timeframe],
            "selected_fresh_tail": row,
            "blocking_reasons": reasons,
        }

    ready_count = sum(value["status"] == "READY" for value in readiness.values())
    summary.update(
        audit_complete=True,
        overall_status=(
            "READY_ALL_FIVE_CANDIDATES"
            if ready_count == len(readiness)
            else "READY_SOME_CANDIDATES"
            if ready_count > 0
            else "BLOCKED_ALL_CANDIDATES"
        ),
        known_locations=locations,
        broker_clock=clock,
        timeframes=timeframe_summary,
        candidate_readiness=readiness,
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BTC FF01 read-only fresh-forward availability audit"
    )
    parser.add_argument("--repo-files-dir", type=Path, default=ROOT / "Files")
    parser.add_argument("--terminal-files-dir", type=Path, default=KNOWN_TERMINAL)
    parser.add_argument("--repro-history-dir", type=Path, default=KNOWN_HISTORY)
    parser.add_argument("--m5-csv", type=Path)
    parser.add_argument("--m15-csv", type=Path)
    parser.add_argument("--h1-csv", type=Path)
    parser.add_argument("--d1-csv", type=Path)
    parser.add_argument("--h4-csv", type=Path)
    parser.add_argument("--broker-utc-offset-hours", type=float, choices=(2.0, 3.0))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = run_audit(args)
        exit_code = 0
    except Exception as exc:
        summary = base_summary()
        summary["fatal_error"] = f"{type(exc).__name__}: {exc}"
        summary["overall_status"] = "BLOCKED_FATAL_AUDIT_ERROR"
        exit_code = 2
    written = write_outputs(summary, args.output_root)
    print(json.dumps({
        "audit_complete": summary["audit_complete"],
        "overall_status": summary["overall_status"],
        **written,
        "candidate_readiness": summary["candidate_readiness"],
        "fatal_error": summary.get("fatal_error", ""),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
