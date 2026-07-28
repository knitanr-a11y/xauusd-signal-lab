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
FRESHNESS_PY = ROOT / "scripts/run_btc_youtube_candidates_dry_run_cycle.py"
RESOLVER_PY = ROOT / "scripts/run_btc_youtube_candidates_operational_forever.py"
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
KNOWN_WARMUP = Path(r"C:\BTC_REPRO\h4_warmup\btcusdsharp_h4.csv")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load existing main module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def text_time(value: Any) -> str:
    return "" if value is None or pd.isna(value) else pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def key(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().resolve()))


def git_dir() -> Path | None:
    marker = ROOT / ".git"
    if marker.is_dir():
        return marker
    if marker.is_file():
        text = marker.read_text(encoding="utf-8", errors="replace").strip()
        if text.lower().startswith("gitdir:"):
            candidate = Path(text.split(":", 1)[1].strip())
            return candidate if candidate.is_absolute() else (ROOT / candidate).resolve()
    return None


def current_commit() -> str:
    directory = git_dir()
    if directory is None:
        return "UNKNOWN_NO_GIT_METADATA"
    try:
        head = (directory / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref:"):
            return head
        ref = head.split(":", 1)[1].strip()
        loose = directory / ref
        if loose.is_file():
            return loose.read_text(encoding="utf-8").strip()
        packed = directory / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line or line.startswith(("#", "^")):
                    continue
                sha, name = line.split(" ", 1)
                if name.strip() == ref:
                    return sha.strip()
    except Exception:
        pass
    return "UNKNOWN_GIT_READ_FAILED"


def read_times(path: Path) -> tuple[dict[str, Any], pd.Series | None]:
    row: dict[str, Any] = {
        "path": str(path.expanduser().resolve()),
        "file_size_bytes": None,
        "rows": 0,
        "first_time_broker_server": "",
        "latest_closed_time_broker_server": "",
        "broker_utc_offset_hours": None,
        "latest_closed_time_utc": "",
        "rows_after_cutoff_utc": None,
        "ascending_order_violations": None,
        "duplicate_timestamp_count": None,
        "read_error": "",
    }
    try:
        row["file_size_bytes"] = int(path.stat().st_size)
        try:
            header = pd.read_csv(path, nrows=0)
            auto = False
        except Exception:
            header = pd.read_csv(path, nrows=0, sep=None, engine="python")
            auto = True
        columns = {str(c).strip().lower(): c for c in header.columns}
        if "time" not in columns:
            raise ValueError(f"missing time column: {list(header.columns)}")
        kwargs = {"sep": None, "engine": "python"} if auto else {"low_memory": False}
        frame = pd.read_csv(path, usecols=[columns["time"]], **kwargs)
        times = pd.to_datetime(frame.iloc[:, 0], errors="coerce")
        invalid = int(times.isna().sum())
        if len(times) == 0:
            raise ValueError("empty CSV")
        if invalid:
            raise ValueError(f"invalid time rows: {invalid}")
        row.update(
            rows=int(len(times)),
            first_time_broker_server=text_time(times.iloc[0]),
            latest_closed_time_broker_server=text_time(times.iloc[-1]),
            ascending_order_violations=int((times.diff() < pd.Timedelta(0)).sum()),
            duplicate_timestamp_count=int(times.duplicated(keep="first").sum()),
        )
        return row, times
    except Exception as exc:
        row["read_error"] = f"{type(exc).__name__}: {exc}"
        return row, None


def exact_file(directory: Path, filename: str) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and p.name.lower() == filename.lower())


def discover(resolver: Any, args: argparse.Namespace) -> tuple[dict[str, list[Path]], list[dict[str, Any]]]:
    found = {tf: [] for tf in TFS}
    locations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for label, directory in (
        ("REPOSITORY_FILES", args.repo_files_dir),
        ("KNOWN_MT5_TERMINAL_FILES", args.terminal_files_dir),
        ("KNOWN_REPRO_HISTORY", args.repro_history_dir),
    ):
        item = {
            "label": label,
            "path": str(directory.expanduser().resolve()),
            "exists": directory.is_dir(),
            "resolution_errors": [],
        }
        locations.append(item)
        if not directory.is_dir():
            continue
        for tf in ("M5", "M15", "H4"):
            try:
                path = Path(resolver.resolve_live_csv(directory, tf.lower()))
            except FileNotFoundError:
                continue
            except Exception as exc:
                item["resolution_errors"].append(f"{tf}: {type(exc).__name__}: {exc}")
                continue
            if key(path) not in seen:
                seen.add(key(path))
                found[tf].append(path)
        for tf in ("H1", "D1"):
            matches = exact_file(directory, f"btcusdsharp_{tf.lower()}.csv")
            if len(matches) > 1:
                item["resolution_errors"].append(f"{tf}: multiple exact matches")
            elif matches and key(matches[0]) not in seen:
                seen.add(key(matches[0]))
                found[tf].append(matches[0])
    locations.append(
        {
            "label": "KNOWN_BTC4_H4_WARMUP",
            "path": str(args.h4_warmup_csv.expanduser().resolve()),
            "exists": args.h4_warmup_csv.is_file(),
            "resolution_errors": [],
        }
    )
    if args.h4_warmup_csv.is_file() and key(args.h4_warmup_csv) not in seen:
        found["H4"].append(args.h4_warmup_csv)
    return found, locations


