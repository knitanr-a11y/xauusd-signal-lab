from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
RESEARCH_DIR = ROOT / "scripts" / "btc_ml_v1" / "research"
CANONICAL_CLOCK_PY = ROOT / "scripts" / "run_btc_youtube_candidates_dry_run_cycle.py"
REPRODUCTION_PY = RESEARCH_DIR / "reproduce_btc_stacking_portfolio.py"

EXPECTED_BRANCH = "feature/btc-fresh-forward-research"
CUTOFF_UTC = pd.Timestamp("2026-07-02 02:15:00")
STAGE_ID = "02_fresh_forward_performance"
DEFAULT_OUTPUT_ROOT = (
    Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    / "xauusd_signal_lab"
    / "btc_ml_v1"
    / "outputs"
    / STAGE_ID
)
DEFAULT_FF01_SUMMARY = (
    Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    / "xauusd_signal_lab"
    / "btc_ml_v1"
    / "outputs"
    / "01_fresh_forward_availability"
    / "LATEST"
    / "01_availability_summary.json"
)
TIMEFRAMES = ("M5", "M15", "H1", "D1", "H4")
TIMEFRAME_MINUTES = {"M5": 5, "M15": 15, "H1": 60, "D1": 1440, "H4": 240}
CANDIDATES = (
    "BTC4_RISK_CAP_400",
    "BTC5_TWO_PIVOT_P2_CLEAN_N_382_786",
    "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886",
    "BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110",
    "BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080",
)
PUBLIC_FILES = (
    "00_READ_ME_FIRST.txt",
    "01_fresh_forward_summary.json",
    "02_fresh_forward_report.txt",
    "03_fresh_forward_trade_ledger.csv",
    "04_candidate_metrics.csv",
    "05_monthly_metrics.csv",
    "06_direction_metrics.csv",
    "07_input_manifest.csv",
    "08_candidate_engine_manifest.csv",
)
TRADE_COLUMNS = [
    "candidate",
    "direction",
    "signal_time_broker_server",
    "signal_time_utc",
    "entry_time_broker_server",
    "entry_time_utc",
    "exit_time_broker_server",
    "exit_time_utc",
    "outcome_status",
    "exit_reason",
    "risk_pips",
    "reward_pips",
    "pnl_pips",
    "rr",
    "entry_bid",
    "stop_chart",
    "target_chart",
    "tp1_chart",
    "tp2_chart",
    "source_period",
    "source_entry_index",
    "hold_hours",
]
METRIC_COLUMNS = [
    "scope",
    "planned_entries",
    "resolved_trades",
    "open_at_data_end",
    "wins",
    "losses",
    "breakeven",
    "win_rate_pct",
    "gross_profit_pips",
    "gross_loss_pips",
    "profit_factor",
    "total_pips",
    "average_pips",
    "max_drawdown_pips",
]
ENGINE_SCRIPTS = {
    "btc4": RESEARCH_DIR / "run_btc3_video_ema_user_contract.py",
    "btc5": RESEARCH_DIR / "btc5_video_5m_ema200_nwave_candidate.py",
    "btc6": RESEARCH_DIR / "btc6_video_m15_ema200_nwave_candidate.py",
    "btc7r": RESEARCH_DIR / "btc7r_m15_impulse_high_win_candidate.py",
    "btc9r": RESEARCH_DIR / "btc9r_m15_prevday_breakout_high_win_candidate.py",
}


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def load_module(name: str, path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"required module is missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): clean_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        if math.isnan(numeric):
            return None
        if math.isinf(numeric):
            return "Infinity" if numeric > 0 else "-Infinity"
        return numeric
    if pd.isna(value) if not isinstance(value, (str, bytes)) else False:
        return None
    return value


def git_identity() -> dict[str, str]:
    marker = ROOT / ".git"
    result = {"branch": "UNKNOWN_NO_GIT_METADATA", "commit": "UNKNOWN_NO_GIT_METADATA"}
    if marker.is_file():
        text = marker.read_text(encoding="utf-8", errors="replace").strip()
        if text.lower().startswith("gitdir:"):
            candidate = Path(text.split(":", 1)[1].strip())
            marker = candidate if candidate.is_absolute() else (ROOT / candidate).resolve()
    if not marker.is_dir():
        return result
    try:
        head = (marker / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
        if not head.startswith("ref:"):
            return {"branch": "DETACHED_HEAD", "commit": head}
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
            "branch": "UNKNOWN_GIT_READ_FAILED",
            "commit": f"UNKNOWN_GIT_READ_FAILED:{type(exc).__name__}",
        }
    return result


def stable_snapshot(source: Path, destination: Path, attempts: int = 4) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(f"source CSV is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            before_size = int(source.stat().st_size)
            before_hash = sha256_file(source)
            temp_path = destination.with_suffix(destination.suffix + f".copying.{os.getpid()}")
            if temp_path.exists():
                temp_path.unlink()
            shutil.copyfile(source, temp_path)
            snapshot_hash = sha256_file(temp_path)
            after_size = int(source.stat().st_size)
            after_hash = sha256_file(source)
            if before_size == after_size == int(temp_path.stat().st_size) and before_hash == snapshot_hash == after_hash:
                os.replace(temp_path, destination)
                return {
                    "source_path": str(source.resolve()),
                    "snapshot_path_internal": str(destination.resolve()),
                    "source_size_bytes": before_size,
                    "source_sha256_at_snapshot": before_hash,
                    "snapshot_sha256": snapshot_hash,
                    "snapshot_attempts": attempt,
                    "source_stable_during_snapshot": True,
                }
            errors.append(
                f"attempt {attempt}: source changed while copying "
                f"(before_size={before_size}, after_size={after_size}, "
                f"before_hash={before_hash}, snapshot_hash={snapshot_hash}, after_hash={after_hash})"
            )
            temp_path.unlink(missing_ok=True)
        except Exception as exc:
            errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
        time.sleep(0.5)
    raise RuntimeError(f"could not create stable read-only snapshot for {source}: {'; '.join(errors)}")


def read_bars_strict(path: Path, timeframe: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = pd.read_csv(path)
    required = {"time", "open", "high", "low", "close"}
    if timeframe in {"M5", "H4"}:
        required |= {"tick_volume", "spread", "real_volume"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{timeframe} snapshot is missing columns: {missing}")
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    invalid = int(frame["time"].isna().sum())
    if invalid:
        raise ValueError(f"{timeframe} snapshot has {invalid} invalid timestamps")
    if len(frame) == 0:
        raise ValueError(f"{timeframe} snapshot is empty")
    if not frame["time"].is_monotonic_increasing:
        raise ValueError(f"{timeframe} snapshot timestamps are not strictly ascending")
    duplicates = int(frame["time"].duplicated(keep=False).sum())
    if duplicates:
        raise ValueError(f"{timeframe} snapshot has {duplicates} duplicated timestamp rows")
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    manifest = {
        "timeframe": timeframe,
        "rows": int(len(frame)),
        "first_time_broker_server": frame.iloc[0]["time"],
        "latest_time_broker_server": frame.iloc[-1]["time"],
        "non_ascending_timestamp_count": 0,
        "duplicate_timestamp_count": 0,
    }
    return frame, manifest


def validate_ff01(summary_path: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    if not summary_path.is_file():
        raise FileNotFoundError(
            f"FF01 summary is missing: {summary_path}. Run FF01 first and review its package."
        )
    summary = read_json(summary_path)
    if summary.get("overall_status") != "READY_ALL_FIVE_CANDIDATES":
        raise RuntimeError(
            f"FF01 overall_status is not READY_ALL_FIVE_CANDIDATES: {summary.get('overall_status')}"
        )
    readiness = summary.get("candidate_readiness", {})
    blocked = [
        candidate
        for candidate in CANDIDATES
        if readiness.get(candidate, {}).get("status") != "READY"
    ]
    if blocked:
        raise RuntimeError(f"FF01 candidate readiness is not READY: {blocked}")
    paths: dict[str, Path] = {}
    for timeframe in TIMEFRAMES:
        selected = summary.get("timeframes", {}).get(timeframe, {}).get("selected_fresh_tail")
        path_text = selected.get("path") if isinstance(selected, dict) else None
        if not path_text:
            raise RuntimeError(f"FF01 selected path is missing for {timeframe}")
        paths[timeframe] = Path(path_text)
    return summary, paths


def infer_broker_clock(
    canonical: Any,
    frames: dict[str, pd.DataFrame],
    ff01_summary: dict[str, Any],
) -> dict[str, Any]:
    references: list[tuple[pd.Timestamp, str]] = []
    for timeframe in ("M5", "M15"):
        latest = pd.Timestamp(frames[timeframe].iloc[-1]["time"])
        references.append(
            (latest + pd.Timedelta(minutes=TIMEFRAME_MINUTES[timeframe]), timeframe)
        )
    reference, timeframe = max(references, key=lambda item: item[0])
    now_utc = canonical._naive_utc()
    inferred, ages = canonical.infer_broker_utc_offset_hours(reference, now_utc=now_utc)
    ff01_offset = ff01_summary.get("broker_clock", {}).get("selected_utc_offset_hours")
    if ff01_offset is None:
        raise RuntimeError("FF01 broker UTC offset is missing")
    if not math.isclose(float(inferred), float(ff01_offset), abs_tol=1e-9):
        raise RuntimeError(
            f"broker UTC offset changed since FF01: current={inferred}, ff01={ff01_offset}. "
            "Rerun FF01 before FF02."
        )
    return {
        "status": "READY_CANONICAL_MAIN_CONVERSION",
        "selected_utc_offset_hours": float(inferred),
        "ff01_selected_utc_offset_hours": float(ff01_offset),
        "selection_mode": "AUTO_NEAREST_UTC2_UTC3",
        "candidate_reference_ages_minutes": ages,
        "reference_timeframe": timeframe,
        "reference_next_bar_open_broker_server": reference,
        "now_utc": now_utc,
        "canonical_module": str(CANONICAL_CLOCK_PY.relative_to(ROOT)),
        "functions_reused": [
            "_naive_utc",
            "infer_broker_utc_offset_hours",
            "_server_time_series_to_utc",
        ],
    }


def to_utc_series(canonical: Any, series: pd.Series, offset: float) -> pd.Series:
    return canonical._server_time_series_to_utc(series, offset)


def run_command(command: list[str], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "command_stdout.txt"
    stderr_path = output_dir / "command_stderr.txt"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(RESEARCH_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    started = datetime.now(UTC)
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    ended = datetime.now(UTC)
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    return {
        "command": command,
        "returncode": int(completed.returncode),
        "started_at_utc": started.strftime("%Y-%m-%d %H:%M:%S"),
        "ended_at_utc": ended.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": float((ended - started).total_seconds()),
        "stdout_path_internal": str(stdout_path.resolve()),
        "stderr_path_internal": str(stderr_path.resolve()),
        "stderr_excerpt": (completed.stderr or "")[-2000:],
    }


def read_ledger(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"candidate ledger was not produced: {path}")
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def as_timestamp(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return pd.NaT
    timestamp = pd.Timestamp(value)
    return timestamp


def numeric(row: pd.Series, name: str) -> float | None:
    if name not in row.index or pd.isna(row[name]):
        return None
    return float(row[name])


def text_value(row: pd.Series, name: str) -> str:
    if name not in row.index or pd.isna(row[name]):
        return ""
    return str(row[name])


def standard_trade_row(
    *,
    candidate: str,
    plan: pd.Series,
    entry_column: str,
    signal_column: str,
    index_column: str,
    canonical: Any,
    offset: float,
    result: dict[str, Any],
    reward_pips: float | None,
    rr: float | None,
    target_chart: float | None,
    tp1_chart: float | None,
    tp2_chart: float | None,
) -> dict[str, Any]:
    entry_raw = pd.Timestamp(plan[entry_column])
    entry_utc = to_utc_series(canonical, pd.Series([entry_raw]), offset).iloc[0]
    signal_raw = as_timestamp(plan[signal_column]) if signal_column in plan.index else pd.NaT
    signal_utc = (
        to_utc_series(canonical, pd.Series([signal_raw]), offset).iloc[0]
        if not pd.isna(signal_raw)
        else pd.NaT
    )
    exit_raw = as_timestamp(result.get("exit_time"))
    exit_utc = (
        to_utc_series(canonical, pd.Series([exit_raw]), offset).iloc[0]
        if not pd.isna(exit_raw)
        else pd.NaT
    )
    hold_hours = (
        float((exit_utc - entry_utc).total_seconds() / 3600.0)
        if not pd.isna(exit_utc)
        else None
    )
    return {
        "candidate": candidate,
        "direction": text_value(plan, "direction"),
        "signal_time_broker_server": signal_raw,
        "signal_time_utc": signal_utc,
        "entry_time_broker_server": entry_raw,
        "entry_time_utc": entry_utc,
        "exit_time_broker_server": exit_raw,
        "exit_time_utc": exit_utc,
        "outcome_status": str(result.get("outcome_status", "UNKNOWN")),
        "exit_reason": str(result.get("exit_reason", "")),
        "risk_pips": numeric(plan, "risk_pips"),
        "reward_pips": reward_pips,
        "pnl_pips": (
            None if result.get("pnl_pips") is None or pd.isna(result.get("pnl_pips"))
            else float(result["pnl_pips"])
        ),
        "rr": rr,
        "entry_bid": numeric(plan, "entry_bid"),
        "stop_chart": numeric(plan, "stop_chart"),
        "target_chart": target_chart,
        "tp1_chart": tp1_chart,
        "tp2_chart": tp2_chart,
        "source_period": text_value(plan, "period"),
        "source_entry_index": (
            int(plan[index_column]) if index_column in plan.index and not pd.isna(plan[index_column])
            else None
        ),
        "hold_hours": hold_hours,
    }


def evaluate_candidate_ledgers(
    *,
    canonical: Any,
    reproduction: Any,
    offset: float,
    snapshots: dict[str, Path],
    engine_dirs: dict[str, Path],
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    m5 = reproduction.read_bars(snapshots["M5"])
    m15 = reproduction.read_bars(snapshots["M15"])
    rows: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}

    specs = {
        "btc4": {
            "candidate": CANDIDATES[0],
            "ledger": engine_dirs["btc4"] / "btc3_video_ema_entry_only_and_boundary_excluded.csv",
            "entry_column": "decision_time",
            "signal_column": "trigger_open_time",
            "index_column": "entry_m5_idx",
            "bars": m5,
            "minutes": 5,
            "simulation": "btc4",
        },
        "btc5": {
            "candidate": CANDIDATES[1],
            "ledger": engine_dirs["btc5"] / "btc5_candidate_trade_ledger.csv",
            "entry_column": "entry_time",
            "signal_column": "trigger_time",
            "index_column": "entry_idx",
            "bars": m5,
            "minutes": 5,
            "simulation": "simple",
        },
        "btc6": {
            "candidate": CANDIDATES[2],
            "ledger": engine_dirs["btc6"] / "btc6_m15_candidate_trade_ledger.csv",
            "entry_column": "entry_time",
            "signal_column": "trigger_time",
            "index_column": "entry_idx",
            "bars": m15,
            "minutes": 15,
            "simulation": "simple",
        },
        "btc7r": {
            "candidate": CANDIDATES[3],
            "ledger": engine_dirs["btc7r"] / "btc7r_candidate_trade_ledger.csv",
            "entry_column": "entry_time",
            "signal_column": "signal_time",
            "index_column": "entry_m5_idx",
            "bars": m5,
            "minutes": 5,
            "simulation": "simple",
        },
        "btc9r": {
            "candidate": CANDIDATES[4],
            "ledger": engine_dirs["btc9r"] / "btc9r_candidate_trade_ledger.csv",
            "entry_column": "entry_time",
            "signal_column": "signal_time",
            "index_column": "entry_m5_idx",
            "bars": m5,
            "minutes": 5,
            "simulation": "simple",
        },
    }

    for key, spec in specs.items():
        ledger = read_ledger(spec["ledger"])
        if ledger.empty:
            details[key] = {
                "candidate": spec["candidate"],
                "raw_planned_entries": 0,
                "fresh_planned_entries": 0,
                "resolved_trades": 0,
                "open_at_data_end": 0,
            }
            continue
        entry_column = str(spec["entry_column"])
        if entry_column not in ledger.columns:
            raise ValueError(f"{spec['candidate']} ledger is missing {entry_column}")
        ledger[entry_column] = pd.to_datetime(ledger[entry_column], errors="coerce")
        invalid = int(ledger[entry_column].isna().sum())
        if invalid:
            raise ValueError(f"{spec['candidate']} ledger has {invalid} invalid entry timestamps")
        ledger["_entry_time_utc"] = to_utc_series(canonical, ledger[entry_column], offset)
        fresh = ledger[ledger["_entry_time_utc"] > CUTOFF_UTC].copy()
        if key == "btc4" and not fresh.empty:
            fresh = fresh[pd.to_numeric(fresh["risk_pips"], errors="coerce") <= 400.0].copy()
        unexpected_periods = sorted(
            set(fresh.get("period", pd.Series(dtype=str)).dropna().astype(str))
            - {"POST_2026_ENTRY_ONLY"}
        )
        if unexpected_periods:
            raise ValueError(
                f"{spec['candidate']} fresh entries have unexpected source periods: {unexpected_periods}"
            )

        for _, plan in fresh.iterrows():
            if spec["simulation"] == "btc4":
                outcome = reproduction.simulate_btc4(plan, spec["bars"])
                reward = (
                    0.5 * float(plan["tp1_pips"]) + 0.5 * float(plan["tp2_pips"])
                    if "tp1_pips" in plan.index and "tp2_pips" in plan.index
                    else None
                )
                risk = numeric(plan, "risk_pips")
                rr = reward / risk if reward is not None and risk and risk > 0 else None
                target_chart = None
                tp1 = numeric(plan, "tp1")
                tp2 = numeric(plan, "tp2")
            else:
                outcome = reproduction.simulate_simple(
                    plan,
                    spec["bars"],
                    minutes=int(spec["minutes"]),
                    index_column=str(spec["index_column"]),
                )
                reward = numeric(plan, "reward_pips")
                rr = numeric(plan, "rr")
                target_chart = numeric(plan, "target_chart")
                tp1 = None
                tp2 = None
            rows.append(
                standard_trade_row(
                    candidate=str(spec["candidate"]),
                    plan=plan,
                    entry_column=entry_column,
                    signal_column=str(spec["signal_column"]),
                    index_column=str(spec["index_column"]),
                    canonical=canonical,
                    offset=offset,
                    result=outcome,
                    reward_pips=reward,
                    rr=rr,
                    target_chart=target_chart,
                    tp1_chart=tp1,
                    tp2_chart=tp2,
                )
            )
        candidate_rows = [row for row in rows if row["candidate"] == spec["candidate"]]
        details[key] = {
            "candidate": spec["candidate"],
            "raw_planned_entries": int(len(ledger)),
            "fresh_planned_entries": int(len(candidate_rows)),
            "resolved_trades": int(
                sum(row["outcome_status"] == "RESOLVED" for row in candidate_rows)
            ),
            "open_at_data_end": int(
                sum(row["outcome_status"] == "OPEN_AT_DATA_END" for row in candidate_rows)
            ),
        }

    trade_frame = pd.DataFrame(rows, columns=TRADE_COLUMNS)
    if not trade_frame.empty:
        trade_frame = trade_frame.sort_values(
            ["entry_time_utc", "candidate", "direction"]
        ).reset_index(drop=True)
    return trade_frame, details


def metric_values(frame: pd.DataFrame) -> dict[str, Any]:
    planned = int(len(frame))
    resolved = frame[frame["pnl_pips"].notna()].copy()
    open_count = int((frame["outcome_status"] == "OPEN_AT_DATA_END").sum()) if planned else 0
    if resolved.empty:
        return {
            "planned_entries": planned,
            "resolved_trades": 0,
            "open_at_data_end": open_count,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate_pct": None,
            "gross_profit_pips": 0.0,
            "gross_loss_pips": 0.0,
            "profit_factor": None,
            "total_pips": 0.0,
            "average_pips": None,
            "max_drawdown_pips": None,
        }
    resolved["pnl_pips"] = pd.to_numeric(resolved["pnl_pips"], errors="raise")
    resolved = resolved.sort_values(["entry_time_utc", "candidate"])
    positive = resolved["pnl_pips"] > 0
    negative = resolved["pnl_pips"] < 0
    zero = resolved["pnl_pips"] == 0
    gross_profit = float(resolved.loc[positive, "pnl_pips"].sum())
    gross_loss = float(-resolved.loc[negative, "pnl_pips"].sum())
    equity = resolved["pnl_pips"].cumsum()
    profit_factor: float | str | None
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = "Infinity"
    else:
        profit_factor = None
    return {
        "planned_entries": planned,
        "resolved_trades": int(len(resolved)),
        "open_at_data_end": open_count,
        "wins": int(positive.sum()),
        "losses": int(negative.sum()),
        "breakeven": int(zero.sum()),
        "win_rate_pct": float(positive.mean() * 100.0),
        "gross_profit_pips": gross_profit,
        "gross_loss_pips": gross_loss,
        "profit_factor": profit_factor,
        "total_pips": float(resolved["pnl_pips"].sum()),
        "average_pips": float(resolved["pnl_pips"].mean()),
        "max_drawdown_pips": float((equity.cummax() - equity).max()),
    }


def build_metric_frames(
    trades: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidate_rows = [
        {"scope": candidate, **metric_values(trades[trades["candidate"] == candidate])}
        for candidate in CANDIDATES
    ]
    candidate_rows.append({"scope": "ALL_FIVE_PORTFOLIO", **metric_values(trades)})
    candidate_metrics = pd.DataFrame(candidate_rows, columns=METRIC_COLUMNS)

    monthly_rows: list[dict[str, Any]] = []
    direction_rows: list[dict[str, Any]] = []
    if not trades.empty:
        working = trades.copy()
        working["entry_month_utc"] = pd.to_datetime(
            working["entry_time_utc"]
        ).dt.to_period("M").astype(str)
        for candidate in (*CANDIDATES, "ALL_FIVE_PORTFOLIO"):
            subset = working if candidate == "ALL_FIVE_PORTFOLIO" else working[working["candidate"] == candidate]
            for month, group in subset.groupby("entry_month_utc"):
                monthly_rows.append(
                    {"scope": candidate, "entry_month_utc": month, **metric_values(group)}
                )
            for direction, group in subset.groupby("direction"):
                direction_rows.append(
                    {"scope": candidate, "direction": direction, **metric_values(group)}
                )
    monthly = pd.DataFrame(
        monthly_rows,
        columns=["scope", "entry_month_utc", *METRIC_COLUMNS[1:]],
    )
    direction = pd.DataFrame(
        direction_rows,
        columns=["scope", "direction", *METRIC_COLUMNS[1:]],
    )
    return candidate_metrics, monthly, direction


def maximum_concurrent_resolved(trades: pd.DataFrame) -> int:
    events: list[tuple[pd.Timestamp, int]] = []
    resolved = trades.dropna(subset=["exit_time_utc"])
    for _, row in resolved.iterrows():
        events.append((pd.Timestamp(row["entry_time_utc"]), 1))
        events.append((pd.Timestamp(row["exit_time_utc"]), -1))
    events.sort(key=lambda item: (item[0], item[1]))
    current = 0
    maximum = 0
    for _, delta in events:
        current += delta
        maximum = max(maximum, current)
    return maximum


def candidate_commands(snapshot_dir: Path, engine_root: Path) -> dict[str, list[str]]:
    return {
        "btc4": [
            sys.executable,
            str(ENGINE_SCRIPTS["btc4"]),
            "--ema-applied-price",
            "close",
            "--data-dir",
            str(snapshot_dir),
            "--output-dir",
            str(engine_root / "btc4"),
            "--spread-usd",
            "30",
            "--pivot-bars",
            "3",
            "--lookback-bars",
            "500",
        ],
        "btc5": [
            sys.executable,
            str(ENGINE_SCRIPTS["btc5"]),
            "--m5",
            str(snapshot_dir / "btcusdsharp_m5.csv"),
            "--out",
            str(engine_root / "btc5"),
        ],
        "btc6": [
            sys.executable,
            str(ENGINE_SCRIPTS["btc6"]),
            "--m15",
            str(snapshot_dir / "btcusdsharp_m15.csv"),
            "--out",
            str(engine_root / "btc6"),
        ],
        "btc7r": [
            sys.executable,
            str(ENGINE_SCRIPTS["btc7r"]),
            "--m5",
            str(snapshot_dir / "btcusdsharp_m5.csv"),
            "--m15",
            str(snapshot_dir / "btcusdsharp_m15.csv"),
            "--h1",
            str(snapshot_dir / "btcusdsharp_h1.csv"),
            "--out",
            str(engine_root / "btc7r"),
        ],
        "btc9r": [
            sys.executable,
            str(ENGINE_SCRIPTS["btc9r"]),
            "--m5",
            str(snapshot_dir / "btcusdsharp_m5.csv"),
            "--m15",
            str(snapshot_dir / "btcusdsharp_m15.csv"),
            "--h1",
            str(snapshot_dir / "btcusdsharp_h1.csv"),
            "--d1",
            str(snapshot_dir / "btcusdsharp_d1.csv"),
            "--out",
            str(engine_root / "btc9r"),
        ],
    }


def report_text(summary: dict[str, Any], candidate_metrics: pd.DataFrame) -> str:
    lines = [
        "BTC FF02 frozen-five fresh-forward performance evaluation",
        "=" * 62,
        f"evaluation_complete: {summary['evaluation_complete']}",
        f"overall_status: {summary['overall_status']}",
        f"generated_at_utc: {summary['generated_at_utc']}",
        f"repository_branch: {summary['repository']['branch']}",
        f"repository_commit: {summary['repository']['commit']}",
        f"cutoff_utc_exclusive: {summary['cutoff_utc_exclusive']}",
        f"broker_utc_offset_hours: {summary['broker_clock'].get('selected_utc_offset_hours')}",
        "",
        "Time contract",
        "-------------",
        "Candidate engines run on immutable snapshots with original MT5 broker-server timestamps.",
        "Only entry/exit boundary filtering and reporting convert timestamps to UTC using the canonical main conversion.",
        "The exclusive rule is entry_time_utc > 2026-07-02 02:15:00.",
        "",
        "Metrics",
        "-------",
    ]
    for _, row in candidate_metrics.iterrows():
        lines.append(
            f"{row['scope']}: planned={row['planned_entries']} resolved={row['resolved_trades']} "
            f"open={row['open_at_data_end']} wins={row['wins']} losses={row['losses']} "
            f"WR={row['win_rate_pct']} PF={row['profit_factor']} "
            f"pips={row['total_pips']} DD={row['max_drawdown_pips']}"
        )
    lines.extend(
        [
            "",
            f"maximum_simultaneous_resolved_positions: {summary['portfolio']['maximum_simultaneous_resolved_positions']}",
            f"exact_unique_fresh_entry_times: {summary['portfolio']['exact_unique_fresh_entry_times']}",
            "",
            "Safety",
            "------",
            "Frozen candidate engines were called without changing conditions, thresholds, TP, SL, spread, pip or overlap rules.",
            "Source CSV files were not modified. Stable internal snapshots were used and deleted after evaluation.",
            "No lot design, monetary DD, collector, M7C, M8C, GOLD, Discord, MT5 order, live-ready or final-signal action was performed.",
            "",
            "STOP: Upload 99_UPLOAD_PACKAGE.zip for review. Do not proceed to another stage automatically.",
        ]
    )
    if summary.get("fatal_error"):
        lines.extend(["", f"fatal_error: {summary['fatal_error']}"])
    return "\n".join(lines) + "\n"


def read_me_text(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "BTC ML V1 / FF02 frozen-five fresh-forward performance",
            "=" * 60,
            f"generated_at_utc: {summary['generated_at_utc']}",
            f"repository_branch: {summary['repository']['branch']}",
            f"repository_commit: {summary['repository']['commit']}",
            f"overall_status: {summary['overall_status']}",
            "",
            "Upload only 99_UPLOAD_PACKAGE.zip to ChatGPT.",
            "",
            "Public files:",
            "01_fresh_forward_summary.json",
            "02_fresh_forward_report.txt",
            "03_fresh_forward_trade_ledger.csv",
            "04_candidate_metrics.csv",
            "05_monthly_metrics.csv",
            "06_direction_metrics.csv",
            "07_input_manifest.csv",
            "08_candidate_engine_manifest.csv",
            "",
            "OPEN_AT_DATA_END entries are not counted as wins or losses.",
            "Exact-time overlaps are not deduplicated because the frozen portfolio has no global one-position cap.",
            "No raw or snapshot candle CSV is included in the ZIP.",
            "",
            "Stop after upload. Results do not authorize live trading, lots, Discord or MT5 orders.",
        ]
    ) + "\n"


def write_csv(frame: pd.DataFrame, path: Path, columns: list[str] | None = None) -> None:
    output = frame.copy()
    if columns is not None:
        output = output.reindex(columns=columns)
    for column in output.columns:
        if pd.api.types.is_datetime64_any_dtype(output[column]):
            output[column] = output[column].dt.strftime("%Y-%m-%d %H:%M:%S")
    output.to_csv(path, index=False, encoding="utf-8-sig")


def replace_latest(archive_dir: Path, latest_dir: Path, names: Sequence[str]) -> None:
    temporary = latest_dir.parent / f"LATEST.__new__.{os.getpid()}"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True, exist_ok=False)
    for name in names:
        shutil.copy2(archive_dir / name, temporary / name)
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    os.replace(temporary, latest_dir)


def write_public_outputs(
    *,
    archive_dir: Path,
    output_root: Path,
    summary: dict[str, Any],
    trades: pd.DataFrame,
    candidate_metrics: pd.DataFrame,
    monthly_metrics: pd.DataFrame,
    direction_metrics: pd.DataFrame,
    input_manifest: pd.DataFrame,
    engine_manifest: pd.DataFrame,
) -> dict[str, str]:
    files = {
        "00_READ_ME_FIRST.txt": read_me_text(summary),
        "01_fresh_forward_summary.json": json.dumps(
            clean_json(summary), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
        )
        + "\n",
        "02_fresh_forward_report.txt": report_text(summary, candidate_metrics),
    }
    for name, text in files.items():
        (archive_dir / name).write_text(text, encoding="utf-8")
    write_csv(trades, archive_dir / "03_fresh_forward_trade_ledger.csv", TRADE_COLUMNS)
    write_csv(candidate_metrics, archive_dir / "04_candidate_metrics.csv", METRIC_COLUMNS)
    write_csv(monthly_metrics, archive_dir / "05_monthly_metrics.csv")
    write_csv(direction_metrics, archive_dir / "06_direction_metrics.csv")
    write_csv(input_manifest, archive_dir / "07_input_manifest.csv")
    write_csv(engine_manifest, archive_dir / "08_candidate_engine_manifest.csv")

    package = archive_dir / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in PUBLIC_FILES:
            archive.write(archive_dir / name, name)
    with zipfile.ZipFile(package, "r") as archive:
        names = archive.namelist()
        if names != list(PUBLIC_FILES):
            raise RuntimeError(f"upload package entries mismatch: {names}")

    latest_dir = output_root / "LATEST"
    latest_names = [*PUBLIC_FILES, package.name]
    replace_latest(archive_dir, latest_dir, latest_names)
    return {
        "output_root": str(output_root),
        "archive_dir": str(archive_dir),
        "latest_dir": str(latest_dir),
        "upload_package": str(latest_dir / package.name),
    }


def base_summary() -> dict[str, Any]:
    return {
        "schema_version": "btc_ff02_frozen_five_fresh_forward_performance_v1",
        "stage": "BTC_FF02_FROZEN_FIVE_CANDIDATE_FRESH_FORWARD_PERFORMANCE_EVALUATION",
        "generated_at_utc": utc_now_text(),
        "repository": git_identity(),
        "cutoff_utc_exclusive": CUTOFF_UTC,
        "evaluation_complete": False,
        "overall_status": "BLOCKED_NOT_RUN",
        "fatal_error": "",
        "ff01_gate": {},
        "broker_clock": {},
        "time_contract": {
            "candidate_engine_input_time_domain": "RAW_MT5_BROKER_SERVER_WALL_CLOCK",
            "candidate_engine_inputs_are_utc_shifted": False,
            "utc_conversion_use": "fresh entry cutoff, exit reporting and metrics timestamps only",
            "latest_csv_row_contract": "CLOSED",
            "same_bar_order": "SL first except BTC4 after TP1 uses break-even first",
        },
        "portfolio_contract": {
            "aggregation": "one strategy trade per candidate signal",
            "exact_time_overlap_deduplication": False,
            "global_one_position_cap": False,
            "pip_contract": "$10 price movement = 1 pip",
            "spread_usd": 30,
            "lot_design": False,
            "monetary_drawdown": False,
        },
        "candidate_results": {},
        "portfolio": {
            "metrics": metric_values(pd.DataFrame(columns=TRADE_COLUMNS)),
            "exact_unique_fresh_entry_times": 0,
            "maximum_simultaneous_resolved_positions": 0,
        },
        "warnings": [],
        "safety": {
            "source_csv_modified": False,
            "stable_internal_snapshot_created": False,
            "snapshot_deleted_after_evaluation": False,
            "snapshot_csv_in_upload_zip": False,
            "candidate_conditions_changed": False,
            "thresholds_changed": False,
            "tp_sl_exit_changed": False,
            "spread_or_pip_changed": False,
            "overlap_policy_changed": False,
            "lot_design_executed": False,
            "monetary_dd_calculated": False,
            "new_candidate_search_executed": False,
            "btc10r_included": False,
            "collector_touched": False,
            "m7c_touched": False,
            "m8c_touched": False,
            "mochipoyo_branch_touched": False,
            "m10w24b_touched": False,
            "gold_touched": False,
            "discord_enabled": False,
            "mt5_orders_enabled": False,
            "live_ready": False,
            "final_signal": False,
        },
        "next_stage_authorized": False,
    }


def empty_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trades = pd.DataFrame(columns=TRADE_COLUMNS)
    candidate_metrics, monthly, direction = build_metric_frames(trades)
    return (
        trades,
        candidate_metrics,
        monthly,
        direction,
        pd.DataFrame(
            columns=[
                "source_path",
                "snapshot_path_internal",
                "source_size_bytes",
                "source_sha256_at_snapshot",
                "snapshot_sha256",
                "snapshot_attempts",
                "source_stable_during_snapshot",
                "timeframe",
                "rows",
                "first_time_broker_server",
                "latest_time_broker_server",
                "non_ascending_timestamp_count",
                "duplicate_timestamp_count",
                "first_time_utc",
                "latest_time_utc",
                "rows_strictly_after_cutoff_utc",
            ]
        ),
        pd.DataFrame(
            columns=[
                "engine_key",
                "candidate",
                "script_path",
                "script_sha256",
                "command",
                "returncode",
                "started_at_utc",
                "ended_at_utc",
                "elapsed_seconds",
                "stdout_path_internal",
                "stderr_path_internal",
                "stderr_excerpt",
                "raw_planned_entries",
                "fresh_planned_entries",
                "resolved_trades",
                "open_at_data_end",
            ]
        ),
    )


def run_evaluation(
    args: argparse.Namespace,
    archive_dir: Path,
) -> tuple[
    dict[str, Any],
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    summary = base_summary()
    if summary["repository"]["branch"] != EXPECTED_BRANCH:
        raise RuntimeError(
            f"wrong branch: {summary['repository']['branch']}; expected {EXPECTED_BRANCH}"
        )

    ff01_summary, source_paths = validate_ff01(Path(args.ff01_summary).expanduser().resolve())
    summary["ff01_gate"] = {
        "summary_path": str(Path(args.ff01_summary).expanduser().resolve()),
        "overall_status": ff01_summary.get("overall_status"),
        "generated_at_utc": ff01_summary.get("generated_at_utc"),
        "repository_commit": ff01_summary.get("repository", {}).get("commit"),
    }

    canonical = load_module("_btc_ff02_canonical_clock", CANONICAL_CLOCK_PY)
    reproduction = load_module("_btc_ff02_reproduction", REPRODUCTION_PY)

    internal_dir = archive_dir / "_internal"
    snapshot_dir = internal_dir / "snapshot"
    engine_root = internal_dir / "engine_raw"
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    snapshot_records: dict[str, dict[str, Any]] = {}
    snapshots: dict[str, Path] = {}
    frames: dict[str, pd.DataFrame] = {}
    input_rows: list[dict[str, Any]] = []
    engine_rows: list[dict[str, Any]] = []
    engine_details: dict[str, dict[str, Any]] = {}

    try:
        for timeframe in TIMEFRAMES:
            destination = snapshot_dir / f"btcusdsharp_{timeframe.lower()}.csv"
            record = stable_snapshot(source_paths[timeframe], destination)
            frame, manifest = read_bars_strict(destination, timeframe)
            snapshot_records[timeframe] = record
            snapshots[timeframe] = destination
            frames[timeframe] = frame
            input_rows.append({**record, **manifest})
        summary["safety"]["stable_internal_snapshot_created"] = True

        clock = infer_broker_clock(canonical, frames, ff01_summary)
        summary["broker_clock"] = clean_json(clock)
        offset = float(clock["selected_utc_offset_hours"])
        for row in input_rows:
            timeframe = str(row["timeframe"])
            frame = frames[timeframe]
            utc_times = to_utc_series(canonical, frame["time"], offset)
            row["first_time_utc"] = utc_times.iloc[0]
            row["latest_time_utc"] = utc_times.iloc[-1]
            row["rows_strictly_after_cutoff_utc"] = int((utc_times > CUTOFF_UTC).sum())

        commands = candidate_commands(snapshot_dir, engine_root)
        engine_dirs = {key: engine_root / key for key in commands}
        failures: list[str] = []
        for key, command in commands.items():
            script = ENGINE_SCRIPTS[key]
            result = run_command(command, engine_dirs[key])
            engine_row = {
                "engine_key": key,
                "candidate": {
                    "btc4": CANDIDATES[0],
                    "btc5": CANDIDATES[1],
                    "btc6": CANDIDATES[2],
                    "btc7r": CANDIDATES[3],
                    "btc9r": CANDIDATES[4],
                }[key],
                "script_path": str(script.relative_to(ROOT)),
                "script_sha256": sha256_file(script),
                **result,
            }
            engine_rows.append(engine_row)
            if result["returncode"] != 0:
                failures.append(
                    f"{engine_row['candidate']} returncode={result['returncode']}"
                )
        if failures:
            raise RuntimeError("candidate engine failure: " + "; ".join(failures))

        trades, engine_details = evaluate_candidate_ledgers(
            canonical=canonical,
            reproduction=reproduction,
            offset=offset,
            snapshots=snapshots,
            engine_dirs=engine_dirs,
        )
        candidate_metrics, monthly, direction = build_metric_frames(trades)
        detail_by_candidate = {
            value["candidate"]: value for value in engine_details.values()
        }
        for row in engine_rows:
            detail = detail_by_candidate.get(str(row["candidate"]), {})
            row.update(detail)

        summary["candidate_results"] = {
            candidate: clean_json(
                {
                    **metric_values(trades[trades["candidate"] == candidate]),
                    "status": (
                        "NO_FRESH_ENTRIES"
                        if len(trades[trades["candidate"] == candidate]) == 0
                        else "COMPLETE_WITH_OPEN_AT_DATA_END"
                        if (
                            trades[trades["candidate"] == candidate]["outcome_status"]
                            == "OPEN_AT_DATA_END"
                        ).any()
                        else "COMPLETE_RESOLVED"
                    ),
                }
            )
            for candidate in CANDIDATES
        }
        portfolio_metrics = metric_values(trades)
        summary["portfolio"] = {
            "metrics": clean_json(portfolio_metrics),
            "exact_unique_fresh_entry_times": int(
                trades["entry_time_utc"].nunique() if not trades.empty else 0
            ),
            "maximum_simultaneous_resolved_positions": maximum_concurrent_resolved(trades),
        }
        total_open = int(portfolio_metrics["open_at_data_end"])
        total_planned = int(portfolio_metrics["planned_entries"])
        summary["evaluation_complete"] = True
        if total_planned == 0:
            summary["overall_status"] = "COMPLETE_NO_FRESH_ENTRIES"
        elif total_open > 0:
            summary["overall_status"] = "COMPLETE_WITH_OPEN_AT_DATA_END"
        else:
            summary["overall_status"] = "COMPLETE_ALL_FRESH_ENTRIES_RESOLVED"

        return (
            summary,
            trades,
            candidate_metrics,
            monthly,
            direction,
            pd.DataFrame(input_rows),
            pd.DataFrame(engine_rows),
        )
    finally:
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
        summary["safety"]["snapshot_deleted_after_evaluation"] = not snapshot_dir.exists()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BTC FF02 frozen-five fresh-forward performance evaluation"
    )
    parser.add_argument("--ff01-summary", default=str(DEFAULT_FF01_SUMMARY))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_root = Path(args.output_root).expanduser().resolve()
    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f_UTC")
    archive_dir = output_root / "archive" / run_id
    archive_dir.mkdir(parents=True, exist_ok=False)

    try:
        (
            summary,
            trades,
            candidate_metrics,
            monthly,
            direction,
            input_manifest,
            engine_manifest,
        ) = run_evaluation(args, archive_dir)
        exit_code = 0
    except Exception as exc:
        summary = base_summary()
        summary["fatal_error"] = f"{type(exc).__name__}: {exc}"
        summary["overall_status"] = "BLOCKED_FATAL_EVALUATION_ERROR"
        (
            trades,
            candidate_metrics,
            monthly,
            direction,
            input_manifest,
            engine_manifest,
        ) = empty_frames()
        exit_code = 2

    written = write_public_outputs(
        archive_dir=archive_dir,
        output_root=output_root,
        summary=summary,
        trades=trades,
        candidate_metrics=candidate_metrics,
        monthly_metrics=monthly,
        direction_metrics=direction,
        input_manifest=input_manifest,
        engine_manifest=engine_manifest,
    )
    print(
        json.dumps(
            clean_json(
                {
                    "evaluation_complete": summary["evaluation_complete"],
                    "overall_status": summary["overall_status"],
                    **written,
                    "portfolio": summary["portfolio"],
                    "fatal_error": summary.get("fatal_error", ""),
                }
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
