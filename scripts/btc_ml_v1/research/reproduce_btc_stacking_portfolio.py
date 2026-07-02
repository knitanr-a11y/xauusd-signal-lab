from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_DIR = Path(__file__).resolve().parent
DEFAULT_REFERENCE = REPO_ROOT / "configs/btc_ml_v1/btc_stacking_reproduction_reference.json"

CANDIDATE_IDS = {
    "btc4": "BTC4_RISK_CAP_400",
    "btc5": "BTC5_TWO_PIVOT_P2_CLEAN_N_382_786",
    "btc6": "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886",
    "btc7r": "BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110",
    "btc9r": "BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_bars(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["time"] = pd.to_datetime(frame["time"])
    return frame.sort_values("time").drop_duplicates("time").reset_index(drop=True)


def validate_input(path: Path, expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing input: {path}"]
    actual_sha = sha256_file(path)
    if actual_sha != expected["sha256"]:
        errors.append(f"sha256 mismatch: {path.name}: {actual_sha} != {expected['sha256']}")
    frame = pd.read_csv(path, usecols=["time"])
    if len(frame) != int(expected["rows"]):
        errors.append(f"row mismatch: {path.name}: {len(frame)} != {expected['rows']}")
    first_time = str(pd.Timestamp(frame.iloc[0]["time"]))
    last_time = str(pd.Timestamp(frame.iloc[-1]["time"]))
    if first_time != expected["first_time"]:
        errors.append(f"first_time mismatch: {path.name}: {first_time} != {expected['first_time']}")
    if last_time != expected["last_time"]:
        errors.append(f"last_time mismatch: {path.name}: {last_time} != {expected['last_time']}")
    return errors


def run_command(command: list[str], *, cwd: Path, log_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(RESEARCH_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    log_path.write_text(
        "COMMAND\n"
        + " ".join(command)
        + "\n\nSTDOUT\n"
        + completed.stdout
        + "\nSTDERR\n"
        + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"candidate command failed ({completed.returncode}); see {log_path}")


def generate_candidates(
    *,
    python_executable: str,
    history_dir: Path,
    h4_warmup_csv: Path,
    output_dir: Path,
) -> dict[str, Path]:
    candidates_root = output_dir / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)

    btc4_input = output_dir / "_btc4_input"
    btc4_input.mkdir(parents=True, exist_ok=True)
    shutil.copy2(h4_warmup_csv, btc4_input / "btcusdsharp_h4.csv")
    shutil.copy2(history_dir / "btcusdsharp_m5.csv", btc4_input / "btcusdsharp_m5.csv")

    outputs = {key: candidates_root / key for key in CANDIDATE_IDS}
    for path in outputs.values():
        path.mkdir(parents=True, exist_ok=True)

    commands = {
        "btc4": [
            python_executable,
            str(RESEARCH_DIR / "run_btc3_video_ema_user_contract.py"),
            "--ema-applied-price",
            "close",
            "--data-dir",
            str(btc4_input),
            "--output-dir",
            str(outputs["btc4"]),
            "--spread-usd",
            "30",
            "--pivot-bars",
            "3",
            "--lookback-bars",
            "500",
        ],
        "btc5": [
            python_executable,
            str(RESEARCH_DIR / "btc5_video_5m_ema200_nwave_candidate.py"),
            "--m5",
            str(history_dir / "btcusdsharp_m5.csv"),
            "--out",
            str(outputs["btc5"]),
        ],
        "btc6": [
            python_executable,
            str(RESEARCH_DIR / "btc6_video_m15_ema200_nwave_candidate.py"),
            "--m15",
            str(history_dir / "btcusdsharp_m15.csv"),
            "--out",
            str(outputs["btc6"]),
        ],
        "btc7r": [
            python_executable,
            str(RESEARCH_DIR / "btc7r_m15_impulse_high_win_candidate.py"),
            "--m5",
            str(history_dir / "btcusdsharp_m5.csv"),
            "--m15",
            str(history_dir / "btcusdsharp_m15.csv"),
            "--h1",
            str(history_dir / "btcusdsharp_h1.csv"),
            "--out",
            str(outputs["btc7r"]),
        ],
        "btc9r": [
            python_executable,
            str(RESEARCH_DIR / "btc9r_m15_prevday_breakout_high_win_candidate.py"),
            "--m5",
            str(history_dir / "btcusdsharp_m5.csv"),
            "--m15",
            str(history_dir / "btcusdsharp_m15.csv"),
            "--h1",
            str(history_dir / "btcusdsharp_h1.csv"),
            "--d1",
            str(history_dir / "btcusdsharp_d1.csv"),
            "--out",
            str(outputs["btc9r"]),
        ],
    }
    for key, command in commands.items():
        run_command(command, cwd=REPO_ROOT, log_path=outputs[key] / "reproduction_command.log")
    return outputs


def simulate_simple(
    plan: pd.Series,
    bars: pd.DataFrame,
    *,
    minutes: int,
    index_column: str,
) -> dict[str, Any]:
    direction = str(plan["direction"])
    stop = float(plan["stop_chart"])
    target = float(plan["target_chart"])
    risk = float(plan["risk_pips"])
    reward = float(plan["reward_pips"])
    entry_time = pd.Timestamp(plan["entry_time"])
    for index in range(int(plan[index_column]), len(bars)):
        row = bars.iloc[index]
        stop_hit = float(row["low"]) <= stop if direction == "LONG" else float(row["high"]) >= stop
        target_hit = float(row["high"]) >= target if direction == "LONG" else float(row["low"]) <= target
        exit_time = pd.Timestamp(row["time"]) + pd.Timedelta(minutes=minutes)
        if stop_hit:
            return {
                "outcome_status": "RESOLVED",
                "exit_time": exit_time,
                "exit_reason": "SL",
                "pnl_pips": -risk,
            }
        if target_hit:
            return {
                "outcome_status": "RESOLVED",
                "exit_time": exit_time,
                "exit_reason": "TP",
                "pnl_pips": reward,
            }
    return {
        "outcome_status": "OPEN_AT_DATA_END",
        "exit_time": pd.NaT,
        "exit_reason": "OPEN",
        "pnl_pips": np.nan,
    }


def simulate_btc4(plan: pd.Series, m5: pd.DataFrame) -> dict[str, Any]:
    direction = str(plan["direction"])
    entry = float(plan["entry_bid"])
    spread = float(plan["spread_usd"])
    stop = float(plan["stop_chart"])
    tp1 = float(plan["tp1"])
    tp2 = float(plan["tp2"])
    partial = False

    for index in range(int(plan["entry_m5_idx"]), len(m5)):
        row = m5.iloc[index]
        high = float(row["high"])
        low = float(row["low"])
        exit_time = pd.Timestamp(row["time"]) + pd.Timedelta(minutes=5)
        if not partial:
            stop_hit = low <= stop if direction == "LONG" else high >= stop
            tp1_hit = high >= tp1 if direction == "LONG" else low <= tp1
            tp2_hit = high >= tp2 if direction == "LONG" else low <= tp2
            if stop_hit:
                return {
                    "outcome_status": "RESOLVED",
                    "exit_time": exit_time,
                    "exit_reason": "SL",
                    "pnl_pips": -float(plan["risk_pips"]),
                }
            if tp2_hit:
                pnl = (
                    0.5 * float(plan["tp1_net_usd"])
                    + 0.5 * float(plan["tp2_net_usd"])
                ) / 10.0
                return {
                    "outcome_status": "RESOLVED",
                    "exit_time": exit_time,
                    "exit_reason": "TP1_AND_TP2",
                    "pnl_pips": pnl,
                }
            if tp1_hit:
                partial = True
                break_even = entry + spread if direction == "LONG" else entry - spread
                break_even_hit = low <= break_even if direction == "LONG" else high >= break_even
                if break_even_hit:
                    pnl = 0.5 * float(plan["tp1_net_usd"]) / 10.0
                    return {
                        "outcome_status": "RESOLVED",
                        "exit_time": exit_time,
                        "exit_reason": "TP1_THEN_BE_SAME_M5",
                        "pnl_pips": pnl,
                    }
        else:
            break_even = entry + spread if direction == "LONG" else entry - spread
            break_even_hit = low <= break_even if direction == "LONG" else high >= break_even
            tp2_hit = high >= tp2 if direction == "LONG" else low <= tp2
            if break_even_hit:
                pnl = 0.5 * float(plan["tp1_net_usd"]) / 10.0
                return {
                    "outcome_status": "RESOLVED",
                    "exit_time": exit_time,
                    "exit_reason": "TP1_THEN_BE",
                    "pnl_pips": pnl,
                }
            if tp2_hit:
                pnl = (
                    0.5 * float(plan["tp1_net_usd"])
                    + 0.5 * float(plan["tp2_net_usd"])
                ) / 10.0
                return {
                    "outcome_status": "RESOLVED",
                    "exit_time": exit_time,
                    "exit_reason": "TP2",
                    "pnl_pips": pnl,
                }
    return {
        "outcome_status": "OPEN_AT_DATA_END",
        "exit_time": pd.NaT,
        "exit_reason": "OPEN",
        "pnl_pips": np.nan,
    }


def standard_rows(
    frame: pd.DataFrame,
    *,
    candidate: str,
    entry_time_column: str,
    sample: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate": candidate,
            "entry_time": pd.to_datetime(frame[entry_time_column]),
            "exit_time": pd.to_datetime(frame["exit_time"]),
            "direction": frame["direction"],
            "risk_pips": pd.to_numeric(frame["risk_pips"]),
            "pnl_pips": pd.to_numeric(frame["pnl_pips"]),
            "exit_reason": frame["exit_reason"],
            "sample": sample,
        }
    )


def load_and_resolve(
    outputs: dict[str, Path],
    *,
    history_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    m5 = read_bars(history_dir / "btcusdsharp_m5.csv")
    m15 = read_bars(history_dir / "btcusdsharp_m15.csv")
    planned: dict[str, pd.DataFrame] = {}
    pre_frames: list[pd.DataFrame] = []
    post_rows: list[dict[str, Any]] = []

    btc4_pre = pd.read_csv(outputs["btc4"] / "btc3_video_ema_trade_ledger_pre2026.csv")
    btc4_pre = btc4_pre[
        (btc4_pre["outcome_status"] == "RESOLVED") & (btc4_pre["risk_pips"] <= 400)
    ].copy()
    pre_frames.append(
        standard_rows(
            btc4_pre,
            candidate=CANDIDATE_IDS["btc4"],
            entry_time_column="decision_time",
            sample="PRE2026",
        )
    )
    btc4_post = pd.read_csv(
        outputs["btc4"] / "btc3_video_ema_entry_only_and_boundary_excluded.csv"
    )
    btc4_post = btc4_post[
        (btc4_post["period"] == "POST_2026_ENTRY_ONLY")
        & (btc4_post["risk_pips"] <= 400)
    ].copy()
    planned["btc4_pre"] = btc4_pre
    planned["btc4_post"] = btc4_post
    for _, plan in btc4_post.iterrows():
        result = simulate_btc4(plan, m5)
        post_rows.append(
            {
                "candidate": CANDIDATE_IDS["btc4"],
                "entry_time": pd.Timestamp(plan["decision_time"]),
                "direction": plan["direction"],
                "risk_pips": float(plan["risk_pips"]),
                "sample": "POST2026",
                **result,
            }
        )

    specs = {
        "btc5": (
            outputs["btc5"] / "btc5_candidate_trade_ledger.csv",
            m5,
            5,
            "entry_idx",
        ),
        "btc6": (
            outputs["btc6"] / "btc6_m15_candidate_trade_ledger.csv",
            m15,
            15,
            "entry_idx",
        ),
        "btc7r": (
            outputs["btc7r"] / "btc7r_candidate_trade_ledger.csv",
            m5,
            5,
            "entry_m5_idx",
        ),
        "btc9r": (
            outputs["btc9r"] / "btc9r_candidate_trade_ledger.csv",
            m5,
            5,
            "entry_m5_idx",
        ),
    }
    for key, (path, bars, minutes, index_column) in specs.items():
        ledger = pd.read_csv(path)
        planned[key] = ledger
        resolved = ledger[
            (ledger["outcome_status"] == "RESOLVED")
            & ledger["period"].isin(["DISCOVERY", "VALIDATION", "TRAIN", "DEV"])
        ].copy()
        pre_frames.append(
            standard_rows(
                resolved,
                candidate=CANDIDATE_IDS[key],
                entry_time_column="entry_time",
                sample="PRE2026",
            )
        )
        post = ledger[ledger["period"] == "POST_2026_ENTRY_ONLY"].copy()
        for _, plan in post.iterrows():
            result = simulate_simple(
                plan,
                bars,
                minutes=minutes,
                index_column=index_column,
            )
            post_rows.append(
                {
                    "candidate": CANDIDATE_IDS[key],
                    "entry_time": pd.Timestamp(plan["entry_time"]),
                    "direction": plan["direction"],
                    "risk_pips": float(plan["risk_pips"]),
                    "sample": "POST2026",
                    **result,
                }
            )

    return pd.concat(pre_frames, ignore_index=True), pd.DataFrame(post_rows), planned


def metrics(frame: pd.DataFrame) -> dict[str, Any]:
    resolved = frame[frame["pnl_pips"].notna()].sort_values(
        ["entry_time", "candidate"]
    ).copy()
    if resolved.empty:
        return {"trades": 0}
    gross_profit = float(resolved.loc[resolved["pnl_pips"] > 0, "pnl_pips"].sum())
    gross_loss = float(-resolved.loc[resolved["pnl_pips"] < 0, "pnl_pips"].sum())
    equity = resolved["pnl_pips"].cumsum()
    return {
        "trades": int(len(resolved)),
        "wins": int((resolved["pnl_pips"] > 0).sum()),
        "losses": int((resolved["pnl_pips"] < 0).sum()),
        "win_rate_pct": float((resolved["pnl_pips"] > 0).mean() * 100.0),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else math.inf,
        "total_pips": float(resolved["pnl_pips"].sum()),
        "average_pips": float(resolved["pnl_pips"].mean()),
        "max_drawdown_pips": float((equity.cummax() - equity).max()),
    }


def entry_fingerprint(frame: pd.DataFrame, *, time_column: str) -> str:
    columns = [time_column, "direction", "risk_pips"]
    if "reward_pips" in frame.columns:
        columns.append("reward_pips")
    elif "tp1_pips" in frame.columns and "tp2_pips" in frame.columns:
        columns.extend(["tp1_pips", "tp2_pips"])
    selected = frame[columns].copy()
    selected[time_column] = pd.to_datetime(selected[time_column]).dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    for column in columns:
        if column not in (time_column, "direction"):
            selected[column] = pd.to_numeric(selected[column]).round(6)
    selected = selected.sort_values([time_column, "direction"])
    text = "\n".join(
        "|".join(map(str, row))
        for row in selected.itertuples(index=False, name=None)
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare_metrics(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    tolerance: float = 1e-5,
) -> list[str]:
    errors: list[str] = []
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if isinstance(expected_value, int):
            if int(actual_value) != expected_value:
                errors.append(f"{key}: {actual_value} != {expected_value}")
        elif not math.isclose(
            float(actual_value),
            float(expected_value),
            rel_tol=tolerance,
            abs_tol=tolerance,
        ):
            errors.append(f"{key}: {actual_value} != {expected_value}")
    return errors


def maximum_concurrent(frame: pd.DataFrame) -> int:
    events: list[tuple[pd.Timestamp, int]] = []
    for _, row in frame.dropna(subset=["exit_time"]).iterrows():
        events.append((pd.Timestamp(row["entry_time"]), 1))
        events.append((pd.Timestamp(row["exit_time"]), -1))
    events.sort(key=lambda item: (item[0], item[1]))
    current = 0
    maximum = 0
    for _, delta in events:
        current += delta
        maximum = max(maximum, current)
    return maximum


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-dir", required=True)
    parser.add_argument("--h4-warmup-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reference-config", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--skip-input-hash-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    history_dir = Path(args.history_dir).expanduser().resolve()
    h4_warmup_csv = Path(args.h4_warmup_csv).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reference = json.loads(Path(args.reference_config).read_text(encoding="utf-8"))

    input_errors: list[str] = []
    if not args.skip_input_hash_check:
        for filename in (
            "btcusdsharp_m5.csv",
            "btcusdsharp_m15.csv",
            "btcusdsharp_h1.csv",
            "btcusdsharp_d1.csv",
        ):
            input_errors.extend(
                validate_input(history_dir / filename, reference["required_csv"][filename])
            )
        input_errors.extend(
            validate_input(
                h4_warmup_csv,
                reference["required_csv"]["btcusdsharp_h4_warmup.csv"],
            )
        )
        if input_errors:
            raise SystemExit("reference input validation failed:\n" + "\n".join(input_errors))

    outputs = generate_candidates(
        python_executable=args.python_executable,
        history_dir=history_dir,
        h4_warmup_csv=h4_warmup_csv,
        output_dir=output_dir,
    )
    pre, post, planned = load_and_resolve(outputs, history_dir=history_dir)
    all_trades = pd.concat([pre, post], ignore_index=True)

    pre.to_csv(output_dir / "btc_stacking_pre2026_trade_ledger.csv", index=False)
    post.to_csv(output_dir / "btc_stacking_post2026_trade_ledger.csv", index=False)
    all_trades.to_csv(output_dir / "btc_stacking_all_evaluated_trade_ledger.csv", index=False)

    summaries = {
        "pre2026": metrics(pre),
        "post2026": metrics(post),
        "all": metrics(all_trades),
    }
    fingerprints = {
        "BTC4_RISK_CAP_400_PRE2026": entry_fingerprint(
            planned["btc4_pre"], time_column="decision_time"
        ),
        "BTC4_RISK_CAP_400_POST2026": entry_fingerprint(
            planned["btc4_post"], time_column="decision_time"
        ),
        "BTC5_ALL_PLANNED": entry_fingerprint(
            planned["btc5"], time_column="entry_time"
        ),
        "BTC6_ALL_PLANNED": entry_fingerprint(
            planned["btc6"], time_column="entry_time"
        ),
        "BTC7R_ALL_PLANNED": entry_fingerprint(
            planned["btc7r"], time_column="entry_time"
        ),
        "BTC9R_ALL_PLANNED": entry_fingerprint(
            planned["btc9r"], time_column="entry_time"
        ),
    }

    metric_errors: dict[str, list[str]] = {}
    for sample in ("pre2026", "post2026", "all"):
        errors = compare_metrics(
            summaries[sample], reference["expected_portfolio"][sample]
        )
        if errors:
            metric_errors[sample] = errors
    fingerprint_errors = {
        key: {
            "actual": value,
            "expected": reference["candidate_entry_fingerprints"].get(key),
        }
        for key, value in fingerprints.items()
        if value != reference["candidate_entry_fingerprints"].get(key)
    }

    report = {
        "stage": "BTC_STACKING_REPRODUCTION_AUDIT",
        "reference_id": reference["reference_id"],
        "input_hash_check_skipped": bool(args.skip_input_hash_check),
        "summaries": summaries,
        "entry_fingerprints": fingerprints,
        "exact_unique_entry_times": {
            "pre2026": int(pre["entry_time"].nunique()),
            "post2026": int(post["entry_time"].nunique()),
            "all": int(all_trades["entry_time"].nunique()),
        },
        "maximum_simultaneous_positions": maximum_concurrent(all_trades),
        "unresolved_post2026": int(post["pnl_pips"].isna().sum()),
        "metric_errors": metric_errors,
        "fingerprint_errors": fingerprint_errors,
        "reproduction_pass": (
            not metric_errors
            and not fingerprint_errors
            and not post["pnl_pips"].isna().any()
        ),
        "orders_enabled": False,
        "discord_enabled": False,
        "live_ready": False,
        "final_signal": False,
    }
    (output_dir / "btc_stacking_reproduction_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["reproduction_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