def infer_clock(freshness: Any, records: list[dict[str, Any]]) -> dict[str, Any]:
    refs = []
    # Exact current-main reference set: BTC4/BTC5 use M5 synthetic entry; BTC6 uses M15.
    for row in records:
        if row["timeframe"] not in {"M5", "M15"} or row["read_error"]:
            continue
        latest = row["latest_closed_time_broker_server"]
        synthetic = pd.Timestamp(latest) + pd.Timedelta(minutes=TF_MINUTES[row["timeframe"]])
        refs.append((synthetic, row))
    if not refs:
        return {
            "status": "BLOCKED_NO_M5_M15_REFERENCE",
            "selected_utc_offset_hours": None,
            "implementation": str(FRESHNESS_PY.relative_to(ROOT)),
        }
    reference, source = max(refs, key=lambda pair: pair[0])
    now = freshness._naive_utc()
    offset, ages = freshness.infer_broker_utc_offset_hours(reference, now_utc=now)
    return {
        "status": "INFERRED_WITH_MAIN_LOGIC",
        "selected_utc_offset_hours": float(offset),
        "now_utc": text_time(now),
        "reference": {
            "timeframe": source["timeframe"],
            "path": source["path"],
            "latest_closed_time_broker_server": source["latest_closed_time_broker_server"],
            "synthetic_entry_time_broker_server": text_time(reference),
        },
        "candidate_reference_ages_minutes": ages,
        "implementation": str(FRESHNESS_PY.relative_to(ROOT)),
        "functions_reused": ["infer_broker_utc_offset_hours", "_server_time_series_to_utc"],
    }


def choose_latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [r for r in rows if not r["read_error"] and r["latest_closed_time_utc"]]
    return max(valid, key=lambda r: pd.Timestamp(r["latest_closed_time_utc"]), default=None)


def readiness(selected: dict[str, dict[str, Any] | None], warmup_ok: bool) -> dict[str, Any]:
    fresh = {tf: bool(selected[tf] and int(selected[tf]["rows_after_cutoff_utc"] or 0) > 0) for tf in TFS}
    checks = {
        "BTC4_RISK_CAP_400": {
            "H4_WARMUP_2017": warmup_ok,
            "H4_AFTER_CUTOFF": fresh["H4"],
            "M5_AFTER_CUTOFF": fresh["M5"],
        },
        "BTC5_TWO_PIVOT_P2_CLEAN_N_382_786": {"M5_AFTER_CUTOFF": fresh["M5"]},
        "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886": {"M15_AFTER_CUTOFF": fresh["M15"]},
        "BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110": {
            "M5_AFTER_CUTOFF": fresh["M5"],
            "M15_AFTER_CUTOFF": fresh["M15"],
            "H1_AFTER_CUTOFF": fresh["H1"],
        },
        "BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080": {
            "M5_AFTER_CUTOFF": fresh["M5"],
            "M15_AFTER_CUTOFF": fresh["M15"],
            "H1_AFTER_CUTOFF": fresh["H1"],
            "D1_AFTER_CUTOFF": fresh["D1"],
        },
    }
    result = {}
    for candidate, required in checks.items():
        missing = [name for name, ok in required.items() if not ok]
        result[candidate] = {
            "status": "READY" if not missing else "BLOCKED",
            "requirements": required,
            "missing_requirements": missing,
        }
    return result


