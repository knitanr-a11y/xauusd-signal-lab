from __future__ import annotations

import argparse
import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from fresh_prospective_engine import clean_json_value, run_engine, write_json

OUTPUT_FILES = [
    "fresh_prospective_candidate_registry.csv",
    "fresh_prospective_parent_event_audit.csv",
    "fresh_prospective_candidate_summary.csv",
    "input_provenance.json",
    "fresh_prospective_summary.json",
    "LATEST_RUN_SUMMARY.txt",
    "FRESH_PROSPECTIVE_RUN_ERROR.txt",
]


def load_config(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def backup_existing_output(output_dir: Path) -> Path | None:
    if not output_dir.exists() or not any(output_dir.iterdir()):
        output_dir.mkdir(parents=True, exist_ok=True)
        return None
    backup_root = output_dir.parent / f"{output_dir.name}_backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = backup_root / stamp
    counter = 1
    while backup_dir.exists():
        backup_dir = backup_root / f"{stamp}_{counter:02d}"
        counter += 1
    shutil.move(str(output_dir), str(backup_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def dataframe_text(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(none)"
    display = frame.copy()
    return display.to_csv(index=False).rstrip()


def build_latest_summary(result: dict[str, Any], backup_dir: Path | None) -> str:
    candidates: pd.DataFrame = result["candidates"]
    parent_audit: pd.DataFrame = result["parent_audit"]
    candidate_summary: pd.DataFrame = result["candidate_summary"]
    resolved = int((candidates.get("resolution_state", pd.Series(dtype=str)) == "RESOLVED").sum())
    unresolved = int((candidates.get("resolution_state", pd.Series(dtype=str)) == "UNRESOLVED").sum())
    accepted_parent = int(
        (
            parent_audit.get("admission_state", pd.Series(dtype=str))
            == "ACCEPTED_PARENT_EVENT"
        ).sum()
    )
    suppressed_parent = int(
        parent_audit.get("admission_state", pd.Series(dtype=str))
        .astype(str)
        .str.startswith("SUPPRESSED")
        .sum()
    )
    lines = [
        "GOLD_ML_V1 FRESH PROSPECTIVE CONFIRMATION",
        f"status={result['status']}",
        f"observation_state={result['observation_state']}",
        f"cutoff_mt5_server_close={result['cutoff_mt5_server_close']}",
        f"candidate_rows={len(candidates)}",
        f"resolved_candidate_rows={resolved}",
        f"unresolved_candidate_rows={unresolved}",
        f"accepted_parent_events={accepted_parent}",
        f"suppressed_parent_events={suppressed_parent}",
        f"backup_dir={backup_dir if backup_dir else 'NONE'}",
        "candidate_rules=FROZEN",
        "retuning=FORBIDDEN_NOT_PERFORMED",
        "performance_gate=NOT_APPLICABLE_PROSPECTIVE_AUDIT_ONLY",
        "automatic_next_phase=FALSE",
        "live_ready=FALSE",
        "final_signal=FALSE",
        "mt5_order=FALSE",
        "discord=FALSE",
        "ai_api=FALSE",
        "live_hook=FALSE",
        "",
        "Candidate summary:",
        dataframe_text(candidate_summary),
        "",
        "Candidate registry:",
        dataframe_text(candidates),
        "",
        "Parent event audit:",
        dataframe_text(parent_audit),
        "",
        "Caveats:",
        "- Candidate generation is causal and does not use future exit information.",
        "- Resolved outcomes use only M1 bars already present at run time.",
        "- Unresolved candidates are preserved explicitly and are not counted as losses or wins.",
        "- Parent events suppressed by the frozen non-overlap rule remain in the audit output.",
        "- NO_CANDIDATE_YET is a valid observation, not a runner failure.",
        "- This run cannot authorize promotion, registration, Discord, MT5 orders or live activation.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(output_dir: Path, result: dict[str, Any], backup_dir: Path | None) -> None:
    candidates: pd.DataFrame = result["candidates"]
    parent_audit: pd.DataFrame = result["parent_audit"]
    candidate_summary: pd.DataFrame = result["candidate_summary"]

    candidates.to_csv(output_dir / "fresh_prospective_candidate_registry.csv", index=False)
    parent_audit.to_csv(output_dir / "fresh_prospective_parent_event_audit.csv", index=False)
    candidate_summary.to_csv(output_dir / "fresh_prospective_candidate_summary.csv", index=False)
    write_json(output_dir / "input_provenance.json", result["provenance"])
    summary_json = {
        key: value
        for key, value in result.items()
        if key not in {"candidates", "parent_audit", "candidate_summary", "provenance"}
    }
    summary_json["candidate_summary"] = candidate_summary.to_dict(orient="records")
    summary_json["candidate_rows"] = int(len(candidates))
    summary_json["parent_audit_rows"] = int(len(parent_audit))
    summary_json["backup_dir"] = str(backup_dir) if backup_dir else None
    write_json(output_dir / "fresh_prospective_summary.json", summary_json)
    (output_dir / "LATEST_RUN_SUMMARY.txt").write_text(
        build_latest_summary(result, backup_dir), encoding="utf-8"
    )
    (output_dir / "FRESH_PROSPECTIVE_RUN_ERROR.txt").write_text(
        "status=PASS\nerror=NONE\n", encoding="utf-8"
    )


def run(files_dir: Path, config_path: Path, output_dir: Path) -> int:
    backup_dir = backup_existing_output(output_dir)
    config = load_config(config_path)
    result = run_engine(files_dir, config)
    write_outputs(output_dir, result, backup_dir)

    candidate_rows = int(len(result["candidates"]))
    unresolved = int(
        (
            result["candidates"].get("resolution_state", pd.Series(dtype=str))
            == "UNRESOLVED"
        ).sum()
    )
    print("=" * 72)
    print("GOLD_ML_V1 FRESH PROSPECTIVE - RUN STATUS: PASS")
    print(f"Observation state: {result['observation_state']}")
    print(f"Candidate rows after cutoff: {candidate_rows}")
    print(f"Unresolved candidate rows: {unresolved}")
    print("No automatic next phase was performed.")
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    try:
        return run(args.files_dir.resolve(), args.config.resolve(), output_dir)
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        error = f"{type(exc).__name__}: {exc}"
        trace = traceback.format_exc()
        (output_dir / "FRESH_PROSPECTIVE_RUN_ERROR.txt").write_text(
            f"status=FAIL\nerror={error}\n\n{trace}", encoding="utf-8"
        )
        (output_dir / "LATEST_RUN_SUMMARY.txt").write_text(
            "GOLD_ML_V1 FRESH PROSPECTIVE CONFIRMATION\n"
            "status=FAIL\n"
            f"error={error}\n"
            "No candidate result is valid from this failed run.\n",
            encoding="utf-8",
        )
        print(f"[FAIL] {error}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
