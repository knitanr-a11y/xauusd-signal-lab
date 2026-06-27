from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from final_challenger_checks import verify
from final_challenger_metrics import COLS, component_metric, metric

EXIT_OK, EXIT_INPUT, EXIT_PARITY = 0, 2, 3


def write_outputs(output_dir: Path, frames: dict[int, pd.DataFrame]) -> None:
    normalized = output_dir / "normalized_final"
    normalized.mkdir(parents=True, exist_ok=True)
    annual, components = [], []
    for year, frame in frames.items():
        export = frame[COLS].copy()
        export["decision_time"] = export["decision_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        export["exit_time"] = export["exit_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        export.to_csv(normalized / f"final_research_challenger_{year}.csv", index=False, lineterminator="\n")
        annual.append({"year": year, **metric(frame)})
        for comp, item in component_metric(frame).items():
            components.append({"year": year, "comp": comp, **item})
    pd.DataFrame(annual).to_csv(output_dir / "final_metrics_by_year.csv", index=False, lineterminator="\n")
    pd.DataFrame(components).to_csv(output_dir / "final_component_metrics.csv", index=False, lineterminator="\n")


def run(artifact_dir: Path, manifest_path: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks, frames = verify(artifact_dir, manifest)
    write_outputs(output_dir, frames)
    passed = all(check["passed"] for check in checks)
    report = {
        "status": "PASS" if passed else "FAIL",
        "package_id": manifest["package_id"],
        "source_of_truth_order": manifest["source_of_truth_order"],
        "checks": checks,
        "controls": manifest["controls"],
    }
    (output_dir / "parity_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    print(json.dumps({"status": report["status"], "output_dir": str(output_dir)}, ensure_ascii=False))
    return EXIT_OK if passed else EXIT_PARITY


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[3]
    package = root / "config/gold_ml_v1/research_challenger/final_20260627"
    parser = argparse.ArgumentParser(description="Verify frozen final GML1 research challenger artifacts")
    parser.add_argument("--artifact-dir", type=Path, default=package / "artifacts")
    parser.add_argument("--manifest", type=Path, default=package / "manifest.json")
    parser.add_argument("--output-dir", type=Path, default=root / "outputs/gold_ml_v1/research_challenger_final_replay")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run(args.artifact_dir.resolve(), args.manifest.resolve(), args.output_dir.resolve())
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "input_error.txt").write_text(str(exc), encoding="utf-8", newline="\n")
        print(str(exc), file=sys.stderr)
        return EXIT_INPUT


if __name__ == "__main__":
    raise SystemExit(main())