def report_text(summary: dict[str, Any]) -> str:
    lines = [
        "BTC fresh forward availability read-only audit",
        "=" * 48,
        f"stage: {summary['stage']}",
        f"generated_at_utc: {summary['generated_at_utc']}",
        f"commit: {summary['repository_commit']}",
        f"cutoff_utc: {summary['cutoff_utc']}",
        f"broker_utc_offset_hours: {summary['broker_clock'].get('selected_utc_offset_hours')}",
        "",
        "Safety: CSV read-only; no candidate engine, performance evaluation, reproduction, collector, Discord or MT5 order.",
        "",
        "Timeframes",
        "----------",
    ]
    for tf in TFS:
        row = summary["timeframes"][tf]["selected_fresh_tail"]
        if row is None:
            lines.append(f"{tf}: NOT FOUND / NOT READABLE")
        else:
            lines += [
                f"{tf}: {row['path']}",
                f"  size={row['file_size_bytes']} rows={row['rows']} first_server={row['first_time_broker_server']}",
                f"  latest_server={row['latest_closed_time_broker_server']} latest_utc={row['latest_closed_time_utc']}",
                f"  after_cutoff={row['rows_after_cutoff_utc']} order_violations={row['ascending_order_violations']} duplicates={row['duplicate_timestamp_count']} read_error={row['read_error'] or 'NONE'}",
            ]
    lines += [
        "",
        "H4",
        "--",
        f"long_warmup_2017: {'PASS' if summary['h4_checks']['long_warmup']['meets_2017_start'] else 'BLOCKED'}",
        f"fresh_tail_after_cutoff: {'PASS' if summary['h4_checks']['fresh_tail']['available_after_cutoff'] else 'BLOCKED'}",
        "",
        "Candidate readiness",
        "-------------------",
    ]
    for candidate, value in summary["candidate_readiness"].items():
        lines.append(f"{candidate}: {value['status']} missing={','.join(value['missing_requirements']) or 'NONE'}")
    lines += ["", "STOP: availability audit complete; fresh performance evaluator was not created or run."]
    return "\n".join(lines) + "\n"


def read_me_text(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "BTC ML V1 / Stage 01 fresh-forward availability audit",
            "=" * 58,
            f"generated_at_utc: {summary['generated_at_utc']}",
            f"repository_commit: {summary['repository_commit']}",
            "",
            "Files in this folder:",
            "01_availability_summary.json  machine-readable complete result",
            "02_availability_report.txt    concise human-readable result",
            "99_UPLOAD_PACKAGE.zip         upload this single file to ChatGPT",
            "",
            "This stage is availability-only and read-only.",
            "No candidate engine, performance evaluator, collector, Discord, MT5 order, live-ready or final-signal action was run.",
            "",
            "After uploading 99_UPLOAD_PACKAGE.zip, stop. Do not run a fresh evaluator unless separately instructed.",
        ]
    ) + "\n"


def replace_latest(archive_dir: Path, latest_dir: Path, filenames: Sequence[str]) -> None:
    temp_latest = latest_dir.parent / f"LATEST.__new__.{os.getpid()}"
    if temp_latest.exists():
        shutil.rmtree(temp_latest)
    temp_latest.mkdir(parents=True, exist_ok=False)
    for name in filenames:
        shutil.copy2(archive_dir / name, temp_latest / name)
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    os.replace(temp_latest, latest_dir)


