from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from batch024_pullback_engine import run_exploration, sha256_file


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def backup_output(output_dir: Path) -> Path | None:
    if not output_dir.exists() or not any(output_dir.iterdir()):
        output_dir.mkdir(parents=True, exist_ok=True)
        return None
    backup_root = output_dir.parent / f"{output_dir.name}_backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = backup_root / stamp
    suffix = 1
    while destination.exists():
        destination = backup_root / f"{stamp}_{suffix:02d}"
        suffix += 1
    shutil.move(str(output_dir), str(destination))
    output_dir.mkdir(parents=True, exist_ok=True)
    return destination


def write_canonical_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(
        path,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
        float_format="%.12g",
        na_rep="",
        lineterminator="\n",
    )


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(
    raw_dir: Path,
    config_path: Path,
    frozen_result_path: Path,
    output_dir: Path,
) -> int:
    config = load_json(config_path)
    frozen = load_json(frozen_result_path)
    backup = backup_output(output_dir)
    result = run_exploration(raw_dir, config)
    outputs = {
        "exploration_attempt_registry.csv": result["attempt_registry"],
        "exploration_year_metrics.csv": result["year_metrics"],
        "exploration_trade_registry.csv": result["trade_registry"],
        "exploration_survivors.csv": result["survivors"],
    }
    actual_hashes: dict[str, str] = {}
    for filename, frame in outputs.items():
        path = output_dir / filename
        write_canonical_csv(frame, path)
        actual_hashes[filename] = file_hash(path)

    expected_hashes = frozen["canonical_output_hashes"]
    mismatches = {
        filename: {"expected": expected_hashes.get(filename), "actual": actual}
        for filename, actual in actual_hashes.items()
        if expected_hashes.get(filename) != actual
    }
    count_checks = {
        "attempted_cells": {"expected": int(frozen["attempted_cells"]), "actual": int(len(result["attempt_registry"]))},
        "year_metric_rows": {"expected": int(frozen["year_metric_rows"]), "actual": int(len(result["year_metrics"]))},
        "signal_audit_rows": {"expected": int(frozen["signal_audit_rows"]), "actual": int(len(result["trade_registry"]))},
        "survivor_count": {"expected": int(frozen["survivor_count"]), "actual": int(len(result["survivors"]))},
    }
    count_mismatches = {
        key: value for key, value in count_checks.items()
        if value["expected"] != value["actual"]
    }
    status = "PASS" if not mismatches and not count_mismatches else "FAIL"
    summary = {
        "status": status,
        "phase": "BATCH024_LOCAL_REPRODUCTION_AGAINST_ASSISTANT_FROZEN_RESULT",
        "run_time_local": datetime.now().isoformat(timespec="seconds"),
        "raw_dir": str(raw_dir),
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "frozen_result": str(frozen_result_path),
        "frozen_result_sha256": sha256_file(frozen_result_path),
        "previous_output_backup": str(backup) if backup else None,
        "time_contract": frozen["time_contract"],
        "canonical_float_format": "%.12g",
        "actual_hashes": actual_hashes,
        "expected_hashes": expected_hashes,
        "hash_mismatches": mismatches,
        "count_checks": count_checks,
        "count_mismatches": count_mismatches,
        "existing_frozen_nine_modified": False,
        "candidate_selection_performed": False,
        "rescue_tuning_performed": False,
        "audit_only": True,
    }
    (output_dir / "local_reproduction_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "GOLD_ML_V1 BATCH024 LOCAL REPRODUCTION",
        f"status={status}",
        f"run_time_local={summary['run_time_local']}",
        "time_column=BAR_OPEN_TIME",
        "M1_close=time+1 minute",
        "M15_close=time+15 minutes",
        "H1_close=time+1 hour",
        "canonical_float_format=%.12g",
        f"attempted_cells={count_checks['attempted_cells']['actual']}",
        f"year_metric_rows={count_checks['year_metric_rows']['actual']}",
        f"signal_audit_rows={count_checks['signal_audit_rows']['actual']}",
        f"survivor_count={count_checks['survivor_count']['actual']}",
        f"hash_mismatch_count={len(mismatches)}",
        f"count_mismatch_count={len(count_mismatches)}",
        "candidate_selection_performed=FALSE",
        "existing_frozen_nine_modified=FALSE",
        "automatic_promotion=FALSE",
        "",
        "Canonical hashes:",
    ]
    for filename in sorted(actual_hashes):
        lines.append(
            f"{filename} expected={expected_hashes.get(filename)} actual={actual_hashes[filename]} "
            f"match={str(expected_hashes.get(filename) == actual_hashes[filename]).upper()}"
        )
    if mismatches or count_mismatches:
        lines.extend([
            "",
            "FAIL_CLOSED: local outputs do not reproduce the assistant-frozen result.",
            "Do not use this local result as a candidate result.",
        ])
    else:
        lines.extend([
            "",
            "PASS: local outputs exactly reproduce the assistant-frozen result.",
            "The frozen result remains zero survivors; no rescue tuning is allowed.",
        ])
    (output_dir / "LATEST_RUN_SUMMARY.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "LOCAL_REPRODUCTION_ERROR.txt").write_text(
        "status=PASS\nerror=NONE\n" if status == "PASS" else
        "status=FAIL\nerror=FROZEN_RESULT_MISMATCH\n",
        encoding="utf-8",
    )
    if status != "PASS":
        raise RuntimeError(
            f"Frozen-result reproduction mismatch: hash={len(mismatches)} count={len(count_mismatches)}"
        )
    print("=" * 72)
    print("GOLD_ML_V1 BATCH024 LOCAL REPRODUCTION - PASS")
    print("All canonical output hashes match the assistant-frozen result.")
    print("Survivors: 0. No candidate was added or promoted.")
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduce Batch024 and compare against assistant-frozen hashes")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--frozen-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    try:
        return run(args.raw_dir.resolve(), args.config.resolve(), args.frozen_result.resolve(), output_dir)
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        error = f"{type(exc).__name__}: {exc}"
        (output_dir / "LOCAL_REPRODUCTION_ERROR.txt").write_text(
            f"status=FAIL\nerror={error}\n\n{traceback.format_exc()}", encoding="utf-8"
        )
        if not (output_dir / "LATEST_RUN_SUMMARY.txt").exists():
            (output_dir / "LATEST_RUN_SUMMARY.txt").write_text(
                "GOLD_ML_V1 BATCH024 LOCAL REPRODUCTION\n"
                "status=FAIL\n"
                f"error={error}\n"
                "No local result is valid from this failed run.\n",
                encoding="utf-8",
            )
        print(f"[FAIL] {error}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
