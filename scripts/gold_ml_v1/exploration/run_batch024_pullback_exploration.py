from __future__ import annotations

import argparse
import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from batch024_pullback_engine import json_clean, run_exploration, sha256_file, write_json

OUTPUT_NAMES = [
    "exploration_attempt_registry.csv",
    "exploration_year_metrics.csv",
    "exploration_trade_registry.csv",
    "exploration_survivors.csv",
    "input_provenance.json",
    "exploration_summary.json",
    "LATEST_RUN_SUMMARY.txt",
    "EXPLORATION_RUN_ERROR.txt",
]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def backup_output(output_dir: Path) -> Path | None:
    if not output_dir.exists() or not any(output_dir.iterdir()):
        output_dir.mkdir(parents=True, exist_ok=True)
        return None
    root = output_dir.parent / f"{output_dir.name}_backups"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = root / stamp
    counter = 1
    while destination.exists():
        destination = root / f"{stamp}_{counter:02d}"
        counter += 1
    shutil.move(str(output_dir), str(destination))
    output_dir.mkdir(parents=True, exist_ok=True)
    return destination


def frame_text(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(none)"
    return frame.to_csv(index=False, date_format="%Y-%m-%d %H:%M:%S").rstrip()


def build_text_summary(
    result: dict[str, Any],
    config: dict[str, Any],
    config_path: Path,
    backup: Path | None,
) -> str:
    attempts: pd.DataFrame = result["attempt_registry"]
    survivors: pd.DataFrame = result["survivors"]
    years: pd.DataFrame = result["year_metrics"]
    trades: pd.DataFrame = result["trade_registry"]
    accepted = trades[trades.get("admission_state", pd.Series(dtype=str)) == "ACCEPTED"] if not trades.empty else trades
    resolved = accepted[accepted.get("resolution_state", pd.Series(dtype=str)) == "RESOLVED"] if not accepted.empty else accepted
    lines = [
        "GOLD_ML_V1 EXPLORATION BATCH024 — M15/H1 PULLBACK",
        "status=PASS",
        f"run_time_local={datetime.now().isoformat(timespec='seconds')}",
        f"config={config_path}",
        f"config_sha256={sha256_file(config_path)}",
        f"backup_dir={backup if backup else 'NONE'}",
        f"predeclared_attempted_cells={config['multiplicity_contract']['attempted_cells']}",
        f"attempt_registry_rows={len(attempts)}",
        f"decision_feature_rows={result['decision_rows']}",
        f"signal_audit_rows={len(trades)}",
        f"accepted_trade_rows={len(accepted)}",
        f"resolved_trade_rows={len(resolved)}",
        f"survivor_count={len(survivors)}",
        "existing_frozen_nine_modified=FALSE",
        "automatic_accumulation=FALSE",
        "automatic_promotion=FALSE",
        "new_candidate_status_for_all_gate_pass=RESEARCH_ONLY",
        "same_lineage_metric_pooling=FORBIDDEN_NOT_PERFORMED",
        "2023=EXPLORATION_ONLY",
        "2024=VALIDATION_ONLY_NO_RETUNE",
        "2025=FINAL_TEST_ONLY_NO_RETUNE",
        "2026=DIAGNOSTIC_ONLY_NEVER_RETUNE",
        "live_ready=FALSE",
        "final_signal=FALSE",
        "mt5_order=FALSE",
        "discord=FALSE",
        "ai_api=FALSE",
        "live_hook=FALSE",
        "",
        "All attempted cells:",
        frame_text(attempts),
        "",
        "All predeclared-gate survivors:",
        frame_text(survivors),
        "",
        "Year metrics for every cell:",
        frame_text(years),
        "",
        "Interpretation:",
        "- PASS means provenance validation and complete report generation succeeded.",
        "- A survivor count of zero is a valid completed exploration result.",
        "- Every attempted cell, failed gate and signal audit row is preserved.",
        "- No result from this batch is automatically added to the frozen nine.",
        "- Any later accumulation requires a separate explicit audit review and new authorization.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run(raw_dir: Path, config_path: Path, output_dir: Path) -> int:
    config = load_json(config_path)
    backup = backup_output(output_dir)
    result = run_exploration(raw_dir, config)

    attempts: pd.DataFrame = result["attempt_registry"]
    years: pd.DataFrame = result["year_metrics"]
    trades: pd.DataFrame = result["trade_registry"]
    survivors: pd.DataFrame = result["survivors"]

    attempts.to_csv(output_dir / "exploration_attempt_registry.csv", index=False)
    years.to_csv(output_dir / "exploration_year_metrics.csv", index=False)
    trades.to_csv(output_dir / "exploration_trade_registry.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
    survivors.to_csv(output_dir / "exploration_survivors.csv", index=False)

    provenance = {
        **result["provenance"],
        "status": "PASS",
        "run_time_local": datetime.now().isoformat(timespec="seconds"),
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "previous_output_backup": str(backup) if backup else None,
        "attempted_cells": int(len(attempts)),
        "audit_only": True,
    }
    write_json(output_dir / "input_provenance.json", provenance)

    summary = {
        "status": "PASS",
        "exit_code": 0,
        "phase": "EXPLORATION_BATCH024_M15_H1_PULLBACK",
        "audit_only": True,
        "predeclared_attempted_cells": int(config["multiplicity_contract"]["attempted_cells"]),
        "attempt_registry_rows": int(len(attempts)),
        "year_metric_rows": int(len(years)),
        "signal_audit_rows": int(len(trades)),
        "survivor_count": int(len(survivors)),
        "survivor_ids": survivors.get("candidate_id", pd.Series(dtype=str)).astype(str).tolist(),
        "candidate_status_counts": attempts["candidate_status"].value_counts(dropna=False).to_dict(),
        "gate_2023_counts": attempts["gate_2023"].value_counts(dropna=False).to_dict(),
        "gate_2024_counts": attempts["gate_2024"].value_counts(dropna=False).to_dict(),
        "gate_2025_counts": attempts["gate_2025"].value_counts(dropna=False).to_dict(),
        "existing_frozen_nine_modified": False,
        "automatic_accumulation": False,
        "automatic_promotion": False,
        "automatic_next_phase": None,
        "execution_switches": config["execution_switches"],
    }
    write_json(output_dir / "exploration_summary.json", json_clean(summary))
    (output_dir / "LATEST_RUN_SUMMARY.txt").write_text(
        build_text_summary(result, config, config_path, backup), encoding="utf-8"
    )
    (output_dir / "EXPLORATION_RUN_ERROR.txt").write_text(
        "status=PASS\nerror=NONE\n", encoding="utf-8"
    )

    missing = sorted(
        set(config["required_outputs"])
        - {path.name for path in output_dir.iterdir() if path.is_file()}
    )
    if missing:
        raise RuntimeError(f"Required exploration outputs missing: {missing}")

    print("=" * 72)
    print("GOLD_ML_V1 EXPLORATION BATCH024 - RUN STATUS: PASS")
    print(f"Attempted cells: {len(attempts)} / {config['multiplicity_contract']['attempted_cells']}")
    print(f"Survivors: {len(survivors)}")
    print("Existing frozen nine were not modified.")
    print("No automatic accumulation, promotion, live action or next phase was performed.")
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit-only Batch024 M15/H1 pullback exploration")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    try:
        return run(args.raw_dir.resolve(), args.config.resolve(), output_dir)
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        error = f"{type(exc).__name__}: {exc}"
        (output_dir / "EXPLORATION_RUN_ERROR.txt").write_text(
            f"status=FAIL\nerror={error}\n\n{traceback.format_exc()}", encoding="utf-8"
        )
        (output_dir / "LATEST_RUN_SUMMARY.txt").write_text(
            "GOLD_ML_V1 EXPLORATION BATCH024\n"
            "status=FAIL\n"
            f"error={error}\n"
            "No exploration result is valid from this failed run.\n"
            "Existing frozen nine were not modified.\n",
            encoding="utf-8",
        )
        print(f"[FAIL] {error}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