def write_outputs(summary: dict[str, Any], output_root: Path) -> dict[str, str]:
    root = output_root.expanduser().resolve()
    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_UTC")
    archive_dir = root / "archive" / run_id
    latest_dir = root / "LATEST"
    archive_dir.mkdir(parents=True, exist_ok=False)

    readme_path = archive_dir / "00_READ_ME_FIRST.txt"
    summary_path = archive_dir / "01_availability_summary.json"
    report_path = archive_dir / "02_availability_report.txt"
    zip_path = archive_dir / "99_UPLOAD_PACKAGE.zip"

    readme_path.write_text(read_me_text(summary), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    report_path.write_text(report_text(summary), encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in (readme_path, summary_path, report_path):
            archive.write(path, path.name)

    names = [readme_path.name, summary_path.name, report_path.name, zip_path.name]
    replace_latest(archive_dir, latest_dir, names)
    return {
        "output_root": str(root),
        "archive_dir": str(archive_dir),
        "latest_dir": str(latest_dir),
        "availability_summary": str(latest_dir / summary_path.name),
        "availability_report": str(latest_dir / report_path.name),
        "upload_package": str(latest_dir / zip_path.name),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only BTC fresh-forward availability audit")
    parser.add_argument("--repo-files-dir", type=Path, default=ROOT / "Files")
    parser.add_argument("--terminal-files-dir", type=Path, default=KNOWN_TERMINAL)
    parser.add_argument("--repro-history-dir", type=Path, default=KNOWN_HISTORY)
    parser.add_argument("--h4-warmup-csv", type=Path, default=KNOWN_WARMUP)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    freshness = load_module("_btc_existing_freshness", FRESHNESS_PY)
    resolver = load_module("_btc_existing_resolver", RESOLVER_PY)
    paths, locations = discover(resolver, args)

    records, parsed = [], {}
    for tf, candidates in paths.items():
        for path in candidates:
            row, times = read_times(path)
            row["timeframe"] = tf
            records.append(row)
            parsed[key(path)] = times

    clock = infer_clock(freshness, records)
    offset = clock["selected_utc_offset_hours"]
    if offset is not None:
        for row in records:
            times = parsed.get(key(Path(row["path"])))
            if times is None or row["read_error"]:
                continue
            utc_times = freshness._server_time_series_to_utc(times, offset)
            row["broker_utc_offset_hours"] = offset
            row["latest_closed_time_utc"] = text_time(utc_times.iloc[-1])
            row["rows_after_cutoff_utc"] = int((utc_times > CUTOFF).sum())

    grouped = {tf: [r for r in records if r["timeframe"] == tf] for tf in TFS}
    selected = {tf: choose_latest(grouped[tf]) for tf in TFS}
    warmups = [r for r in grouped["H4"] if not r["read_error"] and r["first_time_broker_server"]]
    warmup = min(warmups, key=lambda r: pd.Timestamp(r["first_time_broker_server"]), default=None)
    warmup_ok = bool(warmup and pd.Timestamp(warmup["first_time_broker_server"]).year <= 2017)
    h4_tail = selected["H4"]

    summary = {
        "schema_version": "btc_fresh_forward_availability_v2",
        "stage": "BTC_ML_V1_01_FRESH_FORWARD_AVAILABILITY_READ_ONLY_AUDIT",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "repository_commit": current_commit(),
        "cutoff_utc": text_time(CUTOFF),
        "known_locations": locations,
        "broker_clock": clock,
        "timeframes": {tf: {"inspected_files": grouped[tf], "selected_fresh_tail": selected[tf]} for tf in TFS},
        "h4_checks": {
            "long_warmup": {
                "meets_2017_start": warmup_ok,
                "path": "" if warmup is None else warmup["path"],
                "first_time_broker_server": "" if warmup is None else warmup["first_time_broker_server"],
                "reference_expected_first_time": "2017-01-02 04:00:00",
            },
            "fresh_tail": {
                "available_after_cutoff": bool(h4_tail and int(h4_tail["rows_after_cutoff_utc"] or 0) > 0),
                "path": "" if h4_tail is None else h4_tail["path"],
                "rows_after_cutoff_utc": None if h4_tail is None else h4_tail["rows_after_cutoff_utc"],
            },
        },
        "candidate_readiness": readiness(selected, warmup_ok),
        "definitions": {
            "rows_after_cutoff_utc": "strictly greater than cutoff",
            "ascending_order_violations": "adjacent decreases in original CSV order",
            "duplicate_timestamp_count": "duplicates beyond first occurrence",
            "latest_csv_row": "closed by contract",
        },
        "output_contract": {
            "layout": "LOCALAPPDATA/xauusd_signal_lab/btc_ml_v1/outputs/01_fresh_forward_availability/{LATEST,archive}",
            "latest_contains": [
                "00_READ_ME_FIRST.txt",
                "01_availability_summary.json",
                "02_availability_report.txt",
                "99_UPLOAD_PACKAGE.zip",
            ],
        },
        "safety": {
            "read_only_csv_access": True,
            "csv_modified": False,
            "csv_copied": False,
            "csv_moved": False,
            "csv_regenerated": False,
            "candidate_engines_executed": False,
            "fresh_performance_evaluation_executed": False,
            "reproduction_script_executed": False,
            "skip_input_hash_check_used": False,
            "collector_touched": False,
            "mochipoyo_runtime_touched": False,
            "gold_touched": False,
            "btc10r_included": False,
            "orders_enabled": False,
            "discord_enabled": False,
            "live_ready": False,
            "final_signal": False,
        },
    }

    written = write_outputs(summary, args.output_root)
    print(
        json.dumps(
            {
                "audit_complete": True,
                **written,
                "candidate_readiness": summary["candidate_readiness"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
